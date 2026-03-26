"""Tests for League Mechanic Primer data and panel logic."""

import json
import os
import pytest

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "league_mechanics.json")


@pytest.fixture(scope="module")
def data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def mechanics(data):
    return data["mechanics"]


# ── Data integrity ─────────────────────────────────────────────────────────────

def test_data_file_exists():
    assert os.path.exists(DATA_PATH)


def test_has_required_top_level_keys(data):
    for key in ("mechanics", "how_it_works", "tips", "categories"):
        assert key in data, f"Missing top-level key: {key}"


def test_mechanics_non_empty(mechanics):
    assert len(mechanics) >= 10, f"Expected at least 10 mechanics, got {len(mechanics)}"


def test_all_mechanics_have_required_fields(mechanics):
    required = ("name", "category", "how_to_trigger", "what_to_do", "key_rewards")
    for mech in mechanics:
        for field in required:
            assert field in mech, f"Mechanic '{mech.get('name')}' missing field: {field}"


def test_mechanic_names_unique(mechanics):
    names = [m["name"] for m in mechanics]
    assert len(names) == len(set(names)), "Duplicate mechanic names found"


def test_valid_categories(mechanics, data):
    valid = set(data.get("categories", []))
    for mech in mechanics:
        assert mech["category"] in valid, \
            f"Mechanic '{mech['name']}' has invalid category: '{mech['category']}'"


def test_key_rewards_is_list(mechanics):
    for mech in mechanics:
        assert isinstance(mech["key_rewards"], list), \
            f"Mechanic '{mech['name']}' key_rewards is not a list"
        assert len(mech["key_rewards"]) >= 1, \
            f"Mechanic '{mech['name']}' has no key rewards"


def test_tips_is_list_when_present(mechanics):
    for mech in mechanics:
        if "tips" in mech:
            assert isinstance(mech["tips"], list), \
                f"Mechanic '{mech['name']}' tips is not a list"


def test_how_to_trigger_non_empty(mechanics):
    for mech in mechanics:
        assert mech["how_to_trigger"].strip(), \
            f"Mechanic '{mech['name']}' has empty how_to_trigger"


def test_what_to_do_non_empty(mechanics):
    for mech in mechanics:
        assert mech["what_to_do"].strip(), \
            f"Mechanic '{mech['name']}' has empty what_to_do"


# ── Category coverage ──────────────────────────────────────────────────────────

def test_has_combat_mechanics(mechanics):
    combat = [m for m in mechanics if m["category"] == "Combat"]
    assert len(combat) >= 3, f"Expected at least 3 Combat mechanics, got {len(combat)}"


def test_has_management_mechanics(mechanics):
    management = [m for m in mechanics if m["category"] == "Management"]
    assert len(management) >= 3, f"Expected at least 3 Management mechanics, got {len(management)}"


def test_has_exploration_mechanics(mechanics):
    exploration = [m for m in mechanics if m["category"] == "Exploration"]
    assert len(exploration) >= 1, f"Expected at least 1 Exploration mechanic, got {len(exploration)}"


# ── Specific mechanics present ─────────────────────────────────────────────────

def test_key_mechanics_present(mechanics):
    names = {m["name"] for m in mechanics}
    expected = {"Breach", "Delirium", "Expedition", "Heist", "Ritual", "Harvest"}
    for name in expected:
        assert name in names, f"Expected mechanic '{name}' not found"


# ── Search logic (data-level) ──────────────────────────────────────────────────

def _matches(mech: dict, query: str) -> bool:
    """Mirror of panel search logic for data-level testing."""
    if not query:
        return True
    searchable = " ".join([
        mech.get("name", ""),
        mech.get("category", ""),
        mech.get("how_to_trigger", ""),
        mech.get("what_to_do", ""),
        mech.get("notes", ""),
        " ".join(mech.get("key_rewards", [])),
        " ".join(mech.get("tips", [])),
    ]).lower()
    return query in searchable


def test_panel_module_importable():
    """Verify the panel module can be imported without a QApplication."""
    import importlib
    mod = importlib.import_module("ui.widgets.league_mechanics_panel")
    assert hasattr(mod, "LeagueMechanicsPanel")


def test_search_matches_name(mechanics):
    breach = [m for m in mechanics if _matches(m, "breach")]
    assert any(m["name"] == "Breach" for m in breach)


def test_search_matches_reward(mechanics):
    results = [m for m in mechanics if _matches(m, "simulacrum")]
    assert len(results) >= 1, "Expected at least one mechanic mentioning 'simulacrum'"


def test_search_empty_returns_all(mechanics):
    results = [m for m in mechanics if _matches(m, "")]
    assert len(results) == len(mechanics)


def test_search_no_match(mechanics):
    results = [m for m in mechanics if _matches(m, "xyzxyzxyz_no_match")]
    assert len(results) == 0
