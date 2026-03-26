"""
Build Archetype Primer panel.

Foundational guide to PoE build archetypes — Attack, Spell, Minion, DoT,
Trigger, Aura Support, Hit-based Elemental. Shows primary scaling stats,
defensive layers, example skills, and entry difficulty.

Data source: data/build_archetypes.json
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

_DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "build_archetypes.json"
)

_CATEGORY_COLORS = {
    "Attack":  ORANGE,
    "Spell":   BLUE,
    "Minion":  PURPLE,
    "DoT":     RED,
    "Support": GREEN,
}

_DIFFICULTY_COLORS = {
    "Beginner":     GREEN,
    "Intermediate": TEAL,
    "Advanced":     ORANGE,
    "Expert":       RED,
}

_ALL = "All"


def _load_data() -> dict:
    if not os.path.exists(_DATA_PATH):
        return {}
    try:
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[BuildArchetypesPanel] failed to load data: {e}")
        return {}


class BuildArchetypesPanel(QWidget):
    def __init__(self):
        super().__init__()
        data = _load_data()
        self._archetypes    = data.get("archetypes", [])
        self._how_it_works  = data.get("how_it_works", "")
        self._tips          = data.get("tips", [])
        # Build category list from data order (insertion-order dedup)
        seen: set[str] = set()
        cats: list[str] = []
        for a in self._archetypes:
            c = a.get("category", "")
            if c and c not in seen:
                seen.add(c)
                cats.append(c)
        self._categories = [_ALL] + cats
        self._active_cat = _ALL
        self._build_ui()
        self._set_category(_ALL)

    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        header = QLabel(f"Build Archetype Primer  •  {len(self._archetypes)} archetypes")
        header.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 13px;")
        layout.addWidget(header)

        if self._how_it_works:
            how_lbl = QLabel(self._how_it_works)
            how_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px;")
            how_lbl.setWordWrap(True)
            layout.addWidget(how_lbl)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search by archetype, stat, skill, or keyword…")
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

    def _matches(self, arch: dict, query: str) -> bool:
        if not query:
            return True
        searchable = " ".join([
            arch.get("name", ""),
            arch.get("category", ""),
            arch.get("how_it_works", ""),
            arch.get("entry_difficulty", ""),
            arch.get("notes", ""),
            " ".join(arch.get("primary_stats", [])),
            " ".join(arch.get("defensive_layers", [])),
            " ".join(arch.get("example_skills", [])),
        ]).lower()
        return query in searchable

    def _refresh(self):
        query = self._search.text().strip().lower()
        pool = self._archetypes
        if self._active_cat != _ALL:
            pool = [a for a in pool if a.get("category") == self._active_cat]
        filtered = [a for a in pool if self._matches(a, query)]
        self._render(filtered)

    def _render(self, archetypes: list[dict]):
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not archetypes:
            empty = QLabel("No matching archetypes.")
            empty.setStyleSheet(f"color: {DIM}; font-size: 11px;")
            self._list_layout.insertWidget(0, empty)
            return

        for i, arch in enumerate(archetypes):
            card = self._make_card(arch)
            self._list_layout.insertWidget(i, card)

    def _make_card(self, arch: dict) -> QFrame:
        cat   = arch.get("category", "")
        color = _CATEGORY_COLORS.get(cat, ACCENT)
        diff  = arch.get("entry_difficulty", "")

        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: #0f0f1e; border: 1px solid #2a2a4a; "
            f"border-left: 3px solid {color}; border-radius: 4px; padding: 4px; }}"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(6, 4, 6, 4)
        cl.setSpacing(3)

        # Header row: name + category badge + difficulty badge
        header_row = QHBoxLayout()
        name_lbl = QLabel(arch.get("name", ""))
        name_lbl.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 12px;")
        header_row.addWidget(name_lbl)
        header_row.addStretch()

        if diff:
            diff_color = _DIFFICULTY_COLORS.get(diff, DIM)
            diff_badge = QLabel(diff)
            diff_badge.setStyleSheet(f"color: {diff_color}; font-size: 10px;")
            header_row.addWidget(diff_badge)

        if cat:
            cat_badge = QLabel(f"[{cat}]")
            cat_badge.setStyleSheet(f"color: {color}; font-size: 10px;")
            header_row.addWidget(cat_badge)
        cl.addLayout(header_row)

        # How it works
        how = arch.get("how_it_works", "")
        if how:
            how_lbl = QLabel(how)
            how_lbl.setStyleSheet(f"color: {TEXT}; font-size: 10px;")
            how_lbl.setWordWrap(True)
            cl.addWidget(how_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2a2a4a;")
        cl.addWidget(sep)

        # Primary stats
        stats = arch.get("primary_stats", [])
        if stats:
            stats_lbl = QLabel("Primary stats: " + "  •  ".join(stats[:3]))
            stats_lbl.setStyleSheet(f"color: {TEAL}; font-size: 10px;")
            stats_lbl.setWordWrap(True)
            cl.addWidget(stats_lbl)

        # Defensive layers
        defense = arch.get("defensive_layers", [])
        if defense:
            def_lbl = QLabel("Defence: " + "  •  ".join(defense[:3]))
            def_lbl.setStyleSheet(f"color: {GREEN}; font-size: 10px;")
            def_lbl.setWordWrap(True)
            cl.addWidget(def_lbl)

        # Example skills
        skills = arch.get("example_skills", [])
        if skills:
            sk_lbl = QLabel("Examples: " + ", ".join(skills[:4]))
            sk_lbl.setStyleSheet(f"color: {ORANGE}; font-size: 10px;")
            sk_lbl.setWordWrap(True)
            cl.addWidget(sk_lbl)

        # Notes
        notes = arch.get("notes", "")
        if notes:
            notes_lbl = QLabel(notes)
            notes_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px; font-style: italic;")
            notes_lbl.setWordWrap(True)
            cl.addWidget(notes_lbl)

        return card
