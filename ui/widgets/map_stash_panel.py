"""
Map Stash panel.

Scans the player's MapStash tab via OAuth to display all maps with their
rolled affix information: IIQ, IIR, Pack Size, and explicit mod list.

Requires OAuth (account:stashes scope). Scan is user-triggered.
Maps are grouped by tier, sorted tier-descending then name-ascending.
"""

import threading

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot

ACCENT  = "#e2b96f"
TEXT    = "#d4c5a9"
DIM     = "#8a7a65"
GREEN   = "#5cba6e"
RED     = "#e05050"
TEAL    = "#4ae8c8"
ORANGE  = "#e8a84a"

# Rarity label colours matching in-game colouring conventions
_RARITY_COLOR = {
    "Normal": TEXT,
    "Magic":  "#8888ff",
    "Rare":   ACCENT,
    "Unique": ORANGE,
}


class MapStashPanel(QWidget):
    _scan_done = pyqtSignal(bool, str)   # (success, error_msg)
    _updated   = pyqtSignal(object)      # list of map dicts

    def __init__(self, map_scanner, oauth_manager=None, stash_api=None, league="Standard"):
        super().__init__()
        self._scanner  = map_scanner
        self._oauth    = oauth_manager
        self._league   = league
        self._build_ui()

        self._scan_done.connect(self._on_scan_done)
        self._updated.connect(self._on_update)
        map_scanner.on_update(lambda maps: self._updated.emit(maps))

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
                "Map stash scanning requires a PoE OAuth connection.\n"
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
        self._summary_label = QLabel("No scan yet.")
        self._summary_label.setStyleSheet(f"color: {ACCENT}; font-weight: bold;")
        layout.addWidget(self._summary_label)

        # Scrollable map list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        self._map_container = QWidget()
        self._map_layout    = QVBoxLayout(self._map_container)
        self._map_layout.setContentsMargins(0, 0, 0, 0)
        self._map_layout.setSpacing(3)
        self._map_layout.addStretch()
        scroll.setWidget(self._map_container)
        layout.addWidget(scroll)

        note = QLabel("Grouped by tier · Only maps in your MapStash tab are shown.")
        note.setStyleSheet(f"color: {DIM}; font-size: 10px;")
        note.setWordWrap(True)
        layout.addWidget(note)

        # Scan button
        self._scan_btn = QPushButton("Scan Map Stash")
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
        self._scan_btn.setText("Scanning…")
        self._status.setText("")
        self._scanner.scan(
            self._league,
            on_done=lambda ok, err: self._scan_done.emit(ok, err),
        )

    @pyqtSlot(bool, str)
    def _on_scan_done(self, ok: bool, err: str):
        self._scan_btn.setEnabled(True)
        self._scan_btn.setText("Scan Map Stash")
        if not ok:
            self._status.setStyleSheet(f"color: {RED}; font-size: 10px;")
            self._status.setText(f"Error: {err}")

    @pyqtSlot(object)
    def _on_update(self, maps: list):
        self._refresh_auth_ui()

        # Clear existing rows (except trailing stretch)
        while self._map_layout.count() > 1:
            item = self._map_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not maps:
            empty = QLabel("No maps found in MapStash tab.")
            empty.setStyleSheet(f"color: {DIM}; font-size: 11px;")
            self._map_layout.insertWidget(0, empty)
            self._summary_label.setText("0 maps found.")
            self._status.setStyleSheet(f"color: {GREEN}; font-size: 10px;")
            self._status.setText("Scan complete.")
            return

        # Group by tier
        tiers: dict[int, list[dict]] = {}
        for m in maps:
            tiers.setdefault(m["tier"], []).append(m)

        insert_idx = 0
        total_maps = 0
        for tier in sorted(tiers.keys(), reverse=True):
            group = tiers[tier]
            total_maps += len(group)

            tier_label = f"Tier {tier}" if tier > 0 else "Unknown Tier"
            hdr = QLabel(f"{tier_label}  ({len(group)})")
            hdr.setStyleSheet(f"color: {TEAL}; font-size: 10px; font-weight: bold;")
            self._map_layout.insertWidget(insert_idx, hdr)
            insert_idx += 1

            for m in group:
                row = self._make_map_row(m)
                self._map_layout.insertWidget(insert_idx, row)
                insert_idx += 1

        self._summary_label.setText(f"{total_maps} map(s) across {len(tiers)} tier(s)")
        self._status.setStyleSheet(f"color: {GREEN}; font-size: 10px;")
        self._status.setText("Scan complete.")

    def _make_map_row(self, m: dict) -> QWidget:
        row = QWidget()
        row.setStyleSheet("background: #0f0f23; border-radius: 3px;")
        vl = QVBoxLayout(row)
        vl.setContentsMargins(6, 4, 6, 4)
        vl.setSpacing(2)

        # Top row: name | rarity tag | IIQ/IIR/Pack
        hl = QHBoxLayout()
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(6)

        name_color = _RARITY_COLOR.get(m["rarity"], TEXT)
        name_lbl = QLabel(m["name"])
        name_lbl.setStyleSheet(f"color: {name_color}; font-size: 11px; font-weight: bold;")
        hl.addWidget(name_lbl, stretch=1)

        if not m["identified"]:
            unid_lbl = QLabel("Unidentified")
            unid_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px;")
            hl.addWidget(unid_lbl)
        else:
            stats_parts = []
            if m["iiq"] > 0:
                stats_parts.append(f"+{m['iiq']}% IIQ")
            if m["iir"] > 0:
                stats_parts.append(f"+{m['iir']}% IIR")
            if m["pack_size"] > 0:
                stats_parts.append(f"+{m['pack_size']}% Pack")
            if stats_parts:
                stats_lbl = QLabel("  ".join(stats_parts))
                stats_lbl.setStyleSheet(f"color: {TEAL}; font-size: 10px;")
                hl.addWidget(stats_lbl)

        vl.addLayout(hl)

        # Explicit mods (one per line)
        for mod in m.get("mods", []):
            mod_lbl = QLabel(mod)
            mod_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px;")
            mod_lbl.setWordWrap(True)
            vl.addWidget(mod_lbl)

        return row

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
