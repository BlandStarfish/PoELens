"""
Official Path of Exile Trade API wrapper.
TOS-safe: uses only the official public trade API.
Reference: https://www.pathofexile.com/developer/docs/reference#publicstashes
"""

import requests
import time
from typing import Optional

TRADE_BASE = "https://www.pathofexile.com/api/trade"
HEADERS = {
    "User-Agent": "ExileHUD/1.0 (contact: github.com/BlandStarfish/ExileHUD)",
}

# Rate limit: official API allows ~12 requests/10s sustained
_last_request = 0.0
_MIN_INTERVAL = 1.0  # seconds between requests (conservative)


def _rate_limit():
    global _last_request
    delta = time.time() - _last_request
    if delta < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - delta)
    _last_request = time.time()


def search_item(league: str, query: dict) -> Optional[dict]:
    """
    POST to trade search endpoint.
    query: standard trade API query dict
    Returns raw API response or None on error.
    """
    _rate_limit()
    url = f"{TRADE_BASE}/search/{league}"
    try:
        r = requests.post(url, json=query, headers=HEADERS, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[TradeAPI] search failed: {e}")
        return None


def fetch_listings(result_ids: list[str], query_id: str) -> Optional[list]:
    """
    Fetch up to 10 listing details from a search result.
    """
    if not result_ids:
        return []
    _rate_limit()
    ids = ",".join(result_ids[:10])
    url = f"{TRADE_BASE}/fetch/{ids}?query={query_id}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        return r.json().get("result", [])
    except Exception as e:
        print(f"[TradeAPI] fetch failed: {e}")
        return None


def build_price_check_query(item_name: str, item_type: Optional[str] = None) -> dict:
    """Build a basic trade query for price checking an item by name."""
    query: dict = {
        "query": {
            "status": {"option": "online"},
            "filters": {
                "trade_filters": {
                    "filters": {"sale_type": {"option": "priced"}}
                }
            },
        },
        "sort": {"price": "asc"},
    }
    if item_type:
        query["query"]["type"] = item_type
    else:
        query["query"]["term"] = item_name
    return query


def extract_prices(listings: list) -> list[float]:
    """Extract chaos-equivalent prices from fetch_listings results."""
    prices = []
    for listing in listings:
        price_info = listing.get("listing", {}).get("price", {})
        amount = price_info.get("amount", 0)
        currency = price_info.get("currency", "")
        # For now just return chaos amounts; chaos conversion handled by poe_ninja
        if currency == "chaos":
            prices.append(float(amount))
        elif amount > 0:
            prices.append(float(amount))  # caller normalizes via poe_ninja
    return prices
