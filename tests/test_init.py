"""Setup + service tests: entry brings up cover + battery; set_position drives the client."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from smartblinds_ble.tilt import PositionVerificationPending

from custom_components.smartblinds_ble.const import CONF_ADDRESS, CONF_KEY, DOMAIN

from .doubles import FakeTiltClient, make_status

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


async def test_travelling_shade_converges_after_a_delayed_reread(hass: HomeAssistant) -> None:
    # The write returns while the motor is still moving, so the first state is
    # mid-travel; a single scheduled re-read must catch up without waiting for
    # the 30-minute poll.
    entry = _entry()
    entry.add_to_hass(hass)
    fake = FakeTiltClient(position=0, battery=90, travel_fraction=0.4)
    with patch(_CLIENT, return_value=fake):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        await hass.services.async_call(
            "cover",
            "set_cover_position",
            {"entity_id": "cover.office_left", "position": 100},
            blocking=True,
        )
        await hass.async_block_till_done()

        assert hass.states.get("cover.office_left").attributes["current_position"] == 40

        fake.finish_travel()
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=45))
        await hass.async_block_till_done()

    assert hass.states.get("cover.office_left").attributes["current_position"] == 100
    assert fake.set_position_calls == 1  # converged by reading, never by resending


async def test_stuck_shade_fails_the_action(hass: HomeAssistant) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    fake = FakeTiltClient(
        position=20,
        battery=90,
        set_error=PositionVerificationPending("did not move", make_status(20, 90)),
    )
    with patch(_CLIENT, return_value=fake):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        with pytest.raises(HomeAssistantError, match="did not move toward 100%"):
            await hass.services.async_call(
                "cover",
                "set_cover_position",
                {"entity_id": "cover.office_left", "position": 100},
                blocking=True,
            )
        await hass.async_block_till_done()

    # Still reporting where the shade actually is, not the requested target.
    assert hass.states.get("cover.office_left").attributes["current_position"] == 20
