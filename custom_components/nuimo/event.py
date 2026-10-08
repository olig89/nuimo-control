"""One event entity carrying every Nuimo gesture."""

from __future__ import annotations

from typing import Any

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NuimoConfigEntry
from .core.protocol import EVENT_TYPES
from .entity import NuimoEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: NuimoConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([NuimoGestureEvent(entry.runtime_data)])


class NuimoGestureEvent(NuimoEntity, EventEntity):
    """Fires press, release, rotate (with delta), swipes, touches, fly and proximity."""

    _attr_device_class = EventDeviceClass.BUTTON
    _attr_event_types = EVENT_TYPES
    _attr_translation_key = "gesture"

    def __init__(self, nuimo) -> None:
        # "events" keeps the unique id of the first version, so the entity id survives.
        super().__init__(nuimo, "events")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self._nuimo.add_gesture_listener(self._on_gesture))

    # Always available: going unavailable and back would look like a new event to state
    # triggers. Whether the Nuimo is connected is the Connectivity sensor's job.

    @callback
    def _on_gesture(self, name: str, data: dict[str, Any]) -> None:
        self._trigger_event(name, data)
        self.async_write_ha_state()
