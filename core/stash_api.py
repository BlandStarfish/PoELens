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

# Stash tab types that will never contain rare equipment (skip for chaos recipe scan)
_EQUIPMENT_SKIP_TYPES = frozenset([
    "CurrencyStash", "Currency",
    "FragmentStash", "Fragment",
    "MapStash",      "Map",
    "DivinationStash",
    "UniqueStash",
    "GemStash",
    "DeliriumStash",
    "BlightStash",
    "MetamorphStash",
    "BreachStash",
])
_CONTACT      = "github.com/BlandStarfish/PoELens"
_MIN_INTERVAL = 1.0   # minimum seconds between API requests (GGG rate limit respect)


def _ua(client_id: str) -> str:
    """
    GGG-required User-Agent format for OAuth API consumers:
    OAuth {clientId}/{version} (contact: {contact})
    See: pathofexile.com/developer/docs
    """
    return f"OAuth {client_id}/1.0 (contact: {_CONTACT})"

_TRACKED_SET: frozenset[str] = frozenset(TRACKED_CURRENCIES)

# Rogue job names used in Heist contract/blueprint requirements
_HEIST_JOBS = frozenset([
    "Lockpicking", "Agility", "Brute Force", "Counter-Thaumaturgy",
    "Deception", "Demolition", "Engineering", "Perception", "Trap Disarmament",
])


def _extract_heist_job(requirements: list) -> tuple[str, int]:
    """
    Extract rogue job name and required level from a Heist item's requirements array.
    Returns ("Unknown", 0) if no job requirement is found.
    """
    for req in requirements:
        name = req.get("name", "")
        if name in _HEIST_JOBS:
            values = req.get("values", [])
            level  = int(values[0][0]) if values and values[0] else 0
            return name, level
    return "Unknown", 0


def _extract_wing_status(additional_properties: list) -> tuple[int, int]:
    """
    Extract wings unlocked count from a Blueprint's additionalProperties array.
    Looks for a "Wings Unlocked" property with value like "2/4".
    Returns (unlocked, total) as ints; defaults to (0, 0) if not found.
    """
    for prop in additional_properties:
        if prop.get("name") == "Wings Unlocked":
            values = prop.get("values", [])
            if values:
                text = str(values[0][0]) if values[0] else "0/0"
                parts = text.split("/")
                if len(parts) == 2:
                    try:
                        return int(parts[0]), int(parts[1])
                    except ValueError:
                        pass
    return 0, 0


