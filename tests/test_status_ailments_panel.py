"""Tests for Status Ailment Reference data and panel logic."""

import json
import os
import pytest

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "status_ailments.json")


@pytest.fixture(scope="module")
def data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def ailments(data):
    return data["ailments"]


# ── Data integrity ─────────────────────────────────────────────────────────────

def test_data_file_exists():
    assert os.path.exists(DATA_PATH)


def test_has_required_top_level_keys(data):
    for key in ("ailments", "how_it_works", "tips", "categories"):
        assert key in data, f"Missing top-level key: {key}"


def test_ailments_non_empty(ailments):
    assert len(ailments) >= 10, f"Expected at least 10 ailments, got {len(ailments)}"


def test_all_ailments_have_required_fields(ailments):
    required = ("name", "category", "element", "effect", "how_applied", "how_to_cure")
    for ailment in ailments:
        for field in required:
            assert field in ailment, f"Ailment '{ailment.get('name')}' missing field: {field}"


def test_ailment_names_unique(ailments):
    names = [a["name"] for a in ailments]
    assert len(names) == len(set(names)), "Duplicate ailment names found"


def test_valid_categories(ailments, data):
    valid = set(data.get("categories", []))
    for ailment in ailments:
        assert ailment["category"] in valid, \
            f"Ailment '{ailment['name']}' has invalid category: '{ailment['category']}'"


def test_effect_non_empty(ailments):
    for ailment in ailments:
        assert ailment["effect"].strip(), \
            f"Ailment '{ailment['name']}' has empty effect"


def test_how_applied_non_empty(ailments):
    for ailment in ailments:
        assert ailment["how_applied"].strip(), \
            f"Ailment '{ailment['name']}' has empty how_applied"


def test_how_to_cure_non_empty(ailments):
    for ailment in ailments:
        assert ailment["how_to_cure"].strip(), \
            f"Ailment '{ailment['name']}' has empty how_to_cure"


# ── Category coverage ──────────────────────────────────────────────────────────

def test_has_elemental_ailments(ailments):
    elemental = [a for a in ailments if a["category"] == "Elemental"]
    assert len(elemental) >= 4, f"Expected at least 4 Elemental ailments, got {len(elemental)}"


def test_has_physical_and_poison_ailments(ailments):
    phys = [a for a in ailments if a["category"] == "Physical & Poison"]
    assert len(phys) >= 2, f"Expected at least 2 Physical & Poison ailments"


def test_has_debuff_ailments(ailments):
    debuff = [a for a in ailments if a["category"] == "Debuff"]
    assert len(debuff) >= 3, f"Expected at least 3 Debuff ailments"


# ── Specific ailments present ──────────────────────────────────────────────────

def test_key_ailments_present(ailments):
    names = {a["name"] for a in ailments}
    expected = {"Ignite", "Chill", "Freeze", "Shock", "Poison", "Bleed", "Corrupted Blood"}
    for name in expected:
        assert name in names, f"Expected ailment '{name}' not found"


def test_big_three_elemental_ailments(ailments):
    """Ignite (Fire), Chill/Freeze (Cold), Shock (Lightning) must all be present."""
    by_name = {a["name"]: a for a in ailments}
    assert by_name["Ignite"]["element"] == "Fire"
    assert by_name["Chill"]["element"] == "Cold"
    assert by_name["Freeze"]["element"] == "Cold"
    assert by_name["Shock"]["element"] == "Lightning"


def test_lesser_ailments_present(ailments):
    names = {a["name"] for a in ailments}
    for lesser in ("Scorch", "Brittle", "Sap"):
        assert lesser in names, f"Lesser ailment '{lesser}' not found"


# ── Search logic (data-level) ──────────────────────────────────────────────────

def _matches(ailment: dict, query: str) -> bool:
    """Mirror of panel search logic for data-level testing."""
    if not query:
        return True
    searchable = " ".join([
        ailment.get("name", ""),
        ailment.get("category", ""),
        ailment.get("element", ""),
        ailment.get("effect", ""),
        ailment.get("how_applied", ""),
        ailment.get("how_to_cure", ""),
        ailment.get("offensive_use", ""),
        ailment.get("notes", ""),
    ]).lower()
    return query in searchable


def test_panel_module_importable():
    """Verify the panel module can be imported without a QApplication."""
    import importlib
    mod = importlib.import_module("ui.widgets.status_ailments_panel")
    assert hasattr(mod, "StatusAilmentsPanel")


def test_search_matches_name(ailments):
    results = [a for a in ailments if _matches(a, "ignite")]
    assert any(a["name"] == "Ignite" for a in results)


def test_search_matches_effect(ailments):
    results = [a for a in ailments if _matches(a, "immobilizes")]
    assert any(a["name"] == "Freeze" for a in results)


def test_search_matches_cure(ailments):
    results = [a for a in ailments if _matches(a, "staunching")]
    names = {a["name"] for a in results}
    assert "Bleed" in names or "Poison" in names


def test_search_empty_returns_all(ailments):
    results = [a for a in ailments if _matches(a, "")]
    assert len(results) == len(ailments)


def test_search_no_match(ailments):
    results = [a for a in ailments if _matches(a, "xyzxyzxyz_no_match")]
    assert len(results) == 0
