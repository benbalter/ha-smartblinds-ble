"""Sensor platform for SmartBlinds BLE: shade battery level."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import SmartBlindsConfigEntry, SmartBlindsCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartBlindsConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the battery sensor from a config entry."""
    async_add_entities([SmartBlindsBatterySensor(entry.runtime_data)])


class SmartBlindsBatterySensor(CoordinatorEntity[SmartBlindsCoordinator], SensorEntity):
    """Battery level reported by a Tilt roller shade."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: SmartBlindsCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_battery"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> int | None:
        data = self.coordinator.data
        return data.battery_percent if data else None
