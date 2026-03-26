"""
Sanctum Affliction & Boon Reference panel.

Static reference for all major Sanctum afflictions (penalties) and boons (bonuses).
Severity/value filter + full-text search. No API calls — zero latency.

Data source: data/sanctum_afflictions.json
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
RED    = "#e05050"
ORANGE = "#e8864a"
YELLOW = "#e8c84a"
GREEN  = "#5cba6e"
TEAL   = "#4ae8c8"

_DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "sanctum_afflictions.json"
)

_SEVERITY_COLORS = {
    "critical":  RED,
    "dangerous": ORANGE,
    "moderate":  YELLOW,
    "minor":     DIM,
}
_SEVERITY_LABELS = {
    "critical":  "Critical",
    "dangerous": "Dangerous",
    "moderate":  "Moderate",
    "minor":     "Minor",
}

_VALUE_COLORS = {
    "high":   GREEN,
    "medium": TEAL,
    "low":    DIM,
}
_VALUE_LABELS = {
    "high":   "High Value",
    "medium": "Medium",
    "low":    "Low",
}

# Section toggle options
_SHOW_BOTH        = "Both"
_SHOW_AFFLICTIONS = "Afflictions"
_SHOW_BOONS       = "Boons"


def _load_data() -> dict:
    if not os.path.exists(_DATA_PATH):
        return {}
    try:
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[SanctumPanel] failed to load data: {e}")
        return {}


class SanctumPanel(QWidget):
    def __init__(self):
        super().__init__()
        data = _load_data()
        self._afflictions   = data.get("afflictions", [])
        self._boons         = data.get("boons", [])
        self._how_it_works  = data.get("how_it_works", "")
        self._tips          = data.get("tips", [])
        self._active_section = _SHOW_BOTH
        self._build_ui()
        self._refresh()

    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        header = QLabel(
            f"Sanctum Reference  •  {len(self._afflictions)} afflictions  •  "
            f"{len(self._boons)} boons"
        )
        header.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 13px;")
        layout.addWidget(header)

        if self._how_it_works:
            how_lbl = QLabel(self._how_it_works)
            how_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px;")
            how_lbl.setWordWrap(True)
            layout.addWidget(how_lbl)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search by name, effect, or category…")
        self._search.setStyleSheet(
            "QLineEdit { background: #0f0f23; color: #d4c5a9; border: 1px solid #2a2a4a; "
            "border-radius: 4px; padding: 4px 8px; }"
        )
        self._search.textChanged.connect(self._refresh)
        layout.addWidget(self._search)

        # Section toggle row
        section_row = QHBoxLayout()
        section_row.setSpacing(6)
        sec_lbl = QLabel("Show:")
        sec_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px;")
        section_row.addWidget(sec_lbl)
        self._section_buttons: dict[str, QPushButton] = {}
        for label in (_SHOW_BOTH, _SHOW_AFFLICTIONS, _SHOW_BOONS):
            btn = QPushButton(label)
            btn.setFixedHeight(22)
            btn.setStyleSheet(
                "QPushButton { background: #0f0f23; color: #8a7a65; border: 1px solid #2a2a4a; "
                "border-radius: 3px; padding: 0 8px; font-size: 10px; }"
                "QPushButton:hover { background: #1a1a3a; }"
                "QPushButton[active='true'] { color: #e2b96f; border-color: #e2b96f; }"
            )
            btn.clicked.connect(lambda _, lbl=label: self._on_section_filter(lbl))
            self._section_buttons[label] = btn
            section_row.addWidget(btn)
        section_row.addStretch()
        layout.addLayout(section_row)
        self._set_active_section(_SHOW_BOTH)

        # Legend row
        legend_row = QHBoxLayout()
        legend_row.setSpacing(10)
        for severity, label in _SEVERITY_LABELS.items():
            color = _SEVERITY_COLORS[severity]
            lbl = QLabel(f"● {label}")
            lbl.setStyleSheet(f"color: {color}; font-size: 10px;")
            legend_row.addWidget(lbl)
        legend_row.addStretch()
        layout.addLayout(legend_row)

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

    def _on_section_filter(self, label: str):
        self._set_active_section(label)
        self._refresh()

    def _set_active_section(self, label: str):
        self._active_section = label
        for btn_label, btn in self._section_buttons.items():
            btn.setProperty("active", "true" if btn_label == label else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _refresh(self):
        query = self._search.text().strip().lower()

        def _matches(entry: dict) -> bool:
            if not query:
                return True
            return (
                query in entry.get("name", "").lower()
                or query in entry.get("effect", "").lower()
                or query in entry.get("category", "").lower()
                or query in entry.get("notes", "").lower()
            )

        show_afflictions = self._active_section in (_SHOW_BOTH, _SHOW_AFFLICTIONS)
        show_boons       = self._active_section in (_SHOW_BOTH, _SHOW_BOONS)

        filtered_afflictions = [a for a in self._afflictions if _matches(a)] if show_afflictions else []
        filtered_boons       = [b for b in self._boons       if _matches(b)] if show_boons       else []

        self._render(filtered_afflictions, filtered_boons)

    def _render(self, afflictions: list[dict], boons: list[dict]):
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        insert_idx = 0

        if not afflictions and not boons:
            empty = QLabel("No matching entries.")
            empty.setStyleSheet(f"color: {DIM}; font-size: 11px;")
            self._list_layout.insertWidget(0, empty)
            return

        if afflictions:
            section_hdr = QLabel(f"⚠ Afflictions ({len(afflictions)})")
            section_hdr.setStyleSheet(f"color: {RED}; font-size: 11px; font-weight: bold;")
            self._list_layout.insertWidget(insert_idx, section_hdr)
            insert_idx += 1
            for entry in afflictions:
                card = self._make_affliction_card(entry)
                self._list_layout.insertWidget(insert_idx, card)
                insert_idx += 1

        if boons:
            section_hdr = QLabel(f"✦ Boons ({len(boons)})")
            section_hdr.setStyleSheet(f"color: {GREEN}; font-size: 11px; font-weight: bold; margin-top: 4px;")
            self._list_layout.insertWidget(insert_idx, section_hdr)
            insert_idx += 1
            for entry in boons:
                card = self._make_boon_card(entry)
                self._list_layout.insertWidget(insert_idx, card)
                insert_idx += 1

    def _make_affliction_card(self, entry: dict) -> QWidget:
        severity = entry.get("severity", "minor")
        border_color = _SEVERITY_COLORS.get(severity, DIM)

        card = QWidget()
        card.setStyleSheet(f"background: #0f0f23; border-left: 3px solid {border_color}; border-radius: 2px;")
        vl = QVBoxLayout(card)
        vl.setContentsMargins(8, 6, 8, 6)
        vl.setSpacing(3)

        top_row = QHBoxLayout()
        name_lbl = QLabel(entry.get("name", ""))
        name_lbl.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 11px;")
        top_row.addWidget(name_lbl, 1)

        badge_label = _SEVERITY_LABELS.get(severity, severity.title())
        badge = QLabel(badge_label)
        badge.setStyleSheet(
            f"color: {border_color}; font-size: 9px; background: #1a1a3a; "
            "border-radius: 2px; padding: 1px 4px;"
        )
        badge.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top_row.addWidget(badge)
        vl.addLayout(top_row)

        effect_lbl = QLabel(entry.get("effect", ""))
        effect_lbl.setStyleSheet(f"color: {TEXT}; font-size: 11px;")
        effect_lbl.setWordWrap(True)
        vl.addWidget(effect_lbl)

        category = entry.get("category", "")
        if category:
            cat_lbl = QLabel(category)
            cat_lbl.setStyleSheet(f"color: {DIM}; font-size: 9px;")
            vl.addWidget(cat_lbl)

        notes = entry.get("notes", "")
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

    def _make_boon_card(self, entry: dict) -> QWidget:
        value = entry.get("value", "low")
        border_color = _VALUE_COLORS.get(value, DIM)

        card = QWidget()
        card.setStyleSheet(f"background: #0f0f23; border-left: 3px solid {border_color}; border-radius: 2px;")
        vl = QVBoxLayout(card)
        vl.setContentsMargins(8, 6, 8, 6)
        vl.setSpacing(3)

        top_row = QHBoxLayout()
        name_lbl = QLabel(entry.get("name", ""))
        name_lbl.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 11px;")
        top_row.addWidget(name_lbl, 1)

        badge_label = _VALUE_LABELS.get(value, value.title())
        badge = QLabel(badge_label)
        badge.setStyleSheet(
            f"color: {border_color}; font-size: 9px; background: #1a1a3a; "
            "border-radius: 2px; padding: 1px 4px;"
        )
        badge.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top_row.addWidget(badge)
        vl.addLayout(top_row)

        effect_lbl = QLabel(entry.get("effect", ""))
        effect_lbl.setStyleSheet(f"color: {TEXT}; font-size: 11px;")
        effect_lbl.setWordWrap(True)
        vl.addWidget(effect_lbl)

        category = entry.get("category", "")
        if category:
            cat_lbl = QLabel(category)
            cat_lbl.setStyleSheet(f"color: {DIM}; font-size: 9px;")
            vl.addWidget(cat_lbl)

        notes = entry.get("notes", "")
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
