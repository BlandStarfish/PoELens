"""Tests for Rare Mod Reference data integrity."""
import json
import os
import pytest

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "rare_mods.json")

_VALID_DANGER     = {"extreme", "high", "moderate", "low"}
_VALID_CATEGORIES = {"Offense", "Defense", "Summons", "Area", "Debuff", "Misc"}


@pytest.fixture(scope="module")
def data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def mods(data):
    return data["mods"]


def test_data_file_exists():
    assert os.path.exists(DATA_PATH)


def test_has_mods(mods):
    assert len(mods) >= 20, "Expected at least 20 rare mods"


def test_required_fields(mods):
    required = {"name", "effect", "danger", "category"}
    for m in mods:
        for field in required:
            assert field in m, f"Mod {m.get('name', '?')} missing field {field!r}"


def test_valid_danger_levels(mods):
    for m in mods:
        assert m["danger"] in _VALID_DANGER, (
            f"Mod {m['name']} has invalid danger {m['danger']!r}"
        )


def test_valid_categories(mods):
    for m in mods:
        assert m["category"] in _VALID_CATEGORIES, (
            f"Mod {m['name']} has invalid category {m['category']!r}"
        )


def test_name_nonempty(mods):
    for m in mods:
        assert m["name"].strip(), "Mod name is empty"


def test_effect_nonempty(mods):
    for m in mods:
        assert m["effect"].strip(), f"Mod {m['name']}: effect is empty"


def test_unique_mod_names(mods):
    names = [m["name"] for m in mods]
    assert len(set(names)) == len(names), "Duplicate mod names"


def test_necromancer_present(mods):
    names = {m["name"] for m in mods}
    assert "Necromancer" in names


def test_vampiric_present(mods):
    names = {m["name"] for m in mods}
    assert "Vampiric" in names


def test_proximity_shield_present(mods):
    names = {m["name"] for m in mods}
    assert "Proximity Shield" in names


def test_necromancer_is_extreme(mods):
    necro = next(m for m in mods if m["name"] == "Necromancer")
    assert necro["danger"] == "extreme"


def test_vampiric_is_extreme(mods):
    vampiric = next(m for m in mods if m["name"] == "Vampiric")
    assert vampiric["danger"] == "extreme"


def test_extreme_mods_exist(mods):
    extreme = [m for m in mods if m["danger"] == "extreme"]
    assert len(extreme) >= 2, "Expected at least 2 extreme-danger mods"


def test_combo_warning_is_str_or_none(mods):
    for m in mods:
        cw = m.get("combo_warning")
        assert cw is None or isinstance(cw, str), (
            f"Mod {m['name']}: combo_warning must be str or null"
        )


def test_how_it_works_present(data):
    assert data.get("how_it_works", "").strip()


def test_tips_present(data):
    tips = data.get("tips", [])
    assert len(tips) >= 3
    for tip in tips:
        assert isinstance(tip, str) and tip.strip()


def test_mods_span_multiple_categories(mods):
    categories = {m["category"] for m in mods}
    assert len(categories) >= 3, "Expected mods spread across at least 3 categories"
