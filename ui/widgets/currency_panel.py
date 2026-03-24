"""
Currency per hour panel.
User clicks "Start Session" and manually enters current currency counts.
Subsequent snapshots are taken via the Snapshot button.
"""

import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSpinBox, QScrollArea, QFrame,
    QFormLayout, QGroupBox,
)
from PyQt6.QtCore import Qt
from modules.currency_tracker import TRACKED_CURRENCIES

ACCENT = "#e2b96f"
TEXT   = "#d4c5a9"
DIM    = "#8a7a65"
GREEN  = "#5cba6e"


class CurrencyPanel(QWidget):
    def __init__(self, tracker):
        super().__init__()
        self._tracker = tracker
        self._spinboxes: dict[str, QSpinBox] = {}
        self._build_ui()
        tracker.on_update(self._on_update)
        # Restore last known amounts from disk (populated by most recent snapshot)
        last = tracker.get_last_amounts()
        for currency, amount in last.items():
            if currency in self._spinboxes:
                self._spinboxes[currency].setValue(amount)
        # Show current session state if one is already active
        self._on_update(tracker.get_display_data())

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Session start time (shown when a session is active)
        self._session_label = QLabel("")
        self._session_label.setStyleSheet(f"color: {DIM}; font-size: 11px;")
        layout.addWidget(self._session_label)

        # Rate display
        self._rate_label = QLabel("Start a session and take snapshots to track rates.")
        self._rate_label.setStyleSheet(f"color: {ACCENT}; font-weight: bold;")
        self._rate_label.setWordWrap(True)
        layout.addWidget(self._rate_label)

        self._elapsed_label = QLabel("")
        self._elapsed_label.setStyleSheet(f"color: {DIM}; font-size: 11px;")
        layout.addWidget(self._elapsed_label)

        # Historical averages (7-day and all-time)
        self._hist_label = QLabel("")
        self._hist_label.setStyleSheet(f"color: {DIM}; font-size: 11px;")
        self._hist_label.setWordWrap(True)
        layout.addWidget(self._hist_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2a2a4a;")
        layout.addWidget(sep)

        # Currency input grid
        group = QGroupBox("Current counts")
        group.setStyleSheet(f"QGroupBox {{ color: {DIM}; font-size: 11px; }}")
        form = QFormLayout(group)
        form.setSpacing(3)

        for currency in TRACKED_CURRENCIES:
            sb = QSpinBox()
            sb.setRange(0, 999999)
            sb.setStyleSheet("background: #0f0f23; color: #d4c5a9; border: 1px solid #2a2a4a; border-radius: 3px; padding: 2px;")
            self._spinboxes[currency] = sb
            lbl = QLabel(currency)
            lbl.setStyleSheet(f"color: {TEXT}; font-size: 11px;")
            form.addRow(lbl, sb)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(group)
        layout.addWidget(scroll)

        # Buttons
        btn_row = QHBoxLayout()
        start_btn = QPushButton("Start Session")
        start_btn.clicked.connect(self._start_session)
        snap_btn = QPushButton("Snapshot")
        snap_btn.clicked.connect(self._take_snapshot)
        btn_row.addWidget(start_btn)
        btn_row.addWidget(snap_btn)
        layout.addLayout(btn_row)

    def _get_amounts(self) -> dict:
        return {k: sb.value() for k, sb in self._spinboxes.items()}

    def _start_session(self):
        self._tracker.start_session(self._get_amounts())
        self._rate_label.setText("Session started — take snapshots as you play.")
        self._elapsed_label.setText("")
        # Show session start time immediately (before first snapshot)
        self._on_update(self._tracker.get_display_data())

    def _take_snapshot(self):
        self._tracker.snapshot(self._get_amounts())

    def _on_update(self, data: dict):
        start = data.get("session_start")
        if start:
            start_str = datetime.datetime.fromtimestamp(start).strftime("%H:%M")
            self._session_label.setText(f"Session started: {start_str}")
        else:
            self._session_label.setText("")

        if not data.get("rates"):
            self._refresh_historical()
            return

        lines = []
        for currency, chaos_hr in sorted(data["chaos_rates"].items(), key=lambda x: -x[1]):
            if abs(chaos_hr) > 0.01:
                lines.append(f"{currency}: {chaos_hr:+.1f}c/hr")
        self._rate_label.setText("\n".join(lines[:8]) if lines else "No change yet")
        total = data.get("total_chaos_per_hr", 0)
        elapsed = data.get("elapsed_minutes", 0)
        self._elapsed_label.setText(f"Total: {total:.1f}c/hr  |  {elapsed:.0f} min elapsed")
        self._refresh_historical()

    def _refresh_historical(self):
        """Update the 7-day and all-time average labels from the session log."""
        week = self._tracker.get_historical_display_data(days=7)
        alltime = self._tracker.get_historical_display_data(days=None)
        week_total = week.get("total_chaos_per_hr", 0)
        all_total = alltime.get("total_chaos_per_hr", 0)
        if all_total == 0:
            self._hist_label.setText("")
            return
        parts = []
        if week_total > 0:
            parts.append(f"7-day avg: {week_total:.1f}c/hr")
        parts.append(f"All-time avg: {all_total:.1f}c/hr")
        self._hist_label.setText("  |  ".join(parts))

    def refresh(self):
        self._on_update(self._tracker.get_display_data())