def _parse_map_item(item: dict) -> dict:
    """
    Parse a single stash API map item dict into a normalized display dict.

    Extracts Map Tier, Item Quantity, Item Rarity, and Monster Pack Size from
    the GGG item properties array. Each property has the form:
      {"name": "Map Tier", "values": [["14", 0]], ...}
    where values[0][0] is the display string.
    """
    props: dict[str, str] = {}
    for p in item.get("properties", []):
        name   = p.get("name", "")
        values = p.get("values", [])
        if values and values[0]:
            props[name] = str(values[0][0])

    def _pct(key: str) -> int:
        raw = props.get(key, "0")
        try:
            return int(raw.strip("+% "))
        except ValueError:
            return 0

    try:
        tier = int(props.get("Map Tier", "0").strip())
    except ValueError:
        tier = 0

    return {
        "name":       item.get("typeLine", "Unknown"),
        "tier":       tier,
        "rarity":     item.get("rarity", "Normal"),
        "identified": item.get("identified", True),
        "iiq":        _pct("Item Quantity"),
        "iir":        _pct("Item Rarity"),
        "pack_size":  _pct("Monster Pack Size"),
        "mods":       item.get("explicitMods", []),
    }


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

    def get_all_stash_items(self, league: str, max_tabs: int = 20) -> list[dict]:
        """
        Fetch items from all equipment stash tabs (skips Currency, Map, Fragment, etc.).

        Returns a flat list of item dicts. Respects rate limits — each tab costs one API call.
        max_tabs limits how many tabs are scanned to bound the total request time.
        """
        tabs = self.list_tabs(league)
        if tabs is None:
            return []

        eligible = [
            t for t in tabs
            if t.get("type") not in _EQUIPMENT_SKIP_TYPES
        ][:max_tabs]

        items: list[dict] = []
        for tab in eligible:
            tab_id = tab.get("id")
            if not tab_id:
                continue
            tab_data = self.get_tab(league, tab_id)
            if tab_data is None:
                continue
            tab_items = tab_data.get("stash", {}).get("items", [])
            items.extend(tab_items)

        return items

    def get_heist_items(self, league: str) -> dict:
        """
        Scan all stash tabs for Heist Contracts and Blueprints.

        Returns:
          {
            "contracts":  list of contract item dicts (with name, ilvl, job, job_level)
            "blueprints": list of blueprint item dicts (with name, ilvl, wings_unlocked, wings_total)
          }

        Contract typeLine starts with "Contract:".
        Blueprint typeLine starts with "Blueprint:".
        Job type is extracted from the requirements array (non-Level entries).
        Returns empty lists on error.
        """
        tabs = self.list_tabs(league)
        if tabs is None:
            return {"contracts": [], "blueprints": []}

        contracts: list[dict] = []
        blueprints: list[dict] = []

        for tab in tabs:
            tab_id = tab.get("id")
            if not tab_id:
                continue
            tab_data = self.get_tab(league, tab_id)
            if tab_data is None:
                continue
            for item in tab_data.get("stash", {}).get("items", []):
                type_line = item.get("typeLine", "")
                if type_line.startswith("Contract:"):
                    name      = type_line[len("Contract:"):].strip()
                    job, level = _extract_heist_job(item.get("requirements", []))
                    contracts.append({
                        "name":      name,
                        "ilvl":      item.get("ilvl", 0),
                        "job":       job,
                        "job_level": level,
                    })
                elif type_line.startswith("Blueprint:"):
                    name = type_line[len("Blueprint:"):].strip()
                    unlocked, total = _extract_wing_status(item.get("additionalProperties", []))
                    job, level      = _extract_heist_job(item.get("requirements", []))
                    blueprints.append({
                        "name":          name,
                        "ilvl":          item.get("ilvl", 0),
                        "job":           job,
                        "job_level":     level,
                        "wings_unlocked": unlocked,
                        "wings_total":   total,
                    })

        return {"contracts": contracts, "blueprints": blueprints}

    def get_map_items(self, league: str) -> list[dict]:
        """
        Scan MapStash tabs and return map item data with rolled mod info.

        Returns a list of dicts:
          name:        map name (typeLine)
          tier:        int (from Map Tier property, 0 if unknown)
          rarity:      str ("Normal", "Magic", "Rare", "Unique")
          identified:  bool
          iiq:         int (item quantity bonus %)
          iir:         int (item rarity bonus %)
          pack_size:   int (monster pack size bonus %)
          mods:        list[str] (explicit mod strings, human-readable)

        Sorted by tier descending, then map name ascending.
        Returns [] on error or if no MapStash tab exists.
        """
        tabs = self.list_tabs(league)
        if tabs is None:
            return []

        map_tabs = [t for t in tabs if t.get("type") == "MapStash"]
        if not map_tabs:
            return []

        results: list[dict] = []
        for tab in map_tabs:
            tab_id = tab.get("id")
            if not tab_id:
                continue
            tab_data = self.get_tab(league, tab_id)
            if tab_data is None:
                continue
            for item in tab_data.get("stash", {}).get("items", []):
                results.append(_parse_map_item(item))

        results.sort(key=lambda m: (-m["tier"], m["name"]))
        return results

    def get_divination_items(self, league: str) -> dict[str, int]:
        """
        Fetch all DivinationStash tabs and return {card_name: count}.

        Only scans tabs with type "DivinationStash". Returns {} on error or
        if no divination stash tab exists.
        """
        tabs = self.list_tabs(league)
        if tabs is None:
            return {}

        div_tabs = [t for t in tabs if t.get("type") == "DivinationStash"]
        if not div_tabs:
            return {}

        totals: dict[str, int] = {}
        for tab in div_tabs:
            tab_id = tab.get("id")
            if not tab_id:
                continue
            tab_data = self.get_tab(league, tab_id)
            if tab_data is None:
                continue
            for item in tab_data.get("stash", {}).get("items", []):
                name = item.get("typeLine", "")
                if name:
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
