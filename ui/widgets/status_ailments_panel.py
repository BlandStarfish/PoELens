"""
Status Ailment Reference panel.

Reference for all major PoE status ailments: elemental ailments (Ignite,
Chill, Freeze, Shock, Scorch, Brittle, Sap), physical/poison ailments
(Poison, Bleed, Corrupted Blood), and debuffs (Maim, Hinder, Taunt,
Intimidate, Exposure).

Shows effect, how applied, how to cure (on players), and offensive use.

Data source: data/status_ailments.json
No API calls — zero latency, always accurate.
"""

import json
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QScrollArea, QFrame, QPushButton,
)

ACCENT = "#e2b96f"
TEXT   = "#d4c5a9"
DIM    = "#8a7a65"
GREEN  = "#5cba6e"
TEAL   = "#4ae8c8"
ORANGE = "#e8864a"
RED    = "#e05050"
PURPLE = "#a070e8"
BLUE   = "#6090e8"
YELLOW = "#e8c84a"

_DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "status_ailments.json"
)

_CATEGORY_COLORS = {
    "Elemental":          ORANGE,
    "Physical & Poison":  RED,
    "Debuff":             PURPLE,
}

_ELEMENT_COLORS = {
    "Fire":        RED,
    "Cold":        BLUE,
    "Lightning":   YELLOW,
    "Chaos":       PURPLE,
    "Physical":    ORANGE,
    "Elemental":   TEAL,
    "None":        DIM,
}

_ALL = "All"


def _load_data() -> dict:
    if not os.path.exists(_DATA_PATH):
        return {}
    try:
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[StatusAilmentsPanel] failed to load data: {e}")
        return {}


