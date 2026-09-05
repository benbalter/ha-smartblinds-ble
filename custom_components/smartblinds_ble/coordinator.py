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
from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from smartblinds_ble.tilt import ShadeStatus, TiltProtocolError, TiltShadeClient

from .const import DEFAULT_POLL_INTERVAL, DOMAIN, MANUFACTURER, MODEL

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

        def factory(_address: str, *, timeout: float, **_kwargs: object) -> BleakClient:
            device = bluetooth.async_ble_device_from_address(hass, address, connectable=True)
            if device is None:
                raise BleakError(f"{address} is not currently reachable over BLE")
            return BleakClient(device, timeout=timeout)

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
        """Move the shade to a target percent and refresh state from the read-back."""
        status, _moved = await self._make_client(
            allow_position_writes=True
        ).set_position_and_read_status(position_percent)
        self.async_set_updated_data(status)
