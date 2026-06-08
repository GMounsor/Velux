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

## Enabling window open/close (signing keys)

Blinds and awning blinds work without any extra setup. **VELUX windows** (actuators that tilt or swing open) require two additional cryptographic keys to accept open commands from Home Assistant. These keys are unique to your gateway and are stored inside the VELUX Active app on your iPhone.

### Step 1 — Install dependencies

On the computer where you will run the script:

```
pip install requests pycryptodome iphone-backup-decrypt
```

### Step 2 — Create an encrypted iPhone backup

The keys live in your iPhone's keychain, which is only included in **encrypted** backups.

**Windows (Apple Devices app):**
1. Install **Apple Devices** from the Microsoft Store if you haven't already
2. Open Apple Devices and connect your iPhone via USB
3. Click your iPhone in the left sidebar
4. Under **Backups**, select *Back up all of the data on your iPhone to this Windows PC*
5. Tick **Encrypt local backup** and set a password you will remember
6. Click **Back Up Now** and wait for it to finish

**Mac (Finder):**
1. Connect your iPhone via USB and open Finder
2. Select your iPhone in the sidebar
3. Under **Backups**, select *Back up all of the data on your iPhone to this Mac*
4. Tick **Encrypt local backup** and set a password
5. Click **Back Up Now** and wait for it to finish

> ⚠️ Make sure the VELUX Active app has successfully paired with your gateway **before** making the backup. The keys are only written to the keychain after a successful pairing.

### Step 3 — Run the key extraction script

Download [`get_velux_keys.py`](get_velux_keys.py) from this repository. Open a terminal, navigate to the folder where you saved it, and run:

```
cd path\to\folder     # e.g. cd C:\Users\YourName\Downloads
python get_velux_keys.py
```

The script will:
- Ask for your VELUX Active email and password
- Try to retrieve keys directly from the VELUX API
- If that fails, automatically locate your iPhone backup in the default Apple Devices / Finder backup folder (`%APPDATA%\Apple Computer\MobileSync\Backup` on Windows, `~/Library/Application Support/MobileSync/Backup` on Mac) — no path entry required
- Ask for the backup encryption password you set in Step 2
- Decrypt the backup keychain and print the two values you need

If you have more than one backup, the script will list them and ask you to choose.

### Step 4 — Enter the keys into Home Assistant

1. Go to **Settings → Devices & Services → VELUX Active → Configure**
2. Paste the `HashSignKey` value into the **sign_key** field
3. Paste the `SignKeyId` value into the **sign_key_id** field
4. Click **Submit** — the integration will reload automatically
5. Test by pressing **Open** on one of your VELUX windows

### Troubleshooting

| Problem | Solution |
|---------|----------|
| *Backup is NOT encrypted* | Repeat Step 2 and tick **Encrypt local backup** |
| *Wrong passphrase* | Use the password set during backup — not your Apple ID password |
| *No VELUX keys found* | Ensure the backup was made after the VELUX app paired with the gateway; delete the old backup, re-pair if needed, then back up again |
| Keys entered but windows don't open | Check you copied the full values without extra spaces and reload the integration after saving |

If you're still stuck, [open an issue](https://github.com/GMounsor/velux/issues) with the script output.

---

## Notes

- Rain detection uses the gateway's internal `is_raining` flag. The gateway raises this flag automatically when it senses rain; it cannot be triggered independently.
- Wind sensors are not part of the standard VELUX ACTIVE KIX 300 system. If you have a Netatmo anemometer connected, open an issue to discuss adding wind support.
- CO₂ and illuminance from NXS sensors require pyatmo to expose those fields natively; this is planned for a future release.
- This is an unofficial integration and is not affiliated with VELUX or Netatmo.

---

## Credits

Based on [ha-velux-active](https://github.com/Niek/ha-velux-active) by Niek, extended with binary sensor and sensor platforms.
