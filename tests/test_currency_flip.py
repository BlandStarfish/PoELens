"""Tests for modules/currency_flip.py and api/poe_ninja.py flip data."""

import time
import pytest

from modules.currency_flip import CurrencyFlip, _EXCLUDE, _MIN_LISTINGS, _MIN_MARGIN_PCT


class _FakeNinja:
    """Stub PoeNinja that returns controlled flip data."""

    def __init__(self, flip_data: list[dict]):
        self._flip_data = flip_data

    def get_currency_flip_data(self) -> list[dict]:
        return list(self._flip_data)


def _entry(name, buy, sell, listing_count=10):
    return {"name": name, "buy": buy, "sell": sell, "listing_count": listing_count}


class TestCurrencyFlipCalculate:
    def test_profitable_flip_returned(self):
        ninja = _FakeNinja([_entry("Divine Orb", 190.0, 193.0)])
        flip  = CurrencyFlip(ninja)
        results = flip.calculate_flips()
        assert len(results) == 1
        r = results[0]
        assert r["name"] == "Divine Orb"
        assert r["buy"] == 190.0
        assert r["sell"] == 193.0
        assert r["margin_pct"] > 0

    def test_unprofitable_flip_excluded(self):
        ninja = _FakeNinja([_entry("Chaos Orb", 1.0, 0.9)])
        flip  = CurrencyFlip(ninja)
        assert flip.calculate_flips() == []

    def test_zero_margin_excluded(self):
        ninja = _FakeNinja([_entry("Divine Orb", 190.0, 190.0)])
        flip  = CurrencyFlip(ninja)
        assert flip.calculate_flips() == []

    def test_results_sorted_by_margin_descending(self):
        ninja = _FakeNinja([
            _entry("A", 100.0, 102.0),  # 2%
            _entry("B", 100.0, 110.0),  # 10%
            _entry("C", 100.0, 105.0),  # 5%
        ])
        flip    = CurrencyFlip(ninja)
        results = flip.calculate_flips()
        margins = [r["margin_pct"] for r in results]
        assert margins == sorted(margins, reverse=True)

    def test_margin_calculation(self):
        ninja = _FakeNinja([_entry("X", 100.0, 110.0)])
        flip  = CurrencyFlip(ninja)
        r = flip.calculate_flips()[0]
        assert r["margin_pct"] == 10.0

    def test_results_capped_at_20(self):
        entries = [_entry(f"Currency{i}", 100.0, 101.0 + i * 0.1) for i in range(30)]
        ninja   = _FakeNinja(entries)
        flip    = CurrencyFlip(ninja)
        assert len(flip.calculate_flips()) <= 20

    def test_empty_input_returns_empty(self):
        ninja = _FakeNinja([])
        flip  = CurrencyFlip(ninja)
        assert flip.calculate_flips() == []


class TestCurrencyFlipExclusions:
    def test_excluded_currencies_are_filtered(self):
        entries = [_entry(name, 1.0, 2.0) for name in _EXCLUDE]
        ninja   = _FakeNinja(entries)
        flip    = CurrencyFlip(ninja)
        results = flip.calculate_flips()
        names   = {r["name"] for r in results}
        assert names.isdisjoint(_EXCLUDE)

    def test_non_excluded_currency_passes(self):
        ninja   = _FakeNinja([_entry("Divine Orb", 190.0, 200.0)])
        flip    = CurrencyFlip(ninja)
        results = flip.calculate_flips()
        assert any(r["name"] == "Divine Orb" for r in results)


class TestCurrencyFlipListingFilter:
    def test_below_min_listings_excluded(self):
        ninja   = _FakeNinja([_entry("Divine Orb", 190.0, 200.0, listing_count=_MIN_LISTINGS - 1)])
        flip    = CurrencyFlip(ninja)
        assert flip.calculate_flips() == []

    def test_at_min_listings_included(self):
        ninja   = _FakeNinja([_entry("Divine Orb", 190.0, 200.0, listing_count=_MIN_LISTINGS)])
        flip    = CurrencyFlip(ninja)
        assert len(flip.calculate_flips()) == 1


