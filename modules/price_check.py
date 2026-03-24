"""
Price check module.

Hotkey triggers a clipboard read of the item text (Ctrl+C in PoE copies
the item tooltip), parses the item name and type, then queries poe.ninja
for a fast price and optionally the official trade API for live listings.

TOS-safe: reads clipboard only, no game memory or process injection.
"""

import re
import threading
from typing import Callable, Optional

# Maps trade API currency keys to poe.ninja item names (for chaos normalization)
_TRADE_TO_NINJA: dict[str, str] = {
    "chaos":   "Chaos Orb",
    "divine":  "Divine Orb",
    "exalt":   "Exalted Orb",
    "alch":    "Orb of Alchemy",
    "alt":     "Orb of Alteration",
    "aug":     "Orb of Augmentation",
    "fuse":    "Orb of Fusing",
    "chance":  "Orb of Chance",
    "scour":   "Orb of Scouring",
    "regal":   "Regal Orb",
    "jew":     "Jeweller's Orb",
    "chrom":   "Chromatic Orb",
    "blessed": "Blessed Orb",
    "annul":   "Orb of Annulment",
    "mir":     "Mirror of Kalandra",
    "vaal":    "Vaal Orb",
    "ancient": "Ancient Orb",
    "harbinger": "Harbinger's Orb",
}

try:
    from PyQt6.QtWidgets import QApplication
    def _get_clipboard() -> str:
        return QApplication.clipboard().text()
except ImportError:
    import subprocess
    def _get_clipboard() -> str:
        result = subprocess.run(
            ["powershell", "-command", "Get-Clipboard"],
            capture_output=True, text=True
        )
        return result.stdout.strip()


# PoE item tooltip header pattern (Ctrl+C from in-game)
_RARITY_RE = re.compile(r"Rarity: (\w+)")
_ITEM_CLASS_RE = re.compile(r"Item Class: (.+)")


def parse_item_clipboard(text: str) -> dict:
    """
    Parse a PoE item tooltip (copied with Ctrl+C) into structured fields.
    Returns: {name, base_type, rarity, item_class, raw}
    """
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    result = {"raw": text, "name": "", "base_type": "", "rarity": "", "item_class": ""}

    for line in lines:
        if m := _RARITY_RE.match(line):
            result["rarity"] = m.group(1)
        elif m := _ITEM_CLASS_RE.match(line):
            result["item_class"] = m.group(1)

    # Item name is the first non-header line after the separator "--------"
    sections = text.split("--------")
    if sections:
        header_lines = [l.strip() for l in sections[0].splitlines() if l.strip()]
        name_lines = [l for l in header_lines if not l.startswith("Rarity:") and not l.startswith("Item Class:")]
        if len(name_lines) >= 2:
            result["name"] = name_lines[0]
            result["base_type"] = name_lines[1]
        elif name_lines:
            result["name"] = name_lines[0]
            result["base_type"] = name_lines[0]

    return result


class PriceChecker:
    def __init__(self, poe_ninja, trade_api, league: str):
        self._ninja = poe_ninja
        self._trade = trade_api
        self._league = league
        self._on_result: list[Callable] = []

    def on_result(self, callback: Callable):
        """Register callback(result_dict) for when a price check completes."""
        self._on_result.append(callback)

    def check(self):
        """
        Trigger a price check from clipboard. Runs in background thread
        so the hotkey returns immediately.
        """
        threading.Thread(target=self._do_check, daemon=True).start()

    def _do_check(self):
        import time
        time.sleep(0.15)  # give PoE time to populate clipboard after Ctrl+C
        text = _get_clipboard()
        if not text or "Rarity:" not in text:
            self._emit({"error": "No item in clipboard. Copy an item first (Ctrl+C in PoE)."})
            return

        item = parse_item_clipboard(text)
        result = {"item": item, "ninja_price": None, "trade_listings": [], "error": None}

        # Try poe.ninja first (fast, cached)
        search_name = item["name"] if item["rarity"] in ("Unique", "Divination Card") else item["base_type"]
        category = self._guess_category(item)
        ninja_price = self._ninja.get_price(search_name, category)
        result["ninja_price"] = ninja_price
        result["ninja_category"] = category

        # Try live trade API for more precise pricing
        query = self._trade.build_price_check_query(item["name"], item["base_type"] or None)
        search_result = self._trade.search_item(self._league, query)
        if search_result:
            ids = search_result.get("result", [])[:10]
            query_id = search_result.get("id", "")
            if ids:
                listings = self._trade.fetch_listings(ids, query_id)
                raw_prices = self._trade.extract_prices(listings or [])
                prices = self._normalize_prices(raw_prices)
                result["trade_listings"] = sorted(prices)[:5]
                result["trade_url"] = f"https://www.pathofexile.com/trade/search/{self._league}/{query_id}"

        self._emit(result)

    def _normalize_prices(self, raw_prices: list[dict]) -> list[float]:
        """Convert trade API price dicts (amount + currency key) to chaos equivalents."""
        result = []
        for p in raw_prices:
            currency_key = p.get("currency", "")
            amount = p.get("amount", 0.0)
            if not amount:
                continue
            if currency_key == "chaos":
                result.append(amount)
            else:
                ninja_name = _TRADE_TO_NINJA.get(currency_key)
                if ninja_name:
                    chaos_val = self._ninja.get_price(ninja_name, "Currency")
                    result.append(amount * chaos_val if chaos_val else amount)
                else:
                    result.append(amount)  # unknown currency — pass through as-is
        return result

    def _guess_category(self, item: dict) -> str:
        ic = item.get("item_class", "").lower()
        rarity = item.get("rarity", "").lower()
        if "currency" in ic:
            return "Currency"
        if "divination" in ic:
            return "DivinationCard"
        if "gem" in ic:
            return "SkillGem"
        if "flask" in ic and rarity == "unique":
            return "UniqueFlask"
        if "jewel" in ic and rarity == "unique":
            return "UniqueJewel"
        if rarity == "unique":
            # Guess from item class
            if any(x in ic for x in ["sword", "axe", "mace", "bow", "wand", "stave", "dagger", "claw", "sceptre", "spear", "flail"]):
                return "UniqueWeapon"
            if any(x in ic for x in ["helmet", "body", "gloves", "boots", "shield", "quiver", "armour"]):
                return "UniqueArmour"
            return "UniqueAccessory"
        return "BaseType"

    def _emit(self, result: dict):
        for cb in self._on_result:
            try:
                cb(result)
            except Exception as e:
                print(f"[PriceChecker] callback error: {e}")
