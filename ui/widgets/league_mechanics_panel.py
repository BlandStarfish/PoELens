"""
League Mechanic Primer panel.

Quick reference for how each permanent league mechanic works — how to
trigger it, what to do, key rewards, and tips. Replaces alt-tabbing to
the wiki for players returning from a break or learning new mechanics.

Data source: data/league_mechanics.json
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
YELLOW = "#e8c84a"

_DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "league_mechanics.json"
)

_CATEGORY_COLORS = {
    "Combat":     ORANGE,
    "Management": TEAL,
    "Exploration": GREEN,
}

_ALL = "All"


def _load_data() -> dict:
    if not os.path.exists(_DATA_PATH):
        return {}
    try:
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[LeagueMechanicsPanel] failed to load data: {e}")
        return {}


class LeagueMechanicsPanel(QWidget):
    def __init__(self):
        super().__init__()
        data = _load_data()
        self._mechanics     = data.get("mechanics", [])
        self._how_it_works  = data.get("how_it_works", "")
        self._tips          = data.get("tips", [])
        self._categories    = [_ALL] + data.get("categories", [])
        self._active_cat    = _ALL
        self._build_ui()
        self._set_category(_ALL)

    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        header = QLabel(f"League Mechanic Primer  •  {len(self._mechanics)} mechanics")
        header.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 13px;")
        layout.addWidget(header)

        if self._how_it_works:
            how_lbl = QLabel(self._how_it_works)
            how_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px;")
            how_lbl.setWordWrap(True)
            layout.addWidget(how_lbl)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search by mechanic name, reward, or keyword…")
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

    def _matches(self, mech: dict, query: str) -> bool:
        if not query:
            return True
        searchable = " ".join([
            mech.get("name", ""),
            mech.get("category", ""),
            mech.get("how_to_trigger", ""),
            mech.get("what_to_do", ""),
            mech.get("notes", ""),
            " ".join(mech.get("key_rewards", [])),
            " ".join(mech.get("tips", [])),
        ]).lower()
        return query in searchable

    def _refresh(self):
        query = self._search.text().strip().lower()
        pool = self._mechanics
        if self._active_cat != _ALL:
            pool = [m for m in pool if m.get("category") == self._active_cat]
        filtered = [m for m in pool if self._matches(m, query)]
        self._render(filtered)

    def _render(self, mechanics: list[dict]):
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not mechanics:
            empty = QLabel("No matching mechanics.")
            empty.setStyleSheet(f"color: {DIM}; font-size: 11px;")
            self._list_layout.insertWidget(0, empty)
            return

        for i, mech in enumerate(mechanics):
            card = self._make_card(mech)
            self._list_layout.insertWidget(i, card)

    def _make_card(self, mech: dict) -> QFrame:
        cat   = mech.get("category", "")
        color = _CATEGORY_COLORS.get(cat, ACCENT)

        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: #0f0f1e; border: 1px solid #2a2a4a; "
            f"border-left: 3px solid {color}; border-radius: 4px; padding: 4px; }}"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(6, 4, 6, 4)
        cl.setSpacing(3)

        # Header: mechanic name + category badge
        header_row = QHBoxLayout()
        name_lbl = QLabel(mech.get("name", ""))
        name_lbl.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 12px;")
        header_row.addWidget(name_lbl)
        header_row.addStretch()
        if cat:
            cat_badge = QLabel(f"[{cat}]")
            cat_badge.setStyleSheet(f"color: {color}; font-size: 10px;")
            header_row.addWidget(cat_badge)
        cl.addLayout(header_row)

        # How to trigger
        trigger = mech.get("how_to_trigger", "")
        if trigger:
            trigger_lbl = QLabel(f"Trigger: {trigger}")
            trigger_lbl.setStyleSheet(f"color: {TEXT}; font-size: 10px;")
            trigger_lbl.setWordWrap(True)
            cl.addWidget(trigger_lbl)

        # What to do
        what = mech.get("what_to_do", "")
        if what:
            what_lbl = QLabel(what)
            what_lbl.setStyleSheet(f"color: {GREEN}; font-size: 10px;")
            what_lbl.setWordWrap(True)
            cl.addWidget(what_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2a2a4a;")
        cl.addWidget(sep)

        # Key rewards
        rewards = mech.get("key_rewards", [])
        if rewards:
            rew_lbl = QLabel("Rewards: " + "  •  ".join(rewards[:3]))
            rew_lbl.setStyleSheet(f"color: {TEAL}; font-size: 10px;")
            rew_lbl.setWordWrap(True)
            cl.addWidget(rew_lbl)

        # Tips
        tips = mech.get("tips", [])
        if tips:
            tip_lbl = QLabel("Tips: " + "  •  ".join(tips[:2]))
            tip_lbl.setStyleSheet(f"color: {YELLOW}; font-size: 10px;")
            tip_lbl.setWordWrap(True)
            cl.addWidget(tip_lbl)

        # Notes
        notes = mech.get("notes", "")
        if notes:
            notes_lbl = QLabel(notes)
            notes_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px; font-style: italic;")
            notes_lbl.setWordWrap(True)
            cl.addWidget(notes_lbl)

        return card
