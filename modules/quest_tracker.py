"""
Passive skill point quest tracker.

Tracks only quests that award (or deduct) passive skill points.
Syncs completion state via Client.txt log events.
"""

import json
import os
from typing import Callable

_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "passive_quests.json")


class QuestTracker:
    def __init__(self, state):
        """
        state: AppState instance
        """
        self._state = state
        self._quests = self._load_quests()
        # Map log_string -> quest for fast lookup
        self._log_map = {q["log_string"].lower(): q for q in self._quests}
        self._on_update: list[Callable] = []

    def on_update(self, callback: Callable):
        self._on_update.append(callback)

    def _load_quests(self) -> list:
        with open(_DATA_PATH, "r") as f:
            return json.load(f)["quests"]

    def handle_quest_event(self, data: dict):
        """Called by client_log watcher on quest_complete event."""
        name = data.get("name", "").lower()
        quest = self._log_map.get(name)
        if quest:
            self._state.complete_quest(quest["id"])
            self._fire_update()

    def get_status(self) -> list[dict]:
        """
        Returns list of all passive-point quests with completion status.
        Each entry: quest dict + "completed": bool
        """
        completed = set(self._state.completed_quests)
        result = []
        for q in self._quests:
            result.append({**q, "completed": q["id"] in completed})
        return result

    def get_next_quest(self) -> dict | None:
        """Returns the next incomplete quest in act order."""
        for q in self.get_status():
            if not q["completed"] and q.get("passive_points", 0) > 0:
                return q
        return None

    def get_point_totals(self) -> dict:
        """Returns total points available, earned, deducted, and net."""
        completed = set(self._state.completed_quests)
        earned = 0
        deducted = 0
        available = 0
        for q in self._quests:
            pts = q.get("passive_points", 0)
            if pts > 0:
                available += pts
                if q["id"] in completed:
                    earned += pts
            elif pts < 0:
                if q["id"] in completed:
                    deducted += abs(pts)
        return {
            "earned": earned,
            "deducted": deducted,
            "net": earned - deducted,
            "total_available": available,
            "remaining": available - earned,
        }

    def manually_complete(self, quest_id: str):
        """Allow user to manually mark a quest complete in the UI."""
        self._state.complete_quest(quest_id)
        self._fire_update()

    def manually_uncomplete(self, quest_id: str):
        """Allow user to manually unmark — useful for new characters."""
        completed = list(self._state.completed_quests)
        if quest_id in completed:
            completed.remove(quest_id)
            self._state._profile["completed_quests"] = completed
            self._state._save_profile()
            self._fire_update()

    def _fire_update(self):
        for cb in self._on_update:
            try:
                cb(self.get_status())
            except Exception as e:
                print(f"[QuestTracker] update callback error: {e}")
