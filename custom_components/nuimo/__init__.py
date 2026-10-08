"""Senic Nuimo Control: every gesture as one event entity, plus pictures on its LED matrix."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_BRIGHTNESS,
    ATTR_DEVICE_ID,
    ATTR_DURATION,
    ATTR_FADE,
    ATTR_ICON,
    ATTR_LEVEL,
    ATTR_MATRIX,
    ATTR_NUMBER,
    CONF_ADDRESS,
    DOMAIN,
    SERVICE_SHOW,
)
from .core import matrix as mx
from .device import NotConnected, NuimoDevice

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.EVENT, Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type NuimoConfigEntry = ConfigEntry[NuimoDevice]

_PICTURE_KEYS = (ATTR_ICON, ATTR_MATRIX, ATTR_NUMBER, ATTR_LEVEL)

SHOW_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional(ATTR_ICON): vol.In(sorted(mx.ICONS)),
        vol.Optional(ATTR_MATRIX): cv.string,
        vol.Optional(ATTR_NUMBER): vol.All(vol.Coerce(int), vol.Range(min=0, max=99)),
        vol.Optional(ATTR_LEVEL): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
        vol.Optional(ATTR_BRIGHTNESS, default=100): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
        vol.Optional(ATTR_DURATION, default=2): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=mx.MAX_SECONDS)),
        vol.Optional(ATTR_FADE, default=False): cv.boolean,
    }
)


def picture_from_call(data: dict) -> mx.Matrix:
    given = [k for k in _PICTURE_KEYS if data.get(k) is not None]
    if len(given) != 1:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="one_picture", translation_placeholders={"given": ", ".join(given) or "none"}
        )
    key = given[0]
    try:
        if key == ATTR_ICON:
            return mx.ICONS[data[ATTR_ICON]]
        if key == ATTR_MATRIX:
            return mx.Matrix.from_text(data[ATTR_MATRIX])
        if key == ATTR_NUMBER:
            return mx.number(data[ATTR_NUMBER])
        return mx.level(data[ATTR_LEVEL])
    except mx.MatrixError as err:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="bad_picture", translation_placeholders={"error": str(err)}
        ) from err


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    async def show(call: ServiceCall) -> None:
        picture = picture_from_call(call.data)
        registry = dr.async_get(hass)
        devices: list[NuimoDevice] = []
        for device_id in call.data[ATTR_DEVICE_ID]:
            device = registry.async_get(device_id)
            entry = next(
                (
                    e
                    for e in (hass.config_entries.async_get_entry(i) for i in (device.config_entries if device else ()))
                    if e and e.domain == DOMAIN
                ),
                None,
            )
            if entry is None or entry.state is not ConfigEntryState.LOADED:
                raise ServiceValidationError(
                    translation_domain=DOMAIN, translation_key="not_a_nuimo", translation_placeholders={"device_id": device_id}
                )
            devices.append(entry.runtime_data)
        for nuimo in devices:
            try:
                await nuimo.async_show(
                    picture,
                    brightness=call.data[ATTR_BRIGHTNESS] / 100,
                    seconds=call.data[ATTR_DURATION],
                    fade=call.data[ATTR_FADE],
                )
            except NotConnected as err:
                raise HomeAssistantError(
                    translation_domain=DOMAIN, translation_key="not_connected", translation_placeholders={"address": nuimo.address}
                ) from err

    hass.services.async_register(DOMAIN, SERVICE_SHOW, show, schema=SHOW_SCHEMA)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: NuimoConfigEntry) -> bool:
    nuimo = NuimoDevice(hass, entry.data[CONF_ADDRESS])
    entry.runtime_data = nuimo

    def update_device_info() -> None:
        registry = dr.async_get(hass)
        if device := registry.async_get_device_by_identifier((DOMAIN, nuimo.address), entry.entry_id):
            registry.async_update_device(
                device.id,
                model=nuimo.info.get("model") or device.model,
                sw_version=nuimo.info.get("firmware") or device.sw_version,
            )

    entry.async_on_unload(nuimo.add_state_listener(update_device_info))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await nuimo.async_start()
    entry.async_on_unload(nuimo.async_stop)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: NuimoConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_config_entry_device(hass: HomeAssistant, entry: NuimoConfigEntry, device: dr.DeviceEntry) -> bool:
    return True
