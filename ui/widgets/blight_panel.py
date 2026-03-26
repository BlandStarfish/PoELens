"""
Blight Oil Reference panel.

Static reference for all 11 Blight oil tiers and their anointment uses.
Includes key notable anoint recipes and anoint mechanic explanation.

Data source: data/blight_oils.json
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
RED    = "#e05050"
ORANGE = "#e8864a"
YELLOW = "#e8c84a"
GREEN  = "#5cba6e"
TEAL   = "#4ae8c8"

_DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "blight_oils.json"
)

# Rarity colours for oil tier cards
_RARITY_COLORS = {
    "negligible":  DIM,
    "very low":    DIM,
    "low":         GREEN,
    "medium":      TEAL,
    "medium-high": YELLOW,
    "high":        ORANGE,
    "very high":   RED,
}

# Anoint value colours
_VALUE_COLORS = {
    "high":   ACCENT,
    "medium": TEAL,
    "low":    DIM,
}

_SHOW_OILS    = "Oils"
_SHOW_ANOINTS = "Anoints"
_SHOW_BOTH    = "Both"


def _load_data() -> dict:
    if not os.path.exists(_DATA_PATH):
        return {}
    try:
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[BlightPanel] failed to load data: {e}")
        return {}


class BlightPanel(QWidget):
    def __init__(self):
        super().__init__()
        data = _load_data()
        self._oils              = data.get("oils", [])
        self._anoints           = data.get("notable_anoints", [])
        self._how_it_works      = data.get("how_it_works", "")
        self._anoint_rules      = data.get("anoint_rules", {})
        self._tips              = data.get("tips", [])
        self._active_section    = _SHOW_BOTH
        self._build_ui()
        self._refresh()

    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        header = QLabel(
            f"Blight Oil Reference  •  {len(self._oils)} oil tiers  •  "
            f"{len(self._anoints)} notable anoints"
        )
        header.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 13px;")
        layout.addWidget(header)

        if self._how_it_works:
            how_lbl = QLabel(self._how_it_works)
            how_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px;")
            how_lbl.setWordWrap(True)
            layout.addWidget(how_lbl)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search by oil name, anoint name, or effect…")
        self._search.setStyleSheet(
            "QLineEdit { background: #0f0f23; color: #d4c5a9; border: 1px solid #2a2a4a; "
            "border-radius: 4px; padding: 4px 8px; }"
        )
        self._search.textChanged.connect(self._refresh)
        layout.addWidget(self._search)

        # Section toggle
        section_row = QHBoxLayout()
        section_row.setSpacing(6)
        sec_lbl = QLabel("Show:")
        sec_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px;")
        section_row.addWidget(sec_lbl)
        self._section_buttons: dict[str, QPushButton] = {}
        for label in (_SHOW_BOTH, _SHOW_OILS, _SHOW_ANOINTS):
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

        # Anoint rule footer
        rules = self._anoint_rules
        if rules:
            footer_lines = []
            for slot, desc in rules.items():
                footer_lines.append(f"<b style='color:{TEAL}'>{slot.title()}:</b> {desc}")
            footer = QLabel("<br>".join(footer_lines))
            footer.setTextFormat(Qt.TextFormat.RichText)
            footer.setWordWrap(True)
            footer.setStyleSheet(f"color: {DIM}; font-size: 10px;")
            layout.addWidget(footer)

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

        def _oil_matches(oil: dict) -> bool:
            if not query:
                return True
            return (
                query in oil.get("name", "").lower()
                or query in oil.get("notes", "").lower()
                or query in oil.get("color_hint", "").lower()
            )

        def _anoint_matches(anoint: dict) -> bool:
            if not query:
                return True
            return (
                query in anoint.get("name", "").lower()
                or query in anoint.get("effect", "").lower()
                or query in " ".join(anoint.get("oils", [])).lower()
                or query in anoint.get("notes", "").lower()
            )

        show_oils    = self._active_section in (_SHOW_BOTH, _SHOW_OILS)
        show_anoints = self._active_section in (_SHOW_BOTH, _SHOW_ANOINTS)

        filtered_oils    = [o for o in self._oils    if _oil_matches(o)]    if show_oils    else []
        filtered_anoints = [a for a in self._anoints if _anoint_matches(a)] if show_anoints else []

        self._render(filtered_oils, filtered_anoints)

    def _render(self, oils: list[dict], anoints: list[dict]):
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        insert_idx = 0

        if not oils and not anoints:
            empty = QLabel("No matching entries.")
            empty.setStyleSheet(f"color: {DIM}; font-size: 11px;")
            self._list_layout.insertWidget(0, empty)
            return

        if oils:
            section_hdr = QLabel(f"Oil Tiers ({len(oils)})")
            section_hdr.setStyleSheet(f"color: {ACCENT}; font-size: 11px; font-weight: bold;")
            self._list_layout.insertWidget(insert_idx, section_hdr)
            insert_idx += 1
            for oil in oils:
                card = self._make_oil_card(oil)
                self._list_layout.insertWidget(insert_idx, card)
                insert_idx += 1

        if anoints:
            section_hdr = QLabel(f"Notable Anoints ({len(anoints)})")
            section_hdr.setStyleSheet(
                f"color: {TEAL}; font-size: 11px; font-weight: bold; margin-top: 4px;"
            )
            self._list_layout.insertWidget(insert_idx, section_hdr)
            insert_idx += 1
            for anoint in anoints:
                card = self._make_anoint_card(anoint)
                self._list_layout.insertWidget(insert_idx, card)
                insert_idx += 1

    def _make_oil_card(self, oil: dict) -> QWidget:
        market_value = oil.get("market_value", "negligible")
        border_color = _RARITY_COLORS.get(market_value, DIM)

        card = QWidget()
        card.setStyleSheet(
            f"background: #0f0f23; border-left: 3px solid {border_color}; border-radius: 2px;"
        )
        vl = QVBoxLayout(card)
        vl.setContentsMargins(8, 5, 8, 5)
        vl.setSpacing(2)

        top_row = QHBoxLayout()
        tier_badge = QLabel(f"T{oil.get('tier', '?')}")
        tier_badge.setStyleSheet(
            f"color: {DIM}; font-size: 9px; background: #1a1a3a; "
            "border-radius: 2px; padding: 1px 4px;"
        )
        top_row.addWidget(tier_badge)

        name_lbl = QLabel(oil.get("name", ""))
        name_lbl.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 11px;")
        top_row.addWidget(name_lbl)

        color_lbl = QLabel(oil.get("color_hint", ""))
        color_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px;")
        top_row.addWidget(color_lbl)
        top_row.addStretch()

        rarity_lbl = QLabel(oil.get("rarity", ""))
        rarity_lbl.setStyleSheet(f"color: {border_color}; font-size: 9px;")
        rarity_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top_row.addWidget(rarity_lbl)
        vl.addLayout(top_row)

        notes = oil.get("notes", "")
        if notes:
            notes_lbl = QLabel(notes)
            notes_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px;")
            notes_lbl.setWordWrap(True)
            vl.addWidget(notes_lbl)

        return card

    def _make_anoint_card(self, anoint: dict) -> QWidget:
        value        = anoint.get("value", "low")
        border_color = _VALUE_COLORS.get(value, DIM)

        card = QWidget()
        card.setStyleSheet(
            f"background: #0f0f23; border-left: 3px solid {border_color}; border-radius: 2px;"
        )
        vl = QVBoxLayout(card)
        vl.setContentsMargins(8, 6, 8, 6)
        vl.setSpacing(3)

        # Name + value badge
        top_row = QHBoxLayout()
        name_lbl = QLabel(anoint.get("name", ""))
        name_lbl.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 11px;")
        top_row.addWidget(name_lbl, 1)

        value_badge = QLabel(value.title())
        value_badge.setStyleSheet(
            f"color: {border_color}; font-size: 9px; background: #1a1a3a; "
            "border-radius: 2px; padding: 1px 4px;"
        )
        value_badge.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top_row.addWidget(value_badge)
        vl.addLayout(top_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #1a1a3a;")
        vl.addWidget(sep)

        # Effect
        effect_lbl = QLabel(anoint.get("effect", ""))
        effect_lbl.setStyleSheet(f"color: {TEXT}; font-size: 11px;")
        effect_lbl.setWordWrap(True)
        vl.addWidget(effect_lbl)

        # Oil combination
        oils = anoint.get("oils", [])
        if oils:
            oils_lbl = QLabel(
                f"<b style='color:{TEAL}'>Oils:</b> "
                f"<span style='color:{ACCENT}'>{' + '.join(oils)}</span>"
            )
            oils_lbl.setTextFormat(Qt.TextFormat.RichText)
            oils_lbl.setStyleSheet("font-size: 10px;")
            vl.addWidget(oils_lbl)

        # Notes
        notes = anoint.get("notes", "")
        if notes:
            notes_lbl = QLabel(notes)
            notes_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px; font-style: italic;")
            notes_lbl.setWordWrap(True)
            vl.addWidget(notes_lbl)

        return card
