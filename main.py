"""
ExileHUD — Path of Exile TOS-compliant overlay.

Entry point. Wires together all modules and launches the PyQt6 overlay.

Usage:
    python main.py
    python main.py --config state/config.json
"""

import sys
import argparse

# Crash reporter goes in before anything else so all errors are caught
from core.crash_reporter import install as install_crash_reporter
install_crash_reporter()

from core.analytics import track as _track
_track("launch")

# Bootstrap check
try:
    from PyQt6.QtWidgets import QApplication
except ImportError:
    print("Missing dependencies. Run: pip install -r requirements.txt")
    sys.exit(1)

import config as cfg
from core.client_log import ClientLogWatcher
from core.state import AppState
from core.hotkeys import HotkeyManager
from core.oauth import OAuthManager
from core.stash_api import StashAPI
from core.updater import check_and_prompt as check_for_updates
from api.poe_ninja import PoeNinja
from api.poe_trade import build_price_check_query, search_item, fetch_listings, extract_prices
from modules.quest_tracker import QuestTracker
from modules.price_check import PriceChecker
from modules.currency_tracker import CurrencyTracker
from modules.crafting import CraftingModule
from modules.map_overlay import MapOverlay

# Lazy UI import — avoids loading Qt before QApplication exists
import ui.hud as hud_module


def main():
    parser = argparse.ArgumentParser(description="ExileHUD overlay")
    parser.add_argument("--config", help="Path to config JSON override file")
    args = parser.parse_args()

    conf = cfg.load()

    # Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("ExileHUD")
    app.setQuitOnLastWindowClosed(False)

    # Check for updates in background (shows dialog on main thread if found)
    check_for_updates()

    # Core services
    state = AppState()
    ninja = PoeNinja(league=conf["league"], ttl=conf["price_refresh_interval"])

    # Shim trade API functions into an object PriceChecker expects
    class TradeAPI:
        def build_price_check_query(self, name, base): return build_price_check_query(name, base)
        def search_item(self, league, query): return search_item(league, query)
        def fetch_listings(self, ids, qid): return fetch_listings(ids, qid)
        def extract_prices(self, listings): return extract_prices(listings)

    # OAuth + stash API (optional — requires client_id registration with GGG)
    oauth_manager = OAuthManager(conf.get("oauth_client_id", ""))
    stash_api     = StashAPI(oauth_manager)

    # Modules
    quest_tracker    = QuestTracker(state)
    price_checker    = PriceChecker(ninja, TradeAPI(), conf["league"])
    currency_tracker = CurrencyTracker(state, ninja)
    crafting         = CraftingModule(state, ninja)
    map_overlay      = MapOverlay()

    # Client.txt watcher
    log_watcher = ClientLogWatcher(conf["client_log_path"])
    log_watcher.on("zone_change",   lambda d: state.set_zone(d["zone"]))
    log_watcher.on("zone_change",   map_overlay.handle_zone_change)
    log_watcher.on("quest_complete", quest_tracker.handle_quest_event)
    log_watcher.start()

    # Hotkeys
    hk = HotkeyManager(conf["hotkeys"])

    # Build HUD
    hud = hud_module.HUD(
        state=state,
        quest_tracker=quest_tracker,
        price_checker=price_checker,
        currency_tracker=currency_tracker,
        crafting=crafting,
        map_overlay=map_overlay,
        config=conf,
        oauth_manager=oauth_manager,
        stash_api=stash_api,
    )

    # Wire hotkeys to HUD actions
    hk.register("price_check",   price_checker.check)
    hk.register("toggle_hud",    hud.toggle)
    hk.register("passive_tree",  hud.show_passive_tree)
    hk.register("crafting_queue", hud.show_crafting)
    hk.register("map_overlay",   hud.show_map)

    hud.show()
    exit_code = app.exec()
    hk.unregister_all()
    log_watcher.stop()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
