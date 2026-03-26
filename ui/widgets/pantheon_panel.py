"""
Pantheon Powers Reference panel.

Static reference for all Major and Minor Pantheon gods — base powers,
upgrade requirements (capture target + map), and defensive use cases.

Data source: data/pantheon_powers.json
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

_DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "pantheon_powers.json"
)

_SHOW_MAJOR = "Major"
_SHOW_MINOR = "Minor"
_SHOW_BOTH  = "Both"


def _load_data() -> dict:
    if not os.path.exists(_DATA_PATH):
        return {}
    try:
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[PantheonPanel] failed to load data: {e}")
        return {}


class PantheonPanel(QWidget):
    def __init__(self):
        super().__init__()
        data = _load_data()
        self._major_gods    = data.get("major_gods", [])
        self._minor_gods    = data.get("minor_gods", [])
        self._how_it_works  = data.get("how_it_works", "")
        self._vessel_note   = data.get("divine_vessel_note", "")
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
            f"Pantheon Powers  •  {len(self._major_gods)} major gods  •  "
            f"{len(self._minor_gods)} minor gods"
        )
        header.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 13px;")
        layout.addWidget(header)

        if self._how_it_works:
            how_lbl = QLabel(self._how_it_works)
            how_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px;")
            how_lbl.setWordWrap(True)
            layout.addWidget(how_lbl)

        if self._vessel_note:
            vessel_lbl = QLabel(self._vessel_note)
            vessel_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px; font-style: italic;")
            vessel_lbl.setWordWrap(True)
            layout.addWidget(vessel_lbl)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search by god name, power, defensive use, or capture target…")
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
        for label in (_SHOW_BOTH, _SHOW_MAJOR, _SHOW_MINOR):
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

        # Footer swap note
        footer = QLabel(
            "<b style='color:#4ae8c8'>Swap tip:</b> "
            "<span style='color:#8a7a65'>Major + Minor Gods can be swapped freely from any town. "
            "No cost. No cooldown. Swap to counter specific boss mechanics.</span>"
        )
        footer.setTextFormat(Qt.TextFormat.RichText)
        footer.setWordWrap(True)
        footer.setStyleSheet("font-size: 10px;")
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

    def _god_matches(self, god: dict, query: str) -> bool:
        if not query:
            return True
        searchable = " ".join([
            god.get("name", ""),
            god.get("defensive_use", ""),
            god.get("notes", ""),
            god.get("unlock", ""),
            " ".join(god.get("base_powers", [])),
            " ".join(
                u.get("power", "") + " " + u.get("capture_target", "") + " " + u.get("capture_map", "")
                for u in god.get("upgrades", [])
            ),
        ]).lower()
        return query in searchable

    def _refresh(self):
        query = self._search.text().strip().lower()

        show_major = self._active_section in (_SHOW_BOTH, _SHOW_MAJOR)
        show_minor = self._active_section in (_SHOW_BOTH, _SHOW_MINOR)

        major = [g for g in self._major_gods if self._god_matches(g, query)] if show_major else []
        minor = [g for g in self._minor_gods if self._god_matches(g, query)] if show_minor else []

        self._render(major, minor)

    def _render(self, major: list[dict], minor: list[dict]):
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        insert_idx = 0

        if not major and not minor:
            empty = QLabel("No matching gods.")
            empty.setStyleSheet(f"color: {DIM}; font-size: 11px;")
            self._list_layout.insertWidget(0, empty)
            return

        if major:
            section_hdr = QLabel(f"Major Gods ({len(major)})")
            section_hdr.setStyleSheet(f"color: {ACCENT}; font-size: 11px; font-weight: bold;")
            self._list_layout.insertWidget(insert_idx, section_hdr)
            insert_idx += 1
            for god in major:
                card = self._make_card(god, is_major=True)
                self._list_layout.insertWidget(insert_idx, card)
                insert_idx += 1

        if minor:
            section_hdr = QLabel(f"Minor Gods ({len(minor)})")
            section_hdr.setStyleSheet(
                f"color: {TEAL}; font-size: 11px; font-weight: bold; margin-top: 4px;"
            )
            self._list_layout.insertWidget(insert_idx, section_hdr)
            insert_idx += 1
            for god in minor:
                card = self._make_card(god, is_major=False)
                self._list_layout.insertWidget(insert_idx, card)
                insert_idx += 1

    def _make_card(self, god: dict, *, is_major: bool) -> QWidget:
        border_color = ACCENT if is_major else TEAL

        card = QWidget()
        card.setStyleSheet(
            f"background: #0f0f23; border-left: 3px solid {border_color}; border-radius: 2px;"
        )
        vl = QVBoxLayout(card)
        vl.setContentsMargins(8, 6, 8, 6)
        vl.setSpacing(3)

        # Name + major/minor badge
        top_row = QHBoxLayout()
        name_lbl = QLabel(god.get("name", ""))
        name_lbl.setStyleSheet(f"color: {border_color}; font-weight: bold; font-size: 12px;")
        top_row.addWidget(name_lbl, 1)

        rank_badge = QLabel("Major" if is_major else "Minor")
        rank_badge.setStyleSheet(
            f"color: {border_color}; font-size: 9px; background: #1a1a3a; "
            "border-radius: 2px; padding: 1px 4px;"
        )
        rank_badge.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        top_row.addWidget(rank_badge)
        vl.addLayout(top_row)

        # Unlock
        unlock = god.get("unlock", "")
        if unlock:
            unlock_lbl = QLabel(
                f"<b style='color:{DIM}'>Unlock:</b> "
                f"<span style='color:{DIM}'>{unlock}</span>"
            )
            unlock_lbl.setTextFormat(Qt.TextFormat.RichText)
            unlock_lbl.setStyleSheet("font-size: 10px;")
            vl.addWidget(unlock_lbl)

        # Defensive use
        def_use = god.get("defensive_use", "")
        if def_use:
            def_lbl = QLabel(
                f"<b style='color:{YELLOW}'>Defends against:</b> "
                f"<span style='color:{TEXT}'>{def_use}</span>"
            )
            def_lbl.setTextFormat(Qt.TextFormat.RichText)
            def_lbl.setStyleSheet("font-size: 11px;")
            vl.addWidget(def_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #1a1a3a;")
        vl.addWidget(sep)

        # Base powers
        base_powers = god.get("base_powers", [])
        if base_powers:
            for power in base_powers:
                p_lbl = QLabel(f"• {power}")
                p_lbl.setStyleSheet(f"color: {TEXT}; font-size: 11px;")
                p_lbl.setWordWrap(True)
                vl.addWidget(p_lbl)

        # Upgrades
        upgrades = god.get("upgrades", [])
        if upgrades:
            upg_hdr = QLabel("Upgrades (Divine Vessel captures):")
            upg_hdr.setStyleSheet(f"color: {TEAL}; font-size: 10px; margin-top: 3px;")
            vl.addWidget(upg_hdr)
            for upg in upgrades:
                power      = upg.get("power", "")
                target     = upg.get("capture_target", "")
                map_name   = upg.get("capture_map", "")
                upg_lbl = QLabel(
                    f"<span style='color:{GREEN}'>+ {power}</span><br>"
                    f"<span style='color:{DIM}'>  Capture: {target} in {map_name}</span>"
                )
                upg_lbl.setTextFormat(Qt.TextFormat.RichText)
                upg_lbl.setWordWrap(True)
                upg_lbl.setStyleSheet("font-size: 10px;")
                vl.addWidget(upg_lbl)

        # Notes
        notes = god.get("notes", "")
        if notes:
            notes_lbl = QLabel(notes)
            notes_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px; font-style: italic;")
            notes_lbl.setWordWrap(True)
            vl.addWidget(notes_lbl)

        return card