class TestCurrencyFlipMarginFilter:
    def test_below_min_margin_excluded(self):
        # _MIN_MARGIN_PCT = 0.5, so 0.3% should be excluded
        buy = 100.0
        sell = buy * (1 + (_MIN_MARGIN_PCT - 0.2) / 100)
        ninja = _FakeNinja([_entry("SomeCurrency", buy, sell)])
        flip  = CurrencyFlip(ninja)
        assert flip.calculate_flips() == []

    def test_above_min_margin_included(self):
        buy  = 100.0
        sell = buy * (1 + (_MIN_MARGIN_PCT + 0.5) / 100)
        ninja = _FakeNinja([_entry("SomeCurrency", buy, sell)])
        flip  = CurrencyFlip(ninja)
        assert len(flip.calculate_flips()) == 1


class TestCurrencyFlipEdgeCases:
    def test_zero_buy_price_excluded(self):
        ninja   = _FakeNinja([_entry("ZeroCurrency", 0.0, 10.0)])
        flip    = CurrencyFlip(ninja)
        assert flip.calculate_flips() == []

    def test_listing_count_preserved_in_result(self):
        ninja   = _FakeNinja([_entry("Divine Orb", 190.0, 200.0, listing_count=42)])
        flip    = CurrencyFlip(ninja)
        results = flip.calculate_flips()
        assert results[0]["listing_count"] == 42

    def test_result_values_are_rounded(self):
        ninja   = _FakeNinja([_entry("X", 190.123456, 195.987654)])
        flip    = CurrencyFlip(ninja)
        r = flip.calculate_flips()[0]
        # buy/sell rounded to 2 decimal places, margin to 1
        assert r["buy"] == round(190.123456, 2)
        assert r["sell"] == round(195.987654, 2)
        assert r["margin_pct"] == round((195.987654 - 190.123456) / 190.123456 * 100, 1)


class TestPoeNinjaFlipData:
    """Tests for PoeNinja.get_currency_flip_data() and raw cache logic."""

    def test_returns_empty_when_category_not_fetched(self):
        from api.poe_ninja import PoeNinja
        ninja = PoeNinja(league="Standard")
        # Don't call get_price first — raw_cache is empty
        # _get_category will be called internally; with no network it returns []
        # (in test environment with no real network this is a smoke test)
        result = ninja.get_currency_flip_data()
        assert isinstance(result, list)

    def test_raw_cache_populated_by_fetch(self):
        from api.poe_ninja import PoeNinja
        import unittest.mock as mock

        fake_lines = [
            {
                "currencyTypeName": "Divine Orb",
                "chaosEquivalent": 190.0,
                "receive": {"value": 190.0, "listing_count": 15},
                "pay":     {"value": 192.0, "listing_count": 12},
            }
        ]
        ninja = PoeNinja(league="Standard")

        with mock.patch.object(ninja, "_fetch", return_value={"Divine Orb": 190.0}) as mf:
            # Patch _fetch to also populate raw_cache
            def fake_fetch(category):
                if category == "Currency":
                    ninja._raw_cache["Currency"] = (time.time(), fake_lines)
                return {"Divine Orb": 190.0}
            mf.side_effect = fake_fetch
            ninja._get_category("Currency")

        result = ninja.get_currency_flip_data()
        assert len(result) == 1
        assert result[0]["name"] == "Divine Orb"
        assert result[0]["buy"] == 190.0
        assert result[0]["sell"] == 192.0
        assert result[0]["listing_count"] == 15

    def test_entry_without_receive_excluded(self):
        from api.poe_ninja import PoeNinja

        ninja = PoeNinja(league="Standard")
        ninja._raw_cache["Currency"] = (time.time(), [
            {
                "currencyTypeName": "NoData",
                "chaosEquivalent": 10.0,
                # No receive / pay keys
            }
        ])
        # Prevent re-fetch
        ninja._cache["Currency"] = (time.time(), {"NoData": 10.0})
        result = ninja.get_currency_flip_data()
        assert result == []

    def test_set_league_clears_raw_cache(self):
        from api.poe_ninja import PoeNinja
        import time

        ninja = PoeNinja(league="Standard")
        ninja._raw_cache["Currency"] = (time.time(), [{"currencyTypeName": "X"}])
        ninja.set_league("Hardcore")
        assert ninja._raw_cache == {}
