"""Tests for Build Archetype Primer data and panel logic."""

import json
import os
import pytest

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "build_archetypes.json")


@pytest.fixture(scope="module")
def data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def archetypes(data):
    return data["archetypes"]


# ── Data integrity ─────────────────────────────────────────────────────────────

def test_data_file_exists():
    assert os.path.exists(DATA_PATH)


def test_has_required_top_level_keys(data):
    for key in ("archetypes", "how_it_works", "tips", "difficulty_order"):
        assert key in data, f"Missing top-level key: {key}"


def test_archetypes_non_empty(archetypes):
    assert len(archetypes) >= 5, f"Expected at least 5 archetypes, got {len(archetypes)}"


def test_all_archetypes_have_required_fields(archetypes):
    required = (
        "name", "category", "primary_stats", "defensive_layers",
        "how_it_works", "example_skills", "entry_difficulty",
    )
    for arch in archetypes:
        for field in required:
            assert field in arch, f"Archetype '{arch.get('name')}' missing field: {field}"


def test_archetype_names_unique(archetypes):
    names = [a["name"] for a in archetypes]
    assert len(names) == len(set(names)), "Duplicate archetype names found"


def test_primary_stats_is_list(archetypes):
    for arch in archetypes:
        assert isinstance(arch["primary_stats"], list), \
            f"Archetype '{arch['name']}' primary_stats is not a list"
        assert len(arch["primary_stats"]) >= 2, \
            f"Archetype '{arch['name']}' has fewer than 2 primary_stats"


def test_defensive_layers_is_list(archetypes):
    for arch in archetypes:
        assert isinstance(arch["defensive_layers"], list), \
            f"Archetype '{arch['name']}' defensive_layers is not a list"
        assert len(arch["defensive_layers"]) >= 1


def test_example_skills_is_list(archetypes):
    for arch in archetypes:
        assert isinstance(arch["example_skills"], list), \
            f"Archetype '{arch['name']}' example_skills is not a list"
        assert len(arch["example_skills"]) >= 2


def test_valid_difficulty(archetypes, data):
    valid = set(data.get("difficulty_order", []))
    for arch in archetypes:
        assert arch["entry_difficulty"] in valid, \
            f"Archetype '{arch['name']}' has invalid difficulty: '{arch['entry_difficulty']}'"


def test_has_beginner_archetypes(archetypes):
    beginner = [a for a in archetypes if a["entry_difficulty"] == "Beginner"]
    assert len(beginner) >= 1, "Expected at least one Beginner archetype"


def test_how_it_works_non_empty(archetypes):
    for arch in archetypes:
        assert arch["how_it_works"].strip(), \
            f"Archetype '{arch['name']}' has empty how_it_works"


# ── Archetype coverage ─────────────────────────────────────────────────────────

def test_has_attack_archetype(archetypes):
    attack = [a for a in archetypes if a["category"] == "Attack"]
    assert len(attack) >= 1


def test_has_spell_archetype(archetypes):
    spell = [a for a in archetypes if a["category"] == "Spell"]
    assert len(spell) >= 1


def test_has_minion_archetype(archetypes):
    minion = [a for a in archetypes if a["category"] == "Minion"]
    assert len(minion) >= 1


def test_has_dot_archetype(archetypes):
    dot = [a for a in archetypes if a["category"] == "DoT"]
    assert len(dot) >= 1


# ── Search logic (data-level) ──────────────────────────────────────────────────

def _matches(arch: dict, query: str) -> bool:
    """Mirror of panel search logic for data-level testing."""
    if not query:
        return True
    searchable = " ".join([
        arch.get("name", ""),
        arch.get("category", ""),
        arch.get("how_it_works", ""),
        arch.get("entry_difficulty", ""),
        arch.get("notes", ""),
        " ".join(arch.get("primary_stats", [])),
        " ".join(arch.get("defensive_layers", [])),
        " ".join(arch.get("example_skills", [])),
    ]).lower()
    return query in searchable


def test_panel_module_importable():
    """Verify the panel module can be imported without a QApplication."""
    import importlib
    mod = importlib.import_module("ui.widgets.build_archetypes_panel")
    assert hasattr(mod, "BuildArchetypesPanel")


def test_category_list_has_all_categories(archetypes):
    seen: set[str] = set()
    for a in archetypes:
        seen.add(a.get("category", ""))
    assert "Attack" in seen
    assert "Spell" in seen
    assert "Minion" in seen
    assert "DoT" in seen


def test_search_matches_name(archetypes):
    results = [a for a in archetypes if _matches(a, "minion")]
    assert any("Minion" in a["name"] for a in results)


def test_search_matches_skill(archetypes):
    results = [a for a in archetypes if _matches(a, "cyclone")]
    assert len(results) >= 1, "Expected at least one archetype mentioning Cyclone"


def test_search_empty_returns_all(archetypes):
    results = [a for a in archetypes if _matches(a, "")]
    assert len(results) == len(archetypes)


def test_search_no_match(archetypes):
    results = [a for a in archetypes if _matches(a, "xyzxyzxyz_no_match")]
    assert len(results) == 0
