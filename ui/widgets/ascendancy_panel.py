"""
Ascendancy Class Reference panel.

Static reference for all 19 Ascendancy classes across 7 base classes —
playstyle, key notable passives, primary defence, and top builds.

Data source: data/ascendancy_classes.json
No API calls — zero latency, always accurate.
"""

import json
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QScrollArea, QFrame, QPushButton,
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
    os.path.dirname(__file__), "..", "..", "data", "ascendancy_classes.json"
)

# Color per base class
_BASE_COLORS = {
    "Marauder": RED,
    "Ranger":   GREEN,
    "Witch":    PURPLE,
    "Duelist":  YELLOW,
    "Templar":  TEAL,
    "Shadow":   BLUE,
    "Scion":    ACCENT,
}

_ALL = "All"


def _load_data() -> dict:
    if not os.path.exists(_DATA_PATH):
        return {}
    try:
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[AscendancyPanel] failed to load data: {e}")
        return {}


class AscendancyPanel(QWidget):
    def __init__(self):
        super().__init__()
        data = _load_data()
        self._classes       = data.get("classes", [])
        self._how_it_works  = data.get("how_it_works", "")
        self._respec_note   = data.get("respec_note", "")
        self._tips          = data.get("tips", [])
        self._base_classes  = [_ALL] + data.get("base_classes", [])
        self._active_base   = _ALL
        self._build_ui()
        self._set_base(_ALL)

    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        header = QLabel(
            f"Ascendancy Class Reference  •  {len(self._classes)} classes  •  "
            f"{len(self._base_classes) - 1} base classes"
        )
        header.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 13px;")
        layout.addWidget(header)

        if self._how_it_works:
            how_lbl = QLabel(self._how_it_works)
            how_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px;")
            how_lbl.setWordWrap(True)
            layout.addWidget(how_lbl)

        if self._respec_note:
            respec_lbl = QLabel(self._respec_note)
            respec_lbl.setStyleSheet(f"color: {ORANGE}; font-size: 10px; font-style: italic;")
            respec_lbl.setWordWrap(True)
            layout.addWidget(respec_lbl)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search by class name, playstyle, or build…")
        self._search.setStyleSheet(
            "QLineEdit { background: #0f0f23; color: #d4c5a9; border: 1px solid #2a2a4a; "
            "border-radius: 4px; padding: 4px 8px; }"
        )
        self._search.textChanged.connect(self._refresh)
        layout.addWidget(self._search)

        # Base class filter buttons
        base_row = QHBoxLayout()
        base_row.setSpacing(4)
        self._base_buttons: dict[str, QPushButton] = {}
        for base in self._base_classes:
            color = _BASE_COLORS.get(base, ACCENT)
            btn = QPushButton(base)
            btn.setFixedHeight(22)
            btn.setStyleSheet(
                f"QPushButton {{ background: #0f0f23; color: {DIM}; border: 1px solid #2a2a4a; "
                f"border-radius: 3px; padding: 0 6px; font-size: 10px; }}"
                f"QPushButton:hover {{ background: #1a1a3a; }}"
                f"QPushButton[active='true'] {{ color: {color}; border-color: {color}; }}"
            )
            btn.clicked.connect(lambda _, b=base: self._set_base(b))
            self._base_buttons[base] = btn
            base_row.addWidget(btn)
        base_row.addStretch()
        layout.addLayout(base_row)

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

    def _set_base(self, base: str):
        self._active_base = base
        for b, btn in self._base_buttons.items():
            btn.setProperty("active", "true" if b == base else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._refresh()

    def _class_matches(self, cls: dict, query: str) -> bool:
        if not query:
            return True
        searchable = " ".join([
            cls.get("name", ""),
            cls.get("base_class", ""),
            cls.get("playstyle", ""),
            cls.get("primary_defence", ""),
            cls.get("notes", ""),
            " ".join(cls.get("key_notables", [])),
            " ".join(cls.get("top_builds", [])),
        ]).lower()
        return query in searchable

    def _refresh(self):
        query = self._search.text().strip().lower()
        pool = self._classes
        if self._active_base != _ALL:
            pool = [c for c in pool if c.get("base_class") == self._active_base]
        filtered = [c for c in pool if self._class_matches(c, query)]
        self._render(filtered)

    def _render(self, classes: list[dict]):
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not classes:
            empty = QLabel("No matching classes.")
            empty.setStyleSheet(f"color: {DIM}; font-size: 11px;")
            self._list_layout.insertWidget(0, empty)
            return

        for i, cls in enumerate(classes):
            card = self._make_card(cls)
            self._list_layout.insertWidget(i, card)

    def _make_card(self, cls: dict) -> QFrame:
        base  = cls.get("base_class", "")
        color = _BASE_COLORS.get(base, ACCENT)

        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: #0f0f1e; border: 1px solid #2a2a4a; "
            f"border-left: 3px solid {color}; border-radius: 4px; padding: 4px; }}"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(6, 4, 6, 4)
        cl.setSpacing(3)

        # Header row: name + base class badge
        header_row = QHBoxLayout()
        name_lbl = QLabel(cls.get("name", ""))
        name_lbl.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 12px;")
        header_row.addWidget(name_lbl)
        header_row.addStretch()

        base_badge = QLabel(f"[{base}]")
        base_badge.setStyleSheet(f"color: {color}; font-size: 10px;")
        header_row.addWidget(base_badge)
        cl.addLayout(header_row)

        # Playstyle
        playstyle = cls.get("playstyle", "")
        if playstyle:
            ps_lbl = QLabel(playstyle)
            ps_lbl.setStyleSheet(f"color: {TEXT}; font-size: 11px;")
            ps_lbl.setWordWrap(True)
            cl.addWidget(ps_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2a2a4a;")
        cl.addWidget(sep)

        # Key notables
        notables = cls.get("key_notables", [])
        if notables:
            notables_lbl = QLabel("Key notables: " + "  •  ".join(notables))
            notables_lbl.setStyleSheet(f"color: {TEAL}; font-size: 10px;")
            notables_lbl.setWordWrap(True)
            cl.addWidget(notables_lbl)

        # Primary defence
        defence = cls.get("primary_defence", "")
        if defence:
            def_lbl = QLabel(f"Defence: {defence}")
            def_lbl.setStyleSheet(f"color: {YELLOW}; font-size: 10px;")
            def_lbl.setWordWrap(True)
            cl.addWidget(def_lbl)

        # Top builds
        builds = cls.get("top_builds", [])
        if builds:
            builds_lbl = QLabel("Builds: " + " / ".join(builds))
            builds_lbl.setStyleSheet(f"color: {GREEN}; font-size: 10px;")
            builds_lbl.setWordWrap(True)
            cl.addWidget(builds_lbl)

        # Notes
        notes = cls.get("notes", "")
        if notes:
            notes_lbl = QLabel(notes)
            notes_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px; font-style: italic;")
            notes_lbl.setWordWrap(True)
            cl.addWidget(notes_lbl)

        return card
