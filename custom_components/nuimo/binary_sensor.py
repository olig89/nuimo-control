"""Whether Home Assistant is connected to the Nuimo right now."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NuimoConfigEntry
from .entity import NuimoEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: NuimoConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([NuimoConnected(entry.runtime_data)])


class NuimoConnected(NuimoEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, nuimo) -> None:
        super().__init__(nuimo, "connected")

    @property
    def is_on(self) -> bool:
        return self._nuimo.connected

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self._nuimo.add_state_listener(self.async_write_ha_state))
