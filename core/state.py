"""
Persistent application state — quest completion, currency log, crafting queue.
Saved to state/profile.json and state/currency_log.json.
"""

import json
import os
import time

# Cumulative XP required to reach each level (1–100) in Path of Exile 1.
# Source: PathOfBuilding community repo / poewiki.net/wiki/Experience
_XP_TABLE: dict[int, int] = {
    1: 0, 2: 525, 3: 1760, 4: 3781, 5: 7184,
    6: 12186, 7: 19324, 8: 29377, 9: 43181, 10: 61693,
    11: 85990, 12: 117506, 13: 157384, 14: 207736, 15: 269997,
    16: 346462, 17: 439268, 18: 551295, 19: 685171, 20: 843709,
    21: 1030734, 22: 1249629, 23: 1504995, 24: 1800847, 25: 2142652,
    26: 2535122, 27: 2984677, 28: 3496798, 29: 4080655, 30: 4742836,
    31: 5490247, 32: 6334393, 33: 7283446, 34: 8384398, 35: 9541110,
    36: 10874351, 37: 12361842, 38: 14018289, 39: 15859432, 40: 17905634,
    41: 20171471, 42: 22679999, 43: 25456123, 44: 28517857, 45: 31897771,
    46: 35621447, 47: 39721017, 48: 44225461, 49: 49176560, 50: 54607467,
    51: 60565335, 52: 67094245, 53: 74247659, 54: 82075627, 55: 90631041,
    56: 99984974, 57: 110197515, 58: 121340161, 59: 133497202, 60: 146749362,
    61: 161191120, 62: 176922628, 63: 194049893, 64: 212684946, 65: 232956711,
    66: 255001620, 67: 278952403, 68: 304972236, 69: 333233648, 70: 363906163,
    71: 397194041, 72: 433312945, 73: 472476370, 74: 514937180, 75: 560961898,
    76: 610815862, 77: 664824416, 78: 723298169, 79: 786612664, 80: 855129128,
    81: 929261318, 82: 1009443795, 83: 1096169525, 84: 1189918242, 85: 1291270350,
    86: 1400795257, 87: 1519130326, 88: 1646943474, 89: 1784977296, 90: 1934009687,
    91: 2094900291, 92: 2268549086, 93: 2455921256, 94: 2658074992, 95: 2876116901,
    96: 3111280300, 97: 3364828162, 98: 3638186694, 99: 3932818530, 100: 4250334444,
}

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
    "currency_last_amounts": {}, # last manually entered currency counts (restored on restart)
    # XP rate tracker
    "xp_session_start": None,    # timestamp when XP session started
    "xp_session_char": "",       # character name being tracked
    "xp_baseline": 0,            # total XP at session start
    "xp_baseline_level": 0,      # level at session start
    "xp_last": 0,                # most recently polled XP value
    "xp_last_level": 0,          # most recently polled level
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
        # Persist last known amounts so they can be restored after a restart
        self._profile["currency_last_amounts"] = dict(current)
        self._save_currency()
        self._save_profile()
        self._notify("currency_delta", delta)

    @property
    def currency_last_amounts(self) -> dict:
        """Last manually entered currency amounts (from most recent snapshot)."""
        return dict(self._profile.get("currency_last_amounts", {}))

    def get_historical_rate(self, days: int | None = None) -> dict:
        """
        Compute average currency/hr across historical snapshots.
        days=7  — last 7 days only.
        days=None — all-time average.
        Returns {} if no qualifying data.
        """
        sessions = self._currency_log.get("sessions", [])
        if not sessions:
            return {}
        cutoff = (time.time() - days * 86400) if days is not None else 0
        filtered = [s for s in sessions if s.get("timestamp", 0) >= cutoff]
        if not filtered:
            return {}
        total_hours = sum(s.get("elapsed_hours", 0) for s in filtered)
        if total_hours < 0.001:
            return {}
        combined: dict[str, float] = {}
        for s in filtered:
            for currency, delta in s.get("delta", {}).items():
                combined[currency] = combined.get(currency, 0) + delta
        return {k: round(v / total_hours, 2) for k, v in combined.items()}

    def get_session_stats(self, days: int | None = None) -> dict:
        """
        Returns total snapshot count and total tracked hours from the currency log.
        days=None means all-time. days=7 means the last 7 days.
        """
        sessions = self._currency_log.get("sessions", [])
        cutoff = (time.time() - days * 86400) if days is not None else 0
        filtered = [s for s in sessions if s.get("timestamp", 0) >= cutoff]
        total_hours = sum(s.get("elapsed_hours", 0) for s in filtered)
        return {
            "snapshot_count": len(filtered),
            "total_hours": round(total_hours, 1),
        }

    def get_currency_rate(self) -> dict:
        """
        Returns currency/hr rates based on the most recent snapshot.
        Uses the snapshot's own elapsed time so the rate stays accurate
        rather than diluting as time passes between snapshots.
        Only returns rates from the current session — snapshots from
        previous sessions are ignored so starting a new session clears
        the displayed rates.
        """
        sessions = self._currency_log.get("sessions", [])
        if not sessions:
            return {}
        last = sessions[-1]
        # Guard: if the last snapshot predates the current session start,
        # it belongs to a previous session — return empty to signal "no data yet".
        session_start = self._profile.get("currency_session_start")
        if session_start and last.get("timestamp", 0) < session_start:
            return {}
        elapsed = last.get("elapsed_hours", 0)
        if elapsed < 0.001:
            return {}
        return {k: round(v / elapsed, 2) for k, v in last["delta"].items()}

    # ------------------------------------------------------------------
    # XP rate tracking
    # ------------------------------------------------------------------

    def start_xp_session(self, char_name: str, xp: int, level: int):
        """Begin a new XP tracking session for the named character."""
        self._profile["xp_session_start"]  = time.time()
        self._profile["xp_session_char"]   = char_name
        self._profile["xp_baseline"]       = xp
        self._profile["xp_baseline_level"] = level
        self._profile["xp_last"]           = xp
        self._profile["xp_last_level"]     = level
        self._save_profile()
        self._notify("xp_session", {"char": char_name, "level": level})

    def update_xp(self, xp: int, level: int):
        """Record the latest polled XP and level values."""
        self._profile["xp_last"]       = xp
        self._profile["xp_last_level"] = level
        self._save_profile()
        self._notify("xp_update", {"xp": xp, "level": level})

    @property
    def xp_session_start(self) -> float | None:
        return self._profile.get("xp_session_start")

    @property
    def xp_session_char(self) -> str:
        return self._profile.get("xp_session_char", "")

    def reset_character(self):
        """
        Reset character-specific state for a new character.
        Clears: completed quests, passive points, XP session.
        Preserves: currency history, crafting queue, zone, notes.
        """
        self._profile["completed_quests"]    = []
        self._profile["passive_points_used"] = 0
        self._profile["ascendancy_points_used"] = 0
        self._profile["xp_session_start"]   = None
        self._profile["xp_session_char"]    = ""
        self._profile["xp_baseline"]        = 0
        self._profile["xp_baseline_level"]  = 0
        self._profile["xp_last"]            = 0
        self._profile["xp_last_level"]      = 0
        self._save_profile()
        self._notify("completed_quests", [])
        self._notify("xp_session", None)

    def get_xp_display_data(self) -> dict:
        """
        Returns display-ready XP data for the current session.
        Returns {"started": False} if no session is active.
        """
        start = self._profile.get("xp_session_start")
        if not start:
            return {"started": False}

        baseline      = self._profile.get("xp_baseline", 0)
        last_xp       = self._profile.get("xp_last", 0)
        last_level    = self._profile.get("xp_last_level", 0)
        baseline_level = self._profile.get("xp_baseline_level", 0)
        elapsed_hours = (time.time() - start) / 3600
        xp_delta      = last_xp - baseline
        xp_per_hr     = round(xp_delta / elapsed_hours) if elapsed_hours > 0.001 else 0

        # Time-to-level estimation using confirmed XP table
        time_to_level: float | None = None
        if xp_per_hr > 0 and 1 <= last_level < 100:
            xp_for_next = _XP_TABLE.get(last_level + 1)
            if xp_for_next is not None:
                xp_remaining = xp_for_next - last_xp
                if xp_remaining > 0:
                    time_to_level = round(xp_remaining / xp_per_hr * 60, 1)  # minutes

        return {
            "started":         True,
            "char_name":       self._profile.get("xp_session_char", ""),
            "level":           last_level,
            "baseline_level":  baseline_level,
            "xp_this_session": xp_delta,
            "xp_per_hr":       xp_per_hr,
            "elapsed_minutes": round(elapsed_hours * 60, 1),
            "time_to_level":   time_to_level,   # minutes remaining to next level, or None
        }
