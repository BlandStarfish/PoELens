"""
Keystone Passive Reference panel.

Static reference for major PoE keystone passives — effect, trade-off,
which builds need them, and which builds they break.

Data source: data/keystones.json
No API calls — zero latency, always accurate.
"""

import json
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QScrollArea, QFrame,
)

ACCENT  = "#e2b96f"
TEXT    = "#d4c5a9"
DIM     = "#8a7a65"
RED     = "#e05050"
ORANGE  = "#e8864a"
YELLOW  = "#e8c84a"
GREEN   = "#5cba6e"
TEAL    = "#4ae8c8"
PURPLE  = "#a070e8"
BLUE    = "#6090e8"

_DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "keystones.json"
)


def _load_data() -> dict:
    if not os.path.exists(_DATA_PATH):
        return {}
    try:
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[KeystonesPanel] failed to load data: {e}")
        return {}


class KeystonesPanel(QWidget):
    def __init__(self):
        super().__init__()
        data = _load_data()
        self._keystones     = data.get("keystones", [])
        self._how_it_works  = data.get("how_it_works", "")
        self._tips          = data.get("tips", [])
        self._build_ui()
        self._refresh()

    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        header = QLabel(f"Keystone Passive Reference  •  {len(self._keystones)} keystones")
        header.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 13px;")
        layout.addWidget(header)

        if self._how_it_works:
            how_lbl = QLabel(self._how_it_works)
            how_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px;")
            how_lbl.setWordWrap(True)
            layout.addWidget(how_lbl)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search by keystone name, effect, or build type…")
        self._search.setStyleSheet(
            "QLineEdit { background: #0f0f23; color: #d4c5a9; border: 1px solid #2a2a4a; "
            "border-radius: 4px; padding: 4px 8px; }"
        )
        self._search.textChanged.connect(self._refresh)
        layout.addWidget(self._search)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        self._container = QWidget()
        self._list_layout = QVBoxLayout(self._container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(5)
        self._list_layout.addStretch()
        scroll.setWidget(self._container)
        layout.addWidget(scroll)

        if self._tips:
            tips_lbl = QLabel("Tips: " + "  •  ".join(self._tips[:2]))
            tips_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px; font-style: italic;")
            tips_lbl.setWordWrap(True)
            layout.addWidget(tips_lbl)

    def _keystone_matches(self, ks: dict, query: str) -> bool:
        if not query:
            return True
        searchable = " ".join([
            ks.get("name", ""),
            ks.get("effect", ""),
            ks.get("trade_off", ""),
            ks.get("location", ""),
            ks.get("notes", ""),
            " ".join(ks.get("builds_that_need", [])),
            " ".join(ks.get("breaks_for", [])),
        ]).lower()
        return query in searchable

    def _refresh(self):
        query = self._search.text().strip().lower()
        filtered = [ks for ks in self._keystones if self._keystone_matches(ks, query)]
        self._render(filtered)

    def _render(self, keystones: list[dict]):
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not keystones:
            empty = QLabel("No matching keystones.")
            empty.setStyleSheet(f"color: {DIM}; font-size: 11px;")
            self._list_layout.insertWidget(0, empty)
            return

        for i, ks in enumerate(keystones):
            card = self._make_card(ks)
            self._list_layout.insertWidget(i, card)

    def _make_card(self, ks: dict) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: #0f0f1e; border: 1px solid #2a2a4a; "
            f"border-left: 3px solid {ACCENT}; border-radius: 4px; padding: 4px; }}"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(6, 4, 6, 4)
        cl.setSpacing(3)

        # Header: keystone name + location
        header_row = QHBoxLayout()
        name_lbl = QLabel(ks.get("name", ""))
        name_lbl.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 12px;")
        header_row.addWidget(name_lbl)
        header_row.addStretch()

        location = ks.get("location", "")
        if location:
            loc_lbl = QLabel(location)
            loc_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px; font-style: italic;")
            header_row.addWidget(loc_lbl)
        cl.addLayout(header_row)

        # Effect (positive)
        effect = ks.get("effect", "")
        if effect and effect != "N/A":
            eff_lbl = QLabel(effect)
            eff_lbl.setStyleSheet(f"color: {GREEN}; font-size: 11px;")
            eff_lbl.setWordWrap(True)
            cl.addWidget(eff_lbl)

        # Trade-off (negative)
        trade_off = ks.get("trade_off", "")
        if trade_off and trade_off != "N/A":
            trade_lbl = QLabel(f"Trade-off: {trade_off}")
            trade_lbl.setStyleSheet(f"color: {RED}; font-size: 10px;")
            trade_lbl.setWordWrap(True)
            cl.addWidget(trade_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2a2a4a;")
        cl.addWidget(sep)

        # Builds that need it
        needs = ks.get("builds_that_need", [])
        if needs:
            needs_lbl = QLabel("Builds that need it: " + "  •  ".join(needs))
            needs_lbl.setStyleSheet(f"color: {TEAL}; font-size: 10px;")
            needs_lbl.setWordWrap(True)
            cl.addWidget(needs_lbl)

        # Breaks for
        breaks = ks.get("breaks_for", [])
        if breaks:
            breaks_lbl = QLabel("Breaks: " + "  •  ".join(breaks))
            breaks_lbl.setStyleSheet(f"color: {ORANGE}; font-size: 10px;")
            breaks_lbl.setWordWrap(True)
            cl.addWidget(breaks_lbl)

        # Notes
        notes = ks.get("notes", "")
        if notes:
            notes_lbl = QLabel(notes)
            notes_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px; font-style: italic;")
            notes_lbl.setWordWrap(True)
            cl.addWidget(notes_lbl)

        return card
