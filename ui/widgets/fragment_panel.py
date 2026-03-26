"""
Fragment Sets Reference panel.

Static reference for all Vaal, Shaper, Breach, and utility fragment sets —
what fragments are needed, how to get them, boss drops, and notes.

Data source: data/fragment_sets.json
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
PURPLE  = "#b04ae8"

_DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "fragment_sets.json"
)

# Type colours
_TYPE_COLORS = {
    "Vaal":     RED,
    "Shaper":   TEAL,
    "Elder":    PURPLE,
    "Breach":   ORANGE,
    "Pantheon": GREEN,
}

# Tier badge colours
_TIER_COLORS = {
    "Normal":       GREEN,
    "Uber":         RED,
    "Endgame":      ORANGE,
    "Breachstone":  YELLOW,
    "Utility":      DIM,
}

_FILTER_TYPES = ["All", "Vaal", "Shaper", "Elder", "Breach", "Pantheon"]


def _load_data() -> dict:
    if not os.path.exists(_DATA_PATH):
        return {}
    try:
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[FragmentPanel] failed to load data: {e}")
        return {}


class FragmentPanel(QWidget):
    def __init__(self):
        super().__init__()
        data = _load_data()
        self._all_sets      = data.get("fragment_sets", [])
        self._how_it_works  = data.get("how_it_works", "")
        self._tips          = data.get("tips", [])
        self._active_type: str | None = None
        self._build_ui()
        self._refresh()

    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        header = QLabel(
            f"Fragment Sets Reference  •  {len(self._all_sets)} encounter sets"
        )
        header.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 13px;")
        layout.addWidget(header)

        if self._how_it_works:
            how_lbl = QLabel(self._how_it_works)
            how_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px;")
            how_lbl.setWordWrap(True)
            layout.addWidget(how_lbl)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search by boss name, fragment, or drop…")
        self._search.setStyleSheet(
            "QLineEdit { background: #0f0f23; color: #d4c5a9; border: 1px solid #2a2a4a; "
            "border-radius: 4px; padding: 4px 8px; }"
        )
        self._search.textChanged.connect(self._refresh)
        layout.addWidget(self._search)

        # Type filter row
        filter_row = QHBoxLayout()
        filter_row.setSpacing(6)
        filt_lbl = QLabel("Type:")
        filt_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px;")
        filter_row.addWidget(filt_lbl)
        self._filter_buttons: dict[str, QPushButton] = {}
        for ft in _FILTER_TYPES:
            color = _TYPE_COLORS.get(ft, ACCENT)
            btn = QPushButton(ft)
            btn.setFixedHeight(22)
            btn.setStyleSheet(
                f"QPushButton {{ background: #0f0f23; color: {DIM}; border: 1px solid #2a2a4a; "
                f"border-radius: 3px; padding: 0 8px; font-size: 10px; }}"
                f"QPushButton:hover {{ background: #1a1a3a; }}"
                f"QPushButton[active='true'] {{ color: {color}; border-color: {color}; }}"
            )
            btn.clicked.connect(lambda _, t=ft: self._on_type_filter(t))
            self._filter_buttons[ft] = btn
            filter_row.addWidget(btn)
        filter_row.addStretch()
        layout.addLayout(filter_row)
        self._set_active_type("All")

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

    def _on_type_filter(self, ftype: str):
        self._set_active_type(ftype)
        self._refresh()

    def _set_active_type(self, ftype: str):
        self._active_type = None if ftype == "All" else ftype
        for btn_label, btn in self._filter_buttons.items():
            btn.setProperty("active", "true" if btn_label == ftype else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _refresh(self):
        query = self._search.text().strip().lower()
        pool  = self._all_sets

        if self._active_type:
            pool = [s for s in pool if s.get("type") == self._active_type]

        if query:
            pool = [
                s for s in pool
                if query in s.get("name", "").lower()
                or query in s.get("boss", "").lower()
                or query in " ".join(s.get("fragments", [])).lower()
                or query in s.get("notable_drops", "").lower()
                or query in s.get("notes", "").lower()
                or query in s.get("how_to_get", "").lower()
            ]

        self._render(pool)

    def _render(self, sets: list[dict]):
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not sets:
            empty = QLabel("No matching fragment sets.")
            empty.setStyleSheet(f"color: {DIM}; font-size: 11px;")
            self._list_layout.insertWidget(0, empty)
            return

        for i, fset in enumerate(sets):
            card = self._make_card(fset)
            self._list_layout.insertWidget(i, card)

    def _make_card(self, fset: dict) -> QWidget:
        ftype        = fset.get("type", "")
        border_color = _TYPE_COLORS.get(ftype, DIM)
        tier         = fset.get("tier", "")
        tier_color   = _TIER_COLORS.get(tier, DIM)

        card = QWidget()
        card.setStyleSheet(
            f"background: #0f0f23; border-left: 3px solid {border_color}; border-radius: 2px;"
        )
        vl = QVBoxLayout(card)
        vl.setContentsMargins(8, 6, 8, 6)
        vl.setSpacing(3)

        # Name + type + tier badges
        top_row = QHBoxLayout()
        name_lbl = QLabel(fset.get("name", ""))
        name_lbl.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 12px;")
        top_row.addWidget(name_lbl, 1)

        if ftype:
            type_badge = QLabel(ftype)
            type_badge.setStyleSheet(
                f"color: {border_color}; font-size: 9px; background: #1a1a3a; "
                "border-radius: 2px; padding: 1px 4px;"
            )
            type_badge.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            top_row.addWidget(type_badge)

        if tier:
            tier_badge = QLabel(tier)
            tier_badge.setStyleSheet(
                f"color: {tier_color}; font-size: 9px; background: #1a1a3a; "
                "border-radius: 2px; padding: 1px 4px; margin-left: 4px;"
            )
            tier_badge.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            top_row.addWidget(tier_badge)

        vl.addLayout(top_row)

        # Boss
        boss = fset.get("boss", "")
        if boss:
            boss_lbl = QLabel(
                f"<b style='color:{TEAL}'>Boss:</b> "
                f"<span style='color:{TEXT}'>{boss}</span>"
            )
            boss_lbl.setTextFormat(Qt.TextFormat.RichText)
            boss_lbl.setStyleSheet("font-size: 11px;")
            vl.addWidget(boss_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #1a1a3a;")
        vl.addWidget(sep)

        # Fragments
        fragments = fset.get("fragments", [])
        if fragments:
            frags_text = "  +  ".join(fragments)
            frags_lbl = QLabel(
                f"<b style='color:{border_color}'>Fragments:</b> "
                f"<span style='color:{ACCENT}'>{frags_text}</span>"
            )
            frags_lbl.setTextFormat(Qt.TextFormat.RichText)
            frags_lbl.setWordWrap(True)
            frags_lbl.setStyleSheet("font-size: 11px;")
            vl.addWidget(frags_lbl)

        # Area level
        area_level = fset.get("area_level")
        if area_level:
            al_lbl = QLabel(
                f"<b style='color:{TEAL}'>Area Level:</b> "
                f"<span style='color:{DIM}'>{area_level}</span>"
            )
            al_lbl.setTextFormat(Qt.TextFormat.RichText)
            al_lbl.setStyleSheet("font-size: 10px;")
            vl.addWidget(al_lbl)

        # How to get
        how_to_get = fset.get("how_to_get", "")
        if how_to_get:
            how_lbl = QLabel(
                f"<b style='color:{GREEN}'>How to get:</b> "
                f"<span style='color:{DIM}'>{how_to_get}</span>"
            )
            how_lbl.setTextFormat(Qt.TextFormat.RichText)
            how_lbl.setWordWrap(True)
            how_lbl.setStyleSheet("font-size: 10px;")
            vl.addWidget(how_lbl)

        # Notable drops
        drops = fset.get("notable_drops", "")
        if drops:
            drops_lbl = QLabel(
                f"<b style='color:{YELLOW}'>Drops:</b> "
                f"<span style='color:{DIM}'>{drops}</span>"
            )
            drops_lbl.setTextFormat(Qt.TextFormat.RichText)
            drops_lbl.setWordWrap(True)
            drops_lbl.setStyleSheet("font-size: 10px;")
            vl.addWidget(drops_lbl)

        # Notes
        notes = fset.get("notes", "")
        if notes:
            notes_lbl = QLabel(notes)
            notes_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px; font-style: italic;")
            notes_lbl.setWordWrap(True)
            vl.addWidget(notes_lbl)

        return card
