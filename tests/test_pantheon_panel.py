"""Tests for Pantheon Powers Reference data integrity."""
import json
import os
import pytest

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "pantheon_powers.json")

_REQUIRED_GOD_FIELDS = {"name", "unlock", "base_powers", "upgrades", "defensive_use", "notes"}
_REQUIRED_UPGRADE_FIELDS = {"power", "capture_target", "capture_map"}


@pytest.fixture(scope="module")
def data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def major_gods(data):
    return data["major_gods"]


@pytest.fixture(scope="module")
def minor_gods(data):
    return data["minor_gods"]


def test_data_file_exists():
    assert os.path.exists(DATA_PATH)


def test_has_major_gods(major_gods):
    assert len(major_gods) >= 4, "Expected at least 4 major gods"


def test_has_minor_gods(minor_gods):
    assert len(minor_gods) >= 6, "Expected at least 6 minor gods"


def test_major_god_required_fields(major_gods):
    for g in major_gods:
        for field in _REQUIRED_GOD_FIELDS:
            assert field in g, f"Major god {g.get('name', '?')} missing field {field!r}"


def test_minor_god_required_fields(minor_gods):
    for g in minor_gods:
        for field in _REQUIRED_GOD_FIELDS:
            assert field in g, f"Minor god {g.get('name', '?')} missing field {field!r}"


def test_upgrade_required_fields(major_gods, minor_gods):
    for g in major_gods + minor_gods:
        for upg in g.get("upgrades", []):
            for field in _REQUIRED_UPGRADE_FIELDS:
                assert field in upg, (
                    f"God {g['name']!r} upgrade missing field {field!r}"
                )


def test_unique_major_god_names(major_gods):
    names = [g["name"] for g in major_gods]
    assert len(set(names)) == len(names), "Duplicate major god names"


def test_unique_minor_god_names(minor_gods):
    names = [g["name"] for g in minor_gods]
    assert len(set(names)) == len(names), "Duplicate minor god names"


def test_base_powers_nonempty(major_gods, minor_gods):
    for g in major_gods + minor_gods:
        assert len(g.get("base_powers", [])) >= 1, (
            f"God {g['name']!r} has no base powers"
        )


def test_brine_king_present(major_gods):
    names = {g["name"] for g in major_gods}
    assert "Soul of the Brine King" in names


def test_brine_king_has_freeze_defense(major_gods):
    bk = next(g for g in major_gods if g["name"] == "Soul of the Brine King")
    combined = " ".join(bk.get("base_powers", [])).lower()
    assert "frozen" in combined or "freeze" in combined


def test_solaris_present(major_gods):
    names = {g["name"] for g in major_gods}
    assert "Soul of Solaris" in names


def test_solaris_has_physical_reduction(major_gods):
    solaris = next(g for g in major_gods if g["name"] == "Soul of Solaris")
    combined = " ".join(solaris.get("base_powers", [])).lower()
    assert "physical" in combined


def test_shakari_present(minor_gods):
    names = {g["name"] for g in minor_gods}
    assert "Soul of Shakari" in names


def test_shakari_has_poison_defense(minor_gods):
    shakari = next(g for g in minor_gods if g["name"] == "Soul of Shakari")
    combined = " ".join([
        " ".join(shakari.get("base_powers", [])),
        shakari.get("defensive_use", ""),
    ]).lower()
    assert "poison" in combined


def test_shakari_upgrade_mentions_50_percent(minor_gods):
    shakari = next(g for g in minor_gods if g["name"] == "Soul of Shakari")
    upgrades = shakari.get("upgrades", [])
    assert any("50%" in u.get("power", "") for u in upgrades), (
        "Shakari upgrade should mention 50% poison avoidance"
    )


def test_ryslatha_present(minor_gods):
    names = {g["name"] for g in minor_gods}
    assert "Soul of Ryslatha" in names


def test_how_it_works_present(data):
    assert data.get("how_it_works", "").strip()


def test_divine_vessel_note_present(data):
    assert data.get("divine_vessel_note", "").strip()


def test_tips_present(data):
    tips = data.get("tips", [])
    assert len(tips) >= 4
    for tip in tips:
        assert isinstance(tip, str) and tip.strip()


def test_defensive_use_nonempty(major_gods, minor_gods):
    for g in major_gods + minor_gods:
        assert g.get("defensive_use", "").strip(), (
            f"God {g['name']!r} has empty defensive_use"
        )


def test_unlock_nonempty(major_gods, minor_gods):
    for g in major_gods + minor_gods:
        assert g.get("unlock", "").strip(), (
            f"God {g['name']!r} has empty unlock"
        )
