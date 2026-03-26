"""
Essence Reference panel.

Static reference for all 20 Essence types with stat focus, crafting use,
best slots, and Delirium Essence embed-gem details.

Data source: data/essences.json
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
    os.path.dirname(__file__), "..", "..", "data", "essences.json"
)

# Stat category colours
_CAT_COLORS = {
    "Life":      RED,
    "Physical":  ORANGE,
    "Cold":      TEAL,
    "Fire":      "#e84a4a",
    "Lightning": YELLOW,
    "Chaos":     PURPLE,
    "Utility":   GREEN,
    "Defense":   "#4a8ae8",
    "Delirium":  DIM,
}

_TIER_COLOR = {
    "Weeping":   DIM,
    "Wailing":   GREEN,
    "Screaming": YELLOW,
    "Shrieking": ORANGE,
    "Deafening": RED,
}


def _load_data() -> dict:
    if not os.path.exists(_DATA_PATH):
        return {}
    try:
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[EssencePanel] failed to load data: {e}")
        return {}


class EssencePanel(QWidget):
    def __init__(self):
        super().__init__()
        data = _load_data()
        self._all_essences  = data.get("essences", [])
        self._how_it_works  = data.get("how_it_works", "")
        self._tier_note     = data.get("tier_note", "")
        self._special_note  = data.get("special_note", "")
        self._tips          = data.get("tips", [])
        self._categories    = data.get("stat_categories", [])
        self._active_cat: str | None = None
        self._build_ui()
        self._refresh()

    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        header = QLabel(
            f"Essence Reference  •  {len(self._all_essences)} essence types"
        )
        header.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 13px;")
        layout.addWidget(header)

        if self._how_it_works:
            how_lbl = QLabel(self._how_it_works)
            how_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px;")
            how_lbl.setWordWrap(True)
            layout.addWidget(how_lbl)

        if self._tier_note:
            tier_lbl = QLabel(self._tier_note)
            tier_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px; font-style: italic;")
            tier_lbl.setWordWrap(True)
            layout.addWidget(tier_lbl)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search by essence name, stat focus, or crafting use…")
        self._search.setStyleSheet(
            "QLineEdit { background: #0f0f23; color: #d4c5a9; border: 1px solid #2a2a4a; "
            "border-radius: 4px; padding: 4px 8px; }"
        )
        self._search.textChanged.connect(self._refresh)
        layout.addWidget(self._search)

        # Category filter row
        filter_row = QHBoxLayout()
        filter_row.setSpacing(4)
        filt_lbl = QLabel("Type:")
        filt_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px;")
        filter_row.addWidget(filt_lbl)

        self._filter_buttons: dict[str, QPushButton] = {}
        all_cats = ["All"] + self._categories
        for cat in all_cats:
            color = _CAT_COLORS.get(cat, ACCENT)
            btn = QPushButton(cat)
            btn.setFixedHeight(22)
            btn.setStyleSheet(
                f"QPushButton {{ background: #0f0f23; color: {DIM}; border: 1px solid #2a2a4a; "
                f"border-radius: 3px; padding: 0 6px; font-size: 10px; }}"
                f"QPushButton:hover {{ background: #1a1a3a; }}"
                f"QPushButton[active='true'] {{ color: {color}; border-color: {color}; }}"
            )
            btn.clicked.connect(lambda _, c=cat: self._on_cat_filter(c))
            self._filter_buttons[cat] = btn
            filter_row.addWidget(btn)
        filter_row.addStretch()
        layout.addLayout(filter_row)
        self._set_active_cat("All")

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

    def _on_cat_filter(self, cat: str):
        self._set_active_cat(cat)
        self._refresh()

    def _set_active_cat(self, cat: str):
        self._active_cat = None if cat == "All" else cat
        for btn_label, btn in self._filter_buttons.items():
            btn.setProperty("active", "true" if btn_label == cat else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _refresh(self):
        query = self._search.text().strip().lower()
        pool  = self._all_essences

        if self._active_cat:
            pool = [e for e in pool if e.get("stat_category") == self._active_cat]

        if query:
            pool = [
                e for e in pool
                if query in e.get("name", "").lower()
                or query in e.get("stat_focus", "").lower()
                or query in e.get("primary_slots", "").lower()
                or query in e.get("best_for", "").lower()
                or query in e.get("key_mod", "").lower()
                or query in e.get("notes", "").lower()
                or query in e.get("stat_category", "").lower()
            ]

        self._render(pool)

    def _render(self, essences: list[dict]):
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not essences:
            empty = QLabel("No matching essences.")
            empty.setStyleSheet(f"color: {DIM}; font-size: 11px;")
            self._list_layout.insertWidget(0, empty)
            return

        for i, essence in enumerate(essences):
            card = self._make_card(essence)
            self._list_layout.insertWidget(i, card)

    def _make_card(self, essence: dict) -> QWidget:
        cat          = essence.get("stat_category", "Utility")
        border_color = _CAT_COLORS.get(cat, DIM)
        tiers        = essence.get("tiers", [])
        highest_tier = tiers[-1] if tiers else ""
        tier_color   = _TIER_COLOR.get(highest_tier, DIM)

        card = QWidget()
        card.setStyleSheet(
            f"background: #0f0f23; border-left: 3px solid {border_color}; border-radius: 2px;"
        )
        vl = QVBoxLayout(card)
        vl.setContentsMargins(8, 6, 8, 6)
        vl.setSpacing(3)

        # Name + category + tier range badges
        top_row = QHBoxLayout()
        name_lbl = QLabel(f"Essence of {essence.get('name', '')}")
        name_lbl.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 12px;")
        top_row.addWidget(name_lbl, 1)

        cat_badge = QLabel(cat)
        cat_badge.setStyleSheet(
            f"color: {border_color}; font-size: 9px; background: #1a1a3a; "
            "border-radius: 2px; padding: 1px 4px;"
        )
        cat_badge.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top_row.addWidget(cat_badge)

        if tiers:
            tier_range = f"{tiers[0]}–{tiers[-1]}" if len(tiers) > 1 else tiers[0]
            tier_badge = QLabel(tier_range)
            tier_badge.setStyleSheet(
                f"color: {tier_color}; font-size: 9px; background: #1a1a3a; "
                "border-radius: 2px; padding: 1px 4px; margin-left: 4px;"
            )
            tier_badge.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            top_row.addWidget(tier_badge)

        vl.addLayout(top_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #1a1a3a;")
        vl.addWidget(sep)

        # Stat focus
        stat_focus = essence.get("stat_focus", "")
        if stat_focus:
            stat_lbl = QLabel(
                f"<b style='color:{border_color}'>Stat:</b> "
                f"<span style='color:{TEXT}'>{stat_focus}</span>"
            )
            stat_lbl.setTextFormat(Qt.TextFormat.RichText)
            stat_lbl.setStyleSheet("font-size: 11px;")
            vl.addWidget(stat_lbl)

        # Key mod
        key_mod = essence.get("key_mod", "")
        if key_mod:
            mod_lbl = QLabel(
                f"<b style='color:{TEAL}'>Mod:</b> "
                f"<span style='color:{DIM}'>{key_mod}</span>"
            )
            mod_lbl.setTextFormat(Qt.TextFormat.RichText)
            mod_lbl.setWordWrap(True)
            mod_lbl.setStyleSheet("font-size: 10px;")
            vl.addWidget(mod_lbl)

        # Slots
        slots = essence.get("primary_slots", "")
        if slots:
            slots_lbl = QLabel(
                f"<b style='color:{TEAL}'>Slots:</b> "
                f"<span style='color:{DIM}'>{slots}</span>"
            )
            slots_lbl.setTextFormat(Qt.TextFormat.RichText)
            slots_lbl.setStyleSheet("font-size: 10px;")
            vl.addWidget(slots_lbl)

        # Best for
        best_for = essence.get("best_for", "")
        if best_for:
            best_lbl = QLabel(
                f"<b style='color:{GREEN}'>Best for:</b> "
                f"<span style='color:{TEXT}'>{best_for}</span>"
            )
            best_lbl.setTextFormat(Qt.TextFormat.RichText)
            best_lbl.setWordWrap(True)
            best_lbl.setStyleSheet("font-size: 11px;")
            vl.addWidget(best_lbl)

        # Notes
        notes = essence.get("notes", "")
        if notes:
            notes_lbl = QLabel(notes)
            notes_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px; font-style: italic;")
            notes_lbl.setWordWrap(True)
            vl.addWidget(notes_lbl)

        return card
