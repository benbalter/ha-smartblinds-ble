"""Config-flow tests: manual entry + live key validation (TiltShadeClient stubbed)."""

from __future__ import annotations

from unittest.mock import patch

from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak.exc import BleakError
from habluetooth import BluetoothServiceInfoBleak
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from smartblinds_ble.tilt import AuthenticationError

from custom_components.smartblinds_ble.const import CONF_ADDRESS, CONF_KEY, DOMAIN

from .doubles import FakeTiltClient

ADDRESS = "AA:BB:CC:DD:EE:01"
KEY_HEX = bytes(range(32)).hex()
_CLIENT = "custom_components.smartblinds_ble.config_flow.TiltShadeClient"


async def _to_key_step(hass: HomeAssistant) -> dict:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ADDRESS: ADDRESS}
    )
    assert result["step_id"] == "key"
    return result


async def test_user_flow_success(hass: HomeAssistant) -> None:
    result = await _to_key_step(hass)
    with patch(_CLIENT, return_value=FakeTiltClient()):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_KEY: KEY_HEX}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_ADDRESS: ADDRESS, CONF_KEY: KEY_HEX}


async def test_manual_entry_title_is_the_address(hass: HomeAssistant) -> None:
    """With no advertised name, the address alone titles the entry."""
    result = await _to_key_step(hass)
    with patch(_CLIENT, return_value=FakeTiltClient()):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_KEY: KEY_HEX}
        )
    assert result["title"] == ADDRESS


async def test_discovery_disambiguates_by_address(hass: HomeAssistant) -> None:
    """Every shade advertises "RollerSh", so the address must reach the UI."""
    discovery = BluetoothServiceInfoBleak(
        name="RollerSh",
        address=ADDRESS,
        rssi=-60,
        manufacturer_data={},
        service_data={},
        service_uuids=[],
        source="local",
        device=BLEDevice(ADDRESS, "RollerSh", {}),
        advertisement=AdvertisementData(
            local_name="RollerSh",
            manufacturer_data={},
            service_data={},
            service_uuids=[],
            tx_power=None,
            rssi=-60,
            platform_data=(),
        ),
        connectable=True,
        time=0,
        tx_power=None,
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_BLUETOOTH}, data=discovery
    )
    assert result["step_id"] == "key"
    # The name alone is identical across shades; the address is what tells them apart.
    assert ADDRESS in result["description_placeholders"]["address"]

    flow = next(
        f for f in hass.config_entries.flow.async_progress() if f["flow_id"] == result["flow_id"]
    )
    assert ADDRESS in flow["context"]["title_placeholders"]["name"]

    with patch(_CLIENT, return_value=FakeTiltClient()):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_KEY: KEY_HEX}
        )
    assert result["title"] == f"RollerSh ({ADDRESS})"


async def test_invalid_key_format(hass: HomeAssistant) -> None:
    result = await _to_key_step(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_KEY: "not-64-hex"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_key_format"}


async def test_wrong_key_rejected(hass: HomeAssistant) -> None:
    result = await _to_key_step(hass)
    with patch(_CLIENT, return_value=FakeTiltClient(error=AuthenticationError("nope"))):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_KEY: KEY_HEX}
        )
    assert result["errors"] == {"base": "invalid_key"}


async def test_unreachable_shade(hass: HomeAssistant) -> None:
    result = await _to_key_step(hass)
    with patch(_CLIENT, return_value=FakeTiltClient(error=BleakError("unreachable"))):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_KEY: KEY_HEX}
        )
    assert result["errors"] == {"base": "cannot_connect"}
