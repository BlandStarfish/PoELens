"""
Currency Flip Calculator.

Calculates profitable currency exchange opportunities using poe.ninja price data
already in memory. No additional API calls — reuses the currencyoverview fetch.

A "flip" is: buy currency X for chaos, then immediately resell X for more chaos.
The margin is (sell_price - buy_price) / buy_price * 100.
"""

from api.poe_ninja import PoeNinja

# Trivial low-value currencies that produce noise without useful flip opportunities.
# These often have huge spread percentages due to low absolute chaos values.
_EXCLUDE = frozenset({
    "Orb of Transmutation",
    "Orb of Augmentation",
    "Orb of Binding",
    "Scroll of Wisdom",
    "Portal Scroll",
    "Armourer's Scrap",
    "Blacksmith's Whetstone",
    "Chromatic Orb",
    "Jeweller's Orb",
    "Engineer's Orb",
    "Glassblower's Bauble",
    "Imprint",
    "Silver Coin",
})

# Only show flips where at least this many listings exist (filters noise)
_MIN_LISTINGS = 3

# Only surface flips above this margin threshold (%)
_MIN_MARGIN_PCT = 0.5


class CurrencyFlip:
    """
    Calculates currency flip opportunities from live poe.ninja data.

    Usage:
        flip = CurrencyFlip(ninja)
        results = flip.calculate_flips()  # sorted by margin, best first
    """

    def __init__(self, ninja: PoeNinja):
        self._ninja = ninja

    def calculate_flips(self) -> list[dict]:
        """
        Returns a list of flip opportunities sorted by margin (best first).

        Each entry:
          name          — currency name
          buy           — chaos cost to purchase 1 unit (receive.value)
          sell          — chaos received when selling 1 unit (pay.value)
          margin_pct    — (sell - buy) / buy * 100, positive = profitable
          listing_count — number of active sell listings for the currency
        """
        raw = self._ninja.get_currency_flip_data()
        flips = []
        for entry in raw:
            name = entry["name"]
            if name in _EXCLUDE:
                continue
            buy  = entry["buy"]
            sell = entry["sell"]
            if buy <= 0:
                continue
            margin_pct = (sell - buy) / buy * 100
            if margin_pct < _MIN_MARGIN_PCT:
                continue
            if entry["listing_count"] < _MIN_LISTINGS:
                continue
            flips.append({
                "name":          name,
                "buy":           round(buy, 2),
                "sell":          round(sell, 2),
                "margin_pct":    round(margin_pct, 1),
                "listing_count": entry["listing_count"],
            })
        return sorted(flips, key=lambda x: x["margin_pct"], reverse=True)[:20]
