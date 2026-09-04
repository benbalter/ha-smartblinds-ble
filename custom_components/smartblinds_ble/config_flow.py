"""Config flow for SmartBlinds BLE.

Supports Bluetooth auto-discovery (including via ESPHome proxies) and a manual
step. Both collect the per-motor BLE key, which is the main setup hurdle — a user
gets it from `smartblinds-find-key` or by sniffing the app once.

⚠️  STUB: the key-validation step below does not yet talk to hardware. Once
    Milestone 0 confirms the protocol, wire it to smartblinds_ble.SmartBlind so a
    bad key is rejected at setup instead of silently failing later.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import CONF_ADDRESS, CONF_KEY, DOMAIN


class SmartBlindsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SmartBlinds BLE."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered_address: str | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle a shade discovered over Bluetooth."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovered_address = discovery_info.address
        self.context["title_placeholders"] = {"name": discovery_info.address}
        return await self.async_step_key()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual setup: enter the motor's BLE address."""
        if user_input is not None:
            await self.async_set_unique_id(
                user_input[CONF_ADDRESS].upper(), raise_on_progress=False
            )
            self._abort_if_unique_id_configured()
            self._discovered_address = user_input[CONF_ADDRESS].upper()
            return await self.async_step_key()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_ADDRESS): str}),
        )

    async def async_step_key(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect the per-motor BLE key (hex, e.g. '2a')."""
        assert self._discovered_address is not None
        if user_input is not None:
            # TODO(M0): validate the key against the motor before creating the entry.
            return self.async_create_entry(
                title=f"SmartBlind {self._discovered_address}",
                data={
                    CONF_ADDRESS: self._discovered_address,
                    CONF_KEY: user_input[CONF_KEY],
                },
            )

        return self.async_show_form(
            step_id="key",
            data_schema=vol.Schema({vol.Required(CONF_KEY): str}),
            description_placeholders={"address": self._discovered_address},
        )
