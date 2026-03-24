"""
Map overlay panel — shows current zone info and zone history.

Displays:
  - Current zone name (prominent)
  - Act, area level, waypoint, boss info (from static zone database)
  - Session zone history (last 15 zones, most recent first)
"""

import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QFrame,
)
from PyQt6.QtCore import Qt, QMetaObject, pyqtSlot
from PyQt6.QtGui import QColor

ACCENT  = "#e2b96f"
TEXT    = "#d4c5a9"
DIM     = "#8a7a65"
GREEN   = "#5cba6e"
TEAL    = "#4ae8c8"


def _act_resist_note(act) -> str:
    """
    Return a resistance penalty reminder based on act number.
    Acts 6-9 follow Act 5 Kitava (-30%). Act 10+ follows both Kitavas (-60%).
    Only shown when the zone has no zone-specific notes of its own.
    """
    try:
        act = int(act)
    except (TypeError, ValueError):
        return ""
    if 6 <= act <= 9:
        return "-30% all res penalty active (from Act 5 Kitava)"
    if act >= 10:
        return "-60% all res penalty active (from both Kitavas)"
    return ""


class MapPanel(QWidget):
    def __init__(self, map_overlay):
        super().__init__()
        self._overlay = map_overlay
        self._build_ui()
        map_overlay.on_update(self._on_zone_change)
        # Populate with current zone if one already exists
        current = map_overlay.get_current_zone()
        if current:
            self._show_current(current)
        self._refresh_history()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # ── Current zone card ──
        card = QWidget()
        card.setStyleSheet("background: #0f0f23; border-radius: 6px; border: 1px solid #2a2a4a;")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 8, 10, 8)
        card_layout.setSpacing(4)

        self._zone_name = QLabel("No zone detected yet")
        self._zone_name.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 14px; background: transparent; border: none;")
        self._zone_name.setWordWrap(True)
        card_layout.addWidget(self._zone_name)

        self._zone_meta = QLabel("")
        self._zone_meta.setStyleSheet(f"color: {TEXT}; font-size: 11px; background: transparent; border: none;")
        card_layout.addWidget(self._zone_meta)

        self._boss_label = QLabel("")
        self._boss_label.setStyleSheet(f"color: #e84a4a; font-size: 11px; background: transparent; border: none;")
        self._boss_label.setWordWrap(True)
        card_layout.addWidget(self._boss_label)

        self._notes_label = QLabel("")
        self._notes_label.setStyleSheet(f"color: #c8a84b; font-size: 11px; background: transparent; border: none;")
        self._notes_label.setWordWrap(True)
        self._notes_label.hide()
        card_layout.addWidget(self._notes_label)

        layout.addWidget(card)

        # ── Hint label (shown when no zone data) ──
        self._hint = QLabel(
            "Zone info will appear when you enter an area in PoE.\n"
            "Make sure ExileHUD is pointed at your Client.txt in settings."
        )
        self._hint.setWordWrap(True)
        self._hint.setStyleSheet(f"color: {DIM}; font-size: 11px;")
        layout.addWidget(self._hint)

        # ── History header ──
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2a2a4a;")
        layout.addWidget(sep)

        hist_lbl = QLabel("Zone History (this session)")
        hist_lbl.setStyleSheet(f"color: {DIM}; font-size: 11px; font-weight: bold;")
        layout.addWidget(hist_lbl)

        # ── History list ──
        self._history_list = QListWidget()
        self._history_list.setStyleSheet(
            "QListWidget { background: #0f0f23; border: 1px solid #2a2a4a;"
            " color: #d4c5a9; font-size: 11px; }"
            "QListWidget::item { padding: 3px 6px; }"
            "QListWidget::item:selected { background: #1a2a3a; }"
        )
        layout.addWidget(self._history_list, 1)

    def _on_zone_change(self, zone_entry: dict):
        """Called from background thread via ClientLogWatcher. Marshal to main thread."""
        QMetaObject.invokeMethod(
            self, "_update_ui",
            Qt.ConnectionType.QueuedConnection,
        )

    @pyqtSlot()
    def _update_ui(self):
        current = self._overlay.get_current_zone()
        if current:
            self._show_current(current)
        self._refresh_history()

    def _show_current(self, entry: dict):
        self._hint.hide()
        name = entry["name"]
        info = entry["info"]

        self._zone_name.setText(name)

        if info:
            act = info.get("act", "?")
            lvl = info.get("area_level", "?")
            wp  = "✓ Waypoint" if info.get("waypoint") else "No waypoint"
            zone_type = info.get("type", "")
            type_str = "  •  Town" if zone_type == "town" else ""
            self._zone_meta.setText(f"Act {act}  •  Area level {lvl}  •  {wp}{type_str}")

            boss = info.get("boss")
            if boss:
                self._boss_label.setText(f"Boss: {boss}")
                self._boss_label.show()
            else:
                self._boss_label.hide()

            notes = info.get("notes") or _act_resist_note(act)
            if notes:
                self._notes_label.setText(f"\u26a0 {notes}")
                self._notes_label.show()
            else:
                self._notes_label.hide()
        else:
            self._zone_meta.setText("(zone not in database)")
            self._boss_label.hide()
            self._notes_label.hide()

    def _refresh_history(self):
        self._history_list.clear()
        for entry in self._overlay.get_history():
            name = entry["name"]
            info = entry.get("info")
            ts = entry.get("timestamp", 0)
            time_str = datetime.datetime.fromtimestamp(ts).strftime("%H:%M") if ts else ""

            if info:
                act = info.get("act", "?")
                lvl = info.get("area_level", "?")
                text = f"{time_str}  {name}  (Act {act}, lvl {lvl})"
            else:
                text = f"{time_str}  {name}"

            item = QListWidgetItem(text)
            if info and info.get("type") == "town":
                item.setForeground(QColor(DIM))
            self._history_list.addItem(item)
