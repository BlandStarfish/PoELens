"""
Unit tests for modules/heist_planner.py and stash_api Heist helpers.

Tests cover:
  - _process(): contract grouping by job, sorting, blueprint sorting
  - stash_api._extract_heist_job(): known jobs, missing job, empty requirements
  - stash_api._extract_wing_status(): normal case, partial, none, malformed
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.heist_planner import _process, ROGUE_JOBS
from core.stash_api import _extract_heist_job, _extract_wing_status


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _req(job: str, level: int = 3) -> dict:
    """Minimal GGG requirement entry for a rogue job."""
    return {"name": job, "values": [[str(level), 0]]}


def _req_level(level: int = 1) -> dict:
    """The standard 'Level' requirement that every item has — should be ignored."""
    return {"name": "Level", "values": [[str(level), 0]]}


def _contract(name: str, ilvl: int, job: str, job_level: int = 3) -> dict:
    return {"name": name, "ilvl": ilvl, "job": job, "job_level": job_level}


def _blueprint(name: str, ilvl: int, wings_unlocked: int = 0, wings_total: int = 4) -> dict:
    return {
        "name":          name,
        "ilvl":          ilvl,
        "job":           "Lockpicking",
        "job_level":     3,
        "wings_unlocked": wings_unlocked,
        "wings_total":   wings_total,
    }


def _raw(contracts: list, blueprints: list) -> dict:
    return {"contracts": contracts, "blueprints": blueprints}


# ─────────────────────────────────────────────────────────────────────────────
# _extract_heist_job
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractHeistJob:
    def test_known_job_returned(self):
        reqs = [_req_level(1), _req("Lockpicking", 5)]
        job, level = _extract_heist_job(reqs)
        assert job == "Lockpicking"
        assert level == 5

    def test_all_rogue_jobs_recognised(self):
        for job_name in ROGUE_JOBS:
            job, level = _extract_heist_job([_req(job_name, 3)])
            assert job == job_name

    def test_level_requirement_not_matched(self):
        """'Level' is a standard item requirement — must not be returned as the job."""
        job, level = _extract_heist_job([_req_level(20)])
        assert job == "Unknown"

    def test_empty_requirements(self):
        job, level = _extract_heist_job([])
        assert job == "Unknown"
        assert level == 0

    def test_missing_values_field(self):
        reqs = [{"name": "Agility"}]   # no 'values' key
        job, level = _extract_heist_job(reqs)
        assert job == "Agility"
        assert level == 0   # empty values → 0


# ─────────────────────────────────────────────────────────────────────────────
# _extract_wing_status
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractWingStatus:
    def _prop(self, unlocked: int, total: int) -> dict:
        return {"name": "Wings Unlocked", "values": [[f"{unlocked}/{total}", 0]]}

    def test_normal_case(self):
        unlocked, total = _extract_wing_status([self._prop(2, 4)])
        assert unlocked == 2
        assert total == 4

    def test_fully_unlocked(self):
        unlocked, total = _extract_wing_status([self._prop(4, 4)])
        assert unlocked == total == 4

    def test_none_unlocked(self):
        unlocked, total = _extract_wing_status([self._prop(0, 3)])
        assert unlocked == 0
        assert total == 3

    def test_empty_additional_properties(self):
        unlocked, total = _extract_wing_status([])
        assert (unlocked, total) == (0, 0)

    def test_wrong_property_name_ignored(self):
        props = [{"name": "Reward Rooms", "values": [["3", 0]]}]
        assert _extract_wing_status(props) == (0, 0)

    def test_malformed_value(self):
        props = [{"name": "Wings Unlocked", "values": [["not/a/number", 0]]}]
        assert _extract_wing_status(props) == (0, 0)


# ─────────────────────────────────────────────────────────────────────────────
# _process
# ─────────────────────────────────────────────────────────────────────────────

class TestProcess:
    def test_empty_input(self):
        result = _process(_raw([], []))
        assert result["total_contracts"] == 0
        assert result["total_blueprints"] == 0
        assert result["contracts_by_job"] == {}
        assert result["blueprints"] == []

    def test_contracts_grouped_by_job(self):
        raw = _raw([
            _contract("A", 68, "Lockpicking"),
            _contract("B", 70, "Agility"),
            _contract("C", 72, "Lockpicking"),
        ], [])
        result = _process(raw)
        assert set(result["contracts_by_job"].keys()) == {"Lockpicking", "Agility"}
        assert len(result["contracts_by_job"]["Lockpicking"]) == 2
        assert len(result["contracts_by_job"]["Agility"]) == 1

    def test_contracts_sorted_by_ilvl_desc(self):
        raw = _raw([
            _contract("Low",  65, "Lockpicking"),
            _contract("High", 83, "Lockpicking"),
            _contract("Mid",  73, "Lockpicking"),
        ], [])
        result = _process(raw)
        ilvls = [c["ilvl"] for c in result["contracts_by_job"]["Lockpicking"]]
        assert ilvls == sorted(ilvls, reverse=True)

    def test_blueprints_sorted_ilvl_desc_then_wings_desc(self):
        raw = _raw([], [
            _blueprint("B1", ilvl=70, wings_unlocked=1),
            _blueprint("B2", ilvl=83, wings_unlocked=0),
            _blueprint("B3", ilvl=83, wings_unlocked=3),
        ])
        result = _process(raw)
        bps = result["blueprints"]
        assert bps[0]["name"] == "B3"   # ilvl=83, wings=3 (highest first)
        assert bps[1]["name"] == "B2"   # ilvl=83, wings=0
        assert bps[2]["name"] == "B1"   # ilvl=70

    def test_total_counts(self):
        raw = _raw(
            [_contract("A", 68, "Lockpicking"), _contract("B", 70, "Agility")],
            [_blueprint("BP", 75)],
        )
        result = _process(raw)
        assert result["total_contracts"] == 2
        assert result["total_blueprints"] == 1

    def test_unknown_job_preserved(self):
        raw = _raw([_contract("X", 68, "Unknown")], [])
        result = _process(raw)
        assert "Unknown" in result["contracts_by_job"]
