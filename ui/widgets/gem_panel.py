"""
Gem Level Planner panel.

Shows gems equipped on the active character, highlighting sell candidates
(Awakened 4+, 20/20, Lv 20 eligible for Vaal conversion).

Requires OAuth connection with account:characters scope.
Character is selected from the characters available on the account.
"""

import threading

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QComboBox,
)
from PyQt6.QtCore import pyqtSignal, pyqtSlot

ACCENT = "#e2b96f"
TEXT   = "#d4c5a9"
DIM    = "#8a7a65"
GREEN  = "#5cba6e"
RED    = "#e05050"
TEAL   = "#4ae8c8"
ORANGE = "#e8a04a"


class GemPanel(QWidget):
    _scan_done    = pyqtSignal(bool, str)   # (success, error_msg)
    _updated      = pyqtSignal(object)      # result dict from GemPlanner
    _chars_loaded = pyqtSignal(object)      # list of character dicts or None

    def __init__(self, gem_planner, character_api=None, oauth_manager=None, league="Standard"):
        super().__init__()
        self._planner       = gem_planner
        self._character_api = character_api
        self._oauth         = oauth_manager
        self._league        = league
        self._characters: list[dict] = []
        self._build_ui()

        self._scan_done.connect(self._on_scan_done)
        self._updated.connect(self._on_update)
        self._chars_loaded.connect(self._on_chars_loaded)
        gem_planner.on_update(lambda result: self._updated.emit(result))

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # OAuth status
        if self._oauth and self._oauth.is_configured:
            self._auth_label = QLabel("")
            self._auth_label.setStyleSheet(f"color: {DIM}; font-size: 11px;")
            layout.addWidget(self._auth_label)
        else:
            no_oauth = QLabel(
                "Gem tracking requires a PoE OAuth connection.\n"
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

        # Character selector row
        char_row = QHBoxLayout()
        char_row.setSpacing(6)
        char_lbl = QLabel("Character:")
        char_lbl.setStyleSheet(f"color: {DIM}; font-size: 11px;")
        char_row.addWidget(char_lbl)

        self._char_combo = QComboBox()
        self._char_combo.setStyleSheet(
            "QComboBox { background: #0f0f23; color: #d4c5a9; border: 1px solid #2a2a4a; "
            "border-radius: 4px; padding: 3px 6px; font-size: 11px; }"
            "QComboBox::drop-down { border: none; }"
        )
        self._char_combo.addItem("— load characters —")
        char_row.addWidget(self._char_combo, stretch=1)

        self._load_chars_btn = QPushButton("Load")
        self._load_chars_btn.setFixedWidth(48)
        self._load_chars_btn.clicked.connect(self._load_characters)
        char_row.addWidget(self._load_chars_btn)
        layout.addLayout(char_row)

        # Summary
        self._summary_label = QLabel("Select a character and click Scan Gems.")
        self._summary_label.setStyleSheet(f"color: {ACCENT}; font-weight: bold;")
        layout.addWidget(self._summary_label)

        # Scrollable gem list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        self._gem_container = QWidget()
        self._gem_layout    = QVBoxLayout(self._gem_container)
        self._gem_layout.setContentsMargins(0, 0, 0, 0)
        self._gem_layout.setSpacing(3)
        self._gem_layout.addStretch()
        scroll.setWidget(self._gem_container)
        layout.addWidget(scroll)

        note = QLabel("Equipped gems shown. Weapon-swap slot gems shown under Leveling.")
        note.setStyleSheet(f"color: {DIM}; font-size: 10px;")
        note.setWordWrap(True)
        layout.addWidget(note)

        # Scan button
        self._scan_btn = QPushButton("Scan Gems")
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

    # ------------------------------------------------------------------
    # Character loading
    # ------------------------------------------------------------------

    def _load_characters(self):
        if not self._character_api:
            return
        self._load_chars_btn.setEnabled(False)
        self._load_chars_btn.setText("…")
        threading.Thread(
            target=lambda: self._chars_loaded.emit(self._character_api.list_characters()),
            daemon=True,
        ).start()

    @pyqtSlot(object)
    def _on_chars_loaded(self, chars):
        self._load_chars_btn.setEnabled(True)
        self._load_chars_btn.setText("Load")
        if not chars:
            self._status.setStyleSheet(f"color: {RED}; font-size: 10px;")
            self._status.setText("Could not load characters — check OAuth connection")
            return

        self._characters = chars
        self._char_combo.clear()
        for char in chars:
            name    = char.get("name", "?")
            cls     = char.get("class", "")
            league  = char.get("league", "")
            level   = char.get("level", 0)
            label   = f"{name}  ({cls} Lv {level} · {league})"
            self._char_combo.addItem(label)

        # Pre-select highest-level char in current league
        best_idx = 0
        best_lvl = 0
        for i, char in enumerate(chars):
            in_league = char.get("league", "") == self._league
            lvl       = char.get("level", 0)
            if in_league and lvl > best_lvl:
                best_lvl = lvl
                best_idx = i
        self._char_combo.setCurrentIndex(best_idx)
        self._status.setText("")

    # ------------------------------------------------------------------
    # Gem scanning
    # ------------------------------------------------------------------

    def _start_scan(self):
        idx = self._char_combo.currentIndex()
        if not self._characters or idx < 0 or idx >= len(self._characters):
            self._status.setStyleSheet(f"color: {RED}; font-size: 10px;")
            self._status.setText("Load characters first, then select one and scan.")
            return

        char_name = self._characters[idx].get("name", "")
        self._scan_btn.setEnabled(False)
        self._scan_btn.setText("Scanning…")
        self._status.setText("")
        self._planner.scan(
            char_name,
            on_done=lambda ok, err: self._scan_done.emit(ok, err),
        )

    @pyqtSlot(bool, str)
    def _on_scan_done(self, ok: bool, err: str):
        self._scan_btn.setEnabled(True)
        self._scan_btn.setText("Scan Gems")
        if not ok:
            self._status.setStyleSheet(f"color: {RED}; font-size: 10px;")
            self._status.setText(f"Error: {err}")

    @pyqtSlot(object)
    def _on_update(self, result: dict):
        self._refresh_auth_ui()

        sell     = result.get("sell_candidates", [])
        active   = result.get("active_gems", [])
        support  = result.get("support_gems", [])
        total    = result.get("total", 0)

        parts = [f"{total} gem(s)", f"{len(sell)} sell candidate(s)"]
        self._summary_label.setText("  •  ".join(parts))

        # Clear existing gem rows (preserve trailing stretch)
        while self._gem_layout.count() > 1:
            item = self._gem_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        leveling = result.get("leveling_gems", [])

        insert_idx = 0
        for group_label, gems, header_color in (
            ("Sell Candidates",         sell,     ORANGE),
            ("Active Gems",             active,   TEAL),
            ("Support Gems",            support,  DIM),
            ("Leveling (Weapon Swap)",  leveling, GREEN),
        ):
            if not gems:
                continue
            hdr = QLabel(f"{group_label}  ({len(gems)})")
            hdr.setStyleSheet(f"color: {header_color}; font-size: 10px; font-weight: bold;")
            self._gem_layout.insertWidget(insert_idx, hdr)
            insert_idx += 1
            for gem in gems:
                row = _make_gem_row(gem)
                self._gem_layout.insertWidget(insert_idx, row)
                insert_idx += 1

        self._status.setStyleSheet(f"color: {GREEN}; font-size: 10px;")
        self._status.setText("Scan complete.")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_authenticated(self) -> bool:
        return bool(self._oauth and self._oauth.is_authenticated)

    def _refresh_auth_ui(self):
        if self._auth_label is None:
            return
        if self._is_authenticated():
            name = self._oauth.account_name or "account"
            self._auth_label.setText(f"Connected: {name}")
            self._auth_label.setStyleSheet(f"color: {GREEN}; font-size: 11px;")
            self._scan_btn.setEnabled(True)
            self._load_chars_btn.setEnabled(True)
        else:
            self._auth_label.setText("Not connected — use the Currency tab to connect your PoE account")
            self._auth_label.setStyleSheet(f"color: {DIM}; font-size: 11px;")
            self._scan_btn.setEnabled(False)
            self._load_chars_btn.setEnabled(False)


def _make_gem_row(gem: dict) -> QWidget:
    row = QWidget()
    row.setStyleSheet("background: #0f0f23; border-radius: 3px;")
    hl = QHBoxLayout(row)
    hl.setContentsMargins(6, 3, 6, 3)
    hl.setSpacing(8)

    name_lbl = QLabel(gem["name"])
    name_color = ORANGE if gem.get("sell_candidate") else TEXT
    name_lbl.setStyleSheet(f"color: {name_color}; font-size: 11px;")
    hl.addWidget(name_lbl, stretch=1)

    level   = gem["level"]
    quality = gem["quality"]
    lq_lbl  = QLabel(f"Lv {level} / {quality}%")
    lq_color = GREEN if (level >= 20 and quality >= 20) else (TEAL if level >= 20 else DIM)
    lq_lbl.setStyleSheet(f"color: {lq_color}; font-size: 10px;")
    hl.addWidget(lq_lbl)

    reason = gem.get("sell_candidate")
    if reason:
        reason_lbl = QLabel(reason)
        reason_lbl.setStyleSheet(f"color: {ORANGE}; font-size: 10px;")
        hl.addWidget(reason_lbl)

    return row
