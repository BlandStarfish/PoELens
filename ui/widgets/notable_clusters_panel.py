"""
Passive Tree Notable Cluster Reference panel.

Reference for notable passive clusters and keystones worth pathing to,
organized by build type. Shows effect, recommended builds, point cost,
and notes on synergies or tradeoffs.

Data source: data/notable_clusters.json
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
    os.path.dirname(__file__), "..", "..", "data", "notable_clusters.json"
)

_CATEGORY_COLORS = {
    "Offense":    ORANGE,
    "Defense":    BLUE,
    "Utility":    TEAL,
    "Keystones":  GOLD,
}

_ALL = "All"


def _load_data() -> dict:
    if not os.path.exists(_DATA_PATH):
        return {}
    try:
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[NotableClustersPanel] failed to load data: {e}")
        return {}


class NotableClustersPanel(QWidget):
    def __init__(self):
        super().__init__()
        data = _load_data()
        self._clusters     = data.get("clusters", [])
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

        header = QLabel(f"Passive Tree Notable Clusters  •  {len(self._clusters)} clusters")
        header.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 13px;")
        layout.addWidget(header)

        if self._how_it_works:
            how_lbl = QLabel(self._how_it_works)
            how_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px;")
            how_lbl.setWordWrap(True)
            layout.addWidget(how_lbl)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search by cluster name, effect, or build type…")
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

    def _matches(self, cluster: dict, query: str) -> bool:
        if not query:
            return True
        searchable = " ".join([
            cluster.get("name", ""),
            cluster.get("category", ""),
            cluster.get("location", ""),
            " ".join(cluster.get("notables", [])),
            cluster.get("effect", ""),
            " ".join(cluster.get("build_types", [])),
            cluster.get("point_cost", ""),
            cluster.get("notes", ""),
        ]).lower()
        return query in searchable

    def _refresh(self):
        query = self._search.text().strip().lower()
        pool = self._clusters
        if self._active_cat != _ALL:
            pool = [c for c in pool if c.get("category") == self._active_cat]
        filtered = [c for c in pool if self._matches(c, query)]
        self._render(filtered)

    def _render(self, clusters: list[dict]):
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not clusters:
            empty = QLabel("No matching clusters.")
            empty.setStyleSheet(f"color: {DIM}; font-size: 11px;")
            self._list_layout.insertWidget(0, empty)
            return

        for i, cluster in enumerate(clusters):
            card = self._make_card(cluster)
            self._list_layout.insertWidget(i, card)

    def _make_card(self, cluster: dict) -> QFrame:
        cat   = cluster.get("category", "")
        color = _CATEGORY_COLORS.get(cat, ACCENT)

        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: #0f0f1e; border: 1px solid #2a2a4a; "
            f"border-left: 3px solid {color}; border-radius: 4px; padding: 4px; }}"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(6, 4, 6, 4)
        cl.setSpacing(3)

        # Header: cluster name + category badge
        header_row = QHBoxLayout()
        name_lbl = QLabel(cluster.get("name", ""))
        name_lbl.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 12px;")
        header_row.addWidget(name_lbl)
        header_row.addStretch()
        if cat:
            cat_badge = QLabel(f"[{cat}]")
            cat_badge.setStyleSheet(f"color: {color}; font-size: 10px;")
            header_row.addWidget(cat_badge)
        cl.addLayout(header_row)

        # Location
        location = cluster.get("location", "")
        if location:
            loc_lbl = QLabel(f"Location: {location}")
            loc_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px;")
            cl.addWidget(loc_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2a2a4a;")
        cl.addWidget(sep)

        # Effect
        effect = cluster.get("effect", "")
        if effect:
            eff_lbl = QLabel(effect)
            eff_lbl.setStyleSheet(f"color: {TEXT}; font-size: 10px;")
            eff_lbl.setWordWrap(True)
            cl.addWidget(eff_lbl)

        # Build types
        build_types = cluster.get("build_types", [])
        if build_types:
            bt_lbl = QLabel("Builds: " + ", ".join(build_types))
            bt_lbl.setStyleSheet(f"color: {TEAL}; font-size: 10px;")
            bt_lbl.setWordWrap(True)
            cl.addWidget(bt_lbl)

        # Point cost
        cost = cluster.get("point_cost", "")
        if cost:
            cost_lbl = QLabel(f"Cost: {cost}")
            cost_lbl.setStyleSheet(f"color: {ORANGE}; font-size: 10px;")
            cl.addWidget(cost_lbl)

        # Notes
        notes = cluster.get("notes", "")
        if notes:
            notes_lbl = QLabel(notes)
            notes_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px; font-style: italic;")
            notes_lbl.setWordWrap(True)
            cl.addWidget(notes_lbl)

        return card
