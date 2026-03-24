"""
Client.txt watcher — reads the PoE log file and emits parsed events.

All overlay modules subscribe to this event bus instead of reading the log
directly. TOS-safe: read-only file access, no process interaction.

Events emitted:
  zone_change      {"zone": str}
  chat_message     {"channel": str, "player": str, "message": str}
  whisper_in       {"player": str, "message": str}
  whisper_out      {"player": str, "message": str}
  quest_complete   {"name": str}  (parsed from log text)
  level_up         {"level": int, "class": str}
  item_found       {"item": str}   (rarity drops from log)
"""

import re
import threading
import time
from typing import Callable

# ---------------------------------------------------------------------------
# Log line patterns
# ---------------------------------------------------------------------------

_ZONE_RE = re.compile(r"Generating level \d+ area \"([^\"]+)\"")
_CHAT_RE = re.compile(r"\] (\$|#|&|%)([^:]+): (.+)")
_WHISPER_IN_RE = re.compile(r"\] @From ([^:]+): (.+)")
_WHISPER_OUT_RE = re.compile(r"\] @To ([^:]+): (.+)")
_LEVEL_RE = re.compile(r": (.+) \(([^)]+)\) is now level (\d+)")
# Quest completion lines in Client.txt contain the quest name after a prefix
_QUEST_RE = re.compile(r"Quest \"([^\"]+)\" state is now Completed")


class ClientLogWatcher:
    def __init__(self, log_path: str):
        self._path = log_path
        self._handlers: dict[str, list[Callable]] = {}
        self._running = False
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def on(self, event: str, handler: Callable):
        """Subscribe to an event type."""
        self._handlers.setdefault(event, []).append(handler)

    def start(self):
        """Begin tailing the log file in a background thread."""
        self._running = True
        self._thread = threading.Thread(target=self._tail, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _emit(self, event: str, data: dict):
        for handler in self._handlers.get(event, []):
            try:
                handler(data)
            except Exception as exc:
                print(f"[ClientLog] handler error ({event}): {exc}")

    def _tail(self):
        """Seek to end of file on startup, then follow new lines."""
        try:
            f = open(self._path, "r", encoding="utf-8", errors="replace")
        except FileNotFoundError:
            print(f"[ClientLog] log not found: {self._path}")
            return

        try:
            f.seek(0, 2)  # seek to end — only process new lines
            while self._running:
                line = f.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                self._parse(line.rstrip())
        finally:
            f.close()

    def _parse(self, line: str):
        if m := _ZONE_RE.search(line):
            self._emit("zone_change", {"zone": m.group(1)})
            return

        if m := _WHISPER_IN_RE.search(line):
            self._emit("whisper_in", {"player": m.group(1), "message": m.group(2)})
            return

        if m := _WHISPER_OUT_RE.search(line):
            self._emit("whisper_out", {"player": m.group(1), "message": m.group(2)})
            return

        if m := _CHAT_RE.search(line):
            channel_map = {"$": "trade", "#": "global", "&": "party", "%": "guild"}
            self._emit("chat_message", {
                "channel": channel_map.get(m.group(1), "unknown"),
                "player": m.group(2),
                "message": m.group(3),
            })
            return

        if m := _LEVEL_RE.search(line):
            self._emit("level_up", {
                "player": m.group(1),
                "class": m.group(2),
                "level": int(m.group(3)),
            })
            return

        if m := _QUEST_RE.search(line):
            self._emit("quest_complete", {"name": m.group(1)})
