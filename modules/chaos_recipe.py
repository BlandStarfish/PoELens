"""
Chaos Recipe Counter.

Scans stash tabs via the OAuth Stash API to count complete rare item sets
for the Chaos Orb / Regal Orb vendor recipes.

Chaos Orb recipe:  full set of rares, ilvl 60-74 (all unidentified = 2 chaos)
Regal Orb recipe:  full set of rares, ilvl 75+    (all unidentified = 2 regal)

Full set = 1 helmet + 1 chest + 1 gloves + 1 boots + 1 belt
         + 2 rings + 1 amulet + 1 weapon slot
Weapon slot = 1× two-handed weapon  OR  1× one-handed weapon + 1× offhand

TOS: reads stash via official OAuth API only. No game memory access.
"""

import threading
from typing import Callable

# PoE item frameType: 2 = Rare
_RARE_FRAME = 2

# Item level thresholds
_CHAOS_MIN = 60
_REGAL_MIN = 75

# Recipe slot names (matches UI display)
SLOTS = ("helmet", "chest", "gloves", "boots", "belt", "ring", "amulet", "weapon")

# Rings needed per set
_RINGS_PER_SET = 2


def _get_slot(item: dict) -> str | None:
    """
    Determine the chaos recipe slot for an item using its category field.

    Category format (GGG stash API):
      {"armour": ["helmet"]}          → helmet / chest / gloves / boots
      {"accessories": ["ring"]}       → ring / amulet / belt
      {"weapons": ["twohanded", ...]} → weapon (two-handed)
      {"weapons": ["onehanded", ...]} → weapon_1h (one-handed, needs offhand)
      {"offhand": [...]}              → offhand (shield / quiver)
    """
    cat = item.get("category")
    if not isinstance(cat, dict):
        return None

    if "armour" in cat:
        sub = (cat["armour"] or [""])[0]
        mapping = {"helmet": "helmet", "chest": "chest", "gloves": "gloves", "boots": "boots"}
        return mapping.get(sub)

    if "accessories" in cat:
        sub = (cat["accessories"] or [""])[0]
        mapping = {"ring": "ring", "amulet": "amulet", "belt": "belt"}
        return mapping.get(sub)

    if "weapons" in cat:
        sub = (cat["weapons"] or [""])[0]
        return "weapon_2h" if sub == "twohanded" else "weapon_1h"

    if "offhand" in cat:
        return "offhand"

    return None


def count_sets(items: list[dict]) -> dict:
    """
    Count complete chaos and regal recipe sets from a list of stash items.

    Returns:
      {
        "chaos_sets":  int — complete sets using ilvl 60-74 items only
        "regal_sets":  int — complete sets using ilvl 75+ items only
        "any_sets":    int — complete sets using any qualifying items (ilvl 60+)
        "unid_sets":   int — complete sets where all items are unidentified (2x yield)
        "counts":      {slot: {"chaos": n, "regal": n, "any": n, "unid": n}}
        "missing":     [slot, ...] — slots blocking the next complete any_set
      }
    """
    # Per-slot counts by tier; "unid" tracks unidentified rares (any ilvl 60+)
    by_slot: dict[str, dict[str, int]] = {
        s: {"chaos": 0, "regal": 0, "unid": 0}
        for s in ("helmet", "chest", "gloves", "boots", "belt",
                  "ring", "amulet", "weapon_2h", "weapon_1h", "offhand")
    }

    for item in items:
        if item.get("frameType") != _RARE_FRAME:
            continue
        ilvl = item.get("ilvl", 0)
        if ilvl < _CHAOS_MIN:
            continue
        slot = _get_slot(item)
        if slot not in by_slot:
            continue
        tier = "regal" if ilvl >= _REGAL_MIN else "chaos"
        by_slot[slot][tier] += 1
        if not item.get("identified", True):
            by_slot[slot]["unid"] += 1

    def _weapon_slots(tier: str) -> int:
        """Weapon slots available: each 2H fills one slot; each 1H+offhand pair fills one slot."""
        two_h     = by_slot["weapon_2h"][tier]
        one_h     = by_slot["weapon_1h"][tier]
        off_hands = by_slot["offhand"][tier]
        return two_h + min(one_h, off_hands)

    def _complete(tier: str) -> int:
        return min(
            by_slot["helmet"][tier],
            by_slot["chest"][tier],
            by_slot["gloves"][tier],
            by_slot["boots"][tier],
            by_slot["belt"][tier],
            by_slot["ring"][tier] // _RINGS_PER_SET,
            by_slot["amulet"][tier],
            _weapon_slots(tier),
        )

    # "any" combines both tiers
    any_slot: dict[str, int] = {
        s: by_slot[s]["chaos"] + by_slot[s]["regal"]
        for s in by_slot
    }

    def _weapon_slots_any() -> int:
        return any_slot["weapon_2h"] + min(any_slot["weapon_1h"], any_slot["offhand"])

    any_sets = min(
        any_slot["helmet"],
        any_slot["chest"],
        any_slot["gloves"],
        any_slot["boots"],
        any_slot["belt"],
        any_slot["ring"] // _RINGS_PER_SET,
        any_slot["amulet"],
        _weapon_slots_any(),
    )

    # "unid" — only items where identified == False (all slots must be unid for 2x yield)
    unid_sets = _complete("unid")

    # Build user-facing counts (collapse weapon_1h/2h/offhand → "weapon")
    counts: dict[str, dict[str, int]] = {}
    for slot in SLOTS:
        if slot == "weapon":
            counts[slot] = {
                "chaos": _weapon_slots("chaos"),
                "regal": _weapon_slots("regal"),
                "any":   _weapon_slots_any(),
                "unid":  _weapon_slots("unid"),
            }
        else:
            counts[slot] = {
                "chaos": by_slot[slot]["chaos"],
                "regal": by_slot[slot]["regal"],
                "any":   any_slot[slot],
                "unid":  by_slot[slot]["unid"],
            }

    # Slots missing for the NEXT complete any_set
    next_target = any_sets + 1
    need: dict[str, int] = {
        "helmet": 1, "chest": 1, "gloves": 1, "boots": 1,
        "belt": 1, "ring": _RINGS_PER_SET, "amulet": 1, "weapon": 1,
    }
    missing = [
        slot for slot in SLOTS
        if counts[slot]["any"] < next_target * need[slot]
    ]

    return {
        "chaos_sets": _complete("chaos"),
        "regal_sets": _complete("regal"),
        "any_sets":   any_sets,
        "unid_sets":  unid_sets,
        "counts":     counts,
        "missing":    missing,
    }


class ChaosRecipe:
    def __init__(self, stash_api):
        self._stash_api = stash_api
        self._on_update: list[Callable] = []
        self._last_result: dict | None = None

    def on_update(self, callback: Callable):
        self._on_update.append(callback)

    def scan(self, league: str, on_done: Callable[[bool, str], None]):
        """
        Scan all equipment stash tabs and count recipe sets.
        Runs in a background thread; calls on_done(ok, error_msg) when complete.
        """
        def _fetch():
            try:
                items = self._stash_api.get_all_stash_items(league)
                result = count_sets(items)
                self._last_result = result
                self._fire_update()
                on_done(True, "")
            except Exception as e:
                on_done(False, str(e))

        threading.Thread(target=_fetch, daemon=True).start()

    def get_last_result(self) -> dict | None:
        return self._last_result

    def _fire_update(self):
        if self._last_result is None:
            return
        for cb in self._on_update:
            try:
                cb(self._last_result)
            except Exception as e:
                print(f"[ChaosRecipe] callback error: {e}")
