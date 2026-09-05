"""Setup + service tests: entry brings up cover + battery; set_position drives the client."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smartblinds_ble.const import CONF_ADDRESS, CONF_KEY, DOMAIN

from .doubles import FakeTiltClient

ADDRESS = "AA:BB:CC:DD:EE:01"
KEY_HEX = bytes(range(32)).hex()
_CLIENT = "custom_components.smartblinds_ble.coordinator.TiltShadeClient"


def _entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=ADDRESS,
        title="Office Left",
        data={CONF_ADDRESS: ADDRESS, CONF_KEY: KEY_HEX},
    )


async def test_setup_creates_cover_and_battery(hass: HomeAssistant) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    with patch(_CLIENT, return_value=FakeTiltClient(position=30, battery=66)):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    cover = hass.states.get("cover.office_left")
    assert cover is not None
    assert cover.attributes["current_position"] == 30

    battery = hass.states.get("sensor.office_left_battery")
    assert battery is not None
    assert battery.state == "66"


async def test_set_position_service_moves_shade(hass: HomeAssistant) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    fake = FakeTiltClient(position=0, battery=90)
    with patch(_CLIENT, return_value=fake):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        await hass.services.async_call(
            "cover",
            "set_cover_position",
            {"entity_id": "cover.office_left", "position": 80},
            blocking=True,
        )
        await hass.async_block_till_done()

    assert fake.set_position_calls == 1
    assert hass.states.get("cover.office_left").attributes["current_position"] == 80
