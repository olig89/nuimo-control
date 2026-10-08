"""Shared device info for Nuimo entities."""

from __future__ import annotations

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import Entity

from .const import DEFAULT_NAME, DOMAIN, MANUFACTURER
from .device import NuimoDevice


class NuimoEntity(Entity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, nuimo: NuimoDevice, key: str) -> None:
        self._nuimo = nuimo
        self._attr_unique_id = f"{nuimo.address}_{key}"
        self._attr_device_info = dr.DeviceInfo(
            identifiers={(DOMAIN, nuimo.address)},
            connections={(dr.CONNECTION_BLUETOOTH, nuimo.address)},
            name=DEFAULT_NAME,
            manufacturer=MANUFACTURER,
            model="Nuimo",
        )
