"""Tests for Essence Reference data integrity."""
import json
import os
import pytest

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "essences.json")

_VALID_CATEGORIES = {"Life", "Physical", "Cold", "Fire", "Lightning", "Chaos", "Utility", "Defense", "Delirium"}
_VALID_TIERS = {"Weeping", "Wailing", "Screaming", "Shrieking", "Deafening"}
_DELIRIUM_NAMES = {"Horror", "Hysteria", "Insanity", "Delirium"}
_REQUIRED_FIELDS = {"name", "tiers", "stat_category", "stat_focus", "primary_slots", "best_for", "notes"}


@pytest.fixture(scope="module")
def data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def essences(data):
    return data["essences"]


def test_data_file_exists():
    assert os.path.exists(DATA_PATH)


def test_has_essences(essences):
    assert len(essences) >= 15, "Expected at least 15 essence entries"


def test_required_fields(essences):
    for e in essences:
        for field in _REQUIRED_FIELDS:
            assert field in e, f"Essence {e.get('name', '?')} missing field {field!r}"


def test_stat_categories_valid(essences):
    for e in essences:
        cat = e.get("stat_category", "")
        assert cat in _VALID_CATEGORIES, (
            f"Essence {e['name']!r} has invalid stat_category {cat!r}"
        )


def test_tiers_are_valid(essences):
    for e in essences:
        for tier in e.get("tiers", []):
            assert tier in _VALID_TIERS, (
                f"Essence {e['name']!r} has invalid tier {tier!r}"
            )


def test_tiers_nonempty(essences):
    for e in essences:
        assert len(e.get("tiers", [])) >= 1, f"Essence {e['name']!r} has no tiers"


def test_unique_names(essences):
    names = [e["name"] for e in essences]
    assert len(set(names)) == len(names), "Duplicate essence names found"


def test_names_nonempty(essences):
    for e in essences:
        assert e["name"].strip(), "Essence name is empty"


def test_greed_present(essences):
    names = {e["name"] for e in essences}
    assert "Greed" in names, "Essence of Greed missing"


def test_greed_is_life_category(essences):
    greed = next(e for e in essences if e["name"] == "Greed")
    assert greed["stat_category"] == "Life"


def test_greed_has_five_tiers(essences):
    greed = next(e for e in essences if e["name"] == "Greed")
    assert "Weeping" in greed["tiers"] and "Deafening" in greed["tiers"]


def test_loathing_present(essences):
    names = {e["name"] for e in essences}
    assert "Loathing" in names, "Essence of Loathing missing"


def test_loathing_mentions_boots(essences):
    loathing = next(e for e in essences if e["name"] == "Loathing")
    assert "oots" in loathing["primary_slots"]


def test_scorn_is_screaming_plus(essences):
    scorn = next((e for e in essences if e["name"] == "Scorn"), None)
    if scorn:
        assert "Screaming" in scorn["tiers"]
        assert "Weeping" not in scorn["tiers"]


def test_envy_is_chaos_category(essences):
    envy = next((e for e in essences if e["name"] == "Envy"), None)
    if envy:
        assert envy["stat_category"] == "Chaos"


def test_delirium_essences_are_delirium_category(essences):
    delirium_essences = [e for e in essences if e["name"] in _DELIRIUM_NAMES]
    assert len(delirium_essences) >= 1, "Expected at least one Delirium essence"
    for e in delirium_essences:
        assert e["stat_category"] == "Delirium", (
            f"Delirium essence {e['name']!r} should have category 'Delirium'"
        )


def test_delirium_essences_start_at_screaming(essences):
    for e in essences:
        if e["name"] in _DELIRIUM_NAMES:
            assert "Screaming" in e["tiers"]
            assert "Weeping" not in e["tiers"], (
                f"Delirium essence {e['name']!r} should not have Weeping tier"
            )


def test_how_it_works_present(data):
    assert data.get("how_it_works", "").strip()


def test_tips_present(data):
    tips = data.get("tips", [])
    assert len(tips) >= 4
    for tip in tips:
        assert isinstance(tip, str) and tip.strip()


def test_stat_categories_list_present(data):
    cats = data.get("stat_categories", [])
    assert "Life" in cats
    assert "Delirium" in cats


def test_best_for_nonempty(essences):
    for e in essences:
        assert e.get("best_for", "").strip(), f"Essence {e['name']!r} has empty best_for"
