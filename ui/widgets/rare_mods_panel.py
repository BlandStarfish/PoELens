"""
Rare Mod Reference panel.

Static reference for Archnemesis-style rare monster modifiers integrated into PoE core.
Shows what each mod does, its danger level, category, and dangerous combinations.

Data source: data/rare_mods.json
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
    os.path.dirname(__file__), "..", "..", "data", "rare_mods.json"
)

_DANGER_COLORS = {
    "extreme":  RED,
    "high":     ORANGE,
    "moderate": YELLOW,
    "low":      GREEN,
}
_DANGER_LABELS = {
    "extreme":  "Extreme",
    "high":     "High",
    "moderate": "Moderate",
    "low":      "Low",
}

# Category colours for filter badges
_CAT_COLORS = {
    "Offense":  RED,
    "Defense":  TEAL,
    "Summons":  ORANGE,
    "Area":     YELLOW,
    "Debuff":   DIM,
    "Misc":     DIM,
}

_DANGER_LEVELS = ["All", "Extreme", "High", "Moderate", "Low"]


def _load_data() -> dict:
    if not os.path.exists(_DATA_PATH):
        return {}
    try:
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[RareModsPanel] failed to load data: {e}")
        return {}


class RareModsPanel(QWidget):
    def __init__(self):
        super().__init__()
        data = _load_data()
        self._all_mods      = data.get("mods", [])
        self._how_it_works  = data.get("how_it_works", "")
        self._tips          = data.get("tips", [])
        self._active_danger: str | None = None
        self._build_ui()
        self._refresh()

    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        header = QLabel(f"Rare Mod Reference  •  {len(self._all_mods)} modifiers")
        header.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 13px;")
        layout.addWidget(header)

        if self._how_it_works:
            how_lbl = QLabel(self._how_it_works)
            how_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px;")
            how_lbl.setWordWrap(True)
            layout.addWidget(how_lbl)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search by mod name, effect, or category…")
        self._search.setStyleSheet(
            "QLineEdit { background: #0f0f23; color: #d4c5a9; border: 1px solid #2a2a4a; "
            "border-radius: 4px; padding: 4px 8px; }"
        )
        self._search.textChanged.connect(self._refresh)
        layout.addWidget(self._search)

        # Danger filter row
        filter_row = QHBoxLayout()
        filter_row.setSpacing(6)
        filt_lbl = QLabel("Danger:")
        filt_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px;")
        filter_row.addWidget(filt_lbl)
        self._filter_buttons: dict[str, QPushButton] = {}
        for level in _DANGER_LEVELS:
            color = _DANGER_COLORS.get(level.lower(), ACCENT)
            btn = QPushButton(level)
            btn.setFixedHeight(22)
            btn.setStyleSheet(
                f"QPushButton {{ background: #0f0f23; color: {DIM}; border: 1px solid #2a2a4a; "
                f"border-radius: 3px; padding: 0 8px; font-size: 10px; }}"
                f"QPushButton:hover {{ background: #1a1a3a; }}"
                f"QPushButton[active='true'] {{ color: {color}; border-color: {color}; }}"
            )
            btn.clicked.connect(lambda _, lv=level: self._on_danger_filter(lv))
            self._filter_buttons[level] = btn
            filter_row.addWidget(btn)
        filter_row.addStretch()
        layout.addLayout(filter_row)
        self._set_active_danger("All")

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

    def _on_danger_filter(self, level: str):
        self._set_active_danger(level)
        self._refresh()

    def _set_active_danger(self, level: str):
        self._active_danger = None if level == "All" else level.lower()
        for btn_label, btn in self._filter_buttons.items():
            btn.setProperty("active", "true" if btn_label == level else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _refresh(self):
        query = self._search.text().strip().lower()
        pool  = self._all_mods

        if self._active_danger:
            pool = [m for m in pool if m.get("danger") == self._active_danger]

        if query:
            pool = [
                m for m in pool
                if query in m.get("name", "").lower()
                or query in m.get("effect", "").lower()
                or query in m.get("category", "").lower()
                or query in m.get("notes", "").lower()
                or query in (m.get("combo_warning") or "").lower()
            ]

        self._render(pool)

    def _render(self, mods: list[dict]):
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not mods:
            empty = QLabel("No matching modifiers.")
            empty.setStyleSheet(f"color: {DIM}; font-size: 11px;")
            self._list_layout.insertWidget(0, empty)
            return

        for i, mod in enumerate(mods):
            card = self._make_card(mod)
            self._list_layout.insertWidget(i, card)

    def _make_card(self, mod: dict) -> QWidget:
        danger       = mod.get("danger", "low")
        border_color = _DANGER_COLORS.get(danger, DIM)
        category     = mod.get("category", "")
        cat_color    = _CAT_COLORS.get(category, DIM)

        card = QWidget()
        card.setStyleSheet(
            f"background: #0f0f23; border-left: 3px solid {border_color}; border-radius: 2px;"
        )
        vl = QVBoxLayout(card)
        vl.setContentsMargins(8, 6, 8, 6)
        vl.setSpacing(3)

        # Name + danger + category badges
        top_row = QHBoxLayout()
        name_lbl = QLabel(mod.get("name", ""))
        name_lbl.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 12px;")
        top_row.addWidget(name_lbl, 1)

        danger_label = _DANGER_LABELS.get(danger, danger.title())
        danger_badge = QLabel(danger_label)
        danger_badge.setStyleSheet(
            f"color: {border_color}; font-size: 9px; background: #1a1a3a; "
            "border-radius: 2px; padding: 1px 4px;"
        )
        danger_badge.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top_row.addWidget(danger_badge)

        if category:
            cat_badge = QLabel(category)
            cat_badge.setStyleSheet(
                f"color: {cat_color}; font-size: 9px; background: #1a1a3a; "
                "border-radius: 2px; padding: 1px 4px; margin-left: 4px;"
            )
            cat_badge.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            top_row.addWidget(cat_badge)

        vl.addLayout(top_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #1a1a3a;")
        vl.addWidget(sep)

        # Effect
        effect_lbl = QLabel(mod.get("effect", ""))
        effect_lbl.setStyleSheet(f"color: {TEXT}; font-size: 11px;")
        effect_lbl.setWordWrap(True)
        vl.addWidget(effect_lbl)

        # Combo warning
        combo = mod.get("combo_warning")
        if combo:
            combo_lbl = QLabel(
                f"<b style='color:{RED}'>Combo danger:</b> "
                f"<span style='color:{ORANGE}'>{combo}</span>"
            )
            combo_lbl.setTextFormat(Qt.TextFormat.RichText)
            combo_lbl.setWordWrap(True)
            combo_lbl.setStyleSheet("font-size: 10px;")
            vl.addWidget(combo_lbl)

        # Notes
        notes = mod.get("notes", "")
        if notes:
            notes_lbl = QLabel(notes)
            notes_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px; font-style: italic;")
            notes_lbl.setWordWrap(True)
            vl.addWidget(notes_lbl)

        return card
