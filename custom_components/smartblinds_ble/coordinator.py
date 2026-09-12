"""Data update coordinator for a single Tilt roller shade.

Each shade is polled over BLE by opening a brief, on-demand session through the
vendored ``smartblinds_ble.tilt`` library. The BLE client is built from a live
Home Assistant ``BLEDevice`` each session, so connections route transparently
through whichever ESPHome Bluetooth Proxy is in range. Sessions are short and
serialized (never persistent) to spare the solar battery and avoid locking the
shade away from the Tilt app.
"""

from __future__ import annotations

import logging

from bleak import BleakClient
from bleak.exc import BleakError
from bleak_retry_connector import establish_connection
from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from smartblinds_ble.tilt import (
    PositionVerificationPending,
    ShadeStatus,
    TiltProtocolError,
    TiltShadeClient,
)

from .const import (
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    MANUFACTURER,
    MODEL,
    POSITION_TRAVEL_TIME,
)

_LOGGER = logging.getLogger(__name__)

type SmartBlindsConfigEntry = ConfigEntry[SmartBlindsCoordinator]


class SmartBlindsCoordinator(DataUpdateCoordinator[ShadeStatus]):
    """Poll one Tilt shade and issue position writes on demand."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        address: str,
        name: str,
        pairing_key: bytes,
    ) -> None:
        super().__init__(hass, _LOGGER, name=name, update_interval=DEFAULT_POLL_INTERVAL)
        self.address = address
        self.device_name = name
        self._pairing_key = pairing_key
        self._arrival_unsub: CALLBACK_TYPE | None = None
        # Single shared device identity so cover + sensor name the device consistently
        # regardless of which platform registers it first.
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, address)},
            connections={(CONNECTION_BLUETOOTH, address)},
            name=name,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    def _make_client(self, *, allow_position_writes: bool) -> TiltShadeClient:
        """Build a client that resolves a fresh proxy-routed BLEDevice per session."""
        address = self.address
        hass = self.hass
        name = self.device_name

        async def factory(_address: str, *, timeout: float, **_kwargs: object) -> BleakClient:
            device = bluetooth.async_ble_device_from_address(hass, address, connectable=True)
            if device is None:
                raise BleakError(f"{address} is not currently reachable over BLE")
            # establish_connection() rather than BleakClient.connect(): it retries
            # through whichever ESPHome proxy is in range and, crucially, releases
            # the proxy's connection slot when an attempt fails. A raw connect()
            # leaks slots on failure, which is how a marginal-RSSI shade can wedge a
            # proxy and take every shade behind it offline.
            return await establish_connection(BleakClient, device, name, timeout=timeout)

        return TiltShadeClient(
            address,
            self._pairing_key,
            shade_id=address,
            allow_position_writes=allow_position_writes,
            client_factory=factory,
        )

    async def _async_update_data(self) -> ShadeStatus:
        try:
            return await self._make_client(allow_position_writes=False).read_status()
        except (BleakError, TiltProtocolError, TimeoutError) as err:
            raise UpdateFailed(f"Could not read shade {self.address}: {err}") from err

    async def async_set_position(self, position_percent: int) -> None:
        """Move the shade to a target percent and converge state on the read-back."""
        try:
            status, _moved = await self._make_client(
                allow_position_writes=True
            ).set_position_and_read_status(position_percent)
        except PositionVerificationPending as err:
            # The shade answered but never moved toward the target: a stuck
            # motor, an obstruction, or a rejected command. Keep the position it
            # reported and fail the action with a readable message rather than
            # letting the exception surface as a traceback in an automation.
            self.async_set_updated_data(err.status)
            raise HomeAssistantError(
                f"{self.device_name} did not move toward {position_percent}%"
                f" (still reporting {err.status.position_percent}%)"
            ) from err
        except (BleakError, TiltProtocolError, TimeoutError) as err:
            raise HomeAssistantError(f"Could not move {self.device_name}: {err}") from err

        self.async_set_updated_data(status)
        if status.position_percent != position_percent:
            # Accepted and still travelling — the write returns long before the
            # motor arrives, so re-read once it should have finished.
            self._schedule_arrival_refresh()

    def _schedule_arrival_refresh(self) -> None:
        """Re-read the shade once, after it has had time to finish travelling."""
        self._cancel_arrival_refresh()

        @callback
        def _refresh(_now) -> None:
            self._arrival_unsub = None
            self.hass.async_create_task(self.async_request_refresh())

        self._arrival_unsub = async_call_later(self.hass, POSITION_TRAVEL_TIME, _refresh)

    @callback
    def _cancel_arrival_refresh(self) -> None:
        if self._arrival_unsub is not None:
            self._arrival_unsub()
            self._arrival_unsub = None

    async def async_shutdown(self) -> None:
        """Drop any pending arrival re-read when the entry unloads."""
        self._cancel_arrival_refresh()
        await super().async_shutdown()
