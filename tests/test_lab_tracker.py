"""Tests for modules/lab_tracker.py"""

import json
import os
import pytest

from modules.lab_tracker import LabTracker, DIFFICULTIES, POINTS_PER_LAB


@pytest.fixture
def tracker(tmp_path, monkeypatch):
    """LabTracker that saves to a temp directory."""
    state_path = tmp_path / "lab.json"
    monkeypatch.setattr("modules.lab_tracker._STATE_PATH", str(state_path))
    return LabTracker()


class TestLabTrackerInitialState:
    def test_all_labs_incomplete_on_first_run(self, tracker):
        status = tracker.get_status()
        assert status == {d: False for d in DIFFICULTIES}

    def test_all_four_difficulties_present(self, tracker):
        status = tracker.get_status()
        assert set(status.keys()) == {"Normal", "Cruel", "Merciless", "Eternal"}

    def test_zero_ascendancy_points_initially(self, tracker):
        pts = tracker.get_ascendancy_points()
        assert pts["earned"] == 0
        assert pts["available"] == 8


class TestLabTrackerToggle:
    def test_toggle_marks_incomplete_as_complete(self, tracker):
        tracker.toggle("Normal")
        assert tracker.get_status()["Normal"] is True

    def test_toggle_marks_complete_as_incomplete(self, tracker):
        tracker.toggle("Normal")
        tracker.toggle("Normal")
        assert tracker.get_status()["Normal"] is False

    def test_toggle_only_affects_target_difficulty(self, tracker):
        tracker.toggle("Cruel")
        status = tracker.get_status()
        assert status["Cruel"] is True
        assert status["Normal"] is False
        assert status["Merciless"] is False
        assert status["Eternal"] is False

    def test_toggle_unknown_difficulty_is_ignored(self, tracker):
        tracker.toggle("Unknown")
        assert tracker.get_status() == {d: False for d in DIFFICULTIES}


class TestLabTrackerSetCompleted:
    def test_set_completed_true(self, tracker):
        tracker.set_completed("Merciless", True)
        assert tracker.get_status()["Merciless"] is True

    def test_set_completed_false(self, tracker):
        tracker.toggle("Merciless")
        tracker.set_completed("Merciless", False)
        assert tracker.get_status()["Merciless"] is False

    def test_set_completed_unknown_is_ignored(self, tracker):
        tracker.set_completed("Uber", True)
        assert tracker.get_status() == {d: False for d in DIFFICULTIES}


class TestLabTrackerAscendancyPoints:
    def test_one_lab_gives_two_points(self, tracker):
        tracker.toggle("Normal")
        pts = tracker.get_ascendancy_points()
        assert pts["earned"] == 2

    def test_all_labs_give_eight_points(self, tracker):
        for d in DIFFICULTIES:
            tracker.toggle(d)
        pts = tracker.get_ascendancy_points()
        assert pts["earned"] == 8

    def test_available_always_eight(self, tracker):
        pts = tracker.get_ascendancy_points()
        assert pts["available"] == 8

    def test_partial_completion(self, tracker):
        tracker.toggle("Normal")
        tracker.toggle("Cruel")
        pts = tracker.get_ascendancy_points()
        assert pts["earned"] == 4


class TestLabTrackerReset:
    def test_reset_clears_all(self, tracker):
        for d in DIFFICULTIES:
            tracker.toggle(d)
        tracker.reset()
        assert tracker.get_status() == {d: False for d in DIFFICULTIES}

    def test_reset_clears_ascendancy_points(self, tracker):
        for d in DIFFICULTIES:
            tracker.toggle(d)
        tracker.reset()
        assert tracker.get_ascendancy_points()["earned"] == 0


class TestLabTrackerPersistence:
    def test_state_persists_after_reload(self, tmp_path, monkeypatch):
        state_path = tmp_path / "lab.json"
        monkeypatch.setattr("modules.lab_tracker._STATE_PATH", str(state_path))

        t1 = LabTracker()
        t1.toggle("Normal")
        t1.toggle("Eternal")

        t2 = LabTracker()
        status = t2.get_status()
        assert status["Normal"] is True
        assert status["Eternal"] is True
        assert status["Cruel"] is False
        assert status["Merciless"] is False

    def test_reset_clears_persisted_state(self, tmp_path, monkeypatch):
        state_path = tmp_path / "lab.json"
        monkeypatch.setattr("modules.lab_tracker._STATE_PATH", str(state_path))

        t1 = LabTracker()
        t1.toggle("Normal")
        t1.reset()

        t2 = LabTracker()
        assert t2.get_status()["Normal"] is False

    def test_partial_file_handled_gracefully(self, tmp_path, monkeypatch):
        state_path = tmp_path / "lab.json"
        monkeypatch.setattr("modules.lab_tracker._STATE_PATH", str(state_path))
        # Write only some keys — missing keys should default to False
        state_path.write_text(json.dumps({"Normal": True}))
        t = LabTracker()
        status = t.get_status()
        assert status["Normal"] is True
        assert status["Cruel"] is False

    def test_corrupt_file_handled_gracefully(self, tmp_path, monkeypatch):
        state_path = tmp_path / "lab.json"
        monkeypatch.setattr("modules.lab_tracker._STATE_PATH", str(state_path))
        state_path.write_text("not json {{{")
        t = LabTracker()
        assert t.get_status() == {d: False for d in DIFFICULTIES}


class TestLabTrackerCallback:
    def test_on_update_called_on_toggle(self, tracker):
        calls = []
        tracker.on_update(lambda: calls.append(1))
        tracker.toggle("Normal")
        assert len(calls) == 1

    def test_on_update_called_on_reset(self, tracker):
        calls = []
        tracker.on_update(lambda: calls.append(1))
        tracker.reset()
        assert len(calls) == 1

    def test_multiple_callbacks_all_called(self, tracker):
        calls = []
        tracker.on_update(lambda: calls.append("a"))
        tracker.on_update(lambda: calls.append("b"))
        tracker.toggle("Cruel")
        assert calls == ["a", "b"]

    def test_failing_callback_does_not_break_others(self, tracker):
        calls = []
        tracker.on_update(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        tracker.on_update(lambda: calls.append(1))
        tracker.toggle("Normal")
        assert calls == [1]


class TestLabTrackerConstants:
    def test_difficulties_order(self):
        assert DIFFICULTIES == ["Normal", "Cruel", "Merciless", "Eternal"]

    def test_each_lab_grants_two_points(self):
        assert all(v == 2 for v in POINTS_PER_LAB.values())

    def test_total_available_points_is_eight(self):
        assert sum(POINTS_PER_LAB.values()) == 8
