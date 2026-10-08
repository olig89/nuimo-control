"""Nuimo Control Bluetooth protocol: characteristic ids and notification decoding.

Byte layouts follow Senic's own nuimo-linux-python library (getsenic/nuimo-linux-python,
nuimo/nuimo.py), which is the only published reference.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

NUIMO_SERVICE = "f29b1525-cb19-40f3-be5c-7241ecb82fd2"
FLY = "f29b1526-cb19-40f3-be5c-7241ecb82fd2"
TOUCH = "f29b1527-cb19-40f3-be5c-7241ecb82fd2"
ROTATION = "f29b1528-cb19-40f3-be5c-7241ecb82fd2"
BUTTON = "f29b1529-cb19-40f3-be5c-7241ecb82fd2"
LED_MATRIX = "f29b152d-cb19-40f3-be5c-7241ecb82fd2"

BATTERY_LEVEL = "00002a19-0000-1000-8000-00805f9b34fb"
MANUFACTURER = "00002a29-0000-1000-8000-00805f9b34fb"
MODEL = "00002a24-0000-1000-8000-00805f9b34fb"
FIRMWARE = "00002a26-0000-1000-8000-00805f9b34fb"

# Event names. Kept identical to the first (0.1.x) integration so automations survive.
PRESS = "press"
RELEASE = "release"
ROTATE = "rotate"
PROXIMITY = "proximity"
FLY_LEFT = "fly_left"
FLY_RIGHT = "fly_right"

_TOUCH_NAMES = {
    0: "swipe_left",
    1: "swipe_right",
    2: "swipe_up",
    3: "swipe_down",
    4: "touch_left",
    5: "touch_right",
    6: "touch_top",
    7: "touch_bottom",
    8: "long_touch_left",
    9: "long_touch_right",
    10: "long_touch_top",
    11: "long_touch_bottom",
}

EVENT_TYPES: list[str] = [
    PRESS,
    RELEASE,
    ROTATE,
    *_TOUCH_NAMES.values(),
    FLY_LEFT,
    FLY_RIGHT,
    PROXIMITY,
]


@dataclass(frozen=True)
class Gesture:
    """One decoded notification."""

    name: str
    data: dict[str, Any] = field(default_factory=dict)


def decode_button(value: bytes | bytearray) -> Gesture | None:
    if not value:
        return None
    return Gesture(RELEASE if value[0] == 0 else PRESS)


def decode_touch(value: bytes | bytearray) -> Gesture | None:
    if not value:
        return None
    name = _TOUCH_NAMES.get(value[0])
    return Gesture(name) if name else None


def decode_rotation(value: bytes | bytearray) -> int | None:
    """Signed rotation step count since the last notification (little-endian int16)."""
    if len(value) < 2:
        return None
    raw = value[0] | (value[1] << 8)
    if raw & 0x8000:
        raw -= 1 << 16
    return raw or None


def decode_fly(value: bytes | bytearray) -> Gesture | None:
    """Hand movement above the device. Code 4 carries a distance (0-255, larger = further)."""
    if not value:
        return None
    if value[0] == 0:
        return Gesture(FLY_LEFT)
    if value[0] == 1:
        return Gesture(FLY_RIGHT)
    if value[0] == 4 and len(value) >= 2:
        return Gesture(PROXIMITY, {"distance": value[1]})
    return None


def decode_battery(value: bytes | bytearray) -> int | None:
    if not value:
        return None
    return max(0, min(100, int(value[0])))
