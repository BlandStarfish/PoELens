"""
Map Stash Scanner.

Scans MapStash tabs via the OAuth Stash API to display rolled map affix
information (IIQ/IIR/pack size and explicit mods) for all maps in the
player's stash.

Requires OAuth (account:stashes scope). Scan is user-triggered.

TOS: reads stash via official OAuth API only. No game memory access.
"""

import threading
from typing import Callable


class MapStashScanner:
    def __init__(self, stash_api):
        self._stash_api    = stash_api
        self._on_update:   list[Callable] = []
        self._last_result: list[dict] | None = None

    def on_update(self, callback: Callable):
        self._on_update.append(callback)

    def scan(self, league: str, on_done: Callable[[bool, str], None]):
        """
        Scan MapStash tabs for rolled map items with mod info.
        Runs in a background thread; calls on_done(ok, error_msg) when complete.
        Result is a list of map dicts sorted by tier desc, then name asc.
        """
        def _fetch():
            try:
                maps = self._stash_api.get_map_items(league)
                self._last_result = maps
                self._fire_update()
                on_done(True, "")
            except Exception as e:
                on_done(False, str(e))

        threading.Thread(target=_fetch, daemon=True).start()

    def get_last_result(self) -> list[dict] | None:
        return self._last_result

    def _fire_update(self):
        if self._last_result is None:
            return
        for cb in self._on_update:
            try:
                cb(self._last_result)
            except Exception as e:
                print(f"[MapStashScanner] callback error: {e}")
