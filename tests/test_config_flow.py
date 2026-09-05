"""Config-flow tests: manual entry + live key validation (TiltShadeClient stubbed)."""

from __future__ import annotations

from unittest.mock import patch

from bleak.exc import BleakError
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
