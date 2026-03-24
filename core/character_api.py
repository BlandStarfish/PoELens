"""
GGG official character API wrapper.

Uses OAuth Bearer token with scope: account:characters
API base: https://api.pathofexile.com

Endpoints:
  GET /character                — list all characters on account
  GET /character/{name}         — get full character data including passive hashes

Passive hashes are returned as integers in data["passives"]["hashes"].
These map directly to node IDs in the passive tree (same namespace as
PassiveTree.parse_tree_url output).

Disclaimer: This product isn't affiliated with or endorsed by Grinding Gear Games in any way.
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

_API_BASE     = "https://api.pathofexile.com"
_UA           = "ExileHUD/1.0 (contact: github.com/BlandStarfish/ExileHUD)"
_MIN_INTERVAL = 1.0   # minimum seconds between API requests


class CharacterAPI:
    def __init__(self, oauth_manager):
        self._oauth = oauth_manager
        self._last_request = 0.0

    def list_characters(self) -> Optional[list]:
        """
        Returns list of character summary dicts for the account, or None on error.
        Each dict contains at minimum: name, class, league, level, experience.
        """
        data = self._get("/character")
        return data.get("characters") if data is not None else None

    def get_passive_hashes(self, character_name: str) -> Optional[set]:
        """
        Returns the set of allocated passive node ID strings for the named character,
        or None on error.

        Node IDs are strings matching the keys in PassiveTree.nodes — the same format
        produced by PassiveTree.parse_tree_url().
        """
        encoded = urllib.parse.quote(character_name, safe="")
        data = self._get(f"/character/{encoded}")
        if data is None:
            return None
        hashes = data.get("passives", {}).get("hashes", [])
        return {str(h) for h in hashes}

    def get_best_character(self, league: str) -> Optional[dict]:
        """
        Returns the highest-level character in the given league, or None if
        none found or on error. Falls back to highest-level across all leagues
        if no character is in the requested league.
        """
        chars = self.list_characters()
        if not chars:
            return None
        in_league = [c for c in chars if c.get("league", "") == league]
        pool = in_league if in_league else chars
        return max(pool, key=lambda c: c.get("level", 0), default=None)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get(self, path: str) -> Optional[dict]:
        token = self._oauth.get_access_token()
        if not token:
            print("[CharacterAPI] No valid access token — authenticate first")
            return None

        gap = time.time() - self._last_request
        if gap < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - gap)

        url = _API_BASE + path
        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": _UA,
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
                    print(f"[CharacterAPI] Rate limited — retrying after {retry_after}s")
                    time.sleep(retry_after)
                    continue
                if e.code == 401:
                    print("[CharacterAPI] Unauthorized — token may be expired or revoked")
                    return None
                if e.code == 403:
                    print(
                        "[CharacterAPI] Forbidden (403) — token may lack account:characters scope. "
                        "Re-connect in the Currency tab to re-authorize with the full scope."
                    )
                    return None
                print(f"[CharacterAPI] HTTP {e.code}: {e.reason}")
                return None
            except Exception as e:
                print(f"[CharacterAPI] Request failed: {e}")
                return None

        return None
