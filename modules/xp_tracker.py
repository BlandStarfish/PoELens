"""
XP rate tracker.

Polls the GGG Character API (OAuth account:characters scope) to track XP/hr
for the current session. Polls on zone_change events (rate-limited) and via
a periodic timer in the XP panel.
"""

import threading
import time
from typing import Callable

# Minimum seconds between zone-change-triggered polls (avoid API spam)
_ZONE_POLL_COOLDOWN = 120.0


class XPTracker:
    def __init__(self, state, character_api):
        self._state = state
        self._character_api = character_api
        self._on_update: list[Callable] = []
        self._last_zone_poll = 0.0
        # Propagate new-character resets to the XP panel immediately
        state.on_change("xp_session", lambda _: self._fire_update())

    def on_update(self, callback: Callable):
        self._on_update.append(callback)

    def handle_zone_change(self, _data: dict):
        """
        Called on zone_change events (from ClientLogWatcher background thread).
        Triggers a background XP poll if a session is active and the cooldown has elapsed.
        """
        if not self._state.xp_session_start:
            return
        now = time.time()
        if now - self._last_zone_poll >= _ZONE_POLL_COOLDOWN:
            self._last_zone_poll = now
            threading.Thread(target=self._do_poll, daemon=True).start()

    def start_session(self, league: str, on_started: Callable[[bool, str], None]):
        """
        Fetch current XP from the best character in league and start a session.
        Runs in a background thread; calls on_started(ok, char_name_or_error) on completion.
        """
        def _fetch():
            char = self._character_api.get_best_character(league)
            if char is None:
                on_started(False, "Could not fetch character data — check OAuth connection")
                return
            xp    = char.get("experience", 0)
            level = char.get("level", 0)
            name  = char.get("name", "")
            self._state.start_xp_session(name, xp, level)
            self._fire_update()
            on_started(True, name)

        threading.Thread(target=_fetch, daemon=True).start()

    def poll(self):
        """Trigger an immediate XP poll in a background thread."""
        threading.Thread(target=self._do_poll, daemon=True).start()

    def get_display_data(self) -> dict:
        return self._state.get_xp_display_data()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _do_poll(self):
        """Fetch current XP for the tracked character and update state."""
        char_name = self._state.xp_session_char
        if not char_name:
            return
        chars = self._character_api.list_characters()
        if chars is None:
            return
        char = next((c for c in chars if c.get("name") == char_name), None)
        if char is None:
            print(f"[XPTracker] Character '{char_name}' not found in account list")
            return
        xp    = char.get("experience", 0)
        level = char.get("level", 0)
        self._state.update_xp(xp, level)
        self._fire_update()

    def _fire_update(self):
        data = self.get_display_data()
        for cb in self._on_update:
            try:
                cb(data)
            except Exception as e:
                print(f"[XPTracker] callback error: {e}")
