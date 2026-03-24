"""
Persistent application state — quest completion, currency log, crafting queue.
Saved to state/profile.json and state/currency_log.json.
"""

import json
import os
import time

_PROFILE_PATH = os.path.join(os.path.dirname(__file__), "..", "state", "profile.json")
_CURRENCY_LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "state", "currency_log.json")

_PROFILE_DEFAULTS = {
    "completed_quests": [],      # list of quest IDs that award passive points
    "passive_points_used": 0,
    "ascendancy_points_used": 0,
    "current_zone": "",
    "crafting_queue": [],        # list of crafting task dicts
    "currency_session_start": None,
    "currency_baseline": {},     # {"Chaos Orb": N, ...}
}


class AppState:
    def __init__(self):
        os.makedirs(os.path.join(os.path.dirname(__file__), "..", "state"), exist_ok=True)
        self._profile = self._load(_PROFILE_PATH, _PROFILE_DEFAULTS)
        self._currency_log = self._load(_CURRENCY_LOG_PATH, {"sessions": []})
        self._listeners: dict[str, list] = {}

    # ------------------------------------------------------------------
    # Generic persistence
    # ------------------------------------------------------------------

    def _load(self, path: str, defaults: dict) -> dict:
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
            return {**defaults, **data}
        return dict(defaults)

    def _save_profile(self):
        with open(_PROFILE_PATH, "w") as f:
            json.dump(self._profile, f, indent=2)

    def _save_currency(self):
        with open(_CURRENCY_LOG_PATH, "w") as f:
            json.dump(self._currency_log, f, indent=2)

    # ------------------------------------------------------------------
    # Change notifications
    # ------------------------------------------------------------------

    def on_change(self, key: str, callback):
        self._listeners.setdefault(key, []).append(callback)

    def _notify(self, key: str, value):
        for cb in self._listeners.get(key, []):
            try:
                cb(value)
            except Exception as e:
                print(f"[State] listener error ({key}): {e}")

    # ------------------------------------------------------------------
    # Quest tracking
    # ------------------------------------------------------------------

    def complete_quest(self, quest_id: str):
        if quest_id not in self._profile["completed_quests"]:
            self._profile["completed_quests"].append(quest_id)
            self._save_profile()
            self._notify("completed_quests", self._profile["completed_quests"])

    def uncomplete_quest(self, quest_id: str):
        completed = self._profile["completed_quests"]
        if quest_id in completed:
            completed.remove(quest_id)
            self._save_profile()
            self._notify("completed_quests", self._profile["completed_quests"])

    @property
    def completed_quests(self) -> list:
        return list(self._profile["completed_quests"])

    # ------------------------------------------------------------------
    # Zone tracking
    # ------------------------------------------------------------------

    def set_zone(self, zone: str):
        self._profile["current_zone"] = zone
        self._save_profile()
        self._notify("current_zone", zone)

    @property
    def current_zone(self) -> str:
        return self._profile["current_zone"]

    # ------------------------------------------------------------------
    # Crafting queue
    # ------------------------------------------------------------------

    def get_crafting_queue(self) -> list:
        return list(self._profile["crafting_queue"])

    def set_crafting_queue(self, queue: list):
        self._profile["crafting_queue"] = queue
        self._save_profile()
        self._notify("crafting_queue", queue)

    def add_crafting_task(self, task: dict):
        self._profile["crafting_queue"].append(task)
        self._save_profile()
        self._notify("crafting_queue", self._profile["crafting_queue"])

    def remove_crafting_task(self, index: int):
        if 0 <= index < len(self._profile["crafting_queue"]):
            self._profile["crafting_queue"].pop(index)
            self._save_profile()
            self._notify("crafting_queue", self._profile["crafting_queue"])

    # ------------------------------------------------------------------
    # Currency tracking
    # ------------------------------------------------------------------

    @property
    def currency_session_start(self) -> float | None:
        return self._profile.get("currency_session_start")

    def start_currency_session(self, baseline: dict):
        self._profile["currency_session_start"] = time.time()
        self._profile["currency_baseline"] = baseline
        self._save_profile()

    def log_currency_snapshot(self, current: dict):
        start = self._profile.get("currency_session_start")
        if not start:
            return
        elapsed_hours = (time.time() - start) / 3600
        if elapsed_hours < 0.001:
            return
        delta = {
            k: current.get(k, 0) - self._profile["currency_baseline"].get(k, 0)
            for k in set(current) | set(self._profile["currency_baseline"])
        }
        self._currency_log["sessions"].append({
            "timestamp": time.time(),
            "elapsed_hours": elapsed_hours,
            "delta": delta,
        })
        self._save_currency()
        self._notify("currency_delta", delta)

    def get_currency_rate(self) -> dict:
        """Returns approximate currency/hr based on current session."""
        start = self._profile.get("currency_session_start")
        if not start:
            return {}
        elapsed = (time.time() - start) / 3600
        if elapsed < 0.001:
            return {}
        sessions = self._currency_log.get("sessions", [])
        if not sessions:
            return {}
        last = sessions[-1]
        return {k: round(v / elapsed, 2) for k, v in last["delta"].items()}
