"""
Gem Quality & Awakened Gem Reference panel.

Reference for what quality does on popular skill and support gems, plus
a summary of all Awakened gems and their improvements over the base version.

Data source: data/gem_quality.json
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
GOLD   = "#f5c842"

_DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "gem_quality.json"
)

_CATEGORY_COLORS = {
    "Active Skill": TEAL,
    "Support":      ORANGE,
    "Awakened":     GOLD,
}

_ALL = "All"


def _load_data() -> dict:
    if not os.path.exists(_DATA_PATH):
        return {}
    try:
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[GemQualityPanel] failed to load data: {e}")
        return {}


class GemQualityPanel(QWidget):
    def __init__(self):
        super().__init__()
        data = _load_data()
        self._gems         = data.get("gems", [])
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

        header = QLabel(f"Gem Quality & Awakened Reference  •  {len(self._gems)} gems")
        header.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 13px;")
        layout.addWidget(header)

        if self._how_it_works:
            how_lbl = QLabel(self._how_it_works)
            how_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px;")
            how_lbl.setWordWrap(True)
            layout.addWidget(how_lbl)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search by gem name, quality effect, or awakened improvement…")
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

    def _matches(self, gem: dict, query: str) -> bool:
        if not query:
            return True
        searchable = " ".join([
            gem.get("name", ""),
            gem.get("category", ""),
            gem.get("quality_effect", ""),
            gem.get("sell_value", ""),
            gem.get("awakened_name", "") or "",
            gem.get("awakened_improvement", "") or "",
            gem.get("notes", ""),
        ]).lower()
        return query in searchable

    def _refresh(self):
        query = self._search.text().strip().lower()
        pool = self._gems
        if self._active_cat != _ALL:
            pool = [g for g in pool if g.get("category") == self._active_cat]
        filtered = [g for g in pool if self._matches(g, query)]
        self._render(filtered)

    def _render(self, gems: list[dict]):
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not gems:
            empty = QLabel("No matching gems.")
            empty.setStyleSheet(f"color: {DIM}; font-size: 11px;")
            self._list_layout.insertWidget(0, empty)
            return

        for i, gem in enumerate(gems):
            card = self._make_card(gem)
            self._list_layout.insertWidget(i, card)

    def _make_card(self, gem: dict) -> QFrame:
        cat   = gem.get("category", "")
        color = _CATEGORY_COLORS.get(cat, ACCENT)

        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: #0f0f1e; border: 1px solid #2a2a4a; "
            f"border-left: 3px solid {color}; border-radius: 4px; padding: 4px; }}"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(6, 4, 6, 4)
        cl.setSpacing(3)

        # Header: gem name + category badge
        header_row = QHBoxLayout()
        name_lbl = QLabel(gem.get("name", ""))
        name_lbl.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 12px;")
        header_row.addWidget(name_lbl)
        header_row.addStretch()
        if cat:
            cat_badge = QLabel(f"[{cat}]")
            cat_badge.setStyleSheet(f"color: {color}; font-size: 10px;")
            header_row.addWidget(cat_badge)
        cl.addLayout(header_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2a2a4a;")
        cl.addWidget(sep)

        # Quality effect
        q_eff = gem.get("quality_effect", "")
        if q_eff:
            q_lbl = QLabel(f"Quality: {q_eff}")
            q_lbl.setStyleSheet(f"color: {TEAL}; font-size: 10px;")
            q_lbl.setWordWrap(True)
            cl.addWidget(q_lbl)

        # Awakened info (if applicable)
        awk_name = gem.get("awakened_name")
        awk_imp  = gem.get("awakened_improvement")
        awk_lvl  = gem.get("awakened_max_level")
        if awk_name:
            awk_lbl = QLabel(f"Awakened: {awk_name}  (max lvl {awk_lvl})")
            awk_lbl.setStyleSheet(f"color: {GOLD}; font-size: 10px; font-weight: bold;")
            cl.addWidget(awk_lbl)
            if awk_imp:
                imp_lbl = QLabel(f"  → {awk_imp}")
                imp_lbl.setStyleSheet(f"color: {GREEN}; font-size: 10px;")
                imp_lbl.setWordWrap(True)
                cl.addWidget(imp_lbl)

        # Sell value
        sell_val = gem.get("sell_value", "")
        if sell_val:
            sv_lbl = QLabel(f"Value: {sell_val}")
            sv_lbl.setStyleSheet(f"color: {ORANGE}; font-size: 10px;")
            cl.addWidget(sv_lbl)

        # Notes
        notes = gem.get("notes", "")
        if notes:
            notes_lbl = QLabel(notes)
            notes_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px; font-style: italic;")
            notes_lbl.setWordWrap(True)
            cl.addWidget(notes_lbl)

        return card
