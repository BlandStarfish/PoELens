"""
Expedition Remnant Browser panel.

Displays PoE Expedition remnant keywords and their effects from a static data file.
Searchable by keyword, effect, or category. No API calls — zero latency.

Data source: data/expedition_remnants.json
"""

import json
import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QScrollArea, QFrame, QHBoxLayout,
)
from PyQt6.QtCore import Qt

ACCENT = "#e2b96f"
TEXT   = "#d4c5a9"
DIM    = "#8a7a65"
TEAL   = "#4ae8c8"
RED    = "#e05050"
ORANGE = "#e8864a"
YELLOW = "#e8c84a"
GREEN  = "#5cba6e"

_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "expedition_remnants.json")

# Color per danger level
_DANGER_COLORS = {
    "high":   RED,
    "medium": ORANGE,
    "none":   GREEN,
}

_DANGER_LABELS = {
    "high":   "Dangerous",
    "medium": "Situational",
    "none":   "Safe",
}


def _load_remnants() -> list[dict]:
    if not os.path.exists(_DATA_PATH):
        return []
    try:
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("remnants", [])
    except Exception as e:
        print(f"[ExpeditionPanel] failed to load remnants: {e}")
        return []


class ExpeditionPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._all_remnants = _load_remnants()
        self._build_ui()
        self._render_remnants(self._all_remnants)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        header = QLabel(f"Expedition Remnants  •  {len(self._all_remnants)} keywords")
        header.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 13px;")
        layout.addWidget(header)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search by keyword, effect, or category…")
        self._search.setStyleSheet(
            "QLineEdit { background: #0f0f23; color: #d4c5a9; border: 1px solid #2a2a4a; "
            "border-radius: 4px; padding: 4px 8px; }"
        )
        self._search.textChanged.connect(self._on_search)
        layout.addWidget(self._search)

        # Danger legend
        legend_row = QHBoxLayout()
        legend_row.setSpacing(10)
        for danger, label in _DANGER_LABELS.items():
            color = _DANGER_COLORS[danger]
            lbl = QLabel(f"● {label}")
            lbl.setStyleSheet(f"color: {color}; font-size: 10px;")
            legend_row.addWidget(lbl)
        legend_row.addStretch()
        layout.addLayout(legend_row)

        # Scrollable remnant list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        self._remnant_container = QWidget()
        self._remnant_layout    = QVBoxLayout(self._remnant_container)
        self._remnant_layout.setContentsMargins(0, 0, 0, 0)
        self._remnant_layout.setSpacing(4)
        self._remnant_layout.addStretch()
        scroll.setWidget(self._remnant_container)
        layout.addWidget(scroll)

        note = QLabel("Include Remnants with loot bonuses; avoid dangerous monster buffs unless your build can handle them.")
        note.setStyleSheet(f"color: {DIM}; font-size: 10px;")
        note.setWordWrap(True)
        layout.addWidget(note)

    def _on_search(self, text: str):
        query = text.strip().lower()
        if not query:
            self._render_remnants(self._all_remnants)
            return

        filtered = [
            r for r in self._all_remnants
            if query in r.get("keyword", "").lower()
            or query in r.get("effect", "").lower()
            or query in r.get("category", "").lower()
            or query in r.get("notes", "").lower()
        ]
        self._render_remnants(filtered)

    def _render_remnants(self, remnants: list[dict]):
        # Clear existing cards (preserve trailing stretch)
        while self._remnant_layout.count() > 1:
            item = self._remnant_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not remnants:
            empty = QLabel("No matching remnants.")
            empty.setStyleSheet(f"color: {DIM}; font-size: 11px;")
            self._remnant_layout.insertWidget(0, empty)
            return

        # Group by category
        by_category: dict[str, list[dict]] = {}
        for r in remnants:
            cat = r.get("category", "Other")
            by_category.setdefault(cat, []).append(r)

        insert_idx = 0
        for category, cat_remnants in by_category.items():
            hdr = QLabel(category)
            hdr.setStyleSheet(f"color: {TEAL}; font-size: 10px; font-weight: bold;")
            self._remnant_layout.insertWidget(insert_idx, hdr)
            insert_idx += 1

            for remnant in cat_remnants:
                card = self._make_remnant_card(remnant)
                self._remnant_layout.insertWidget(insert_idx, card)
                insert_idx += 1

    def _make_remnant_card(self, remnant: dict) -> QWidget:
        danger      = remnant.get("danger", "none")
        danger_color = _DANGER_COLORS.get(danger, DIM)

        card = QWidget()
        card.setStyleSheet(f"background: #0f0f23; border-left: 3px solid {danger_color}; border-radius: 2px;")
        vl = QVBoxLayout(card)
        vl.setContentsMargins(8, 6, 8, 6)
        vl.setSpacing(3)

        # Keyword name + danger badge
        top_row = QHBoxLayout()
        top_row.setSpacing(6)
        keyword_lbl = QLabel(remnant.get("keyword", ""))
        keyword_lbl.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 11px;")
        keyword_lbl.setWordWrap(True)
        top_row.addWidget(keyword_lbl, 1)

        danger_label = _DANGER_LABELS.get(danger, danger)
        badge = QLabel(danger_label)
        badge.setStyleSheet(
            f"color: {danger_color}; font-size: 9px; background: #1a1a3a; "
            f"border-radius: 2px; padding: 1px 4px;"
        )
        badge.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top_row.addWidget(badge)
        vl.addLayout(top_row)

        # Effect description
        effect_lbl = QLabel(remnant.get("effect", ""))
        effect_lbl.setStyleSheet(f"color: {TEXT}; font-size: 11px;")
        effect_lbl.setWordWrap(True)
        vl.addWidget(effect_lbl)

        # Notes (tips / build-specific advice)
        notes = remnant.get("notes", "")
        if notes:
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet("color: #1a1a3a;")
            vl.addWidget(sep)
            notes_lbl = QLabel(notes)
            notes_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px;")
            notes_lbl.setWordWrap(True)
            vl.addWidget(notes_lbl)

        return card
