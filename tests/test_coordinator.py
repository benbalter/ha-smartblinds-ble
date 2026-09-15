"""Connections must go through bleak-retry-connector, not a bare BleakClient.

Home Assistant warns when an integration calls ``BleakClient.connect()`` directly,
because a failed attempt strands the ESPHome proxy's connection slot. On
2026-09-11 that stranded slot wedged the proxy serving all four shades, which then
needed a manual power cycle. These tests pin the fix.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from bleak.exc import BleakError
from homeassistant.core import HomeAssistant

from custom_components.smartblinds_ble.const import (
    IDLE_POLL_INTERVALS,
    IDLE_POLLS_BEFORE_BACKOFF,
)
from custom_components.smartblinds_ble.coordinator import SmartBlindsCoordinator

from .doubles import FakeTiltClient

MODULE = "custom_components.smartblinds_ble.coordinator"
ADDRESS = "AA:BB:CC:DD:EE:01"


def _coordinator(hass: HomeAssistant) -> SmartBlindsCoordinator:
    return SmartBlindsCoordinator(
        hass, address=ADDRESS, name="Office Left", pairing_key=bytes(range(32))
    )


async def test_factory_connects_via_establish_connection(hass: HomeAssistant) -> None:
    client = _coordinator(hass)._make_client(allow_position_writes=False)
    connected = object()

    with (
        patch(f"{MODULE}.bluetooth.async_ble_device_from_address", return_value=object()),
        patch(f"{MODULE}.establish_connection", AsyncMock(return_value=connected)) as establish,
    ):
        result = await client._client_factory(ADDRESS, timeout=10.0, pair=False)

    assert result is connected
    assert establish.await_count == 1
    # The shade's name is passed through so proxy logs identify which shade stalled.
    assert establish.await_args.args[2] == "Office Left"


async def test_factory_raises_when_the_shade_is_out_of_range(hass: HomeAssistant) -> None:
    client = _coordinator(hass)._make_client(allow_position_writes=False)

    with (
        patch(f"{MODULE}.bluetooth.async_ble_device_from_address", return_value=None),
        patch(f"{MODULE}.establish_connection", AsyncMock()) as establish,
        pytest.raises(BleakError, match="not currently reachable"),
    ):
        await client._client_factory(ADDRESS, timeout=10.0, pair=False)

    # No connection attempt at all when HA has no BLEDevice for it.
    assert establish.await_count == 0


async def test_polling_backs_off_while_nothing_changes(hass: HomeAssistant) -> None:
    """Idle shades should stop costing a BLE session every 30 minutes.

    These are solar-charged motors; 48 polls a day per shade, nearly all returning
    the identical status, is radio time spent to learn nothing.
    """
    coordinator = _coordinator(hass)
    fake = FakeTiltClient(position=30, battery=66)

    with patch(f"{MODULE}.TiltShadeClient", return_value=fake):
        await coordinator.async_refresh()
        assert coordinator.update_interval == IDLE_POLL_INTERVALS[0]

        for _ in range(IDLE_POLLS_BEFORE_BACKOFF):
            await coordinator.async_refresh()
        assert coordinator.update_interval == IDLE_POLL_INTERVALS[1]

        for _ in range(IDLE_POLLS_BEFORE_BACKOFF):
            await coordinator.async_refresh()
        assert coordinator.update_interval == IDLE_POLL_INTERVALS[2]

        # The ladder is clamped; it does not run off the end.
        for _ in range(IDLE_POLLS_BEFORE_BACKOFF * 3):
            await coordinator.async_refresh()
        assert coordinator.update_interval == IDLE_POLL_INTERVALS[-1]


async def test_a_change_returns_to_full_rate(hass: HomeAssistant) -> None:
    coordinator = _coordinator(hass)
    fake = FakeTiltClient(position=30, battery=66)

    with patch(f"{MODULE}.TiltShadeClient", return_value=fake):
        for _ in range(IDLE_POLLS_BEFORE_BACKOFF * 2):
            await coordinator.async_refresh()
        assert coordinator.update_interval != IDLE_POLL_INTERVALS[0]

        fake._position = 80  # the shade moved: news, so poll attentively again
        await coordinator.async_refresh()
        assert coordinator.update_interval == IDLE_POLL_INTERVALS[0]
