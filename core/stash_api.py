"""
GGG official stash tab API wrapper.

Uses OAuth Bearer token with scope: account:stashes
API base: https://api.pathofexile.com

Endpoints:
  GET /stash/{realm}/{league}              — list stash tabs
  GET /stash/{realm}/{league}/{stash_id}   — get tab contents

realm is typically "pc" for PC players (alternatives: "xbox", "sony").

Disclaimer: This product isn't affiliated with or endorsed by Grinding Gear Games in any way.
"""

import json
import time
import urllib.error
import urllib.request
from typing import Optional

from modules.currency_tracker import TRACKED_CURRENCIES

_API_BASE     = "https://api.pathofexile.com"
_CONTACT      = "github.com/BlandStarfish/ExileHUD"
_MIN_INTERVAL = 1.0   # minimum seconds between API requests (GGG rate limit respect)


def _ua(client_id: str) -> str:
    """
    GGG-required User-Agent format for OAuth API consumers:
    OAuth {clientId}/{version} (contact: {contact})
    See: pathofexile.com/developer/docs
    """
    return f"OAuth {client_id}/1.0 (contact: {_CONTACT})"

_TRACKED_SET: frozenset[str] = frozenset(TRACKED_CURRENCIES)


class StashAPI:
    def __init__(self, oauth_manager, realm: str = "pc"):
        self._oauth = oauth_manager
        self._realm = realm
        self._last_request = 0.0

    def list_tabs(self, league: str) -> Optional[list]:
        """
        Returns list of stash tab summary dicts for the league, or None on error.
        Each tab dict contains at minimum: id, name, type, index.
        """
        data = self._get(f"/stash/{self._realm}/{league}")
        return data.get("stashes") if data is not None else None

    def get_tab(self, league: str, stash_id: str) -> Optional[dict]:
        """
        Returns full stash tab data (including items) for stash_id, or None on error.
        """
        return self._get(f"/stash/{self._realm}/{league}/{stash_id}")

    def get_currency_amounts(self, league: str) -> dict[str, int]:
        """
        Fetch all currency stash tabs and aggregate tracked currency counts.

        Prefers tabs with type "CurrencyStash". Falls back to the first 3
        premium/normal stash tabs if no dedicated currency tab exists.

        Returns {currency_name: count} for currencies in TRACKED_CURRENCIES only.
        Returns {} on API error or if no tabs are accessible.
        """
        tabs = self.list_tabs(league)
        if tabs is None:
            return {}

        currency_tabs = [t for t in tabs if t.get("type") in ("CurrencyStash", "Currency")]
        if not currency_tabs:
            # No dedicated currency tab — check first 3 normal stash tabs
            currency_tabs = [
                t for t in tabs
                if t.get("type") in ("PremiumStash", "NormalStash")
            ][:3]

        if not currency_tabs:
            return {}

        totals: dict[str, int] = {}
        for tab in currency_tabs:
            tab_id = tab.get("id")
            if not tab_id:
                continue
            tab_data = self.get_tab(league, tab_id)
            if tab_data is None:
                continue
            items = tab_data.get("stash", {}).get("items", [])
            for item in items:
                name = item.get("typeLine", "")
                if name in _TRACKED_SET:
                    totals[name] = totals.get(name, 0) + item.get("stackSize", 1)

        return totals

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get(self, path: str) -> Optional[dict]:
        token = self._oauth.get_access_token()
        if not token:
            print("[StashAPI] No valid access token — authenticate first")
            return None

        # Enforce minimum interval between requests
        gap = time.time() - self._last_request
        if gap < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - gap)

        url = _API_BASE + path
        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": _ua(self._oauth.client_id),
        }

        for attempt in range(2):
            req = urllib.request.Request(url, headers=headers)
            try:
                self._last_request = time.time()
                with urllib.request.urlopen(req, timeout=15) as resp:
                    return json.loads(resp.read())
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt == 0:
                    retry_after = int(e.headers.get("Retry-After", "5"))
                    print(f"[StashAPI] Rate limited — retrying after {retry_after}s")
                    time.sleep(retry_after)
                    continue
                if e.code == 401:
                    print("[StashAPI] Unauthorized — token may be expired or revoked")
                    return None
                print(f"[StashAPI] HTTP {e.code}: {e.reason}")
                return None
            except Exception as e:
                print(f"[StashAPI] Request failed: {e}")
                return None

        return None
