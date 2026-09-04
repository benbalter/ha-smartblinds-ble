"""Cover platform for SmartBlinds BLE.

Each shade is an optimistic (assumed-state) tilt cover: the motor is open-loop
(reads return 0xFF), so HA tracks position and cannot see app/wand changes.

Tilt maps HA's 0..100% onto the motor's native 0..200.

⚠️  STUB: command paths are wired to the smartblinds_ble library but unproven on
    hardware (Milestone 0). Expect to adjust once the protocol is confirmed.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components import bluetooth
from homeassistant.components.cover import (
    ATTR_TILT_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ADDRESS, CONF_KEY, DOMAIN, ENTITY_NAME, MANUFACTURER

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the cover from a config entry."""
    async_add_entities(
        [SmartBlindsCover(hass, entry.data[CONF_ADDRESS], entry.data[CONF_KEY])]
    )


class SmartBlindsCover(CoverEntity):
    """An optimistic tilt-only cover for a single shade motor."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_assumed_state = True
    _attr_device_class = CoverDeviceClass.BLIND
    _attr_supported_features = (
        CoverEntityFeature.OPEN_TILT
        | CoverEntityFeature.CLOSE_TILT
        | CoverEntityFeature.SET_TILT_POSITION
        | CoverEntityFeature.STOP_TILT
    )

    def __init__(self, hass: HomeAssistant, address: str, key: str) -> None:
        self.hass = hass
        self._address = address
        self._key = key
        self._attr_unique_id = address
        self._attr_current_cover_tilt_position: int | None = None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, address)},
            name=ENTITY_NAME.format(address=address),
            manufacturer=MANUFACTURER,
        )

    async def _blind(self):
        """Build a SmartBlind bound to the live BLEDevice (routes via proxies)."""
        # Imported lazily so the platform loads even if the lib isn't installed yet.
        from smartblinds_ble import SmartBlind  # noqa: PLC0415

        device = bluetooth.async_ble_device_from_address(
            self.hass, self._address, connectable=True
        )
        if device is None:
            raise RuntimeError(f"{self._address} not currently reachable over BLE")
        return SmartBlind(device, key=self._key)

    async def async_set_cover_tilt_position(self, **kwargs: Any) -> None:
        """Set tilt to a 0..100 position."""
        position = kwargs[ATTR_TILT_POSITION]
        blind = await self._blind()
        await blind.set_tilt_percent(position)
        self._attr_current_cover_tilt_position = position
        self.async_write_ha_state()

    async def async_open_cover_tilt(self, **kwargs: Any) -> None:
        await self.async_set_cover_tilt_position(**{ATTR_TILT_POSITION: 100})

    async def async_close_cover_tilt(self, **kwargs: Any) -> None:
        await self.async_set_cover_tilt_position(**{ATTR_TILT_POSITION: 0})

    async def async_stop_cover_tilt(self, **kwargs: Any) -> None:
        """No native stop; disconnecting halts motion. TODO(M0): confirm."""
        _LOGGER.debug("stop_tilt is a no-op in the stub")
