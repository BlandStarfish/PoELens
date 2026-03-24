"""
Quest panel — shows passive skill point quests with completion status,
current point totals, and step-by-step guidance for the next quest.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame, QPushButton, QCheckBox,
)
from PyQt6.QtCore import Qt

ACCENT = "#e2b96f"
TEXT   = "#d4c5a9"
DIM    = "#8a7a65"
GREEN  = "#5cba6e"
RED    = "#e05050"


class QuestPanel(QWidget):
    def __init__(self, quest_tracker):
        super().__init__()
        self._tracker = quest_tracker
        self._build_ui()
        quest_tracker.on_update(lambda _: self._refresh())
        self._refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)

        # Point summary bar
        self._summary = QLabel()
        self._summary.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 11px;")
        layout.addWidget(self._summary)

        # Next quest callout
        self._next_label = QLabel()
        self._next_label.setWordWrap(True)
        self._next_label.setStyleSheet(f"color: {GREEN}; font-size: 11px; padding: 4px; background: #1a2a1a; border-radius: 4px;")
        layout.addWidget(self._next_label)

        # Scroll area for quest list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setSpacing(2)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.addStretch()
        scroll.setWidget(self._list_widget)
        layout.addWidget(scroll)

    def _refresh(self):
        totals = self._tracker.get_point_totals()
        self._summary.setText(
            f"Passive points from quests: {totals['net']} net  "
            f"({totals['earned']} earned — {totals['deducted']} deducted)  "
            f"| {totals['remaining']} still available"
        )

        next_q = self._tracker.get_next_quest()
        if next_q:
            steps_text = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(next_q["steps"]))
            self._next_label.setText(
                f"Next: Act {next_q['act']} — {next_q['name']} (+{next_q['passive_points']} pts)\n{steps_text}"
            )
            self._next_label.show()
        else:
            self._next_label.hide()

        # Rebuild quest list
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for quest in self._tracker.get_status():
            row = self._make_quest_row(quest)
            self._list_layout.insertWidget(self._list_layout.count() - 1, row)

    def _make_quest_row(self, quest: dict) -> QWidget:
        row = QWidget()
        row.setFixedHeight(28)
        hl = QHBoxLayout(row)
        hl.setContentsMargins(4, 0, 4, 0)

        pts = quest.get("passive_points", 0)
        pts_str = f"+{pts}" if pts > 0 else str(pts)
        color = GREEN if quest["completed"] else (RED if pts < 0 else TEXT)

        check = QCheckBox()
        check.setChecked(quest["completed"])
        check.stateChanged.connect(
            lambda state, qid=quest["id"]: self._toggle(qid, state)
        )

        name_lbl = QLabel(f"Act {quest['act']}: {quest['name']}")
        name_lbl.setStyleSheet(f"color: {'#555' if quest['completed'] else TEXT};")
        if quest["completed"]:
            name_lbl.setStyleSheet("color: #555; text-decoration: line-through;")

        pts_lbl = QLabel(pts_str)
        pts_lbl.setFixedWidth(32)
        pts_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        pts_lbl.setStyleSheet(f"color: {color}; font-weight: bold;")

        hl.addWidget(check)
        hl.addWidget(name_lbl, 1)
        hl.addWidget(pts_lbl)
        return row

    def _toggle(self, quest_id: str, state: int):
        if state == 2:  # checked
            self._tracker.manually_complete(quest_id)
        else:
            self._tracker.manually_uncomplete(quest_id)
