from __future__ import annotations

import asyncio

import pytest

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.nuimo.const import DOMAIN
from custom_components.nuimo.core import matrix as mx
from custom_components.nuimo.core.protocol import LED_MATRIX

from .conftest import ADDRESS, FakeClient, connect

EVENT = "event.nuimo_control_button"
BATTERY = "sensor.nuimo_control_battery"
CONNECTED = "binary_sensor.nuimo_control_connectivity"


async def test_entities_keep_the_first_versions_unique_ids(hass: HomeAssistant, nuimo):
    reg = er.async_get(hass)
    assert reg.async_get_entity_id("event", DOMAIN, f"{ADDRESS}_events") == EVENT
    assert reg.async_get_entity_id("sensor", DOMAIN, f"{ADDRESS}_battery") == BATTERY
    assert reg.async_get_entity_id("binary_sensor", DOMAIN, f"{ADDRESS}_connected") == CONNECTED


async def test_button_and_touch_events(hass: HomeAssistant, nuimo):
    nuimo._on_button(None, bytearray(b"\x01"))
    await hass.async_block_till_done()
    assert hass.states.get(EVENT).attributes["event_type"] == "press"
    nuimo._on_touch(None, bytearray(b"\x09"))
    await hass.async_block_till_done()
    assert hass.states.get(EVENT).attributes["event_type"] == "long_touch_right"
    nuimo._on_fly(None, bytearray(b"\x04\x20"))
    await hass.async_block_till_done()
    state = hass.states.get(EVENT)
    assert state.attributes["event_type"] == "proximity" and state.attributes["distance"] == 32


async def test_rotation_is_batched_into_one_event(hass: HomeAssistant, nuimo):
    fired = []
    hass.bus.async_listen("state_changed", lambda e: e.data["entity_id"] == EVENT and fired.append(e))
    for chunk in (b"\x0a\x00", b"\x05\x00", b"\xfd\xff"):  # +10, +5, -3
        nuimo._on_rotation(None, bytearray(chunk))
    await asyncio.sleep(0.15)
    await hass.async_block_till_done()
    assert len(fired) == 1
    attrs = hass.states.get(EVENT).attributes
    assert attrs["event_type"] == "rotate"
    assert attrs["delta"] == 12 and attrs["direction"] == "clockwise" and attrs["notifications"] == 3


async def test_battery_and_connectivity(hass: HomeAssistant, nuimo):
    assert hass.states.get(CONNECTED).state == "off"
    connect(nuimo)
    await hass.async_block_till_done()
    assert hass.states.get(CONNECTED).state == "on"
    nuimo._on_battery(None, bytearray(b"\x40"))
    await hass.async_block_till_done()
    assert hass.states.get(BATTERY).state == "64"
    # The event entity stays available while disconnected, so state triggers don't misfire.
    await nuimo._disconnect()
    await hass.async_block_till_done()
    assert hass.states.get(CONNECTED).state == "off"
    assert hass.states.get(EVENT).state != "unavailable"


def _device_id(hass: HomeAssistant) -> str:
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    return dr.async_get(hass).async_get_device_by_identifier((DOMAIN, ADDRESS), entry.entry_id).id


async def test_device_info_updates_from_the_device(hass: HomeAssistant, nuimo):
    nuimo.info = {"model": "Nuimo Control", "firmware": "2.6.0"}
    connect(nuimo)
    await hass.async_block_till_done()
    device = dr.async_get(hass).async_get(_device_id(hass))
    assert device.model == "Nuimo Control" and device.sw_version == "2.6.0"


async def test_show_icon_writes_the_right_bytes(hass: HomeAssistant, nuimo):
    client = connect(nuimo)
    await hass.services.async_call(
        DOMAIN, "show", {"device_id": _device_id(hass), "icon": "check", "brightness": 50, "duration": 3}, blocking=True
    )
    await hass.async_block_till_done()
    assert client.writes == [(LED_MATRIX, mx.encode(mx.ICONS["check"], 0.5, 3.0, False))]


async def test_show_number_level_and_picture(hass: HomeAssistant, nuimo):
    client = connect(nuimo)
    device_id = _device_id(hass)
    for data, expected in (
        ({"number": 42}, mx.number(42)),
        ({"level": 50}, mx.level(50)),
        ({"matrix": "\n".join(["#########"] + ["........."] * 8)}, mx.Matrix([True] * 9 + [False] * 72)),
    ):
        client.writes.clear()
        await hass.services.async_call(DOMAIN, "show", {"device_id": device_id, **data}, blocking=True)
        await hass.async_block_till_done()
        assert client.writes[-1][1][:11] == mx.encode(expected)[:11]


async def test_latest_picture_wins_while_a_write_is_in_flight(hass: HomeAssistant, nuimo):
    gate = asyncio.Event()

    class SlowClient(FakeClient):
        async def write_gatt_char(self, uuid, data, response=False):
            await gate.wait()
            await super().write_gatt_char(uuid, data, response)

    client = connect(nuimo, SlowClient())
    for icon in ("up", "down", "left", "right"):
        await nuimo.async_show(mx.ICONS[icon], 1.0, 2.0, False)
    gate.set()
    await hass.async_block_till_done()
    sent = [data for _, data in client.writes]
    assert sent == [mx.encode(mx.ICONS["up"], 1.0, 2.0), mx.encode(mx.ICONS["right"], 1.0, 2.0)]


async def test_show_errors(hass: HomeAssistant, nuimo):
    device_id = _device_id(hass)
    with pytest.raises(HomeAssistantError, match="isn't connected"):
        await hass.services.async_call(DOMAIN, "show", {"device_id": device_id, "icon": "play"}, blocking=True)
    connect(nuimo)
    with pytest.raises(ServiceValidationError, match="exactly one"):
        await hass.services.async_call(DOMAIN, "show", {"device_id": device_id, "icon": "play", "number": 3}, blocking=True)
    with pytest.raises(ServiceValidationError, match="exactly one"):
        await hass.services.async_call(DOMAIN, "show", {"device_id": device_id}, blocking=True)
    with pytest.raises(ServiceValidationError, match="can't be shown"):
        await hass.services.async_call(DOMAIN, "show", {"device_id": device_id, "matrix": "###"}, blocking=True)
    with pytest.raises(ServiceValidationError, match="isn't a Nuimo"):
        await hass.services.async_call(DOMAIN, "show", {"device_id": "nope", "icon": "play"}, blocking=True)


async def test_unload(hass: HomeAssistant, nuimo):
    assert await hass.config_entries.async_unload(nuimo.entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(EVENT).state == "unavailable"


async def test_user_flow_rejects_a_bad_address(hass: HomeAssistant):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"address": "not-a-mac"})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"address": "invalid_address"}
