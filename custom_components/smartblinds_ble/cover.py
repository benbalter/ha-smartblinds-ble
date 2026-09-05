"""Cover platform for SmartBlinds BLE (Tilt roller shades).

Unlike the legacy MySmartBlinds motors, Tilt roller shades report a real
position (0-100%) and battery, so this is a proper position cover with state
read back from the shade -- not an optimistic/assumed-state entity.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import SmartBlindsConfigEntry, SmartBlindsCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartBlindsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the shade cover from a config entry."""
    async_add_entities([SmartBlindsCover(entry.runtime_data)])


class SmartBlindsCover(CoordinatorEntity[SmartBlindsCoordinator], CoverEntity):
    """A position cover for a single Tilt roller shade (0% closed, 100% open)."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_device_class = CoverDeviceClass.SHADE
    _attr_supported_features = (
        CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.SET_POSITION
    )

    def __init__(self, coordinator: SmartBlindsCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = coordinator.address
        self._attr_device_info = coordinator.device_info

    @property
    def current_cover_position(self) -> int | None:
        data = self.coordinator.data
        return data.position_percent if data else None

    @property
    def is_closed(self) -> bool | None:
        data = self.coordinator.data
        return None if data is None else data.position_percent == 0

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_position(int(kwargs[ATTR_POSITION]))

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_position(100)

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_position(0)
