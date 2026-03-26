"""Tests for Map Boss Quick Reference data and panel logic."""

import json
import os
import pytest

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "map_bosses.json")


@pytest.fixture(scope="module")
def data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def bosses(data):
    return data["bosses"]


# ── Data integrity ─────────────────────────────────────────────────────────────

def test_data_file_exists():
    assert os.path.exists(DATA_PATH)


def test_has_required_top_level_keys(data):
    for key in ("bosses", "how_it_works", "tips", "categories"):
        assert key in data, f"Missing top-level key: {key}"


def test_bosses_non_empty(bosses):
    assert len(bosses) >= 12, f"Expected at least 12 bosses, got {len(bosses)}"


def test_all_bosses_have_required_fields(bosses):
    required = ("name", "map", "category", "key_mechanics", "dangerous_abilities", "recommended_prep")
    for boss in bosses:
        for field in required:
            assert field in boss, f"Boss '{boss.get('name')}' missing field: {field}"


def test_boss_names_unique(bosses):
    names = [b["name"] for b in bosses]
    assert len(names) == len(set(names)), "Duplicate boss names found"


def test_valid_categories(bosses):
    valid = {"Shaper Guardian", "Elder Guardian", "Conqueror", "Pinnacle"}
    for boss in bosses:
        assert boss["category"] in valid, \
            f"Boss '{boss['name']}' has invalid category: '{boss['category']}'"


def test_dangerous_abilities_is_list(bosses):
    for boss in bosses:
        assert isinstance(boss["dangerous_abilities"], list), \
            f"Boss '{boss['name']}' dangerous_abilities is not a list"


def test_all_dangerous_abilities_non_empty_list(bosses):
    for boss in bosses:
        assert len(boss["dangerous_abilities"]) >= 1, \
            f"Boss '{boss['name']}' has no dangerous abilities listed"


def test_how_it_works_non_empty(data):
    assert data["how_it_works"].strip(), "how_it_works is empty"


def test_tips_non_empty(data):
    assert len(data["tips"]) >= 2, "Expected at least 2 tips"


def test_four_shaper_guardians(bosses):
    shapers = [b for b in bosses if b["category"] == "Shaper Guardian"]
    assert len(shapers) == 4, f"Expected 4 Shaper Guardians, got {len(shapers)}"


def test_four_elder_guardians(bosses):
    elders = [b for b in bosses if b["category"] == "Elder Guardian"]
    assert len(elders) == 4, f"Expected 4 Elder Guardians, got {len(elders)}"


def test_four_conquerors(bosses):
    conqs = [b for b in bosses if b["category"] == "Conqueror"]
    assert len(conqs) == 4, f"Expected 4 Conquerors, got {len(conqs)}"


# ── Spot checks ────────────────────────────────────────────────────────────────

def test_sirus_exists(bosses):
    names = {b["name"] for b in bosses}
    assert any("Sirus" in n for n in names), "Sirus not found"


def test_maven_exists(bosses):
    names = {b["name"] for b in bosses}
    assert any("Maven" in n for n in names), "The Maven not found"


def test_shaper_exists(bosses):
    names = {b["name"] for b in bosses}
    assert any("Shaper" in n for n in names), "The Shaper not found"


def test_baran_exists(bosses):
    names = {b["name"] for b in bosses}
    assert any("Baran" in n for n in names), "Baran not found"


def test_conquerors_have_map_names(bosses):
    conqs = [b for b in bosses if b["category"] == "Conqueror"]
    for boss in conqs:
        assert boss["map"].strip(), f"Conqueror '{boss['name']}' has empty map"


def test_all_mechanics_non_empty(bosses):
    for boss in bosses:
        assert boss["key_mechanics"].strip(), f"Boss '{boss['name']}' has empty key_mechanics"


def test_all_prep_non_empty(bosses):
    for boss in bosses:
        assert boss["recommended_prep"].strip(), f"Boss '{boss['name']}' has empty recommended_prep"


def test_categories_list_complete(data):
    expected = {"Shaper Guardian", "Elder Guardian", "Conqueror", "Pinnacle"}
    assert set(data["categories"]) == expected
