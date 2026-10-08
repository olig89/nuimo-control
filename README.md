# Nuimo Control for Home Assistant

A Home Assistant integration for the Senic **Nuimo Control**, over Bluetooth.

- **One event entity** with every gesture: `press`, `release`, `rotate`, the four swipes, the four touches and long touches, `fly_left`, `fly_right` and `proximity`.
  - `rotate` carries `delta` (signed steps; summed over 80 ms so a turn doesn't flood Home Assistant), `direction` and `notifications`.
  - `proximity` carries `distance` (0–255).
- **Battery** sensor (kept across restarts) and a **Connectivity** sensor.
- **`nuimo.show`** action: draw on the 9×9 LEDs with a built-in icon, your own picture (nine rows of nine characters), a number (0–99) or a level bar (0–100 %), with brightness, how long to show it, and fade. A newer picture replaces one that hasn't been sent yet, so it keeps up with a dial being turned.
- Reconnects by itself, waiting for the Nuimo to advertise rather than polling.

What a gesture *does* belongs in an automation (or Button Blueprinter), not here.

## Install

HACS → Integrations → ⋮ → Custom repositories → add this repo as an Integration, download, restart. Home Assistant finds a Nuimo nearby by itself; or add it by Bluetooth address.

## Show something

```yaml
action: nuimo.show
data:
  device_id: <your Nuimo>
  level: 60
  brightness: 50
  duration: 1.5
```

## Development

`custom_components/nuimo/core/` holds the protocol, LED matrix and rotation logic with no Home Assistant imports. Byte layouts follow Senic's own [nuimo-linux-python](https://github.com/getsenic/nuimo-linux-python).

```bash
pip install -r requirements_test.txt
python -m pytest
```
