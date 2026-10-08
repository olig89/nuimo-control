"""One Nuimo: keeps the Bluetooth connection up and turns notifications into gestures."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from homeassistant.components import bluetooth
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback

from .const import RECONNECT_DELAYS_S, ROTATION_WINDOW_S
from .core import protocol
from .core.matrix import Matrix, encode
from .core.rotation import RotationAccumulator

_LOGGER = logging.getLogger(__name__)

GestureListener = Callable[[str, dict[str, Any]], None]
StateListener = Callable[[], None]

# A connection that lasted this long resets the reconnect delay.
_STABLE_S = 60


class NotConnected(Exception):
    """The Nuimo isn't connected right now."""


class NuimoDevice:
    def __init__(self, hass: HomeAssistant, address: str) -> None:
        self.hass = hass
        self.address = address
        self.connected = False
        self.battery: int | None = None
        self.info: dict[str, str] = {}
        self._client: BleakClient | None = None
        self._task: asyncio.Task | None = None
        self._stopping = False
        self._disconnected = asyncio.Event()
        self._seen = asyncio.Event()
        self._gesture_listeners: list[GestureListener] = []
        self._state_listeners: list[StateListener] = []
        self._rotation = RotationAccumulator()
        self._rotation_timer: asyncio.TimerHandle | None = None
        self._led_pending: bytes | None = None
        self._led_task: asyncio.Task | None = None
        self._unsub_seen: CALLBACK_TYPE | None = None

    # ---- listeners -------------------------------------------------------

    @callback
    def add_gesture_listener(self, listener: GestureListener) -> CALLBACK_TYPE:
        self._gesture_listeners.append(listener)
        return lambda: self._gesture_listeners.remove(listener)

    @callback
    def add_state_listener(self, listener: StateListener) -> CALLBACK_TYPE:
        self._state_listeners.append(listener)
        return lambda: self._state_listeners.remove(listener)

    @callback
    def _emit(self, name: str, data: dict[str, Any] | None = None) -> None:
        for listener in list(self._gesture_listeners):
            listener(name, data or {})

    @callback
    def _state_changed(self) -> None:
        for listener in list(self._state_listeners):
            listener()

    # ---- lifecycle -------------------------------------------------------

    async def async_start(self) -> None:
        self._unsub_seen = bluetooth.async_register_callback(
            self.hass,
            self._on_advertisement,
            bluetooth.BluetoothCallbackMatcher(address=self.address, connectable=True),
            bluetooth.BluetoothScanningMode.PASSIVE,
        )
        self._task = self.hass.async_create_background_task(self._run(), f"nuimo {self.address}")

    async def async_stop(self) -> None:
        self._stopping = True
        if self._unsub_seen:
            self._unsub_seen()
        if self._rotation_timer:
            self._rotation_timer.cancel()
        self._disconnected.set()
        self._seen.set()
        for task in (self._led_task, self._task):
            if task and not task.done():
                task.cancel()
        await self._disconnect()
        for task in (self._led_task, self._task):
            if task:
                try:
                    await task
                except (asyncio.CancelledError, Exception):  # noqa: BLE001 - shutting down
                    pass

    @callback
    def _on_advertisement(self, _info: bluetooth.BluetoothServiceInfoBleak, _change: Any) -> None:
        self._seen.set()

    def _ble_device(self) -> BLEDevice | None:
        return bluetooth.async_ble_device_from_address(self.hass, self.address, connectable=True)

    async def _run(self) -> None:
        attempt = 0
        while not self._stopping:
            ble_device = self._ble_device()
            if ble_device is None:
                # Not in range of a connectable adapter: wait until it advertises again.
                self._seen.clear()
                try:
                    await asyncio.wait_for(self._seen.wait(), timeout=RECONNECT_DELAYS_S[-1])
                except TimeoutError:
                    pass
                continue
            started = self.hass.loop.time()
            try:
                await self._connect(ble_device)
                await self._disconnected.wait()
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001 - any Bluetooth failure means retry
                _LOGGER.debug("Nuimo %s: connection failed: %s", self.address, err)
            finally:
                await self._disconnect()
            if self._stopping:
                return
            if self.hass.loop.time() - started > _STABLE_S:
                attempt = 0
            delay = RECONNECT_DELAYS_S[min(attempt, len(RECONNECT_DELAYS_S) - 1)]
            attempt += 1
            await asyncio.sleep(delay)

    async def _connect(self, ble_device: BLEDevice) -> None:
        self._disconnected.clear()
        client = await establish_connection(
            BleakClientWithServiceCache,
            ble_device,
            f"Nuimo {self.address}",
            disconnected_callback=self._on_disconnected,
            ble_device_callback=self._ble_device,
            max_attempts=3,
        )
        self._client = client
        await client.start_notify(protocol.BUTTON, self._on_button)
        await client.start_notify(protocol.TOUCH, self._on_touch)
        await client.start_notify(protocol.ROTATION, self._on_rotation)
        await client.start_notify(protocol.FLY, self._on_fly)
        try:
            await client.start_notify(protocol.BATTERY_LEVEL, self._on_battery)
        except Exception:  # noqa: BLE001 - not every firmware notifies; read instead
            _LOGGER.debug("Nuimo %s: battery notifications not available", self.address)
        try:
            self._set_battery(protocol.decode_battery(await client.read_gatt_char(protocol.BATTERY_LEVEL)))
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Nuimo %s: could not read the battery", self.address)
        if not self.info:
            for uuid, key in (
                (protocol.MODEL, "model"),
                (protocol.FIRMWARE, "firmware"),
                (protocol.MANUFACTURER, "manufacturer"),
            ):
                try:
                    self.info[key] = bytes(await client.read_gatt_char(uuid)).decode("utf-8", "replace").strip("\x00 ")
                except Exception:  # noqa: BLE001
                    pass
        self.connected = True
        _LOGGER.info("Nuimo %s connected", self.address)
        self._state_changed()

    @callback
    def _on_disconnected(self, _client: BleakClient) -> None:
        self._disconnected.set()

    async def _disconnect(self) -> None:
        client, self._client = self._client, None
        was_connected = self.connected
        self.connected = False
        if client is not None:
            try:
                await client.disconnect()
            except Exception:  # noqa: BLE001
                pass
        if was_connected:
            _LOGGER.info("Nuimo %s disconnected", self.address)
            self._state_changed()

    # ---- notifications ---------------------------------------------------

    @callback
    def _on_button(self, _char: Any, data: bytearray) -> None:
        if gesture := protocol.decode_button(data):
            self._emit(gesture.name)

    @callback
    def _on_touch(self, _char: Any, data: bytearray) -> None:
        if gesture := protocol.decode_touch(data):
            self._emit(gesture.name)

    @callback
    def _on_fly(self, _char: Any, data: bytearray) -> None:
        if gesture := protocol.decode_fly(data):
            self._emit(gesture.name, gesture.data)

    @callback
    def _on_rotation(self, _char: Any, data: bytearray) -> None:
        steps = protocol.decode_rotation(data)
        if steps is None:
            return
        if self._rotation.add(steps):
            self._rotation_timer = self.hass.loop.call_later(ROTATION_WINDOW_S, self._flush_rotation)

    @callback
    def _flush_rotation(self) -> None:
        self._rotation_timer = None
        if batch := self._rotation.flush():
            self._emit(protocol.ROTATE, batch.as_event_data())

    @callback
    def _on_battery(self, _char: Any, data: bytearray) -> None:
        self._set_battery(protocol.decode_battery(data))

    @callback
    def _set_battery(self, value: int | None) -> None:
        if value is not None and value != self.battery:
            self.battery = value
            self._state_changed()

    # ---- LED matrix ------------------------------------------------------

    async def async_show(self, matrix: Matrix, brightness: float, seconds: float, fade: bool) -> None:
        """Queue a picture. A newer picture replaces one that hasn't been sent yet."""
        if not self.connected or self._client is None:
            raise NotConnected
        self._led_pending = encode(matrix, brightness, seconds, fade)
        if self._led_task is None or self._led_task.done():
            self._led_task = self.hass.async_create_task(self._write_leds(), eager_start=True)

    async def _write_leds(self) -> None:
        while self._led_pending is not None:
            payload, self._led_pending = self._led_pending, None
            client = self._client
            if client is None:
                return
            try:
                await client.write_gatt_char(protocol.LED_MATRIX, payload, response=True)
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("Nuimo %s: could not draw on the LEDs: %s", self.address, err)
                return
