"""
Currency per hour tracker.

Tracks currency delta over a session and reports currency/hr rates.
Currency counts can be entered manually via spinboxes, or auto-filled
from the official GGG stash tab API via OAuth (requires a registered client_id).
See core/oauth.py and core/stash_api.py for OAuth details.
"""

import time
from typing import Callable


TRACKED_CURRENCIES = [
    "Chaos Orb",
    "Divine Orb",
    "Exalted Orb",
    "Orb of Alteration",
    "Orb of Augmentation",
    "Orb of Transmutation",
    "Orb of Alchemy",
    "Orb of Fusing",
    "Jeweller's Orb",
    "Chromatic Orb",
    "Vaal Orb",
    "Blessed Orb",
    "Regal Orb",
    "Orb of Scouring",
    "Orb of Annulment",
    "Mirror of Kalandra",
    "Ancient Orb",
    "Harbinger's Orb",
    "Engineer's Orb",
]


class CurrencyTracker:
    def __init__(self, state, poe_ninja):
        self._state = state
        self._ninja = poe_ninja
        self._on_update: list[Callable] = []

    def on_update(self, callback: Callable):
        self._on_update.append(callback)

    def start_session(self, current_amounts: dict):
        """
        Begin a new tracking session.
        current_amounts: {currency_name: count}
        """
        self._state.start_currency_session(current_amounts)
        self._fire_update()

    def snapshot(self, current_amounts: dict):
        """
        Record a snapshot of current currency amounts.
        Calculates delta from session start and emits currency/hr.
        """
        self._state.log_currency_snapshot(current_amounts)
        self._fire_update()

    def get_last_amounts(self) -> dict:
        """Returns the last manually entered currency amounts (restored from disk on restart)."""
        return self._state.currency_last_amounts

    def get_display_data(self) -> dict:
        """
        Returns display-ready data including:
        - session_start: float | None  (Unix timestamp when session started)
        - rates: {currency: per_hr}
        - chaos_rates: {currency: chaos_per_hr}  (converted via poe.ninja)
        - total_chaos_per_hr: float
        - elapsed_minutes: float  (time since session start)
        """
        start = self._state.currency_session_start
        elapsed = (time.time() - start) / 60 if start else 0

        rates = self._state.get_currency_rate()
        if not rates:
            return {
                "session_start": start,
                "rates": {},
                "chaos_rates": {},
                "total_chaos_per_hr": 0,
                "elapsed_minutes": round(elapsed, 1),
            }

        chaos_rates = {}
        total_chaos = 0.0
        for currency, rate in rates.items():
            chaos_val = self._ninja.get_price(currency, "Currency") or 1.0
            chaos_per_hr = rate * chaos_val
            chaos_rates[currency] = round(chaos_per_hr, 2)
            total_chaos += chaos_per_hr

        return {
            "session_start": start,
            "rates": rates,
            "chaos_rates": chaos_rates,
            "total_chaos_per_hr": round(total_chaos, 2),
            "elapsed_minutes": round(elapsed, 1),
        }

    def get_historical_display_data(self, days: int | None = None) -> dict:
        """
        Returns average chaos/hr computed across all historical snapshots
        (or the last `days` days). Useful for 7-day and all-time summaries.
        Returns {"total_chaos_per_hr": 0, "chaos_rates": {}} if no data.
        """
        rates = self._state.get_historical_rate(days=days)
        if not rates:
            return {"total_chaos_per_hr": 0.0, "chaos_rates": {}}
        chaos_rates = {}
        total_chaos = 0.0
        for currency, rate in rates.items():
            chaos_val = self._ninja.get_price(currency, "Currency") or 1.0
            chaos_per_hr = rate * chaos_val
            chaos_rates[currency] = round(chaos_per_hr, 2)
            total_chaos += chaos_per_hr
        return {
            "total_chaos_per_hr": round(total_chaos, 2),
            "chaos_rates": chaos_rates,
        }

    def _fire_update(self):
        data = self.get_display_data()
        for cb in self._on_update:
            try:
                cb(data)
            except Exception as e:
                print(f"[CurrencyTracker] callback error: {e}")
