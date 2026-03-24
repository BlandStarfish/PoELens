"""
Currency per hour panel.

Primary workflow: connect PoE account via OAuth (requires a registered client_id),
click "Auto-fill from Stash" to populate counts, then use Start Session / Snapshot
to track currency/hr. Manual spinbox entry is a fallback for users without OAuth.
"""

import datetime
import threading

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSpinBox, QScrollArea, QFrame,
    QFormLayout, QGroupBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from modules.currency_tracker import TRACKED_CURRENCIES

ACCENT = "#e2b96f"
TEXT   = "#d4c5a9"
DIM    = "#8a7a65"
GREEN  = "#5cba6e"
RED    = "#e05050"


class CurrencyPanel(QWidget):
    # Signals for thread-safe UI updates from background OAuth/stash threads
    _auth_success = pyqtSignal()
    _auth_failed  = pyqtSignal(str)
    _stash_loaded = pyqtSignal(object)   # emits dict: {currency_name: count}
    _stash_error  = pyqtSignal(str)

    def __init__(self, tracker, oauth_manager=None, stash_api=None, league="Standard"):
        super().__init__()
        self._tracker = tracker
        self._oauth = oauth_manager
        self._stash_api = stash_api
        self._league = league
        self._spinboxes: dict[str, QSpinBox] = {}
        self._build_ui()

        # Connect signals to slots (ensures UI updates happen on the Qt main thread)
        self._auth_success.connect(self._on_auth_success)
        self._auth_failed.connect(self._on_auth_failed)
        self._stash_loaded.connect(self._on_stash_loaded)
        self._stash_error.connect(self._on_stash_error)

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

        # ── OAuth / stash API section (only when client_id is configured) ──
        if self._oauth and self._oauth.is_configured:
            self._build_oauth_section(layout)
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet("color: #2a2a4a;")
            layout.addWidget(sep)

        # ── Session start time ──
        self._session_label = QLabel("")
        self._session_label.setStyleSheet(f"color: {DIM}; font-size: 11px;")
        layout.addWidget(self._session_label)

        # ── Rate display ──
        self._rate_label = QLabel("Start a session and take snapshots to track rates.")
        self._rate_label.setStyleSheet(f"color: {ACCENT}; font-weight: bold;")
        self._rate_label.setWordWrap(True)
        layout.addWidget(self._rate_label)

        self._elapsed_label = QLabel("")
        self._elapsed_label.setStyleSheet(f"color: {DIM}; font-size: 11px;")
        layout.addWidget(self._elapsed_label)

        # ── Historical averages ──
        self._hist_label = QLabel("")
        self._hist_label.setStyleSheet(f"color: {DIM}; font-size: 11px;")
        self._hist_label.setWordWrap(True)
        layout.addWidget(self._hist_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2a2a4a;")
        layout.addWidget(sep)

        # ── Currency input spinboxes ──
        group = QGroupBox("Current counts")
        group.setStyleSheet(f"QGroupBox {{ color: {DIM}; font-size: 11px; }}")
        form = QFormLayout(group)
        form.setSpacing(3)

        for currency in TRACKED_CURRENCIES:
            sb = QSpinBox()
            sb.setRange(0, 999999)
            sb.setStyleSheet(
                "background: #0f0f23; color: #d4c5a9; border: 1px solid #2a2a4a;"
                " border-radius: 3px; padding: 2px;"
            )
            self._spinboxes[currency] = sb
            lbl = QLabel(currency)
            lbl.setStyleSheet(f"color: {TEXT}; font-size: 11px;")
            form.addRow(lbl, sb)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(group)
        layout.addWidget(scroll)

        # ── Session buttons ──
        btn_row = QHBoxLayout()
        start_btn = QPushButton("Start Session")
        start_btn.clicked.connect(self._start_session)
        snap_btn = QPushButton("Snapshot")
        snap_btn.clicked.connect(self._take_snapshot)
        btn_row.addWidget(start_btn)
        btn_row.addWidget(snap_btn)
        layout.addLayout(btn_row)

    def _build_oauth_section(self, layout: QVBoxLayout):
        """Add the OAuth connect / auto-fill row to the layout."""
        oauth_row = QHBoxLayout()
        oauth_row.setSpacing(6)

        self._auth_status_label = QLabel("")
        self._auth_status_label.setStyleSheet(f"color: {DIM}; font-size: 11px;")
        oauth_row.addWidget(self._auth_status_label, 1)

        self._connect_btn = QPushButton("Connect PoE Account")
        self._connect_btn.setStyleSheet(
            f"QPushButton {{ color: {ACCENT}; font-size: 11px; padding: 3px 8px; }}"
        )
        self._connect_btn.clicked.connect(self._connect_account)
        oauth_row.addWidget(self._connect_btn)

        self._autofill_btn = QPushButton("Auto-fill from Stash")
        self._autofill_btn.setStyleSheet(
            f"QPushButton {{ color: {GREEN}; font-size: 11px; padding: 3px 8px; }}"
        )
        self._autofill_btn.clicked.connect(self._auto_fill)
        self._autofill_btn.hide()
        oauth_row.addWidget(self._autofill_btn)

        layout.addLayout(oauth_row)
        self._update_auth_status()

    # ------------------------------------------------------------------
    # OAuth / stash API
    # ------------------------------------------------------------------

    def _update_auth_status(self):
        """Sync auth status label and button visibility with current token state."""
        if not self._oauth:
            return
        if self._oauth.is_authenticated:
            name = self._oauth.account_name or "account"
            self._auth_status_label.setText(f"Connected: {name}")
            self._auth_status_label.setStyleSheet(f"color: {GREEN}; font-size: 11px;")
            self._connect_btn.hide()
            self._autofill_btn.show()
        else:
            self._auth_status_label.setText("Not connected")
            self._auth_status_label.setStyleSheet(f"color: {DIM}; font-size: 11px;")
            self._connect_btn.show()
            self._connect_btn.setEnabled(True)
            self._connect_btn.setText("Connect PoE Account")
            self._autofill_btn.hide()

    def _connect_account(self):
        """Start the OAuth authorization flow in a background thread."""
        self._connect_btn.setEnabled(False)
        self._connect_btn.setText("Connecting...")
        self._oauth.start_auth_flow(
            on_complete=lambda _: self._auth_success.emit(),
            on_error=lambda msg: self._auth_failed.emit(msg),
        )

    @pyqtSlot()
    def _on_auth_success(self):
        self._update_auth_status()

    @pyqtSlot(str)
    def _on_auth_failed(self, message: str):
        self._auth_status_label.setText(f"Auth failed: {message[:70]}")
        self._auth_status_label.setStyleSheet(f"color: {RED}; font-size: 11px;")
        self._connect_btn.setEnabled(True)
        self._connect_btn.setText("Connect PoE Account")

    def _auto_fill(self):
        """Fetch stash currency amounts in a background thread and populate spinboxes."""
        self._autofill_btn.setEnabled(False)
        self._autofill_btn.setText("Loading...")

        def _fetch():
            try:
                amounts = self._stash_api.get_currency_amounts(self._league)
                self._stash_loaded.emit(amounts)
            except Exception as e:
                self._stash_error.emit(str(e))

        threading.Thread(target=_fetch, daemon=True).start()

    @pyqtSlot(object)
    def _on_stash_loaded(self, amounts: dict):
        for currency, count in amounts.items():
            if currency in self._spinboxes:
                self._spinboxes[currency].setValue(count)
        self._autofill_btn.setEnabled(True)
        self._autofill_btn.setText("Auto-fill from Stash")
        if amounts:
            n_nonzero = sum(1 for v in amounts.values() if v > 0)
            name = self._oauth.account_name or "account"
            self._auth_status_label.setText(f"Connected: {name}  ({n_nonzero} currencies loaded)")
            self._auth_status_label.setStyleSheet(f"color: {GREEN}; font-size: 11px;")
        else:
            self._auth_status_label.setText("No currency tab found — enter amounts manually")
            self._auth_status_label.setStyleSheet(f"color: {DIM}; font-size: 11px;")

    @pyqtSlot(str)
    def _on_stash_error(self, message: str):
        self._autofill_btn.setEnabled(True)
        self._autofill_btn.setText("Auto-fill from Stash")
        self._auth_status_label.setText(f"Stash error: {message[:60]}")
        self._auth_status_label.setStyleSheet(f"color: {RED}; font-size: 11px;")

    # ------------------------------------------------------------------
    # Session / rate display
    # ------------------------------------------------------------------

    def _get_amounts(self) -> dict:
        return {k: sb.value() for k, sb in self._spinboxes.items()}

    def _start_session(self):
        self._tracker.start_session(self._get_amounts())
        self._rate_label.setText("Session started — take snapshots as you play.")
        self._elapsed_label.setText("")
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
        summary = "  |  ".join(parts)

        # Top-3 currencies by all-time chaos/hr (positive earners only)
        chaos_rates = alltime.get("chaos_rates", {})
        top = sorted(
            [(k, v) for k, v in chaos_rates.items() if v > 0.01],
            key=lambda x: -x[1],
        )[:3]
        if top:
            top_str = "  ·  ".join(f"{k}: +{v:.1f}c/hr" for k, v in top)
            summary += f"\nTop: {top_str}"

        self._hist_label.setText(summary)

    def refresh(self):
        self._on_update(self._tracker.get_display_data())
