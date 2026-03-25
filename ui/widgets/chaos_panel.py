"""
Chaos Recipe Counter panel.

Scans stash tabs via OAuth to count complete vendor recipe sets:
  - Chaos Orb: full set of rare items, ilvl 60-74
  - Regal Orb: full set of rare items, ilvl 75+

Requires OAuth (account:stashes scope). Scan is user-triggered.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGridLayout,
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot

from modules.chaos_recipe import SLOTS

ACCENT = "#e2b96f"
TEXT   = "#d4c5a9"
DIM    = "#8a7a65"
GREEN  = "#5cba6e"
RED    = "#e05050"
TEAL   = "#4ecdc4"

# Slot display names for UI
_SLOT_LABELS = {
    "helmet": "Helmet",
    "chest":  "Chest",
    "gloves": "Gloves",
    "boots":  "Boots",
    "belt":   "Belt",
    "ring":   "Rings (×2)",
    "amulet": "Amulet",
    "weapon": "Weapon",
}


class ChaosPanel(QWidget):
    _scan_done = pyqtSignal(bool, str)   # (success, error_msg)
    _updated   = pyqtSignal(object)      # chaos_recipe result dict

    def __init__(self, chaos_recipe, oauth_manager=None, stash_api=None, league="Standard"):
        super().__init__()
        self._recipe   = chaos_recipe
        self._oauth    = oauth_manager
        self._stash_api = stash_api
        self._league   = league
        self._slot_labels: dict[str, QLabel] = {}
        self._build_ui()

        self._scan_done.connect(self._on_scan_done)
        self._updated.connect(self._on_update)
        chaos_recipe.on_update(lambda r: self._updated.emit(r))

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Auth status
        if self._oauth and self._oauth.is_configured:
            self._auth_label = QLabel("")
            self._auth_label.setStyleSheet(f"color: {DIM}; font-size: 11px;")
            layout.addWidget(self._auth_label)
        else:
            no_oauth = QLabel(
                "Chaos recipe counting requires a PoE OAuth connection.\n"
                "Set oauth_client_id in the Settings tab to enable."
            )
            no_oauth.setStyleSheet(f"color: {DIM}; font-size: 11px;")
            no_oauth.setWordWrap(True)
            layout.addWidget(no_oauth)
            self._auth_label = None

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2a2a4a;")
        layout.addWidget(sep)

        # Summary row
        self._chaos_label = QLabel("—")
        self._chaos_label.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 14px;")
        self._regal_label = QLabel("—")
        self._regal_label.setStyleSheet(f"color: {TEAL}; font-weight: bold; font-size: 14px;")

        summary_row = QHBoxLayout()
        chaos_lbl = QLabel("Chaos sets:")
        chaos_lbl.setStyleSheet(f"color: {TEXT}; font-size: 12px;")
        regal_lbl = QLabel("Regal sets:")
        regal_lbl.setStyleSheet(f"color: {TEXT}; font-size: 12px;")
        summary_row.addWidget(chaos_lbl)
        summary_row.addWidget(self._chaos_label)
        summary_row.addStretch()
        summary_row.addWidget(regal_lbl)
        summary_row.addWidget(self._regal_label)
        layout.addLayout(summary_row)

        self._missing_label = QLabel("")
        self._missing_label.setStyleSheet(f"color: {DIM}; font-size: 11px;")
        self._missing_label.setWordWrap(True)
        layout.addWidget(self._missing_label)

        # Per-slot grid
        grid_frame = QFrame()
        grid_frame.setStyleSheet("background: #0f0f23; border-radius: 4px;")
        grid = QGridLayout(grid_frame)
        grid.setSpacing(4)
        grid.setContentsMargins(8, 6, 8, 6)

        # Header row
        for col, header in enumerate(("Slot", "60-74", "75+", "Any", "Unid")):
            lbl = QLabel(header)
            style = f"color: {TEAL}; font-size: 10px; font-weight: bold;" if header == "Unid" \
                    else f"color: {DIM}; font-size: 10px; font-weight: bold;"
            lbl.setStyleSheet(style)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(lbl, 0, col)

        for row, slot in enumerate(SLOTS, start=1):
            name_lbl = QLabel(_SLOT_LABELS.get(slot, slot))
            name_lbl.setStyleSheet(f"color: {TEXT}; font-size: 11px;")
            grid.addWidget(name_lbl, row, 0)

            for col, key in enumerate(("chaos", "regal", "any", "unid"), start=1):
                val_lbl = QLabel("—")
                val_lbl.setStyleSheet(f"color: {DIM}; font-size: 11px;")
                val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                grid.addWidget(val_lbl, row, col)
                self._slot_labels[f"{slot}_{key}"] = val_lbl

        layout.addWidget(grid_frame)

        self._note = QLabel(
            "Note: scans up to 20 non-currency stash tabs.\n"
            "Open your PoE account first via the Currency tab."
        )
        self._note.setStyleSheet(f"color: {DIM}; font-size: 10px;")
        self._note.setWordWrap(True)
        layout.addWidget(self._note)

        # Scan button
        self._scan_btn = QPushButton("Scan Stash Tabs")
        self._scan_btn.setStyleSheet(
            f"QPushButton {{ background: {ACCENT}; color: #1a1a2e; font-weight: bold; padding: 5px 14px; }}"
            f"QPushButton:hover {{ background: #c8a84b; }}"
        )
        self._scan_btn.clicked.connect(self._start_scan)
        layout.addWidget(self._scan_btn)

        self._status = QLabel("")
        self._status.setStyleSheet(f"color: {DIM}; font-size: 10px;")
        layout.addWidget(self._status)

        self._refresh_auth_ui()

    def _start_scan(self):
        self._scan_btn.setEnabled(False)
        self._scan_btn.setText("Scanning stash tabs…")
        self._status.setText("")
        self._recipe.scan(
            self._league,
            on_done=lambda ok, err: self._scan_done.emit(ok, err),
        )

    @pyqtSlot(bool, str)
    def _on_scan_done(self, ok: bool, err: str):
        self._scan_btn.setEnabled(True)
        self._scan_btn.setText("Scan Stash Tabs")
        if not ok:
            self._status.setStyleSheet(f"color: {RED}; font-size: 10px;")
            self._status.setText(f"Error: {err}")

    @pyqtSlot(object)
    def _on_update(self, result: dict):
        self._refresh_auth_ui()

        chaos = result.get("chaos_sets", 0)
        regal = result.get("regal_sets", 0)
        any_s = result.get("any_sets", 0)

        self._chaos_label.setText(str(chaos))
        self._regal_label.setText(str(regal))

        # Update per-slot grid
        counts = result.get("counts", {})
        for slot in SLOTS:
            slot_data = counts.get(slot, {})
            for key in ("chaos", "regal", "any", "unid"):
                lbl = self._slot_labels.get(f"{slot}_{key}")
                if lbl:
                    val = slot_data.get(key, 0)
                    lbl.setText(str(val))
                    if key == "unid":
                        lbl.setStyleSheet(
                            f"color: {TEAL if val > 0 else DIM}; font-size: 11px;"
                        )
                    else:
                        lbl.setStyleSheet(
                            f"color: {GREEN if val > 0 else DIM}; font-size: 11px;"
                        )

        # Missing slots for next set + unid summary
        missing   = result.get("missing", [])
        unid_sets = result.get("unid_sets", 0)

        parts = []
        if missing and any_s == 0:
            names = ", ".join(_SLOT_LABELS.get(s, s) for s in missing)
            parts.append(f"Missing for first set: {names}")
        elif missing:
            names = ", ".join(_SLOT_LABELS.get(s, s) for s in missing)
            parts.append(f"{any_s} complete set(s)  •  Missing for next: {names}")
        else:
            parts.append(f"{any_s} complete set(s) ready")

        if unid_sets > 0:
            parts.append(f"{unid_sets} fully-unid set(s) → 2× yield")

        self._missing_label.setText("  |  ".join(parts))

        self._status.setStyleSheet(f"color: {GREEN}; font-size: 10px;")
        self._status.setText("Scan complete.")

    def _refresh_auth_ui(self):
        if self._auth_label is None:
            return
        if self._oauth and self._oauth.is_authenticated:
            name = self._oauth.account_name or "account"
            self._auth_label.setText(f"Connected: {name}")
            self._auth_label.setStyleSheet(f"color: {GREEN}; font-size: 11px;")
            self._scan_btn.setEnabled(True)
        else:
            self._auth_label.setText("Not connected — use the Currency tab to connect your PoE account")
            self._auth_label.setStyleSheet(f"color: {DIM}; font-size: 11px;")
            self._scan_btn.setEnabled(False)
