"""
Tests for vendor_recipes.json data integrity.

Validates that the data file is well-formed and all recipes have required fields.
"""

import json
import os
import pytest

_DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "vendor_recipes.json"
)

_VALID_CATEGORIES = {"Currency", "Quality", "Leveling", "Unique"}


@pytest.fixture(scope="module")
def recipes():
    with open(_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["recipes"]


def test_data_file_exists():
    assert os.path.exists(_DATA_PATH), "vendor_recipes.json not found"


def test_has_recipes(recipes):
    assert len(recipes) > 0


def test_minimum_recipe_count(recipes):
    assert len(recipes) >= 15, f"Expected at least 15 recipes, got {len(recipes)}"


def test_all_four_categories_represented(recipes):
    found = {r.get("category") for r in recipes}
    for cat in _VALID_CATEGORIES:
        assert cat in found, f"Category '{cat}' has no recipes"


def test_all_recipes_have_name(recipes):
    for r in recipes:
        assert r.get("name"), f"Recipe missing name: {r}"


def test_all_recipes_have_category(recipes):
    for r in recipes:
        cat = r.get("category")
        assert cat in _VALID_CATEGORIES, \
            f"Recipe '{r.get('name')}' has invalid category: {cat!r}"


def test_all_recipes_have_ingredients(recipes):
    for r in recipes:
        assert r.get("ingredients"), f"Recipe '{r.get('name')}' missing ingredients"


def test_all_recipes_have_result(recipes):
    for r in recipes:
        assert r.get("result"), f"Recipe '{r.get('name')}' missing result"


def test_unique_recipe_names(recipes):
    names = [r["name"] for r in recipes]
    assert len(names) == len(set(names)), "Duplicate recipe names found"


def test_chromatic_recipe_present(recipes):
    """Chromatic Orb recipe is the most commonly used vendor recipe."""
    chrom = next((r for r in recipes if "Chromatic" in r.get("name", "")), None)
    assert chrom is not None, "Chromatic Orb recipe not found"
    assert chrom.get("category") == "Currency"
    ingredients = chrom.get("ingredients", "").lower()
    assert "color" in ingredients or "rgb" in ingredients or "r+g+b" in ingredients


def test_jeweller_recipe_present(recipes):
    """6-socket → Jeweller's Orbs recipe is a core vendor sink."""
    jeweller = next((r for r in recipes if "Jeweller" in r.get("name", "")), None)
    assert jeweller is not None, "Jeweller's Orb recipe not found"
    assert jeweller.get("category") == "Currency"


def test_fusing_recipe_present(recipes):
    """6-link → Fusings recipe is high value and commonly referenced."""
    fusing = next((r for r in recipes if "Fusing" in r.get("name", "")), None)
    assert fusing is not None, "Orbs of Fusing recipe not found"
    assert fusing.get("category") == "Currency"


def test_quality_recipes_present(recipes):
    """Whetstone, Scrap, Bauble, Chisel — all four quality recipes should be present."""
    quality_recipes = [r for r in recipes if r.get("category") == "Quality"]
    assert len(quality_recipes) >= 4, \
        f"Expected at least 4 Quality recipes, got {len(quality_recipes)}"


def test_flask_upgrade_recipe_present(recipes):
    """Flask upgrade recipe is a key early-leveling tool."""
    flask = next(
        (r for r in recipes if "flask" in r.get("name", "").lower()
         and r.get("category") == "Leveling"),
        None,
    )
    assert flask is not None, "Flask upgrade recipe not found in Leveling category"


def test_all_notes_are_strings(recipes):
    """Notes are optional but if present must be non-empty strings."""
    for r in recipes:
        notes = r.get("notes")
        if notes is not None:
            assert isinstance(notes, str) and len(notes) > 0, \
                f"Recipe '{r.get('name')}' has invalid notes: {notes!r}"
