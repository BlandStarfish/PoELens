"""
Tests for scarabs.json data integrity.

Validates that the data file is well-formed and all scarabs have required fields.
"""

import json
import os
import pytest

_DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "scarabs.json"
)

_VALID_TIERS = {"Rusted", "Polished", "Gilded", "Winged"}


@pytest.fixture(scope="module")
def scarabs():
    with open(_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["scarabs"]


def test_data_file_exists():
    assert os.path.exists(_DATA_PATH), "scarabs.json not found"


def test_has_scarabs(scarabs):
    assert len(scarabs) > 0


def test_minimum_scarab_count(scarabs):
    assert len(scarabs) >= 40, f"Expected at least 40 scarabs, got {len(scarabs)}"


def test_all_scarabs_have_name(scarabs):
    for s in scarabs:
        assert s.get("name"), f"Scarab missing name: {s}"


def test_all_scarabs_have_mechanic(scarabs):
    for s in scarabs:
        assert s.get("mechanic"), f"Scarab '{s.get('name')}' missing mechanic"


def test_all_scarabs_have_valid_tier(scarabs):
    for s in scarabs:
        tier = s.get("tier")
        assert tier in _VALID_TIERS, \
            f"Scarab '{s.get('name')}' has invalid tier: {tier!r}"


def test_all_scarabs_have_effect(scarabs):
    for s in scarabs:
        assert s.get("effect"), f"Scarab '{s.get('name')}' missing effect"


def test_all_scarabs_have_atlas_passive(scarabs):
    for s in scarabs:
        assert s.get("atlas_passive"), f"Scarab '{s.get('name')}' missing atlas_passive"


def test_unique_scarab_names(scarabs):
    names = [s["name"] for s in scarabs]
    assert len(names) == len(set(names)), "Duplicate scarab names found"


def test_all_four_tiers_represented(scarabs):
    tiers = {s.get("tier") for s in scarabs}
    for tier in _VALID_TIERS:
        assert tier in tiers, f"No scarabs with tier: {tier}"


def test_minimum_mechanic_count(scarabs):
    mechanics = {s.get("mechanic") for s in scarabs}
    assert len(mechanics) >= 8, \
        f"Expected at least 8 distinct mechanics, got {len(mechanics)}"


def test_each_mechanic_has_all_four_tiers(scarabs):
    """Every mechanic in the dataset should have all 4 tiers defined."""
    from collections import defaultdict
    by_mechanic: dict[str, set] = defaultdict(set)
    for s in scarabs:
        by_mechanic[s.get("mechanic", "")].add(s.get("tier"))
    for mechanic, tiers in by_mechanic.items():
        assert tiers == _VALID_TIERS, \
            f"Mechanic '{mechanic}' missing tiers: {_VALID_TIERS - tiers}"


def test_breach_scarabs_present(scarabs):
    breach = [s for s in scarabs if s.get("mechanic") == "Breach"]
    assert len(breach) == 4, f"Expected 4 Breach scarabs, got {len(breach)}"


def test_legion_scarabs_present(scarabs):
    legion = [s for s in scarabs if s.get("mechanic") == "Legion"]
    assert len(legion) == 4, f"Expected 4 Legion scarabs, got {len(legion)}"


def test_expedition_scarabs_present(scarabs):
    expedition = [s for s in scarabs if s.get("mechanic") == "Expedition"]
    assert len(expedition) == 4, f"Expected 4 Expedition scarabs, got {len(expedition)}"


def test_winged_effects_more_powerful_than_rusted(scarabs):
    """Winged tier effects should be longer/more descriptive than Rusted — a proxy for completeness."""
    from collections import defaultdict
    by_mechanic: dict[str, dict] = defaultdict(dict)
    for s in scarabs:
        by_mechanic[s["mechanic"]][s["tier"]] = s["effect"]
    for mechanic, tiers in by_mechanic.items():
        if "Rusted" in tiers and "Winged" in tiers:
            assert len(tiers["Winged"]) >= len(tiers["Rusted"]), \
                f"Mechanic '{mechanic}': Winged effect should be at least as descriptive as Rusted"


def test_group_by_mechanic_utility():
    """Test the grouping helper used by the panel."""
    from ui.widgets.scarab_panel import _group_by_mechanic
    sample = [
        {"name": "Rusted Breach Scarab", "mechanic": "Breach", "tier": "Rusted", "effect": "1 Breach", "atlas_passive": "x"},
        {"name": "Winged Breach Scarab", "mechanic": "Breach", "tier": "Winged", "effect": "4 Breaches", "atlas_passive": "x"},
        {"name": "Rusted Legion Scarab", "mechanic": "Legion", "tier": "Rusted", "effect": "1 Legion", "atlas_passive": "y"},
    ]
    groups = _group_by_mechanic(sample)
    assert set(groups.keys()) == {"Breach", "Legion"}
    assert groups["Breach"][0]["tier"] == "Rusted"
    assert groups["Breach"][1]["tier"] == "Winged"
