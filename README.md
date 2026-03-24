# ExileHUD

A TOS-compliant Path of Exile overlay providing real-time quality-of-life tools as a transparent, always-on-top panel alongside the game.

---

## ⚠️ Analytics Disclosure

**This software collects anonymous usage analytics. By installing or running ExileHUD, you agree to this collection.**

When the installer completes and each time the app launches, the following data is sent to the developer:

| Field | Value |
|---|---|
| `event` | `"install"` or `"launch"` |
| `anon_id` | First 16 hex chars of SHA-256(your machine hostname). Not reversible. Not your hostname. |
| `os` | OS name and release (e.g. `Windows 11`) |
| `timestamp` | UTC timestamp of the event |

**What is NOT collected:** your PoE account name, character name, item data, currency amounts, IP address, file paths, or any gameplay data.

**If you do not consent**, do not install this software. Alternatively, clone the source and set `ANALYTICS_WEBHOOK_URL = ""` in `core/analytics.py` and `installer_gui.py` before building.

---

## Features

| Feature | Status |
|---|---|
| Quest Passive Point Tracker | ✅ Complete |
| Passive Tree Viewer + Build Import | ✅ Complete |
| Price Checking (poe.ninja + Trade API) | ✅ Complete |
| Currency Per Hour (manual + OAuth stash auto-fill) | ✅ Complete |
| Crafting Cheat Sheets + Task Queue | ✅ Complete |
| Map Overlay (zone info, resistance warnings) | ✅ Complete |

---

## Installation

### Option A — GUI Installer (recommended)

1. Download `ExileHUD-Setup.zip`
2. Extract and run `ExileHUD-Setup.exe`
3. Enter the installer password (contact the developer)
4. Follow on-screen prompts — no Python required

### Option B — From Source

Requires Python 3.10+.

```
git clone https://github.com/BlandStarfish/ExileHUD
cd ExileHUD
python install.py
python main.py
```

---

## Configuration

All settings live in `state/config.json` (created on first run). Edit this file to override defaults:

```json
{
  "league": "Mirage",
  "client_log_path": "C:\\...\\Path of Exile\\logs\\Client.txt",
  "oauth_client_id": "",
  "overlay_opacity": 0.92
}
```

### Hotkeys (defaults)

| Action | Hotkey |
|---|---|
| Price check (copy + check) | `Ctrl+C` |
| Toggle HUD visibility | `Ctrl+Shift+H` |
| Jump to Passive Tree tab | `Ctrl+Shift+P` |
| Jump to Crafting tab | `Ctrl+Shift+C` |
| Jump to Map tab | `Ctrl+Shift+M` |

### Optional: Currency Stash Auto-fill (OAuth)

To enable automatic currency reading from your stash:

1. Email `oauth@grindinggear.com` to register an OAuth client_id
2. Add it to `state/config.json`: `"oauth_client_id": "your_id_here"`
3. In the Currency tab, click **Connect PoE Account** and authorize in your browser

---

## TOS Compliance

ExileHUD is read-only and passive:

- Reads `Client.txt` log file only (no game memory access)
- Reads clipboard only (no input simulation)
- Uses only public official APIs (poe.ninja, official Trade API, official Stash API via OAuth)
- No process injection, packet interception, or automation

This product isn't affiliated with or endorsed by Grinding Gear Games in any way.

---

## Requirements

- Windows 10/11
- Path of Exile (PoE 1)
- Python 3.10+ (source install only)

See `requirements.txt` for Python package dependencies.
