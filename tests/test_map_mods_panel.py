"""Tests for Mapping Mod Reference data and panel logic."""

import json
import os
import pytest

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "map_mods.json")


@pytest.fixture(scope="module")
def data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def mods(data):
    return data["mods"]


# ── Data integrity ──────────────────────────────────────────────────────────────

def test_data_file_exists():
    assert os.path.exists(DATA_PATH)


def test_has_required_top_level_keys(data):
    for key in ("mods", "how_it_works", "tips", "categories"):
        assert key in data, f"Missing top-level key: {key}"


def test_mods_non_empty(mods):
    assert len(mods) >= 15, f"Expected at least 15 mods, got {len(mods)}"


def test_all_mods_have_required_fields(mods):
    required = ("name", "category", "effect", "danger_level", "who_is_affected", "counter", "notes")
    for mod in mods:
        for field in required:
            assert field in mod, f"Mod '{mod.get('name')}' missing field: {field}"


def test_mod_names_unique(mods):
    names = [m["name"] for m in mods]
    assert len(names) == len(set(names)), "Duplicate mod names found"


def test_valid_categories(mods, data):
    valid = set(data.get("categories", []))
    for mod in mods:
        assert mod["category"] in valid, \
            f"Mod '{mod['name']}' has invalid category: '{mod['category']}'"


def test_valid_danger_levels(mods):
    valid = {"Fatal", "High", "Medium", "Low", "None"}
    for mod in mods:
        assert mod["danger_level"] in valid, \
            f"Mod '{mod['name']}' has invalid danger_level: '{mod['danger_level']}'"


def test_effect_non_empty(mods):
    for mod in mods:
        assert mod["effect"].strip(), f"Mod '{mod['name']}' has empty effect"


# ── Category coverage ───────────────────────────────────────────────────────────

def test_has_avoid_mods(mods):
    avoid = [m for m in mods if m["category"] == "Avoid"]
    assert len(avoid) >= 3, f"Expected at least 3 Avoid mods, got {len(avoid)}"


def test_has_dangerous_mods(mods):
    danger = [m for m in mods if m["category"] == "Dangerous"]
    assert len(danger) >= 5, f"Expected at least 5 Dangerous mods, got {len(danger)}"


def test_has_beneficial_mods(mods):
    ben = [m for m in mods if m["category"] == "Beneficial"]
    assert len(ben) >= 1, f"Expected at least 1 Beneficial mod"


# ── Key mods present ────────────────────────────────────────────────────────────

def test_key_mods_present(mods):
    names = {m["name"] for m in mods}
    expected = {
        "Players cannot Regenerate Life, Mana or Energy Shield",
        "Monsters reflect X% of Elemental Damage",
        "Monsters reflect X% of Physical Damage",
    }
    for name in expected:
        assert name in names, f"Expected mod '{name}' not found"


def test_reflect_mods_are_fatal(mods):
    by_name = {m["name"]: m for m in mods}
    el_ref = by_name.get("Monsters reflect X% of Elemental Damage")
    ph_ref = by_name.get("Monsters reflect X% of Physical Damage")
    assert el_ref is not None and el_ref["danger_level"] == "Fatal"
    assert ph_ref is not None and ph_ref["danger_level"] == "Fatal"


def test_no_regen_is_dangerous_or_higher(mods):
    by_name = {m["name"]: m for m in mods}
    no_regen = by_name.get("Players cannot Regenerate Life, Mana or Energy Shield")
    assert no_regen is not None
    assert no_regen["danger_level"] in ("High", "Fatal")


# ── Search logic (data-level) ───────────────────────────────────────────────────

def _matches(mod: dict, query: str) -> bool:
    """Mirror of panel search logic for data-level testing."""
    if not query:
        return True
    searchable = " ".join([
        mod.get("name", ""),
        mod.get("short_name", "") or "",
        mod.get("category", ""),
        mod.get("effect", ""),
        mod.get("danger_level", ""),
        mod.get("who_is_affected", ""),
        mod.get("counter", ""),
        mod.get("notes", ""),
    ]).lower()
    return query in searchable


def test_panel_module_importable():
    """Verify the panel module can be imported without a QApplication."""
    import importlib
    mod = importlib.import_module("ui.widgets.map_mods_panel")
    assert hasattr(mod, "MapModsPanel")


def test_search_matches_name(mods):
    results = [m for m in mods if _matches(m, "reflect")]
    assert len(results) >= 2


def test_search_matches_short_name(mods):
    results = [m for m in mods if _matches(m, "no regen")]
    assert len(results) > 0


def test_search_matches_effect(mods):
    results = [m for m in mods if _matches(m, "leech")]
    assert len(results) > 0


def test_search_matches_counter(mods):
    results = [m for m in mods if _matches(m, "flask")]
    assert len(results) > 0


def test_search_empty_returns_all(mods):
    results = [m for m in mods if _matches(m, "")]
    assert len(results) == len(mods)


def test_search_no_match(mods):
    results = [m for m in mods if _matches(m, "xyzxyzxyz_no_match")]
    assert len(results) == 0


def test_filter_avoid(mods):
    avoid = [m for m in mods if m["category"] == "Avoid"]
    assert all(m["category"] == "Avoid" for m in avoid)


def test_filter_dangerous(mods):
    danger = [m for m in mods if m["category"] == "Dangerous"]
    assert all(m["category"] == "Dangerous" for m in danger)


def test_tips_non_empty(data):
    tips = data.get("tips", [])
    assert len(tips) >= 2, "Expected at least 2 tips"


def test_how_it_works_non_empty(data):
    how = data.get("how_it_works", "")
    assert how.strip(), "how_it_works should not be empty"
