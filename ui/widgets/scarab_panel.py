"""
Scarab Browser panel.

Static reference for all PoE scarab types and their effects per tier.
Searchable by mechanic name or effect. Grouped by mechanic with tier rows.

Data source: data/scarabs.json
No API calls — zero latency, always accurate.
"""

import json
import os
from collections import defaultdict

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QScrollArea, QPushButton,
)

ACCENT = "#e2b96f"
TEXT   = "#d4c5a9"
DIM    = "#8a7a65"
GREEN  = "#5cba6e"
TEAL   = "#4ae8c8"
ORANGE = "#e8864a"
RED    = "#e05050"

_DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "scarabs.json"
)

# Color per scarab tier
_TIER_COLORS = {
    "Rusted":   DIM,
    "Polished": TEAL,
    "Gilded":   ACCENT,
    "Winged":   ORANGE,
}

_TIERS = ["Rusted", "Polished", "Gilded", "Winged"]


def _load_scarabs() -> list[dict]:
    if not os.path.exists(_DATA_PATH):
        return []
    try:
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("scarabs", [])
    except Exception as e:
        print(f"[ScarabPanel] failed to load scarabs: {e}")
        return []


def _group_by_mechanic(scarabs: list[dict]) -> dict[str, list[dict]]:
    """Group scarab entries by mechanic, preserving tier order within each mechanic."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for s in scarabs:
        groups[s.get("mechanic", "Unknown")].append(s)
    # Sort each group by tier order
    tier_order = {t: i for i, t in enumerate(_TIERS)}
    for mechanic in groups:
        groups[mechanic].sort(key=lambda s: tier_order.get(s.get("tier", ""), 99))
    return dict(sorted(groups.items()))


class ScarabPanel(QWidget):
    def __init__(self):
        super().__init__()
        self._all_scarabs = _load_scarabs()
        self._active_tier: str | None = None
        self._build_ui()
        self._render_scarabs(self._all_scarabs)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        mechanic_count = len({s.get("mechanic") for s in self._all_scarabs})
        header = QLabel(f"Scarab Browser  •  {mechanic_count} mechanics  •  {len(self._all_scarabs)} scarabs")
        header.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 13px;")
        layout.addWidget(header)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search by mechanic, effect, or atlas passive…")
        self._search.setStyleSheet(
            "QLineEdit { background: #0f0f23; color: #d4c5a9; border: 1px solid #2a2a4a; "
            "border-radius: 4px; padding: 4px 8px; }"
        )
        self._search.textChanged.connect(self._on_search)
        layout.addWidget(self._search)

        # Tier filter buttons
        filter_row = QHBoxLayout()
        filter_row.setSpacing(6)
        filter_lbl = QLabel("Tier:")
        filter_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px;")
        filter_row.addWidget(filter_lbl)
        self._filter_buttons: dict[str, QPushButton] = {}
        for label in ["All"] + _TIERS:
            btn = QPushButton(label)
            btn.setFixedHeight(22)
            color = _TIER_COLORS.get(label, ACCENT)
            btn.setStyleSheet(
                f"QPushButton {{ background: #0f0f23; color: {DIM}; border: 1px solid #2a2a4a; "
                f"border-radius: 3px; padding: 0 8px; font-size: 10px; }}"
                f"QPushButton:hover {{ background: #1a1a3a; }}"
                f"QPushButton[active='true'] {{ color: {color}; border-color: {color}; }}"
            )
            btn.clicked.connect(lambda _, lbl=label: self._on_tier_filter(lbl))
            self._filter_buttons[label] = btn
            filter_row.addWidget(btn)
        filter_row.addStretch()
        layout.addLayout(filter_row)
        self._set_active_filter("All")

        # Tier color legend
        legend_row = QHBoxLayout()
        legend_row.setSpacing(10)
        for tier, color in _TIER_COLORS.items():
            lbl = QLabel(f"● {tier}")
            lbl.setStyleSheet(f"color: {color}; font-size: 10px;")
            legend_row.addWidget(lbl)
        legend_row.addStretch()
        layout.addLayout(legend_row)

        # Scrollable scarab list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        self._scarab_container = QWidget()
        self._scarab_layout    = QVBoxLayout(self._scarab_container)
        self._scarab_layout.setContentsMargins(0, 0, 0, 0)
        self._scarab_layout.setSpacing(6)
        self._scarab_layout.addStretch()
        scroll.setWidget(self._scarab_container)
        layout.addWidget(scroll)

        note = QLabel(
            "Tiers: Rusted < Polished < Gilded < Winged. "
            "Use Atlas passive nodes to amplify the matching mechanic."
        )
        note.setStyleSheet(f"color: {DIM}; font-size: 10px;")
        note.setWordWrap(True)
        layout.addWidget(note)

    def _on_tier_filter(self, label: str):
        self._set_active_filter(label)
        self._on_search(self._search.text())

    def _set_active_filter(self, label: str):
        self._active_tier = None if label == "All" else label
        for btn_label, btn in self._filter_buttons.items():
            btn.setProperty("active", "true" if btn_label == label else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _on_search(self, text: str):
        query = text.strip().lower()
        pool = self._all_scarabs

        if self._active_tier:
            pool = [s for s in pool if s.get("tier") == self._active_tier]

        if not query:
            self._render_scarabs(pool)
            return

        filtered = [
            s for s in pool
            if query in s.get("mechanic", "").lower()
            or query in s.get("effect", "").lower()
            or query in s.get("atlas_passive", "").lower()
            or query in s.get("tier", "").lower()
            or query in s.get("name", "").lower()
        ]
        self._render_scarabs(filtered)

    def _render_scarabs(self, scarabs: list[dict]):
        while self._scarab_layout.count() > 1:
            item = self._scarab_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not scarabs:
            empty = QLabel("No matching scarabs.")
            empty.setStyleSheet(f"color: {DIM}; font-size: 11px;")
            self._scarab_layout.insertWidget(0, empty)
            return

        groups = _group_by_mechanic(scarabs)
        for i, (mechanic, entries) in enumerate(groups.items()):
            group_widget = self._make_mechanic_group(mechanic, entries)
            self._scarab_layout.insertWidget(i, group_widget)

    def _make_mechanic_group(self, mechanic: str, entries: list[dict]) -> QWidget:
        group = QWidget()
        group.setStyleSheet("background: #0f0f23; border-radius: 4px;")
        vl = QVBoxLayout(group)
        vl.setContentsMargins(8, 6, 8, 6)
        vl.setSpacing(3)

        # Mechanic header
        header = QLabel(mechanic)
        header.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 11px;")
        vl.addWidget(header)

        # Atlas passive (from first entry — same for all tiers of a mechanic)
        atlas = entries[0].get("atlas_passive", "") if entries else ""
        if atlas:
            atlas_lbl = QLabel(f"Atlas: {atlas}")
            atlas_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px; font-style: italic;")
            atlas_lbl.setWordWrap(True)
            vl.addWidget(atlas_lbl)

        # One row per tier
        for entry in entries:
            tier  = entry.get("tier", "")
            color = _TIER_COLORS.get(tier, DIM)
            effect = entry.get("effect", "")
            row_lbl = QLabel(f"<b style='color:{color}'>{tier}:</b> {effect}")
            row_lbl.setStyleSheet(f"color: {TEXT}; font-size: 10px;")
            row_lbl.setWordWrap(True)
            from PyQt6.QtCore import Qt
            row_lbl.setTextFormat(Qt.TextFormat.RichText)
            vl.addWidget(row_lbl)

        return group
