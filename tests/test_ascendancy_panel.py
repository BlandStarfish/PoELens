"""Tests for Ascendancy Class Reference data and panel logic."""

import json
import os
import pytest

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "ascendancy_classes.json")


@pytest.fixture(scope="module")
def data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def classes(data):
    return data["classes"]


# ── Data integrity ─────────────────────────────────────────────────────────────

def test_data_file_exists():
    assert os.path.exists(DATA_PATH)


def test_has_required_top_level_keys(data):
    for key in ("classes", "how_it_works", "respec_note", "tips", "base_classes"):
        assert key in data, f"Missing top-level key: {key}"


def test_class_count(classes):
    assert len(classes) == 19, f"Expected 19 Ascendancy classes, got {len(classes)}"


def test_all_classes_have_required_fields(classes):
    required = ("name", "base_class", "playstyle", "key_notables", "primary_defence", "top_builds")
    for cls in classes:
        for field in required:
            assert field in cls, f"Class '{cls.get('name')}' missing field: {field}"


def test_class_names_unique(classes):
    names = [c["name"] for c in classes]
    assert len(names) == len(set(names)), "Duplicate class names found"


def test_base_classes_valid(classes):
    valid_bases = {"Marauder", "Ranger", "Witch", "Duelist", "Templar", "Shadow", "Scion"}
    for cls in classes:
        assert cls["base_class"] in valid_bases, \
            f"Class '{cls['name']}' has invalid base_class: '{cls['base_class']}'"


def test_marauder_has_three_ascendancies(classes):
    marauder = [c for c in classes if c["base_class"] == "Marauder"]
    assert len(marauder) == 3, f"Expected 3 Marauder Ascendancies, got {len(marauder)}"


def test_ranger_has_three_ascendancies(classes):
    ranger = [c for c in classes if c["base_class"] == "Ranger"]
    assert len(ranger) == 3, f"Expected 3 Ranger Ascendancies, got {len(ranger)}"


def test_witch_has_three_ascendancies(classes):
    witch = [c for c in classes if c["base_class"] == "Witch"]
    assert len(witch) == 3, f"Expected 3 Witch Ascendancies, got {len(witch)}"


def test_scion_has_one_ascendancy(classes):
    scion = [c for c in classes if c["base_class"] == "Scion"]
    assert len(scion) == 1, f"Expected 1 Scion Ascendancy, got {len(scion)}"


def test_all_classes_have_key_notables(classes):
    for cls in classes:
        notables = cls.get("key_notables", [])
        assert isinstance(notables, list) and len(notables) >= 2, \
            f"Class '{cls['name']}' has fewer than 2 key notables"


def test_all_classes_have_top_builds(classes):
    for cls in classes:
        builds = cls.get("top_builds", [])
        assert isinstance(builds, list) and len(builds) >= 2, \
            f"Class '{cls['name']}' has fewer than 2 top builds"


def test_how_it_works_non_empty(data):
    assert data["how_it_works"].strip(), "how_it_works is empty"


def test_respec_note_non_empty(data):
    assert data["respec_note"].strip(), "respec_note is empty"


def test_tips_non_empty(data):
    assert len(data["tips"]) >= 2, "Expected at least 2 tips"


def test_base_classes_list_complete(data):
    expected = {"Marauder", "Ranger", "Witch", "Duelist", "Templar", "Shadow", "Scion"}
    assert set(data["base_classes"]) == expected


# ── Spot checks ────────────────────────────────────────────────────────────────

def test_juggernaut_exists(classes):
    names = {c["name"] for c in classes}
    assert "Juggernaut" in names


def test_necromancer_exists(classes):
    names = {c["name"] for c in classes}
    assert "Necromancer" in names


def test_ascendant_exists(classes):
    names = {c["name"] for c in classes}
    assert "Ascendant" in names


def test_deadeye_is_ranger(classes):
    deadeye = next((c for c in classes if c["name"] == "Deadeye"), None)
    assert deadeye is not None
    assert deadeye["base_class"] == "Ranger"


def test_inquisitor_is_templar(classes):
    inq = next((c for c in classes if c["name"] == "Inquisitor"), None)
    assert inq is not None
    assert inq["base_class"] == "Templar"


def test_necromancer_has_minion_builds(classes):
    necro = next((c for c in classes if c["name"] == "Necromancer"), None)
    assert necro is not None
    builds_text = " ".join(necro["top_builds"]).lower()
    assert any(kw in builds_text for kw in ("spectre", "zombie", "minion", "skeleton")), \
        "Necromancer top_builds should reference minion skills"


def test_all_playstyles_non_empty(classes):
    for cls in classes:
        assert cls["playstyle"].strip(), f"Class '{cls['name']}' has empty playstyle"


def test_all_primary_defences_non_empty(classes):
    for cls in classes:
        assert cls["primary_defence"].strip(), f"Class '{cls['name']}' has empty primary_defence"
