"""Tests for Blight Oil Reference data integrity."""
import json
import os
import pytest

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "blight_oils.json")

_VALID_VALUES = {"high", "medium", "low"}


@pytest.fixture(scope="module")
def data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def oils(data):
    return data["oils"]


@pytest.fixture(scope="module")
def anoints(data):
    return data["notable_anoints"]


def test_data_file_exists():
    assert os.path.exists(DATA_PATH)


def test_has_oils(oils):
    assert len(oils) == 11, "Expected exactly 11 oil tiers"


def test_has_anoints(anoints):
    assert len(anoints) >= 8, "Expected at least 8 notable anoints"


def test_oil_required_fields(oils):
    required = {"name", "tier", "rarity", "market_value"}
    for oil in oils:
        for field in required:
            assert field in oil, f"Oil {oil.get('name', '?')} missing field {field!r}"


def test_anoint_required_fields(anoints):
    required = {"name", "effect", "oils", "value"}
    for a in anoints:
        for field in required:
            assert field in a, f"Anoint {a.get('name', '?')} missing field {field!r}"


def test_oil_tiers_are_sequential(oils):
    tiers = sorted(o["tier"] for o in oils)
    assert tiers == list(range(1, 12)), "Oil tiers must be 1–11 in sequence"


def test_oil_names_nonempty(oils):
    for oil in oils:
        assert oil["name"].strip(), "Oil name is empty"


def test_unique_oil_names(oils):
    names = [o["name"] for o in oils]
    assert len(set(names)) == len(names), "Duplicate oil names"


def test_clear_oil_is_tier_1(oils):
    clear = next(o for o in oils if o["name"] == "Clear Oil")
    assert clear["tier"] == 1


def test_opalescent_oil_is_tier_11(oils):
    opal = next(o for o in oils if o["name"] == "Opalescent Oil")
    assert opal["tier"] == 11


def test_anoint_oils_field_is_list(anoints):
    for a in anoints:
        assert isinstance(a["oils"], list), f"Anoint {a['name']}: oils must be a list"
        assert len(a["oils"]) == 3, f"Anoint {a['name']}: expected 3 oils"


def test_anoint_valid_value(anoints):
    for a in anoints:
        assert a["value"] in _VALID_VALUES, (
            f"Anoint {a['name']} has invalid value {a['value']!r}"
        )


def test_constitution_present(anoints):
    names = {a["name"] for a in anoints}
    assert "Constitution" in names, "Constitution anoint missing"


def test_constitution_uses_verdant_oils(anoints):
    const = next(a for a in anoints if a["name"] == "Constitution")
    assert const["oils"] == ["Verdant", "Verdant", "Verdant"]


def test_high_value_anoints_exist(anoints):
    high = [a for a in anoints if a["value"] == "high"]
    assert len(high) >= 3, "Expected at least 3 high-value anoints"


def test_how_it_works_present(data):
    assert data.get("how_it_works", "").strip()


def test_tips_present(data):
    tips = data.get("tips", [])
    assert len(tips) >= 4
    for tip in tips:
        assert isinstance(tip, str) and tip.strip()


def test_anoint_rules_present(data):
    rules = data.get("anoint_rules", {})
    assert "amulet" in rules, "Expected amulet anoint rule"
    assert "ring" in rules, "Expected ring anoint rule"


def test_all_anoint_oil_names_are_valid_oil_names(oils, anoints):
    # Anoint recipes use short names (e.g. "Verdant") while oil entries use full names
    # ("Verdant Oil"). Accept both formats.
    valid_full   = {o["name"] for o in oils}
    valid_short  = {o["name"].removesuffix(" Oil") for o in oils}
    valid_names  = valid_full | valid_short
    for a in anoints:
        for oil_name in a["oils"]:
            assert oil_name in valid_names, (
                f"Anoint {a['name']} references unknown oil {oil_name!r}"
            )