class StatusAilmentsPanel(QWidget):
    def __init__(self):
        super().__init__()
        data = _load_data()
        self._ailments     = data.get("ailments", [])
        self._how_it_works = data.get("how_it_works", "")
        self._tips         = data.get("tips", [])
        self._categories   = [_ALL] + data.get("categories", [])
        self._active_cat   = _ALL
        self._build_ui()
        self._set_category(_ALL)

    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        header = QLabel(f"Status Ailment Reference  •  {len(self._ailments)} ailments")
        header.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 13px;")
        layout.addWidget(header)

        if self._how_it_works:
            how_lbl = QLabel(self._how_it_works)
            how_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px;")
            how_lbl.setWordWrap(True)
            layout.addWidget(how_lbl)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search by ailment name, element, effect, or cure…")
        self._search.setStyleSheet(
            "QLineEdit { background: #0f0f23; color: #d4c5a9; border: 1px solid #2a2a4a; "
            "border-radius: 4px; padding: 4px 8px; }"
        )
        self._search.textChanged.connect(self._refresh)
        layout.addWidget(self._search)

        # Category filter buttons
        cat_row = QHBoxLayout()
        cat_row.setSpacing(5)
        self._cat_buttons: dict[str, QPushButton] = {}
        for cat in self._categories:
            color = _CATEGORY_COLORS.get(cat, ACCENT)
            btn = QPushButton(cat)
            btn.setFixedHeight(22)
            btn.setStyleSheet(
                f"QPushButton {{ background: #0f0f23; color: {DIM}; border: 1px solid #2a2a4a; "
                f"border-radius: 3px; padding: 0 8px; font-size: 10px; }}"
                f"QPushButton:hover {{ background: #1a1a3a; }}"
                f"QPushButton[active='true'] {{ color: {color}; border-color: {color}; }}"
            )
            btn.clicked.connect(lambda _, c=cat: self._set_category(c))
            self._cat_buttons[cat] = btn
            cat_row.addWidget(btn)
        cat_row.addStretch()
        layout.addLayout(cat_row)

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

    def _set_category(self, cat: str):
        self._active_cat = cat
        for c, btn in self._cat_buttons.items():
            btn.setProperty("active", "true" if c == cat else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._refresh()

    def _matches(self, ailment: dict, query: str) -> bool:
        if not query:
            return True
        searchable = " ".join([
            ailment.get("name", ""),
            ailment.get("category", ""),
            ailment.get("element", ""),
            ailment.get("effect", ""),
            ailment.get("how_applied", ""),
            ailment.get("how_to_cure", ""),
            ailment.get("offensive_use", ""),
            ailment.get("notes", ""),
        ]).lower()
        return query in searchable

    def _refresh(self):
        query = self._search.text().strip().lower()
        pool = self._ailments
        if self._active_cat != _ALL:
            pool = [a for a in pool if a.get("category") == self._active_cat]
        filtered = [a for a in pool if self._matches(a, query)]
        self._render(filtered)

    def _render(self, ailments: list[dict]):
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not ailments:
            empty = QLabel("No matching ailments.")
            empty.setStyleSheet(f"color: {DIM}; font-size: 11px;")
            self._list_layout.insertWidget(0, empty)
            return

        for i, ailment in enumerate(ailments):
            card = self._make_card(ailment)
            self._list_layout.insertWidget(i, card)

    def _make_card(self, ailment: dict) -> QFrame:
        cat     = ailment.get("category", "")
        element = ailment.get("element", "")
        color   = _CATEGORY_COLORS.get(cat, ACCENT)
        el_color = _ELEMENT_COLORS.get(element, DIM)

        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: #0f0f1e; border: 1px solid #2a2a4a; "
            f"border-left: 3px solid {color}; border-radius: 4px; padding: 4px; }}"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(6, 4, 6, 4)
        cl.setSpacing(3)

        # Header: name + element badge + category badge
        header_row = QHBoxLayout()
        name_lbl = QLabel(ailment.get("name", ""))
        name_lbl.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 12px;")
        header_row.addWidget(name_lbl)
        header_row.addStretch()

        if element and element != "None":
            el_badge = QLabel(element)
            el_badge.setStyleSheet(f"color: {el_color}; font-size: 10px;")
            header_row.addWidget(el_badge)

        if cat:
            cat_badge = QLabel(f"[{cat}]")
            cat_badge.setStyleSheet(f"color: {color}; font-size: 10px;")
            header_row.addWidget(cat_badge)
        cl.addLayout(header_row)

        # Effect
        effect = ailment.get("effect", "")
        if effect:
            effect_lbl = QLabel(effect)
            effect_lbl.setStyleSheet(f"color: {TEXT}; font-size: 10px;")
            effect_lbl.setWordWrap(True)
            cl.addWidget(effect_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2a2a4a;")
        cl.addWidget(sep)

        # How applied
        applied = ailment.get("how_applied", "")
        if applied:
            app_lbl = QLabel(f"Applied: {applied}")
            app_lbl.setStyleSheet(f"color: {TEAL}; font-size: 10px;")
            app_lbl.setWordWrap(True)
            cl.addWidget(app_lbl)

        # How to cure (player perspective)
        cure = ailment.get("how_to_cure", "")
        if cure:
            cure_lbl = QLabel(f"Cure: {cure}")
            cure_lbl.setStyleSheet(f"color: {GREEN}; font-size: 10px;")
            cure_lbl.setWordWrap(True)
            cl.addWidget(cure_lbl)

        # Offensive use
        off_use = ailment.get("offensive_use", "")
        if off_use:
            off_lbl = QLabel(f"Offense: {off_use}")
            off_lbl.setStyleSheet(f"color: {ORANGE}; font-size: 10px;")
            off_lbl.setWordWrap(True)
            cl.addWidget(off_lbl)

        # Notes
        notes = ailment.get("notes", "")
        if notes:
            notes_lbl = QLabel(notes)
            notes_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px; font-style: italic;")
            notes_lbl.setWordWrap(True)
            cl.addWidget(notes_lbl)

        return card
