"""Constants for Nuimo Control."""

from __future__ import annotations

DOMAIN = "nuimo"
CONF_ADDRESS = "address"

DEFAULT_NAME = "Nuimo Control"
MANUFACTURER = "Senic"

# Rotation steps are summed over this window before one ``rotate`` event fires.
ROTATION_WINDOW_S = 0.08

# Wait between reconnect attempts, growing while the device stays away.
RECONNECT_DELAYS_S = (2, 5, 10, 30, 60)

SERVICE_SHOW = "show"
ATTR_DEVICE_ID = "device_id"
ATTR_ICON = "icon"
ATTR_MATRIX = "matrix"
ATTR_NUMBER = "number"
ATTR_LEVEL = "level"
ATTR_BRIGHTNESS = "brightness"
ATTR_DURATION = "duration"
ATTR_FADE = "fade"
