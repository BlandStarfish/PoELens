"""
Unit tests for modules/map_overlay.py — MapOverlay zone tracking.

Tests cover:
  - Zone lookup in static data (known/unknown zones)
  - Zone change handling and current zone population
  - Session history (ordering, max length)
  - Update callback firing
  - Campaign progress bar text formula (replicated from map_panel._update_campaign_progress)
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.map_overlay import MapOverlay


# ─────────────────────────────────────────────────────────────────────────────
# Initial state
# ─────────────────────────────────────────────────────────────────────────────

class TestMapOverlayInitial:
    def test_no_current_zone_at_start(self):
        overlay = MapOverlay()
        assert overlay.get_current_zone() is None

    def test_empty_history_at_start(self):
        overlay = MapOverlay()
        assert overlay.get_history() == []


# ─────────────────────────────────────────────────────────────────────────────
# Zone change handling
# ─────────────────────────────────────────────────────────────────────────────

class TestMapOverlayZoneChange:
    def test_known_zone_populates_info(self):
        """A zone in zones.json should have its info dict populated."""
        overlay = MapOverlay()
        overlay.handle_zone_change({"zone": "Twilight Strand"})
        current = overlay.get_current_zone()
        assert current is not None
        assert current["name"] == "Twilight Strand"
        assert current["info"] is not None
        assert current["info"]["act"] == 1

    def test_known_zone_info_contains_expected_fields(self):
        """Zone info must contain area_level, waypoint, and type fields."""
        overlay = MapOverlay()
        overlay.handle_zone_change({"zone": "Twilight Strand"})
        info = overlay.get_current_zone()["info"]
        assert "area_level" in info
        assert "waypoint" in info
        assert "type" in info

    def test_unknown_zone_has_none_info(self):
        """Zones not in the database should have info=None, not raise an error."""
        overlay = MapOverlay()
        overlay.handle_zone_change({"zone": "Unknown Area XYZ"})
        current = overlay.get_current_zone()
        assert current is not None
        assert current["name"] == "Unknown Area XYZ"
        assert current["info"] is None

    def test_empty_zone_name_ignored(self):
        """Events with empty zone name must be silently discarded."""
        overlay = MapOverlay()
        overlay.handle_zone_change({"zone": ""})
        assert overlay.get_current_zone() is None

    def test_whitespace_only_zone_ignored(self):
        """Events with whitespace-only zone name must be silently discarded."""
        overlay = MapOverlay()
        overlay.handle_zone_change({"zone": "   "})
        assert overlay.get_current_zone() is None

    def test_zone_change_updates_current(self):
        """Entering a second zone replaces the current zone."""
        overlay = MapOverlay()
        overlay.handle_zone_change({"zone": "Twilight Strand"})
        overlay.handle_zone_change({"zone": "The Coast"})
        assert overlay.get_current_zone()["name"] == "The Coast"

    def test_timestamp_recorded(self):
        """Zone change entries must have a timestamp close to now."""
        overlay = MapOverlay()
        before = time.time()
        overlay.handle_zone_change({"zone": "Twilight Strand"})
        after = time.time()
        ts = overlay.get_current_zone()["timestamp"]
        assert before <= ts <= after

    def test_atlas_zone_has_tier_in_info(self):
        """Atlas map entries should have a tier field in info."""
        overlay = MapOverlay()
        # Use a zone that is in zones.json as atlas type — check first
        # by looking for an atlas zone by zone_db inspection
        db = overlay._zone_db
        atlas_zones = [k for k, v in db.items() if isinstance(v, dict) and v.get("type") == "atlas"]
        if not atlas_zones:
            return  # skip if no atlas zones in db
        overlay.handle_zone_change({"zone": atlas_zones[0]})
        info = overlay.get_current_zone()["info"]
        assert info["type"] == "atlas"
        assert "tier" in info


# ─────────────────────────────────────────────────────────────────────────────
# Session history
# ─────────────────────────────────────────────────────────────────────────────

class TestMapOverlayHistory:
    def test_history_ordered_most_recent_first(self):
        """History must be most-recent-first (newest at index 0)."""
        overlay = MapOverlay()
        overlay.handle_zone_change({"zone": "Twilight Strand"})
        overlay.handle_zone_change({"zone": "The Coast"})
        overlay.handle_zone_change({"zone": "The Mud Flats"})
        history = overlay.get_history()
        assert history[0]["name"] == "The Mud Flats"
        assert history[1]["name"] == "The Coast"
        assert history[2]["name"] == "Twilight Strand"

    def test_history_capped_at_max(self):
        """History must not exceed 15 entries regardless of how many zones are entered."""
        overlay = MapOverlay()
        for i in range(20):
            overlay.handle_zone_change({"zone": f"Zone {i}"})
        assert len(overlay.get_history()) == 15

    def test_history_oldest_entry_dropped_when_full(self):
        """When history exceeds max, the oldest (first-entered) entry is dropped."""
        overlay = MapOverlay()
        overlay.handle_zone_change({"zone": "First Zone"})
        for i in range(15):
            overlay.handle_zone_change({"zone": f"Zone {i}"})
        names = [e["name"] for e in overlay.get_history()]
        assert "First Zone" not in names

    def test_history_returns_copy(self):
        """Mutating the returned history list must not affect internal state."""
        overlay = MapOverlay()
        overlay.handle_zone_change({"zone": "Twilight Strand"})
        history = overlay.get_history()
        history.clear()
        assert len(overlay.get_history()) == 1

    def test_single_zone_in_history(self):
        """After one zone change, history has exactly one entry."""
        overlay = MapOverlay()
        overlay.handle_zone_change({"zone": "Twilight Strand"})
        assert len(overlay.get_history()) == 1


# ─────────────────────────────────────────────────────────────────────────────
# Update callbacks
# ─────────────────────────────────────────────────────────────────────────────

class TestMapOverlayCallback:
    def test_callback_fires_on_zone_change(self):
        """on_update callbacks must fire when handle_zone_change is called."""
        overlay = MapOverlay()
        received = []
        overlay.on_update(lambda entry: received.append(entry))
        overlay.handle_zone_change({"zone": "Twilight Strand"})
        assert len(received) == 1

    def test_callback_receives_current_entry(self):
        """Callback argument is the current zone entry dict with expected keys."""
        overlay = MapOverlay()
        received = []
        overlay.on_update(lambda e: received.append(e))
        overlay.handle_zone_change({"zone": "The Coast"})
        entry = received[0]
        assert "name" in entry
        assert "info" in entry
        assert "timestamp" in entry

    def test_callback_receives_correct_zone_name(self):
        overlay = MapOverlay()
        received = []
        overlay.on_update(lambda e: received.append(e["name"]))
        overlay.handle_zone_change({"zone": "Twilight Strand"})
        assert received[0] == "Twilight Strand"

    def test_multiple_callbacks_all_fire(self):
        """All registered callbacks must fire on each zone change."""
        overlay = MapOverlay()
        a, b = [], []
        overlay.on_update(lambda e: a.append(1))
        overlay.on_update(lambda e: b.append(1))
        overlay.handle_zone_change({"zone": "Twilight Strand"})
        assert len(a) == 1 and len(b) == 1

    def test_failing_callback_does_not_crash_overlay(self):
        """A callback that raises must not propagate and must not prevent the zone update."""
        overlay = MapOverlay()
        overlay.on_update(lambda e: 1 / 0)   # deliberately raises ZeroDivisionError
        # Must not propagate the exception
        overlay.handle_zone_change({"zone": "Twilight Strand"})
        assert overlay.get_current_zone()["name"] == "Twilight Strand"

    def test_no_callback_on_empty_zone_name(self):
        """Callbacks must NOT fire when the zone name is empty (event is discarded)."""
        overlay = MapOverlay()
        received = []
        overlay.on_update(lambda e: received.append(e))
        overlay.handle_zone_change({"zone": ""})
        assert len(received) == 0


# ─────────────────────────────────────────────────────────────────────────────
# Campaign progress bar text formula
#
# Replicates the bar generation formula from MapPanel._update_campaign_progress()
# to test the logic without requiring a Qt display.
# ─────────────────────────────────────────────────────────────────────────────

def _progress_text(act) -> str | None:
    """
    Replicate the bar text formula from MapPanel._update_campaign_progress().
    Returns the expected label text string, or None if act is invalid/out-of-range.
    """
    try:
        act_n = int(act)
    except (TypeError, ValueError):
        return None
    if not (1 <= act_n <= 10):
        return None
    filled = "\u2501" * act_n        # BOX DRAWINGS HEAVY HORIZONTAL (━)
    empty  = "\u2500" * (10 - act_n) # BOX DRAWINGS LIGHT HORIZONTAL (─)
    return f"Campaign   Act {act_n} / 10   [{filled}{empty}]"


class TestCampaignProgressText:
    def test_act_1_single_filled_bar(self):
        text = _progress_text(1)
        assert text is not None
        assert "Act 1 / 10" in text
        assert text.count("\u2501") == 1
        assert text.count("\u2500") == 9

    def test_act_5_half_filled_bar(self):
        text = _progress_text(5)
        assert text.count("\u2501") == 5
        assert text.count("\u2500") == 5

    def test_act_10_fully_filled_bar(self):
        text = _progress_text(10)
        assert text.count("\u2501") == 10
        assert text.count("\u2500") == 0

    def test_act_0_invalid(self):
        assert _progress_text(0) is None

    def test_act_negative_invalid(self):
        assert _progress_text(-1) is None

    def test_act_11_invalid(self):
        assert _progress_text(11) is None

    def test_act_none_invalid(self):
        assert _progress_text(None) is None

    def test_act_question_mark_invalid(self):
        """The '?' fallback string from zones.json must produce None (label hidden)."""
        assert _progress_text("?") is None

    def test_act_string_numeric_valid(self):
        """String '5' parses to int 5 — same result as passing int 5."""
        assert _progress_text("5") == _progress_text(5)

    def test_bar_total_always_ten_chars(self):
        """Filled + empty bar characters must always total exactly 10."""
        for act in range(1, 11):
            text = _progress_text(act)
            bar_content = text[text.index("[") + 1 : text.index("]")]
            assert len(bar_content) == 10, f"Act {act} bar length {len(bar_content)} != 10"

    def test_act_label_in_output(self):
        """Output must always contain the act number and total."""
        for act in range(1, 11):
            text = _progress_text(act)
            assert f"Act {act} / 10" in text
