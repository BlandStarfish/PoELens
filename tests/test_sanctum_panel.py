"""Tests for Sanctum Affliction & Boon data integrity."""
import json
import os
import pytest

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sanctum_afflictions.json")

_VALID_SEVERITIES = {"critical", "dangerous", "moderate", "minor"}
_VALID_VALUES     = {"high", "medium", "low"}


@pytest.fixture(scope="module")
def data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def afflictions(data):
    return data["afflictions"]


@pytest.fixture(scope="module")
def boons(data):
    return data["boons"]


def test_data_file_exists():
    assert os.path.exists(DATA_PATH)


def test_has_afflictions(afflictions):
    assert len(afflictions) >= 15, "Expected at least 15 afflictions"


def test_has_boons(boons):
    assert len(boons) >= 8, "Expected at least 8 boons"


def test_affliction_required_fields(afflictions):
    required = {"name", "effect", "severity", "category"}
    for a in afflictions:
        for field in required:
            assert field in a, f"Affliction {a.get('name', '?')} missing field {field!r}"


def test_boon_required_fields(boons):
    required = {"name", "effect", "value", "category"}
    for b in boons:
        for field in required:
            assert field in b, f"Boon {b.get('name', '?')} missing field {field!r}"


def test_affliction_valid_severity(afflictions):
    for a in afflictions:
        assert a["severity"] in _VALID_SEVERITIES, (
            f"Affliction {a['name']} has invalid severity {a['severity']!r}"
        )


def test_boon_valid_value(boons):
    for b in boons:
        assert b["value"] in _VALID_VALUES, (
            f"Boon {b['name']} has invalid value {b['value']!r}"
        )


def test_affliction_names_nonempty(afflictions):
    for a in afflictions:
        assert a["name"].strip(), "Affliction name is empty"


def test_boon_names_nonempty(boons):
    for b in boons:
        assert b["name"].strip(), "Boon name is empty"


def test_unique_affliction_names(afflictions):
    names = [a["name"] for a in afflictions]
    assert len(set(names)) == len(names), "Duplicate affliction names"


def test_unique_boon_names(boons):
    names = [b["name"] for b in boons]
    assert len(set(names)) == len(names), "Duplicate boon names"


def test_blind_devotion_present(afflictions):
    names = {a["name"] for a in afflictions}
    assert "Blind Devotion" in names, "Blind Devotion affliction missing"


def test_blind_devotion_is_critical(afflictions):
    bd = next(a for a in afflictions if a["name"] == "Blind Devotion")
    assert bd["severity"] == "critical"


def test_fortified_soul_present(boons):
    names = {b["name"] for b in boons}
    assert "Fortified Soul" in boons or any("fortified" in n.lower() for n in names), (
        "Expected a resolve-boosting boon"
    )


def test_high_value_boons_exist(boons):
    high = [b for b in boons if b["value"] == "high"]
    assert len(high) >= 3, "Expected at least 3 high-value boons"


def test_critical_afflictions_exist(afflictions):
    critical = [a for a in afflictions if a["severity"] == "critical"]
    assert len(critical) >= 2, "Expected at least 2 critical-severity afflictions"


def test_how_it_works_present(data):
    assert data.get("how_it_works", "").strip()


def test_tips_present(data):
    tips = data.get("tips", [])
    assert len(tips) >= 4
    for tip in tips:
        assert isinstance(tip, str) and tip.strip()


def test_affliction_effects_nonempty(afflictions):
    for a in afflictions:
        assert a["effect"].strip(), f"Affliction {a['name']} has empty effect"


def test_boon_effects_nonempty(boons):
    for b in boons:
        assert b["effect"].strip(), f"Boon {b['name']} has empty effect"
