"""
Labyrinth completion tracker.

Tracks which Labyrinth difficulties have been completed for the current character.
State persists to state/lab.json. Supports manual toggle and full reset.

No API calls, no event subscriptions — purely manual tracking with persistence.
"""

import json
import os
from typing import Callable

_STATE_PATH = os.path.join(os.path.dirname(__file__), "..", "state", "lab.json")

DIFFICULTIES = ["Normal", "Cruel", "Merciless", "Eternal"]

# Ascendancy points awarded per lab difficulty (2 per completion, 8 total)
POINTS_PER_LAB = {
    "Normal":    2,
    "Cruel":     2,
    "Merciless": 2,
    "Eternal":   2,
}


class LabTracker:
    """
    Tracks lab completion for 4 difficulties with persistence.

    Usage:
        tracker = LabTracker()
        tracker.toggle("Normal")        # mark Normal done / undone
        status = tracker.get_status()   # {"Normal": True, "Cruel": False, ...}
        tracker.reset()                 # clear all for new character
    """

    def __init__(self):
        self._state: dict[str, bool] = self._load()
        self._on_update: list[Callable] = []

    def on_update(self, callback: Callable):
        """Register a callback invoked (with no args) when completion state changes."""
        self._on_update.append(callback)

    def toggle(self, difficulty: str):
        """Toggle completion state for the given difficulty."""
        if difficulty not in DIFFICULTIES:
            return
        self._state[difficulty] = not self._state.get(difficulty, False)
        self._save()
        self._fire_update()

    def set_completed(self, difficulty: str, completed: bool):
        """Explicitly set completion state for a difficulty."""
        if difficulty not in DIFFICULTIES:
            return
        self._state[difficulty] = completed
        self._save()
        self._fire_update()

    def get_status(self) -> dict[str, bool]:
        """Returns completion status for all 4 difficulties."""
        return {d: self._state.get(d, False) for d in DIFFICULTIES}

    def get_ascendancy_points(self) -> dict:
        """
        Returns a summary of ascendancy points earned and available.
        earned    — total points from completed labs
        available — total possible points (always 8)
        """
        status   = self.get_status()
        earned   = sum(POINTS_PER_LAB[d] for d, done in status.items() if done)
        available = sum(POINTS_PER_LAB.values())
        return {"earned": earned, "available": available}

    def reset(self):
        """Clear all lab completion for a new character."""
        self._state = {d: False for d in DIFFICULTIES}
        self._save()
        self._fire_update()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> dict[str, bool]:
        if os.path.exists(_STATE_PATH):
            try:
                with open(_STATE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return {d: bool(data.get(d, False)) for d in DIFFICULTIES}
            except Exception as e:
                print(f"[LabTracker] failed to load state: {e}")
        return {d: False for d in DIFFICULTIES}

    def _save(self):
        os.makedirs(os.path.dirname(_STATE_PATH), exist_ok=True)
        try:
            with open(_STATE_PATH, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2)
        except Exception as e:
            print(f"[LabTracker] failed to save state: {e}")

    def _fire_update(self):
        for cb in self._on_update:
            try:
                cb()
            except Exception as e:
                print(f"[LabTracker] update callback error: {e}")
