"""A Nuimo without Bluetooth: the connection loop is replaced and notifications are fed in by hand."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.nuimo.const import CONF_ADDRESS, DOMAIN

ADDRESS = "AA:BB:CC:DD:EE:01"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture(autouse=True)
def no_bluetooth_stack(mock_bluetooth):
    yield


class FakeClient:
    """Records LED writes."""

    def __init__(self) -> None:
        self.writes: list[tuple[str, bytes]] = []

    async def write_gatt_char(self, uuid: str, data: bytes, response: bool = False) -> None:
        self.writes.append((uuid, bytes(data)))

    async def disconnect(self) -> None:
        pass


@pytest.fixture
async def nuimo(hass: HomeAssistant):
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_ADDRESS: ADDRESS}, unique_id=ADDRESS, title="Nuimo Control")
    entry.add_to_hass(hass)
    with patch("custom_components.nuimo.device.NuimoDevice.async_start"):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    device = entry.runtime_data
    device.entry = entry
    return device


def connect(device, client: FakeClient | None = None) -> FakeClient:
    client = client or FakeClient()
    device._client = client
    device.connected = True
    device._state_changed()
    return client
