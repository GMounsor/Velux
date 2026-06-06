# Velux Active — Home Assistant Integration

A Home Assistant custom integration for **VELUX ACTIVE with NETATMO** (KIX 300 gateway), built on top of the [ha-velux-active](https://github.com/Niek/ha-velux-active) baseline and extended with sensor and binary sensor support.

Uses the official VELUX cloud login flow via [`pyatmo`](https://github.com/jabesq-org/pyatmo).

---

## Features

- **Config flow** — set up with your VELUX ACTIVE app email and password
- **Token caching** — stored access and refresh tokens survive restarts
- **Covers** (`cover`) — open, close, stop, and set position on all blinds and awning blinds
- **Open/closed sensors** (`binary_sensor`) — one per cover, showing whether each blind or window is open
- **Rain detection** (`binary_sensor`) — one per gateway, from the gateway's built-in rain flag
- **Indoor climate sensors** (`sensor`) — temperature and humidity from NXS room sensors
- **30-second polling** with immediate optimistic state updates after commands

---

## Supported devices

| Type | Description | HA platform |
|------|-------------|-------------|
| `NXG` | KIX 300 / KIG 300 gateway | coordinator + `binary_sensor` (rain) |
| `NXO` | Roller blind / awning blind / window actuator | `cover` + `binary_sensor` (open) |
| `NXS` | Indoor climate sensor | `sensor` (temperature, humidity) |

---

## Installation

### Via HACS (recommended)

1. In HACS → **Integrations** → ⋮ → **Custom repositories**
2. Add `https://github.com/GMounsor/Velux` with category **Integration**
3. Search for **Velux Active** and install it
4. Restart Home Assistant

### Manual

1. Copy `custom_components/velux_active` into your HA `custom_components` directory
2. Restart Home Assistant

---

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Velux Active**
3. Enter the email and password from your VELUX ACTIVE app

---

## Notes

- Rain detection uses the gateway's internal `is_raining` flag. The gateway raises this flag automatically when it senses rain; it cannot be triggered independently.
- Wind sensors are not part of the standard VELUX ACTIVE KIX 300 system. If you have a Netatmo anemometer connected, open an issue to discuss adding wind support.
- CO₂ and illuminance from NXS sensors require pyatmo to expose those fields natively; this is planned for a future release.
- This is an unofficial integration and is not affiliated with VELUX or Netatmo.

---

## Credits

Based on [ha-velux-active](https://github.com/Niek/ha-velux-active) by Niek, extended with binary sensor and sensor platforms.
