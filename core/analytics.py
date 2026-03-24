"""
ExileHUD anonymous usage analytics.

Sends a single non-blocking HTTP POST to ANALYTICS_WEBHOOK_URL when the app
launches or the installer completes. No personally identifiable information is
collected. See README.md for the full disclosure of what is sent.

To disable: set ANALYTICS_WEBHOOK_URL = "" in this file before building.
"""

import hashlib
import json
import platform
import socket
import threading
import urllib.request
from datetime import datetime, timezone

# ── Configure before building ────────────────────────────────────────────────
# Create a Discord webhook: Server Settings > Integrations > Webhooks > New Webhook
# Paste the webhook URL here. Leave empty to disable analytics entirely.
ANALYTICS_WEBHOOK_URL = ""
# ─────────────────────────────────────────────────────────────────────────────

_APP_NAME = "ExileHUD"


def _anon_id() -> str:
    """SHA-256 of the machine hostname. Consistent per machine, not reversible."""
    try:
        raw = socket.gethostname().encode("utf-8")
    except Exception:
        raw = b"unknown"
    return hashlib.sha256(raw).hexdigest()[:16]


def _os_info() -> str:
    try:
        return f"{platform.system()} {platform.release()} ({platform.version()[:40]})"
    except Exception:
        return "unknown"


def _send(event: str, extra: dict | None = None):
    """Fire-and-forget analytics POST. Silently swallows all errors."""
    if not ANALYTICS_WEBHOOK_URL:
        return

    payload = {
        "event":     event,
        "app":       _APP_NAME,
        "anon_id":   _anon_id(),
        "os":        _os_info(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        payload.update(extra)

    # Format as a Discord embed
    discord_body = {
        "embeds": [{
            "title": f"{_APP_NAME} — {event}",
            "color": 0xe2b96f,
            "fields": [
                {"name": k, "value": str(v), "inline": True}
                for k, v in payload.items()
            ],
        }]
    }

    body = json.dumps(discord_body).encode("utf-8")
    req = urllib.request.Request(
        ANALYTICS_WEBHOOK_URL,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": f"{_APP_NAME}/analytics"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5):
            pass
    except Exception:
        pass  # analytics are best-effort, never crash the app


def track(event: str, extra: dict | None = None):
    """Send an analytics event in a background thread (non-blocking)."""
    threading.Thread(target=_send, args=(event, extra), daemon=True).start()
