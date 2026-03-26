"""Tests for Keystone Passive Reference data and panel logic."""

import json
import os
import pytest

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "keystones.json")


@pytest.fixture(scope="module")
def data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def keystones(data):
    return data["keystones"]


# ── Data integrity ─────────────────────────────────────────────────────────────

def test_data_file_exists():
    assert os.path.exists(DATA_PATH)


def test_has_required_top_level_keys(data):
    for key in ("keystones", "how_it_works", "tips"):
        assert key in data, f"Missing top-level key: {key}"


def test_keystones_non_empty(keystones):
    assert len(keystones) >= 15, f"Expected at least 15 keystones, got {len(keystones)}"


def test_all_keystones_have_required_fields(keystones):
    required = ("name", "effect", "trade_off", "builds_that_need", "breaks_for", "location")
    for ks in keystones:
        for field in required:
            assert field in ks, f"Keystone '{ks.get('name')}' missing field: {field}"


def test_keystone_names_unique(keystones):
    names = [ks["name"] for ks in keystones]
    assert len(names) == len(set(names)), "Duplicate keystone names found"


def test_builds_that_need_is_list(keystones):
    for ks in keystones:
        assert isinstance(ks["builds_that_need"], list), \
            f"'{ks['name']}' builds_that_need is not a list"


def test_breaks_for_is_list(keystones):
    for ks in keystones:
        assert isinstance(ks["breaks_for"], list), \
            f"'{ks['name']}' breaks_for is not a list"


def test_how_it_works_non_empty(data):
    assert data["how_it_works"].strip(), "how_it_works is empty"


def test_tips_non_empty(data):
    assert len(data["tips"]) >= 2, "Expected at least 2 tips"


# ── Spot checks ────────────────────────────────────────────────────────────────

def test_resolute_technique_exists(keystones):
    names = {ks["name"] for ks in keystones}
    assert "Resolute Technique" in names


def test_chaos_inoculation_exists(keystones):
    names = {ks["name"] for ks in keystones}
    assert "Chaos Inoculation" in names


def test_vaal_pact_exists(keystones):
    names = {ks["name"] for ks in keystones}
    assert "Vaal Pact" in names


def test_elemental_equilibrium_exists(keystones):
    names = {ks["name"] for ks in keystones}
    assert "Elemental Equilibrium" in names


def test_blood_magic_exists(keystones):
    names = {ks["name"] for ks in keystones}
    assert "Blood Magic" in names


def test_chaos_inoculation_breaks_life_builds(keystones):
    ci = next((ks for ks in keystones if ks["name"] == "Chaos Inoculation"), None)
    assert ci is not None
    breaks_text = " ".join(ci["breaks_for"]).lower()
    assert "life" in breaks_text, "CI should mention breaking life-based builds"


def test_resolute_technique_effect_mentions_miss(keystones):
    rt = next((ks for ks in keystones if ks["name"] == "Resolute Technique"), None)
    assert rt is not None
    assert "miss" in rt["effect"].lower() or "never" in rt["effect"].lower()


def test_vaal_pact_trade_off_mentions_regen(keystones):
    vp = next((ks for ks in keystones if ks["name"] == "Vaal Pact"), None)
    assert vp is not None
    assert "regen" in vp["trade_off"].lower() or "regeneration" in vp["trade_off"].lower()


def test_acrobatics_exists(keystones):
    names = {ks["name"] for ks in keystones}
    assert "Acrobatics" in names


def test_iron_reflexes_exists(keystones):
    names = {ks["name"] for ks in keystones}
    assert "Iron Reflexes" in names


def test_all_effects_non_empty(keystones):
    for ks in keystones:
        assert ks["effect"].strip(), f"Keystone '{ks['name']}' has empty effect"


def test_all_trade_offs_non_empty(keystones):
    for ks in keystones:
        assert ks["trade_off"].strip(), f"Keystone '{ks['name']}' has empty trade_off"
