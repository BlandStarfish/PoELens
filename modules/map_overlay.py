"""
Map overlay module.

Tracks zone changes from Client.txt and enriches them with static zone data
(act, area level, boss, waypoint). Maintains a session history of visited zones.

TOS-safe: reads only Client.txt zone_change events via the event bus.
"""

import json
import os
import time
from typing import Callable, Optional

_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "zones.json")

_MAX_HISTORY = 15


class MapOverlay:
    def __init__(self):
        self._zone_db = self._load_zone_db()
        self._current: Optional[dict] = None
        self._history: list[dict] = []
        self._on_update: list[Callable] = []

    def on_update(self, callback: Callable):
        self._on_update.append(callback)

    def handle_zone_change(self, data: dict):
        """Called by ClientLogWatcher on zone_change events."""
        zone_name = data.get("zone", "").strip()
        if not zone_name:
            return

        entry = {
            "name": zone_name,
            "info": self._zone_db.get(zone_name),  # None if not in static data
            "timestamp": time.time(),
        }
        self._current = entry
        self._history.insert(0, entry)
        if len(self._history) > _MAX_HISTORY:
            self._history.pop()

        self._fire_update()

    def get_current_zone(self) -> Optional[dict]:
        """Returns the current zone entry, or None if no zone seen yet."""
        return self._current

    def get_history(self) -> list[dict]:
        """Returns zone history, most recent first."""
        return list(self._history)

    def _load_zone_db(self) -> dict:
        if not os.path.exists(_DATA_PATH):
            return {}
        try:
            with open(_DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f).get("zones", {})
        except Exception as e:
            print(f"[MapOverlay] failed to load zone data: {e}")
            return {}

    def _fire_update(self):
        for cb in self._on_update:
            try:
                cb(self._current)
            except Exception as e:
                print(f"[MapOverlay] callback error: {e}")
