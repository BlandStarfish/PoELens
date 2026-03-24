"""
Central configuration for ExileHUD.
Edit state/config.json to override defaults without touching this file.
"""

import json
import os

DEFAULTS = {
    # PoE version: "poe1" or "poe2"
    "poe_version": "poe1",

    # Path to Client.txt — adjust if your PoE install is elsewhere
    "client_log_path": r"C:\Program Files (x86)\Grinding Gear Games\Path of Exile\logs\Client.txt",

    # League name (used for poe.ninja lookups)
    "league": "Mirage",

    # Screen the overlay renders on (0 = primary)
    "overlay_screen": 0,

    # Overlay opacity 0.0–1.0
    "overlay_opacity": 0.92,

    # Global hotkeys
    "hotkeys": {
        "price_check": "ctrl+c",
        "toggle_hud": "ctrl+shift+h",
        "passive_tree": "ctrl+shift+p",
        "crafting_queue": "ctrl+shift+c",
        "map_overlay": "ctrl+shift+m",
    },

    # poe.ninja refresh interval in seconds
    "price_refresh_interval": 300,

    # Currency tracker reset hour (0–23, local time)
    "currency_reset_hour": 0,

    # GGG OAuth client_id for stash tab API access (auto-fill currency counts).
    # Register by emailing oauth@grindinggear.com.
    # Leave empty string to use manual spinbox entry only.
    "oauth_client_id": "",
}

_config = None
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "state", "config.json")


def load() -> dict:
    global _config
    cfg = dict(DEFAULTS)
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            overrides = json.load(f)
        cfg.update(overrides)
        if "hotkeys" in overrides:
            cfg["hotkeys"] = {**DEFAULTS["hotkeys"], **overrides["hotkeys"]}
    _config = cfg
    return cfg


def get() -> dict:
    if _config is None:
        return load()
    return _config


def save(updates: dict):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    existing = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            existing = json.load(f)
    existing.update(updates)
    with open(CONFIG_PATH, "w") as f:
        json.dump(existing, f, indent=2)
    load()
