"""Tests for Fragment Sets Reference data integrity."""
import json
import os
import pytest

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "fragment_sets.json")

_VALID_TYPES = {"Vaal", "Shaper", "Elder", "Breach", "Pantheon"}
_REQUIRED_FIELDS = {"name", "boss", "type", "tier", "fragments", "area_level",
                    "how_to_get", "notable_drops", "notes"}


@pytest.fixture(scope="module")
def data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def sets(data):
    return data["fragment_sets"]


def test_data_file_exists():
    assert os.path.exists(DATA_PATH)


def test_has_sets(sets):
    assert len(sets) >= 5, "Expected at least 5 fragment set entries"


def test_required_fields(sets):
    for s in sets:
        for field in _REQUIRED_FIELDS:
            assert field in s, f"Set {s.get('name', '?')} missing field {field!r}"


def test_types_valid(sets):
    for s in sets:
        assert s["type"] in _VALID_TYPES, (
            f"Set {s['name']!r} has invalid type {s['type']!r}"
        )


def test_fragments_are_lists(sets):
    for s in sets:
        assert isinstance(s["fragments"], list), (
            f"Set {s['name']!r} fragments must be a list"
        )
        assert len(s["fragments"]) >= 1, (
            f"Set {s['name']!r} must have at least one fragment"
        )


def test_area_level_is_int(sets):
    for s in sets:
        assert isinstance(s["area_level"], int), (
            f"Set {s['name']!r} area_level must be an int"
        )
        assert s["area_level"] >= 1


def test_unique_names(sets):
    names = [s["name"] for s in sets]
    assert len(set(names)) == len(names), "Duplicate fragment set names"


def test_apex_of_sacrifice_present(sets):
    names = {s["name"] for s in sets}
    assert "Apex of Sacrifice" in names


def test_apex_has_four_fragments(sets):
    apex = next(s for s in sets if s["name"] == "Apex of Sacrifice")
    assert len(apex["fragments"]) == 4


def test_apex_is_vaal_type(sets):
    apex = next(s for s in sets if s["name"] == "Apex of Sacrifice")
    assert apex["type"] == "Vaal"


def test_shaper_realm_present(sets):
    names = {s["name"] for s in sets}
    assert "The Shaper's Realm" in names


def test_shaper_has_four_fragments(sets):
    shaper = next(s for s in sets if s["name"] == "The Shaper's Realm")
    assert len(shaper["fragments"]) == 4


def test_shaper_is_shaper_type(sets):
    shaper = next(s for s in sets if s["name"] == "The Shaper's Realm")
    assert shaper["type"] == "Shaper"


def test_breach_entries_exist(sets):
    breach_sets = [s for s in sets if s["type"] == "Breach"]
    assert len(breach_sets) >= 3, "Expected at least 3 Breach entries"


def test_chayula_requires_300_splinters(sets):
    chayula = next((s for s in sets if "Chayula" in s["name"]), None)
    if chayula:
        combined = " ".join([chayula.get("notes", ""), chayula.get("how_to_get", "")])
        assert "300" in combined, "Chayula should note the 300-splinter requirement"


def test_alluring_abyss_is_uber(sets):
    abyss = next((s for s in sets if "Alluring Abyss" in s["name"]), None)
    if abyss:
        assert abyss["tier"] == "Uber"


def test_how_it_works_present(data):
    assert data.get("how_it_works", "").strip()


def test_tips_present(data):
    tips = data.get("tips", [])
    assert len(tips) >= 3
    for tip in tips:
        assert isinstance(tip, str) and tip.strip()


def test_names_nonempty(sets):
    for s in sets:
        assert s["name"].strip(), "Fragment set name is empty"


def test_bosses_nonempty(sets):
    for s in sets:
        assert s["boss"].strip(), f"Set {s['name']!r} has empty boss field"
