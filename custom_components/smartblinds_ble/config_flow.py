"""Config flow for SmartBlinds BLE (Tilt roller shades).

Supports Bluetooth auto-discovery (including via ESPHome proxies) and manual
entry. Both collect the shade's 64-hex pairing key, which is validated live by
authenticating a read-only session before the entry is created, so a wrong or
stale key is rejected at setup instead of failing silently later.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from bleak import BleakClient
from bleak.exc import BleakError
from bleak_retry_connector import establish_connection
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from smartblinds_ble.tilt import AuthenticationError, TiltProtocolError, TiltShadeClient

from .const import CONF_ADDRESS, CONF_KEY, DOMAIN

_LOGGER = logging.getLogger(__name__)


class SmartBlindsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for a single Tilt roller shade."""

    VERSION = 1

    def __init__(self) -> None:
        self._address: str | None = None
        self._name: str | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle a shade discovered over Bluetooth."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._address = discovery_info.address
        self._name = discovery_info.name or discovery_info.address
        self.context["title_placeholders"] = {"name": self._name}
        return await self.async_step_key()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle manual setup: enter the shade's BLE address."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS].upper()
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            self._address = address
            self._name = address
            return await self.async_step_key()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_ADDRESS): str}),
        )

    async def async_step_key(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect and validate the 64-hex pairing key."""
        assert self._address is not None
        errors: dict[str, str] = {}
        if user_input is not None:
            error = await self._validate_key(user_input[CONF_KEY])
            if error is None:
                return self.async_create_entry(
                    title=self._name or self._address,
                    data={CONF_ADDRESS: self._address, CONF_KEY: user_input[CONF_KEY].strip().lower()},
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="key",
            data_schema=vol.Schema({vol.Required(CONF_KEY): str}),
            errors=errors,
            description_placeholders={"name": self._name or self._address},
        )

    async def _validate_key(self, key_hex: str) -> str | None:
        """Return an error slug if the key is malformed or fails to authenticate."""
        try:
            key = bytes.fromhex(key_hex.strip())
        except ValueError:
            return "invalid_key_format"
        if len(key) != 32:
            return "invalid_key_format"

        address = self._address
        hass = self.hass

        async def factory(_address: str, *, timeout: float, **_kwargs: object) -> BleakClient:
            device = bluetooth.async_ble_device_from_address(hass, address, connectable=True)
            if device is None:
                raise BleakError(f"{address} is not currently reachable over BLE")
            # Same reasoning as the coordinator: let bleak-retry-connector own
            # connection establishment so a failed validation attempt cannot strand
            # a proxy connection slot.
            return await establish_connection(BleakClient, device, self._name or address, timeout=timeout)

        client = TiltShadeClient(address, key, client_factory=factory)
        try:
            await client.read_status()
        except AuthenticationError:
            return "invalid_key"
        except (BleakError, TiltProtocolError, TimeoutError):
            return "cannot_connect"
        return None
