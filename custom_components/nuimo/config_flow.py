"""Add a Nuimo found over Bluetooth, or by its address."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import CONF_ADDRESS, DEFAULT_NAME, DOMAIN

MAC_RE = re.compile(r"^(?:[0-9A-F]{2}:){5}[0-9A-F]{2}$")


class NuimoConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._discovered: BluetoothServiceInfoBleak | None = None

    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak) -> ConfigFlowResult:
        await self.async_set_unique_id(discovery_info.address.upper())
        self._abort_if_unique_id_configured()
        self._discovered = discovery_info
        self.context["title_placeholders"] = {"name": discovery_info.name or DEFAULT_NAME}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        assert self._discovered is not None
        if user_input is not None:
            return self.async_create_entry(
                title=DEFAULT_NAME, data={CONF_ADDRESS: self._discovered.address.upper()}
            )
        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": self._discovered.name or DEFAULT_NAME},
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            address = user_input[CONF_ADDRESS].strip().upper()
            if not MAC_RE.match(address):
                errors[CONF_ADDRESS] = "invalid_address"
            elif not bluetooth.async_address_present(self.hass, address, connectable=True):
                errors[CONF_ADDRESS] = "not_found"
            else:
                await self.async_set_unique_id(address)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=DEFAULT_NAME, data={CONF_ADDRESS: address})
        return self.async_show_form(
            step_id="user", data_schema=vol.Schema({vol.Required(CONF_ADDRESS): str}), errors=errors
        )
