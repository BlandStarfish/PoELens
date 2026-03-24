"""
poe.ninja price cache.
Fetches currency and item prices and keeps them in memory with a TTL.
TOS-safe: uses only public poe.ninja endpoints, no game process interaction.
"""

import requests
import time
from typing import Optional

BASE = "https://poe.ninja/api/data"

# Maps item category names to poe.ninja endpoint slugs
ITEM_ENDPOINTS = {
    "Currency":        ("currencyoverview", "Currency"),
    "Fragment":        ("currencyoverview", "Fragment"),
    "Oil":             ("itemoverview",     "Oil"),
    "Incubator":       ("itemoverview",     "Incubator"),
    "Scarab":          ("itemoverview",     "Scarab"),
    "Fossil":          ("itemoverview",     "Fossil"),
    "Resonator":       ("itemoverview",     "Resonator"),
    "Essence":         ("itemoverview",     "Essence"),
    "DivinationCard":  ("itemoverview",     "DivinationCard"),
    "UniqueWeapon":    ("itemoverview",     "UniqueWeapon"),
    "UniqueArmour":    ("itemoverview",     "UniqueArmour"),
    "UniqueAccessory": ("itemoverview",     "UniqueAccessory"),
    "UniqueFlask":     ("itemoverview",     "UniqueFlask"),
    "UniqueJewel":     ("itemoverview",     "UniqueJewel"),
    "SkillGem":        ("itemoverview",     "SkillGem"),
    "BaseType":        ("itemoverview",     "BaseType"),
}


class PoeNinja:
    def __init__(self, league: str, ttl: int = 300):
        self._league = league
        self._ttl = ttl
        self._cache: dict[str, tuple[float, dict]] = {}  # category -> (timestamp, prices)

    def get_price(self, item_name: str, category: str = "Currency") -> Optional[float]:
        """
        Returns chaos value of item_name in the given category, or None if not found.
        """
        prices = self._get_category(category)
        return prices.get(item_name)

    def get_all(self, category: str) -> dict:
        """Returns {item_name: chaos_value} for the whole category."""
        return dict(self._get_category(category))

    def _get_category(self, category: str) -> dict:
        cached = self._cache.get(category)
        if cached and (time.time() - cached[0]) < self._ttl:
            return cached[1]
        prices = self._fetch(category)
        self._cache[category] = (time.time(), prices)
        return prices

    def _fetch(self, category: str) -> dict:
        if category not in ITEM_ENDPOINTS:
            return {}
        endpoint, type_name = ITEM_ENDPOINTS[category]
        url = f"{BASE}/{endpoint}?league={self._league}&type={type_name}"
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"[poe.ninja] fetch failed ({category}): {e}")
            return {}

        prices = {}
        if endpoint == "currencyoverview":
            for entry in data.get("lines", []):
                prices[entry["currencyTypeName"]] = entry.get("chaosEquivalent", 0)
        else:
            for entry in data.get("lines", []):
                prices[entry["name"]] = entry.get("chaosValue", 0)
        return prices

    def set_league(self, league: str):
        self._league = league
        self._cache.clear()
