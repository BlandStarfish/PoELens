"""
Gem Level Planner.

Reads equipped gems from the GGG Character API and classifies them by
level, quality, and sell potential.

Sell candidates:
  - Any gem at level 20 (eligible for Vaal → 20/20 conversion)
  - Awakened gems at level 4+ (high trade value)
  - 20/20 gems (level 20, quality 20) — ready to sell or convert

Requires OAuth (account:characters scope). Scan is user-triggered.
TOS: reads character data via official OAuth API only.
"""

import threading
from typing import Callable

# GGG item frameType for skill gems
_GEM_FRAME = 4


def _extract_gem_level_quality(properties: list) -> tuple[int, int]:
    """
    Extract level and quality integers from a gem's properties array.
    Returns (level, quality) — (1, 0) if not found.
    """
    level   = 1
    quality = 0
    for prop in properties:
        name   = prop.get("name", "")
        values = prop.get("values", [])
        if not values:
            continue
        raw = str(values[0][0]) if values[0] else ""
        if name == "Level":
            # Value may be "20 (Max)" or just "20"
            try:
                level = int(raw.split()[0])
            except (ValueError, IndexError):
                pass
        elif name == "Quality":
            # Value like "+20%"
            try:
                quality = int(raw.lstrip("+").rstrip("%"))
            except ValueError:
                pass
    return level, quality


_WEAPON_SWAP_SLOTS = frozenset({"Weapon2", "Offhand2"})


def _collect_gems(items: list) -> list[dict]:
    """
    Walk equipped items and collect all socketed gems.
    Returns a list of gem dicts with name, level, quality, support,
    sell_candidate, and weapon_swap (True if in the secondary weapon set).
    """
    gems = []
    for item in items:
        inventory_id = item.get("inventoryId", "")
        in_weapon_swap = inventory_id in _WEAPON_SWAP_SLOTS
        for gem in item.get("socketedItems", []):
            if gem.get("frameType") != _GEM_FRAME:
                continue
            name    = gem.get("typeLine", "")
            support = gem.get("support", False)
            level, quality = _extract_gem_level_quality(gem.get("properties", []))
            sell_candidate = _classify_sell_candidate(name, level, quality)
            gems.append({
                "name":           name,
                "level":          level,
                "quality":        quality,
                "support":        support,
                "sell_candidate": sell_candidate,
                "weapon_swap":    in_weapon_swap,
            })
    return gems


def _classify_sell_candidate(name: str, level: int, quality: int) -> str | None:
    """
    Returns a human-readable sell-candidate reason string, or None if not a sell candidate.

    Criteria:
      - Awakened gem at level 4+: high value
      - Any gem at level 20 + quality 20: 20/20 sell candidate
      - Any gem at level 20: eligible for Vaal 20/20 conversion
    """
    is_awakened = name.startswith("Awakened ")
    if is_awakened and level >= 4:
        return f"Awakened Lv {level} — sell or level to 5"
    if level >= 20 and quality >= 20:
        return "20/20 — ready to sell"
    if level >= 20:
        return "Lv 20 — Vaal for 20/20 or sell"
    return None


class GemPlanner:
    def __init__(self, character_api):
        self._character_api  = character_api
        self._on_update: list[Callable] = []
        self._last_result: dict | None  = None

    def on_update(self, callback: Callable):
        self._on_update.append(callback)

    def scan(self, character_name: str, on_done: Callable[[bool, str], None]):
        """
        Fetch equipped items for character_name and extract gem data.
        Runs in a background thread; calls on_done(ok, error_msg) when complete.
        """
        def _fetch():
            try:
                items = self._character_api.get_character_items(character_name)
                if items is None:
                    on_done(False, "Could not fetch character items — check OAuth connection")
                    return
                gems   = _collect_gems(items)
                result = _build_result(gems)
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
                print(f"[GemPlanner] callback error: {e}")


def _build_result(gems: list[dict]) -> dict:
    """
    Organise gems into a structured result dict.
      {
        "sell_candidates":  [gem_dict, ...]  — sorted by level desc, name asc
        "active_gems":      [gem_dict, ...]  — non-support, non-sell-candidate, not weapon-swap
        "support_gems":     [gem_dict, ...]  — support gems only (not weapon-swap)
        "leveling_gems":    [gem_dict, ...]  — gems in weapon-swap set (secondary weapon slots)
        "total":            int
      }
    """
    sell_candidates = sorted(
        [g for g in gems if g["sell_candidate"]],
        key=lambda g: (-g["level"], g["name"]),
    )
    # Weapon-swap gems are in their own group (they're being passively leveled)
    leveling_gems = sorted(
        [g for g in gems if g["weapon_swap"] and not g["sell_candidate"]],
        key=lambda g: (-g["level"], g["name"]),
    )
    active_gems = sorted(
        [g for g in gems if not g["support"] and not g["sell_candidate"] and not g["weapon_swap"]],
        key=lambda g: (-g["level"], g["name"]),
    )
    support_gems = sorted(
        [g for g in gems if g["support"] and not g["sell_candidate"] and not g["weapon_swap"]],
        key=lambda g: (-g["level"], g["name"]),
    )
    return {
        "sell_candidates": sell_candidates,
        "active_gems":     active_gems,
        "support_gems":    support_gems,
        "leveling_gems":   leveling_gems,
        "total":           len(gems),
    }
