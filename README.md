# Velux Active — Home Assistant Integration

> ⚠️ **EXPERIMENTAL — USE AT YOUR OWN RISK**
>
> This is an unofficial, community-built integration. It is not affiliated with, endorsed by, or supported by VELUX or Netatmo. It is provided **as-is, with no warranties of any kind** — express or implied. Use of this integration is entirely at your own risk. The authors accept no responsibility for any damage, data loss, malfunction, or unexpected behaviour of your devices. Always ensure you have a way to control your windows and blinds independently of Home Assistant before using this integration.

---

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

## Part 1 — Installing the integration

### Step 1 — Install HACS (if you haven't already)

HACS is the Home Assistant Community Store. It lets you install custom integrations like this one. If you already have HACS installed, skip to Step 2.

1. In Home Assistant, go to **Settings → Add-ons** and make sure you are running Home Assistant OS or Supervised (HACS requires add-on support).
2. Follow the official HACS installation guide at [hacs.xyz/docs/setup/download](https://hacs.xyz/docs/setup/download).
3. Once installed, restart Home Assistant when prompted.

### Step 2 — Add this repository to HACS

1. In Home Assistant, click **HACS** in the left sidebar.
2. Click **Integrations**.
3. Click the three-dot menu (⋮) in the top-right corner and choose **Custom repositories**.
4. In the **Repository** box, paste: `https://github.com/GMounsor/Velux`
5. Set **Category** to **Integration**.
6. Click **Add**.

### Step 3 — Install the integration

1. Still in HACS → **Integrations**, use the search box to find **Velux Active**.
2. Click on it, then click **Download** (bottom right).
3. When asked, confirm the download.
4. **Restart Home Assistant**: go to **Settings → System → Restart** and click **Restart Home Assistant**.

### Step 4 — Add the integration to Home Assistant

1. Go to **Settings → Devices & Services**.
2. Click **+ Add Integration** (bottom right).
3. Search for **Velux Active** and click on it.
4. Enter the **email address** and **password** you use to log in to the VELUX Active app on your phone.
5. Click **Submit**.

Your blinds and awning blinds will now appear in Home Assistant. VELUX windows (the kind that tilt or swing open) need two extra keys — see Part 2 below.

---

## Part 2 — Enabling window open/close (signing keys)

Blinds and awning blinds work straight away. **VELUX windows** (actuators that physically open) require two additional security keys before Home Assistant can send open and close commands. These keys are unique to your gateway and are stored inside the VELUX Active app on your iPhone.

The steps below use a script to extract them safely from an encrypted iPhone backup on your computer. Your keys never leave your machine.

### Step 1 — Install Python

The extraction script requires Python 3.8 or newer. To check if you already have it:

- **Windows**: Open Command Prompt (press `Win+R`, type `cmd`, press Enter) and run `python --version`. If you see `Python 3.x.x` you are ready. If not, download Python from [python.org/downloads](https://www.python.org/downloads/) — click the big **Download Python** button, run the installer, and tick **"Add Python to PATH"** before clicking Install.
- **Mac**: Open Terminal (press `Cmd+Space`, type `Terminal`, press Enter) and run `python3 --version`. macOS usually includes Python 3.

### Step 2 — Install the required Python libraries

In the same Command Prompt or Terminal window, paste this command and press Enter:

```
pip install requests pycryptodome iphone-backup-decrypt
```

Wait for it to finish. You should see lines ending in "Successfully installed". If you see a "pip not found" error on Windows, try `python -m pip install requests pycryptodome iphone-backup-decrypt` instead.

### Step 3 — Download the key extraction script

1. Go to [github.com/GMounsor/Velux](https://github.com/GMounsor/Velux).
2. Click on the file **`get_velux_keys.py`**.
3. Click the **Download raw file** button (the download icon near the top right).
4. Save it somewhere easy to find, such as your **Downloads** folder.

### Step 4 — Create an encrypted iPhone backup

The keys are stored in your iPhone's keychain, which is only included in **encrypted** backups. If you already have an encrypted backup of your iPhone on this computer, skip to Step 5.

> ⚠️ Make sure the VELUX Active app is installed on your iPhone and has **successfully connected to your gateway** before making the backup. The keys are only stored after a successful pairing.

**On Windows (using Apple Devices):**

1. If you don't have it, install **Apple Devices** from the Microsoft Store (search "Apple Devices" — it's the free app by Apple).
2. Connect your iPhone to your computer with a USB cable.
3. If your iPhone asks "Trust This Computer?", tap **Trust** and enter your iPhone passcode.
4. Open the **Apple Devices** app. Your iPhone should appear in the left sidebar — click on it.
5. Under the **Backups** section, select **Back up all of the data on your iPhone to this Windows PC**.
6. Tick the box **Encrypt local backup** and set a password. Write this password down — you will need it in Step 5.
7. Click **Back Up Now** and wait for it to finish (this may take several minutes).

**On Mac (using Finder):**

1. Connect your iPhone to your Mac with a USB cable.
2. If your iPhone asks "Trust This Computer?", tap **Trust** and enter your iPhone passcode.
3. Open **Finder** (the smiley face icon in your Dock).
4. Your iPhone will appear in the left sidebar under **Locations** — click on it.
5. Click the **General** tab, then under **Backups**, select **Back up all of the data on your iPhone to this Mac**.
6. Tick **Encrypt local backup** and set a password. Write this password down — you will need it in Step 5.
7. Click **Back Up Now** and wait for it to finish.

### Step 5 — Run the key extraction script

1. Open Command Prompt (Windows) or Terminal (Mac).
2. Navigate to the folder where you saved `get_velux_keys.py`. For example, if you saved it to your Downloads folder:
   - **Windows**: `cd %USERPROFILE%\Downloads`
   - **Mac**: `cd ~/Downloads`
3. Run the script:
   - **Windows**: `python get_velux_keys.py`
   - **Mac**: `python3 get_velux_keys.py`
4. The script will ask for your **VELUX Active app email and password** — enter them and press Enter.
5. When asked if you have an encrypted backup, type `y` and press Enter.
6. The script will find your backup automatically. If you have more than one backup listed, enter the number next to your iPhone and press Enter.
7. Enter the **backup encryption password** you set in Step 4 (the characters won't appear as you type — this is normal).

The script will print two values:

```
HashSignKey  (sign_key)    : xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SignKeyId    (sign_key_id) : XXXXXXXXXXXXXXXXXXXXXXXX==
```

Copy both values — you will need them in the next step.

### Step 6 — Enter the keys into Home Assistant

1. In Home Assistant, go to **Settings → Devices & Services**.
2. Find the **VELUX Active** integration and click **Configure**.
3. Paste the `HashSignKey` value into the **sign_key** field.
4. Paste the `SignKeyId` value into the **sign_key_id** field.
5. Click **Submit**. The integration will reload automatically.
6. Test it by going to a VELUX window in Home Assistant and pressing **Open**.

### Troubleshooting

| Problem | What to try |
|---------|-------------|
| `pip` command not found | Try `python -m pip install ...` instead, or reinstall Python with "Add to PATH" ticked |
| *Backup is NOT encrypted* | Repeat Step 4 — make sure to tick **Encrypt local backup** |
| *Wrong passphrase* | Use the password you set when creating the backup. This is not your Apple ID password. |
| *No VELUX keys found* | Make sure the VELUX app has paired with your gateway, then delete the old backup, re-pair the app if needed, and create a fresh encrypted backup |
| Script finds no backup | Make sure the backup finished successfully in Apple Devices or Finder |
| Keys entered but windows don't open | Check you copied the full values with no extra spaces; reload the integration after saving |

If you are still stuck, [open an issue](https://github.com/GMounsor/velux/issues) and include the output printed by the script.

---

## Notes

- Rain detection uses the gateway's internal `is_raining` flag. The gateway raises this flag automatically when it senses rain; it cannot be triggered independently.
- Wind sensors are not part of the standard VELUX ACTIVE KIX 300 system. If you have a Netatmo anemometer connected, open an issue to discuss adding wind support.
- CO₂ and illuminance from NXS sensors require pyatmo to expose those fields natively; this is planned for a future release.
- This is an unofficial integration and is not affiliated with VELUX or Netatmo.

---

## Credits

Based on [ha-velux-active](https://github.com/Niek/ha-velux-active) by Niek, extended with binary sensor and sensor platforms.
