"""The SmartBlinds BLE integration.

Local, hub-free control of Tilt / SmarterHome roller shades over BLE, through
Home Assistant's Bluetooth stack (including ESPHome Bluetooth Proxies). Uses the
vendored encrypted Tilt protocol in the ``smartblinds-ble`` library.
"""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_ADDRESS, CONF_KEY
from .coordinator import SmartBlindsConfigEntry, SmartBlindsCoordinator

PLATFORMS: list[Platform] = [Platform.COVER, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: SmartBlindsConfigEntry) -> bool:
    """Set up a Tilt shade from a config entry."""
    coordinator = SmartBlindsCoordinator(
        hass,
        address=entry.data[CONF_ADDRESS],
        name=entry.title,
        pairing_key=bytes.fromhex(entry.data[CONF_KEY]),
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SmartBlindsConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
