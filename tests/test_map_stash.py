"""
Unit tests for Map Stash Scanner feature.

Tests cover:
  - _parse_map_item: property parsing for tier, IIQ, IIR, pack size, mods
  - get_map_items: filtering to MapStash tabs, sorting, empty cases
  - MapStashScanner: scan threading, callback firing, get_last_result
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.stash_api import _parse_map_item


# ---------------------------------------------------------------------------
# _parse_map_item
# ---------------------------------------------------------------------------

def _make_item(type_line="Crimson Temple", tier=14, rarity="Rare",
               identified=True, iiq=45, iir=25, pack_size=15,
               mods=None):
    """Build a minimal GGG stash API item dict for a map."""
    props = [
        {"name": "Map Tier", "values": [[str(tier), 0]]},
    ]
    if iiq:
        props.append({"name": "Item Quantity", "values": [[f"+{iiq}%", 1]]})
    if iir:
        props.append({"name": "Item Rarity", "values": [[f"+{iir}%", 1]]})
    if pack_size:
        props.append({"name": "Monster Pack Size", "values": [[f"+{pack_size}%", 1]]})
    return {
        "typeLine":     type_line,
        "rarity":       rarity,
        "identified":   identified,
        "properties":   props,
        "explicitMods": mods or [],
    }


class TestParseMapItem:
    def test_basic_fields(self):
        item = _make_item("Crimson Temple", tier=14, rarity="Rare")
        result = _parse_map_item(item)
        assert result["name"] == "Crimson Temple"
        assert result["tier"] == 14
        assert result["rarity"] == "Rare"
        assert result["identified"] is True

    def test_iiq_iir_pack_size(self):
        item = _make_item(iiq=45, iir=25, pack_size=15)
        result = _parse_map_item(item)
        assert result["iiq"] == 45
        assert result["iir"] == 25
        assert result["pack_size"] == 15

    def test_zero_stats_for_normal_map(self):
        item = _make_item(rarity="Normal", iiq=0, iir=0, pack_size=0)
        result = _parse_map_item(item)
        assert result["iiq"] == 0
        assert result["iir"] == 0
        assert result["pack_size"] == 0

    def test_mods_populated(self):
        mods = [
            "Players have -10% to all Resistances",
            "Monsters deal 30% extra Physical Damage as Fire",
        ]
        item = _make_item(mods=mods)
        result = _parse_map_item(item)
        assert result["mods"] == mods

    def test_empty_mods_for_normal_map(self):
        item = _make_item(rarity="Normal", mods=[])
        result = _parse_map_item(item)
        assert result["mods"] == []

    def test_unidentified_map(self):
        item = _make_item(identified=False, mods=[])
        result = _parse_map_item(item)
        assert result["identified"] is False

    def test_magic_rarity(self):
        item = _make_item(rarity="Magic", iiq=20, iir=0, pack_size=0)
        result = _parse_map_item(item)
        assert result["rarity"] == "Magic"
        assert result["iiq"] == 20

    def test_tier_zero_when_absent(self):
        item = {
            "typeLine": "Beach",
            "rarity": "Normal",
            "identified": True,
            "properties": [],
            "explicitMods": [],
        }
        result = _parse_map_item(item)
        assert result["tier"] == 0

    def test_missing_optional_fields_use_defaults(self):
        """Item missing rarity/identified/explicitMods should not crash."""
        item = {
            "typeLine": "Crimson Temple",
            "properties": [{"name": "Map Tier", "values": [["12", 0]]}],
        }
        result = _parse_map_item(item)
        assert result["tier"] == 12
        assert result["rarity"] == "Normal"
        assert result["identified"] is True
        assert result["mods"] == []

    def test_malformed_tier_falls_back_to_zero(self):
        item = {
            "typeLine": "Beach",
            "rarity": "Normal",
            "identified": True,
            "properties": [{"name": "Map Tier", "values": [["N/A", 0]]}],
            "explicitMods": [],
        }
        result = _parse_map_item(item)
        assert result["tier"] == 0

    def test_malformed_iiq_falls_back_to_zero(self):
        item = {
            "typeLine": "Beach",
            "rarity": "Magic",
            "identified": True,
            "properties": [
                {"name": "Map Tier", "values": [["5", 0]]},
                {"name": "Item Quantity", "values": [["N/A", 1]]},
            ],
            "explicitMods": [],
        }
        result = _parse_map_item(item)
        assert result["iiq"] == 0


# ---------------------------------------------------------------------------
# get_map_items (via StashAPI with mock)
# ---------------------------------------------------------------------------

class _MockOAuth:
    def get_access_token(self):
        return "fake_token"
    @property
    def client_id(self):
        return "test_client"


class _MockStashAPI:
    """Minimal double that delegates get_map_items() logic to StashAPI."""
    def __init__(self, tab_list, tab_contents):
        self._tab_list     = tab_list
        self._tab_contents = tab_contents

    def list_tabs(self, league):
        return self._tab_list

    def get_tab(self, league, stash_id):
        return self._tab_contents.get(stash_id)


class TestGetMapItems:
    def _make_stash_api(self, tab_list, tab_contents):
        from core.stash_api import StashAPI
        api = StashAPI.__new__(StashAPI)
        api._oauth        = _MockOAuth()
        api._realm        = "pc"
        api._last_request = 0.0
        # Patch methods
        api.list_tabs = lambda league: tab_list
        api.get_tab   = lambda league, sid: tab_contents.get(sid)
        return api

    def test_returns_empty_when_no_map_tab(self):
        api = self._make_stash_api(
            [{"id": "c1", "type": "CurrencyStash"}],
            {"c1": {"stash": {"items": []}}}
        )
        result = api.get_map_items("Mirage")
        assert result == []

    def test_returns_empty_when_list_tabs_fails(self):
        api = self._make_stash_api(None, {})
        result = api.get_map_items("Mirage")
        assert result == []

    def test_returns_maps_from_map_stash(self):
        items = [_make_item("Crimson Temple", tier=14), _make_item("Beach", tier=1)]
        api = self._make_stash_api(
            [{"id": "m1", "type": "MapStash"}],
            {"m1": {"stash": {"items": items}}}
        )
        result = api.get_map_items("Mirage")
        assert len(result) == 2
        # Sorted tier desc
        assert result[0]["tier"] == 14
        assert result[1]["tier"] == 1

    def test_skips_non_map_tabs(self):
        map_items  = [_make_item("Crimson Temple", tier=14)]
        curr_items = [{"typeLine": "Chaos Orb", "rarity": "Currency", "identified": True, "properties": []}]
        api = self._make_stash_api(
            [{"id": "c1", "type": "CurrencyStash"}, {"id": "m1", "type": "MapStash"}],
            {
                "c1": {"stash": {"items": curr_items}},
                "m1": {"stash": {"items": map_items}},
            }
        )
        result = api.get_map_items("Mirage")
        assert len(result) == 1
        assert result[0]["name"] == "Crimson Temple"

    def test_sorted_by_tier_desc_then_name_asc(self):
        items = [
            _make_item("Waste Pool", tier=6),
            _make_item("Crimson Temple", tier=14),
            _make_item("Beach", tier=1),
            _make_item("Alleyways", tier=1),
        ]
        api = self._make_stash_api(
            [{"id": "m1", "type": "MapStash"}],
            {"m1": {"stash": {"items": items}}}
        )
        result = api.get_map_items("Mirage")
        assert result[0]["name"] == "Crimson Temple"
        assert result[1]["name"] == "Waste Pool"
        assert result[2]["name"] == "Alleyways"   # alphabetical within tier 1
        assert result[3]["name"] == "Beach"


# ---------------------------------------------------------------------------
# MapStashScanner
# ---------------------------------------------------------------------------

class TestMapStashScanner:
    def test_get_last_result_initially_none(self):
        from modules.map_stash import MapStashScanner

        class _FakeStashAPI:
            def get_map_items(self, league):
                return []

        scanner = MapStashScanner(_FakeStashAPI())
        assert scanner.get_last_result() is None

    def test_scan_calls_on_done_success(self):
        from modules.map_stash import MapStashScanner
        import threading

        maps = [_parse_map_item(_make_item("Beach", tier=1))]

        class _FakeStashAPI:
            def get_map_items(self, league):
                return maps

        scanner  = MapStashScanner(_FakeStashAPI())
        results  = []
        done_evt = threading.Event()

        def on_done(ok, err):
            results.append((ok, err))
            done_evt.set()

        scanner.scan("Mirage", on_done)
        done_evt.wait(timeout=5)

        assert results == [(True, "")]
        assert scanner.get_last_result() == maps

    def test_scan_fires_on_update_callback(self):
        from modules.map_stash import MapStashScanner
        import threading

        maps = [_parse_map_item(_make_item("Crimson Temple", tier=14))]

        class _FakeStashAPI:
            def get_map_items(self, league):
                return maps

        scanner    = MapStashScanner(_FakeStashAPI())
        callbacks  = []
        done_evt   = threading.Event()

        scanner.on_update(lambda m: callbacks.append(m))
        scanner.scan("Mirage", lambda ok, err: done_evt.set())
        done_evt.wait(timeout=5)

        assert len(callbacks) == 1
        assert callbacks[0] == maps

    def test_scan_calls_on_done_error_on_exception(self):
        from modules.map_stash import MapStashScanner
        import threading

        class _ErrorStashAPI:
            def get_map_items(self, league):
                raise RuntimeError("network error")

        scanner  = MapStashScanner(_ErrorStashAPI())
        results  = []
        done_evt = threading.Event()

        def on_done(ok, err):
            results.append((ok, err))
            done_evt.set()

        scanner.scan("Mirage", on_done)
        done_evt.wait(timeout=5)

        assert results[0][0] is False
        assert "network error" in results[0][1]
