"""
Labyrinth completion tracker panel.

Shows completion status for Normal / Cruel / Merciless / Eternal lab.
Manual toggle per difficulty. Resets for new characters via Reset button.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QMessageBox,
)
from PyQt6.QtCore import Qt

from modules.lab_tracker import LabTracker, DIFFICULTIES, POINTS_PER_LAB

ACCENT = "#e2b96f"
TEXT   = "#d4c5a9"
DIM    = "#8a7a65"
GREEN  = "#5cba6e"

# Sub-label shown under each difficulty name
_DIFF_SUBLABELS = {
    "Normal":    "Act 3  •  2 ascendancy points",
    "Cruel":     "Act 6  •  2 ascendancy points",
    "Merciless": "Act 8  •  2 ascendancy points",
    "Eternal":   "Act 10 / Aspirant  •  2 ascendancy points",
}


class LabPanel(QWidget):
    def __init__(self, lab_tracker: LabTracker):
        super().__init__()
        self._tracker = lab_tracker
        self._tracker.on_update(self._refresh)
        self._row_widgets: dict[str, dict] = {}
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        # Header + points summary
        header_row = QHBoxLayout()
        header = QLabel("Labyrinth Tracker")
        header.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 13px;")
        header_row.addWidget(header)
        header_row.addStretch()
        self._points_lbl = QLabel("")
        self._points_lbl.setStyleSheet(f"color: {DIM}; font-size: 11px;")
        header_row.addWidget(self._points_lbl)
        layout.addLayout(header_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2a2a4a;")
        layout.addWidget(sep)

        # One row per difficulty
        for diff in DIFFICULTIES:
            row_widget, widgets = self._make_difficulty_row(diff)
            self._row_widgets[diff] = widgets
            layout.addWidget(row_widget)

        layout.addStretch()

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("color: #2a2a4a;")
        layout.addWidget(sep2)

        # Reset button
        reset_row = QHBoxLayout()
        reset_row.addStretch()
        reset_btn = QPushButton("Reset (New Character)")
        reset_btn.setToolTip("Clear all lab completion for a fresh character.")
        reset_btn.clicked.connect(self._on_reset)
        reset_row.addWidget(reset_btn)
        layout.addLayout(reset_row)

    def _make_difficulty_row(self, difficulty: str) -> tuple[QWidget, dict]:
        widget = QWidget()
        widget.setStyleSheet("background: #0f0f23; border-radius: 4px;")
        hl = QHBoxLayout(widget)
        hl.setContentsMargins(10, 8, 10, 8)
        hl.setSpacing(10)

        # Status icon (✓ or ○)
        status_lbl = QLabel("○")
        status_lbl.setFixedWidth(18)
        status_lbl.setStyleSheet(f"color: {DIM}; font-size: 16px; font-weight: bold;")
        status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hl.addWidget(status_lbl)

        # Name + sublabel
        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        name_lbl = QLabel(difficulty)
        name_lbl.setStyleSheet(f"color: {TEXT}; font-size: 12px; font-weight: bold;")
        sub_lbl = QLabel(_DIFF_SUBLABELS.get(difficulty, ""))
        sub_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px;")
        text_col.addWidget(name_lbl)
        text_col.addWidget(sub_lbl)
        hl.addLayout(text_col, 1)

        # Toggle button
        toggle_btn = QPushButton("Mark Done")
        toggle_btn.setFixedWidth(90)
        toggle_btn.clicked.connect(lambda _, d=difficulty: self._tracker.toggle(d))
        hl.addWidget(toggle_btn)

        widgets = {
            "status_lbl":  status_lbl,
            "name_lbl":    name_lbl,
            "toggle_btn":  toggle_btn,
            "row_widget":  widget,
        }
        return widget, widgets

    def _refresh(self):
        status = self._tracker.get_status()
        pts    = self._tracker.get_ascendancy_points()
        self._points_lbl.setText(f"Ascendancy: {pts['earned']} / {pts['available']} pts")

        for diff, done in status.items():
            w = self._row_widgets.get(diff)
            if not w:
                continue
            if done:
                w["status_lbl"].setText("✓")
                w["status_lbl"].setStyleSheet(f"color: {GREEN}; font-size: 16px; font-weight: bold;")
                w["name_lbl"].setStyleSheet(f"color: {GREEN}; font-size: 12px; font-weight: bold;")
                w["toggle_btn"].setText("Mark Undone")
                w["row_widget"].setStyleSheet(
                    f"background: #0a1a0a; border-left: 3px solid {GREEN}; border-radius: 2px;"
                )
            else:
                w["status_lbl"].setText("○")
                w["status_lbl"].setStyleSheet(f"color: {DIM}; font-size: 16px; font-weight: bold;")
                w["name_lbl"].setStyleSheet(f"color: {TEXT}; font-size: 12px; font-weight: bold;")
                w["toggle_btn"].setText("Mark Done")
                w["row_widget"].setStyleSheet("background: #0f0f23; border-radius: 4px;")

    def _on_reset(self):
        reply = QMessageBox.question(
            self,
            "Reset Lab Progress",
            "Clear all Labyrinth completion for a new character?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._tracker.reset()
