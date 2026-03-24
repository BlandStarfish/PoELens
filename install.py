"""
ExileHUD installer.

Run once after cloning:
    python install.py

Does the following:
  1. Checks Python version (3.10+ required)
  2. Installs pip dependencies from requirements.txt
  3. Creates state/ directory and default config.json
  4. Writes run.bat for one-click launch
  5. Optionally creates a Desktop shortcut
"""

import sys
import os
import json
import subprocess
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))

# ─────────────────────────────────────────────
# 1. Python version check
# ─────────────────────────────────────────────

def check_python():
    major, minor = sys.version_info[:2]
    if major < 3 or (major == 3 and minor < 10):
        print(f"[ERROR] Python 3.10+ required. You have {major}.{minor}.")
        sys.exit(1)
    print(f"[OK]  Python {major}.{minor}")

# ─────────────────────────────────────────────
# 2. Install dependencies
# ─────────────────────────────────────────────

def install_deps():
    req = os.path.join(HERE, "requirements.txt")
    if not os.path.exists(req):
        print("[SKIP] requirements.txt not found — skipping pip install")
        return
    print("[...] Installing dependencies (this may take a minute)...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", req, "--quiet"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"[ERROR] pip install failed:\n{result.stderr}")
        sys.exit(1)
    print("[OK]  Dependencies installed")

# ─────────────────────────────────────────────
# 3. State directory and config
# ─────────────────────────────────────────────

DEFAULTS = {
    "poe_version": "poe1",
    "client_log_path": r"C:\Program Files (x86)\Grinding Gear Games\Path of Exile\logs\Client.txt",
    "league": "Standard",
    "overlay_screen": 0,
    "overlay_opacity": 0.92,
    "hotkeys": {
        "price_check":    "ctrl+d",
        "toggle_hud":     "ctrl+shift+h",
        "passive_tree":   "ctrl+shift+p",
        "crafting_queue": "ctrl+shift+c",
        "map_overlay":    "ctrl+shift+m",
    },
    "price_refresh_interval": 300,
    "currency_reset_hour": 0,
}

def setup_state():
    state_dir = os.path.join(HERE, "state")
    os.makedirs(state_dir, exist_ok=True)

    config_path = os.path.join(state_dir, "config.json")
    if os.path.exists(config_path):
        print("[OK]  state/config.json already exists — not overwritten")
        return

    # Try to auto-detect PoE log path
    candidates = [
        r"C:\Program Files (x86)\Grinding Gear Games\Path of Exile\logs\Client.txt",
        r"C:\Program Files\Grinding Gear Games\Path of Exile\logs\Client.txt",
        os.path.expanduser(r"~\AppData\Local\Path of Exile\Client.txt"),
    ]
    found_log = next((p for p in candidates if os.path.exists(p)), None)
    if found_log:
        DEFAULTS["client_log_path"] = found_log
        print(f"[OK]  Auto-detected PoE log: {found_log}")
    else:
        print("[WARN] Could not auto-detect Client.txt — edit state/config.json manually")

    with open(config_path, "w") as f:
        json.dump(DEFAULTS, f, indent=2)
    print("[OK]  state/config.json created")

# ─────────────────────────────────────────────
# 4. Write run.bat
# ─────────────────────────────────────────────

def write_run_bat():
    bat = os.path.join(HERE, "run.bat")
    if os.path.exists(bat):
        print("[OK]  run.bat already exists")
        return
    content = f'@echo off\n"{sys.executable}" "{os.path.join(HERE, "main.py")}"\n'
    with open(bat, "w") as f:
        f.write(content)
    print("[OK]  run.bat created")

# ─────────────────────────────────────────────
# 5. Optional Desktop shortcut
# ─────────────────────────────────────────────

def create_shortcut():
    try:
        import winreg
    except ImportError:
        return  # Not Windows

    answer = input("\nCreate a Desktop shortcut for ExileHUD? [y/N] ").strip().lower()
    if answer != "y":
        print("[SKIP] Desktop shortcut skipped")
        return

    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    shortcut_path = os.path.join(desktop, "ExileHUD.bat")
    bat_path = os.path.join(HERE, "run.bat")

    with open(shortcut_path, "w") as f:
        f.write(f'@echo off\nstart "" "{bat_path}"\n')
    print(f"[OK]  Desktop shortcut created: {shortcut_path}")

# ─────────────────────────────────────────────
# 6. Download passive tree data
# ─────────────────────────────────────────────

def download_tree_data():
    data_dir = os.path.join(HERE, "data")
    tree_path = os.path.join(data_dir, "passive_tree.json")
    if os.path.exists(tree_path):
        print("[OK]  data/passive_tree.json already exists")
        return

    print("[...] Downloading passive tree data from GGG CDN...")
    try:
        import urllib.request
        import re

        # Fetch the passive tree page to find the current data URL
        req_obj = urllib.request.Request(
            "https://www.pathofexile.com/passive-skill-tree",
            headers={"User-Agent": "ExileHUD/1.0 (installer)"}
        )
        with urllib.request.urlopen(req_obj, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        # Page embeds something like: "https://web.poecdn.com/.../data/SkillTree.json"
        # or the GGG export repo URL pattern
        match = (
            re.search(r'"(https://[^"]+/data/SkillTree\.json[^"]*)"', html) or
            re.search(r'"(https://[^"]+SkillTree\.json[^"]*)"', html)
        )
        if not match:
            print("[WARN] Could not find tree data URL in page — using official GGG export repo")
            _download_tree_fallback(tree_path)
            return

        tree_url = match.group(1)
        print(f"[...] Tree data URL: {tree_url[:80]}...")

        req_obj2 = urllib.request.Request(
            tree_url, headers={"User-Agent": "ExileHUD/1.0 (installer)"}
        )
        with urllib.request.urlopen(req_obj2, timeout=30) as resp:
            data = resp.read()

        with open(tree_path, "wb") as f:
            f.write(data)

        size_kb = len(data) // 1024
        print(f"[OK]  Passive tree data saved ({size_kb} KB)")

    except Exception as e:
        print(f"[WARN] Could not download passive tree data: {e}")
        print("       You can run this manually later: python -m modules.passive_tree --download")


def _download_tree_fallback(tree_path: str):
    """Use the official GGG-maintained export repo as fallback."""
    import urllib.request
    fallback = (
        "https://raw.githubusercontent.com/grindinggear/skilltree-export/master/data.json"
    )
    try:
        req = urllib.request.Request(fallback, headers={"User-Agent": "ExileHUD/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        with open(tree_path, "wb") as f:
            f.write(data)
        print(f"[OK]  Passive tree data saved from fallback ({len(data)//1024} KB)")
    except Exception as e:
        print(f"[WARN] Fallback also failed: {e}")


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("  ExileHUD Installer")
    print("=" * 50)

    check_python()
    install_deps()
    setup_state()
    write_run_bat()
    download_tree_data()
    create_shortcut()

    print("\n" + "=" * 50)
    print("  Setup complete!")
    print("  To launch ExileHUD:")
    print("    run.bat          (double-click)")
    print("    python main.py   (from terminal)")
    print("=" * 50)
