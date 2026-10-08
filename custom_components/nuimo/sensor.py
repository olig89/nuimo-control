"""Battery level, kept across restarts and while the Nuimo is away."""

from __future__ import annotations

from homeassistant.components.sensor import RestoreSensor, SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NuimoConfigEntry
from .entity import NuimoEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: NuimoConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([NuimoBattery(entry.runtime_data)])


class NuimoBattery(NuimoEntity, RestoreSensor):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, nuimo) -> None:
        super().__init__(nuimo, "battery")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if self._nuimo.battery is not None:
            self._attr_native_value = self._nuimo.battery
        elif (last := await self.async_get_last_sensor_data()) is not None:
            self._attr_native_value = last.native_value
        self.async_on_remove(self._nuimo.add_state_listener(self._update))

    @callback
    def _update(self) -> None:
        if self._nuimo.battery is not None and self._nuimo.battery != self._attr_native_value:
            self._attr_native_value = self._nuimo.battery
            self.async_write_ha_state()
