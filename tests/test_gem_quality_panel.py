"""Tests for Gem Quality & Awakened Gem Reference data and panel logic."""

import json
import os
import pytest

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "gem_quality.json")


@pytest.fixture(scope="module")
def data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def gems(data):
    return data["gems"]


# ── Data integrity ──────────────────────────────────────────────────────────────

def test_data_file_exists():
    assert os.path.exists(DATA_PATH)


def test_has_required_top_level_keys(data):
    for key in ("gems", "how_it_works", "tips", "categories"):
        assert key in data, f"Missing top-level key: {key}"


def test_gems_non_empty(gems):
    assert len(gems) >= 15, f"Expected at least 15 gems, got {len(gems)}"


def test_all_gems_have_required_fields(gems):
    required = ("name", "category", "quality_effect", "notes")
    for gem in gems:
        for field in required:
            assert field in gem, f"Gem '{gem.get('name')}' missing field: {field}"


def test_gem_names_unique(gems):
    names = [g["name"] for g in gems]
    assert len(names) == len(set(names)), "Duplicate gem names found"


def test_valid_categories(gems, data):
    valid = set(data.get("categories", []))
    for gem in gems:
        assert gem["category"] in valid, \
            f"Gem '{gem['name']}' has invalid category: '{gem['category']}'"


def test_quality_effect_non_empty(gems):
    for gem in gems:
        assert gem["quality_effect"].strip(), \
            f"Gem '{gem['name']}' has empty quality_effect"


# ── Category coverage ───────────────────────────────────────────────────────────

def test_has_active_skills(gems):
    active = [g for g in gems if g["category"] == "Active Skill"]
    assert len(active) >= 3, f"Expected at least 3 Active Skill gems, got {len(active)}"


def test_has_supports(gems):
    supports = [g for g in gems if g["category"] == "Support"]
    assert len(supports) >= 10, f"Expected at least 10 Support gems, got {len(supports)}"


# ── Awakened gem integrity ──────────────────────────────────────────────────────

def test_awakened_gems_have_improvement(gems):
    for gem in gems:
        awk_name = gem.get("awakened_name")
        awk_imp  = gem.get("awakened_improvement")
        if awk_name is not None:
            assert awk_imp is not None, \
                f"Gem '{gem['name']}' has awakened_name but no awakened_improvement"


def test_awakened_gems_have_max_level(gems):
    for gem in gems:
        awk_name = gem.get("awakened_name")
        awk_lvl  = gem.get("awakened_max_level")
        if awk_name is not None:
            assert awk_lvl is not None, \
                f"Gem '{gem['name']}' has awakened_name but no awakened_max_level"
            assert awk_lvl >= 1, \
                f"Gem '{gem['name']}' has invalid awakened_max_level: {awk_lvl}"


# ── Key gems present ────────────────────────────────────────────────────────────

def test_key_supports_present(gems):
    names = {g["name"] for g in gems}
    expected = {"Empower Support", "Enlighten Support", "Multistrike Support", "Spell Echo Support"}
    for name in expected:
        assert name in names, f"Expected gem '{name}' not found"


def test_empower_has_awakened(gems):
    by_name = {g["name"]: g for g in gems}
    empower = by_name.get("Empower Support")
    assert empower is not None
    assert empower.get("awakened_name") == "Awakened Empower Support"
    assert empower.get("awakened_max_level") == 5


def test_enlighten_no_awakened(gems):
    """Enlighten and Enhance have no Awakened versions."""
    by_name = {g["name"]: g for g in gems}
    enlighten = by_name.get("Enlighten Support")
    if enlighten:
        assert enlighten.get("awakened_name") is None


# ── Search logic (data-level) ───────────────────────────────────────────────────

def _matches(gem: dict, query: str) -> bool:
    """Mirror of panel search logic for data-level testing."""
    if not query:
        return True
    searchable = " ".join([
        gem.get("name", ""),
        gem.get("category", ""),
        gem.get("quality_effect", ""),
        gem.get("sell_value", "") or "",
        gem.get("awakened_name", "") or "",
        gem.get("awakened_improvement", "") or "",
        gem.get("notes", ""),
    ]).lower()
    return query in searchable


def test_panel_module_importable():
    """Verify the panel module can be imported without a QApplication."""
    import importlib
    mod = importlib.import_module("ui.widgets.gem_quality_panel")
    assert hasattr(mod, "GemQualityPanel")


def test_search_matches_name(gems):
    results = [g for g in gems if _matches(g, "empower")]
    assert any(g["name"] == "Empower Support" for g in results)


def test_search_matches_awakened_name(gems):
    results = [g for g in gems if _matches(g, "awakened multistrike")]
    assert len(results) > 0


def test_search_matches_quality_effect(gems):
    results = [g for g in gems if _matches(g, "freeze")]
    assert len(results) > 0


def test_search_empty_returns_all(gems):
    results = [g for g in gems if _matches(g, "")]
    assert len(results) == len(gems)


def test_search_no_match(gems):
    results = [g for g in gems if _matches(g, "xyzxyzxyz_no_match")]
    assert len(results) == 0


def test_filter_active_skills(gems):
    active = [g for g in gems if g["category"] == "Active Skill"]
    assert all(g["category"] == "Active Skill" for g in active)


def test_filter_supports(gems):
    supports = [g for g in gems if g["category"] == "Support"]
    assert all(g["category"] == "Support" for g in supports)


def test_tips_non_empty(data):
    tips = data.get("tips", [])
    assert len(tips) >= 2, "Expected at least 2 tips"


def test_how_it_works_non_empty(data):
    how = data.get("how_it_works", "")
    assert how.strip(), "how_it_works should not be empty"
