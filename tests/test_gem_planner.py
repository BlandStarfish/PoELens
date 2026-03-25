"""
Unit tests for modules/gem_planner.py.

Tests cover:
  - _extract_gem_level_quality(): normal, max-level format, quality format, missing
  - _classify_sell_candidate(): Awakened 4+, 20/20, Lv 20, not a candidate
  - _collect_gems(): item walking, weapon_swap detection, support flag
  - _build_result(): grouping into sell/active/support/leveling, sorting
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.gem_planner import (
    _extract_gem_level_quality,
    _classify_sell_candidate,
    _collect_gems,
    _build_result,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _prop(name: str, value: str) -> dict:
    return {"name": name, "values": [[value, 0]]}


def _gem(name: str, level: int, quality: int = 0, support: bool = False) -> dict:
    """Minimal GGG socketed gem dict."""
    return {
        "typeLine":   name,
        "frameType":  4,
        "support":    support,
        "properties": [_prop("Level", str(level)), _prop("Quality", f"+{quality}%")],
    }


def _item(gems: list, inventory_id: str = "Weapon") -> dict:
    """Minimal GGG equipped item dict wrapping socketed gems."""
    return {"inventoryId": inventory_id, "socketedItems": gems}


# ─────────────────────────────────────────────────────────────────────────────
# _extract_gem_level_quality
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractLevelQuality:
    def test_normal_level_and_quality(self):
        props = [_prop("Level", "18"), _prop("Quality", "+14%")]
        assert _extract_gem_level_quality(props) == (18, 14)

    def test_max_level_format(self):
        """GGG returns '20 (Max)' for max-level gems."""
        props = [_prop("Level", "20 (Max)"), _prop("Quality", "+20%")]
        assert _extract_gem_level_quality(props) == (20, 20)

    def test_no_properties(self):
        assert _extract_gem_level_quality([]) == (1, 0)

    def test_missing_quality(self):
        props = [_prop("Level", "15")]
        level, quality = _extract_gem_level_quality(props)
        assert level == 15
        assert quality == 0

    def test_missing_level(self):
        props = [_prop("Quality", "+8%")]
        level, quality = _extract_gem_level_quality(props)
        assert level == 1
        assert quality == 8

    def test_empty_values_field(self):
        props = [{"name": "Level", "values": []}]
        level, quality = _extract_gem_level_quality(props)
        assert level == 1   # default


# ─────────────────────────────────────────────────────────────────────────────
# _classify_sell_candidate
# ─────────────────────────────────────────────────────────────────────────────

class TestClassifySellCandidate:
    def test_awakened_level_4_is_candidate(self):
        reason = _classify_sell_candidate("Awakened Brutality Support", 4, 10)
        assert reason is not None
        assert "Awakened" in reason

    def test_awakened_level_5_is_candidate(self):
        reason = _classify_sell_candidate("Awakened Brutality Support", 5, 20)
        assert reason is not None

    def test_awakened_level_3_not_candidate(self):
        assert _classify_sell_candidate("Awakened Brutality Support", 3, 0) is None

    def test_20_20_gem_is_candidate(self):
        reason = _classify_sell_candidate("Fireball", 20, 20)
        assert reason is not None
        assert "20/20" in reason

    def test_level_20_quality_0_is_candidate(self):
        reason = _classify_sell_candidate("Fireball", 20, 0)
        assert reason is not None
        assert "Vaal" in reason or "Lv 20" in reason

    def test_low_level_normal_gem_not_candidate(self):
        assert _classify_sell_candidate("Fireball", 15, 10) is None

    def test_non_awakened_20_4_is_vaal_candidate_not_ready_to_sell(self):
        """Level 20, quality < 20: Vaal candidate but not 'ready to sell' (needs 20q first)."""
        reason = _classify_sell_candidate("Brutality Support", 20, 4)
        assert reason is not None
        assert "Vaal" in reason
        assert "ready to sell" not in reason


# ─────────────────────────────────────────────────────────────────────────────
# _collect_gems
# ─────────────────────────────────────────────────────────────────────────────

class TestCollectGems:
    def test_collects_gems_from_single_item(self):
        items = [_item([_gem("Fireball", 15)], "BodyArmour")]
        gems = _collect_gems(items)
        assert len(gems) == 1
        assert gems[0]["name"] == "Fireball"
        assert gems[0]["level"] == 15

    def test_non_gem_frameType_skipped(self):
        non_gem = {"typeLine": "Not a gem", "frameType": 0, "support": False, "properties": []}
        items = [_item([non_gem], "BodyArmour")]
        assert _collect_gems(items) == []

    def test_multiple_items_all_gems_collected(self):
        items = [
            _item([_gem("Fireball", 15)], "BodyArmour"),
            _item([_gem("Frostbolt", 12), _gem("Brutality Support", 18, support=True)], "Helm"),
        ]
        gems = _collect_gems(items)
        assert len(gems) == 3

    def test_weapon_swap_flag_set_for_weapon2(self):
        items = [_item([_gem("Fireball", 10)], "Weapon2")]
        gems = _collect_gems(items)
        assert gems[0]["weapon_swap"] is True

    def test_weapon_swap_flag_set_for_offhand2(self):
        items = [_item([_gem("Fireball", 10)], "Offhand2")]
        gems = _collect_gems(items)
        assert gems[0]["weapon_swap"] is True

    def test_primary_weapon_not_weapon_swap(self):
        for slot in ("Weapon", "Offhand", "BodyArmour", "Helm", "Gloves", "Boots"):
            items = [_item([_gem("Fireball", 10)], slot)]
            gems = _collect_gems(items)
            assert gems[0]["weapon_swap"] is False, f"Expected False for slot {slot}"

    def test_support_flag_propagated(self):
        items = [_item([_gem("Brutality Support", 18, support=True)], "BodyArmour")]
        gems = _collect_gems(items)
        assert gems[0]["support"] is True

    def test_empty_items_list(self):
        assert _collect_gems([]) == []

    def test_item_with_no_socketed_gems(self):
        items = [{"inventoryId": "Helm", "socketedItems": []}]
        assert _collect_gems(items) == []


# ─────────────────────────────────────────────────────────────────────────────
# _build_result
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildResult:
    def _make_gem(self, name, level, quality=0, support=False,
                  sell_candidate=None, weapon_swap=False) -> dict:
        return {
            "name":           name,
            "level":          level,
            "quality":        quality,
            "support":        support,
            "sell_candidate": sell_candidate,
            "weapon_swap":    weapon_swap,
        }

    def test_sell_candidate_in_sell_group(self):
        gems = [self._make_gem("Fireball", 20, sell_candidate="Lv 20 — Vaal for 20/20 or sell")]
        result = _build_result(gems)
        assert len(result["sell_candidates"]) == 1
        assert result["active_gems"] == []
        assert result["support_gems"] == []
        assert result["leveling_gems"] == []

    def test_active_gem_not_support_not_swap(self):
        gems = [self._make_gem("Fireball", 15)]
        result = _build_result(gems)
        assert len(result["active_gems"]) == 1
        assert result["support_gems"] == []
        assert result["leveling_gems"] == []

    def test_support_gem_in_support_group(self):
        gems = [self._make_gem("Brutality Support", 18, support=True)]
        result = _build_result(gems)
        assert len(result["support_gems"]) == 1
        assert result["active_gems"] == []

    def test_weapon_swap_gem_in_leveling_group(self):
        gems = [self._make_gem("Fireball", 10, weapon_swap=True)]
        result = _build_result(gems)
        assert len(result["leveling_gems"]) == 1
        assert result["active_gems"] == []
        assert result["support_gems"] == []

    def test_sell_candidate_weapon_swap_goes_to_sell_group(self):
        """A sell-candidate in weapon-swap should still be in sell_candidates."""
        gems = [self._make_gem("Fireball", 20, weapon_swap=True,
                               sell_candidate="Lv 20 — Vaal for 20/20 or sell")]
        result = _build_result(gems)
        assert len(result["sell_candidates"]) == 1
        assert result["leveling_gems"] == []   # sell takes priority over leveling

    def test_total_count(self):
        gems = [
            self._make_gem("A", 15),
            self._make_gem("B", 18, support=True),
            self._make_gem("C", 20, sell_candidate="20/20 — ready to sell"),
        ]
        assert _build_result(gems)["total"] == 3

    def test_sell_candidates_sorted_level_desc_name_asc(self):
        gems = [
            self._make_gem("ZZZ", 20, sell_candidate="20/20 — ready to sell"),
            self._make_gem("AAA", 20, sell_candidate="20/20 — ready to sell"),
            self._make_gem("MMM", 21, sell_candidate="Awakened Lv 5 — sell or level to 5"),
        ]
        result = _build_result(gems)
        names = [g["name"] for g in result["sell_candidates"]]
        assert names[0] == "MMM"   # level 21 first
        assert names[1] == "AAA"   # then sorted by name
        assert names[2] == "ZZZ"

    def test_empty_gems_list(self):
        result = _build_result([])
        assert result["total"] == 0
        assert result["sell_candidates"] == []
        assert result["active_gems"] == []
        assert result["support_gems"] == []
        assert result["leveling_gems"] == []
