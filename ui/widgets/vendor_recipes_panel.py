"""
Vendor Recipe Browser panel.

Static reference for important PoE vendor recipes. Searchable by ingredient or result.
Categories: Currency, Quality, Leveling, Unique.

Data source: data/vendor_recipes.json
No API calls — zero latency, always accurate.
"""

import json
import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QScrollArea, QFrame, QPushButton,
)
from PyQt6.QtCore import Qt

ACCENT = "#e2b96f"
TEXT   = "#d4c5a9"
DIM    = "#8a7a65"
GREEN  = "#5cba6e"
TEAL   = "#4ae8c8"
ORANGE = "#e8864a"
PURPLE = "#9a4ae8"

_DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "vendor_recipes.json"
)

# Color per category
_CATEGORY_COLORS = {
    "Currency": ACCENT,
    "Quality":  GREEN,
    "Leveling": TEAL,
    "Unique":   PURPLE,
}

_CATEGORIES = ["Currency", "Quality", "Leveling", "Unique"]


def _load_recipes() -> list[dict]:
    if not os.path.exists(_DATA_PATH):
        return []
    try:
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("recipes", [])
    except Exception as e:
        print(f"[VendorRecipesPanel] failed to load recipes: {e}")
        return []


class VendorRecipesPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._all_recipes = _load_recipes()
        self._active_category: str | None = None
        self._build_ui()
        self._render_recipes(self._all_recipes)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        header = QLabel(f"Vendor Recipes  •  {len(self._all_recipes)} recipes")
        header.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 13px;")
        layout.addWidget(header)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search by name, ingredient, or result…")
        self._search.setStyleSheet(
            "QLineEdit { background: #0f0f23; color: #d4c5a9; border: 1px solid #2a2a4a; "
            "border-radius: 4px; padding: 4px 8px; }"
        )
        self._search.textChanged.connect(self._on_search)
        layout.addWidget(self._search)

        # Category filter buttons
        filter_row = QHBoxLayout()
        filter_row.setSpacing(6)
        filter_lbl = QLabel("Category:")
        filter_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px;")
        filter_row.addWidget(filter_lbl)
        self._filter_buttons: dict[str, QPushButton] = {}
        for label in ["All"] + _CATEGORIES:
            btn = QPushButton(label)
            btn.setFixedHeight(22)
            color = _CATEGORY_COLORS.get(label, ACCENT)
            btn.setStyleSheet(
                f"QPushButton {{ background: #0f0f23; color: {DIM}; border: 1px solid #2a2a4a; "
                f"border-radius: 3px; padding: 0 8px; font-size: 10px; }}"
                f"QPushButton:hover {{ background: #1a1a3a; }}"
                f"QPushButton[active='true'] {{ color: {color}; border-color: {color}; }}"
            )
            btn.clicked.connect(lambda _, lbl=label: self._on_category_filter(lbl))
            self._filter_buttons[label] = btn
            filter_row.addWidget(btn)
        filter_row.addStretch()
        layout.addLayout(filter_row)
        self._set_active_filter("All")

        # Category color legend
        legend_row = QHBoxLayout()
        legend_row.setSpacing(10)
        for cat, color in _CATEGORY_COLORS.items():
            lbl = QLabel(f"● {cat}")
            lbl.setStyleSheet(f"color: {color}; font-size: 10px;")
            legend_row.addWidget(lbl)
        legend_row.addStretch()
        layout.addLayout(legend_row)

        # Scrollable recipe list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        self._recipe_container = QWidget()
        self._recipe_layout    = QVBoxLayout(self._recipe_container)
        self._recipe_layout.setContentsMargins(0, 0, 0, 0)
        self._recipe_layout.setSpacing(4)
        self._recipe_layout.addStretch()
        scroll.setWidget(self._recipe_container)
        layout.addWidget(scroll)

        note = QLabel(
            "Vendor by selling items directly to any NPC vendor. "
            "All vendor recipes work in acts and endgame."
        )
        note.setStyleSheet(f"color: {DIM}; font-size: 10px;")
        note.setWordWrap(True)
        layout.addWidget(note)

    def _on_category_filter(self, label: str):
        self._set_active_filter(label)
        self._on_search(self._search.text())

    def _set_active_filter(self, label: str):
        self._active_category = None if label == "All" else label
        for btn_label, btn in self._filter_buttons.items():
            btn.setProperty("active", "true" if btn_label == label else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _on_search(self, text: str):
        query = text.strip().lower()
        pool = self._all_recipes

        if self._active_category:
            pool = [r for r in pool if r.get("category") == self._active_category]

        if not query:
            self._render_recipes(pool)
            return

        filtered = [
            r for r in pool
            if query in r.get("name", "").lower()
            or query in r.get("ingredients", "").lower()
            or query in r.get("result", "").lower()
            or query in r.get("notes", "").lower()
            or query in r.get("category", "").lower()
        ]
        self._render_recipes(filtered)

    def _render_recipes(self, recipes: list[dict]):
        while self._recipe_layout.count() > 1:
            item = self._recipe_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not recipes:
            empty = QLabel("No matching recipes.")
            empty.setStyleSheet(f"color: {DIM}; font-size: 11px;")
            self._recipe_layout.insertWidget(0, empty)
            return

        for i, recipe in enumerate(recipes):
            card = self._make_recipe_card(recipe)
            self._recipe_layout.insertWidget(i, card)

    def _make_recipe_card(self, recipe: dict) -> QWidget:
        category     = recipe.get("category", "")
        accent_color = _CATEGORY_COLORS.get(category, DIM)

        card = QWidget()
        card.setStyleSheet(
            f"background: #0f0f23; border-left: 3px solid {accent_color}; border-radius: 2px;"
        )
        vl = QVBoxLayout(card)
        vl.setContentsMargins(8, 6, 8, 6)
        vl.setSpacing(4)

        # Name + category badge
        top_row = QHBoxLayout()
        top_row.setSpacing(6)
        name_lbl = QLabel(recipe.get("name", ""))
        name_lbl.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 11px;")
        name_lbl.setWordWrap(True)
        top_row.addWidget(name_lbl, 1)

        badge = QLabel(category)
        badge.setStyleSheet(
            f"color: {accent_color}; font-size: 9px; background: #1a1a3a; "
            f"border-radius: 2px; padding: 1px 4px;"
        )
        top_row.addWidget(badge)
        vl.addLayout(top_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #1a1a3a;")
        vl.addWidget(sep)

        # Ingredients → Result
        ing_lbl = QLabel(f"<b style='color:{DIM}'>In:</b> {recipe.get('ingredients', '')}")
        ing_lbl.setStyleSheet(f"color: {TEXT}; font-size: 10px;")
        ing_lbl.setWordWrap(True)
        ing_lbl.setTextFormat(Qt.TextFormat.RichText)
        vl.addWidget(ing_lbl)

        result_lbl = QLabel(f"<b style='color:{accent_color}'>Out:</b> {recipe.get('result', '')}")
        result_lbl.setStyleSheet(f"color: {TEXT}; font-size: 10px;")
        result_lbl.setWordWrap(True)
        result_lbl.setTextFormat(Qt.TextFormat.RichText)
        vl.addWidget(result_lbl)

        notes = recipe.get("notes", "")
        if notes:
            notes_lbl = QLabel(notes)
            notes_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px; font-style: italic;")
            notes_lbl.setWordWrap(True)
            vl.addWidget(notes_lbl)

        return card
