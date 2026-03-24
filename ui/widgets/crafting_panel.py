"""
Crafting panel — cheat sheets + task queue unified.

Left side: method cheat sheet browser.
Right side: your personal crafting queue with live cost.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QComboBox, QLineEdit, QSpinBox,
    QSplitter, QListWidget, QListWidgetItem, QTextEdit,
)
from PyQt6.QtCore import Qt

ACCENT = "#e2b96f"
TEXT   = "#d4c5a9"
DIM    = "#8a7a65"
GREEN  = "#5cba6e"
RED    = "#e05050"


class CraftingPanel(QWidget):
    def __init__(self, crafting):
        super().__init__()
        self._crafting = crafting
        self._build_ui()
        crafting.on_update(lambda _: self._refresh_queue())
        self._refresh_methods()
        self._refresh_queue()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        splitter = QSplitter(Qt.Orientation.Vertical)

        # ---- Top: cheat sheet browser ----
        sheet_widget = QWidget()
        sheet_layout = QVBoxLayout(sheet_widget)
        sheet_layout.setContentsMargins(0, 0, 0, 0)

        method_row = QHBoxLayout()
        self._method_combo = QComboBox()
        self._method_combo.currentIndexChanged.connect(self._on_method_selected)
        method_row.addWidget(QLabel("Method:"))
        method_row.addWidget(self._method_combo, 1)

        add_to_queue_btn = QPushButton("+ Add to Queue")
        add_to_queue_btn.clicked.connect(self._add_to_queue)
        method_row.addWidget(add_to_queue_btn)
        sheet_layout.addLayout(method_row)

        self._method_detail = QTextEdit()
        self._method_detail.setReadOnly(True)
        self._method_detail.setStyleSheet(
            "background: #0f0f23; color: #d4c5a9; border: 1px solid #2a2a4a; font-size: 11px;"
        )
        self._method_detail.setFixedHeight(180)
        sheet_layout.addWidget(self._method_detail)

        splitter.addWidget(sheet_widget)

        # ---- Bottom: task queue ----
        queue_widget = QWidget()
        queue_layout = QVBoxLayout(queue_widget)
        queue_layout.setContentsMargins(0, 0, 0, 0)

        queue_header = QHBoxLayout()
        queue_lbl = QLabel("Crafting Queue")
        queue_lbl.setStyleSheet(f"color: {ACCENT}; font-weight: bold;")
        queue_header.addWidget(queue_lbl)
        queue_header.addStretch()
        self._total_label = QLabel("Total: 0c")
        self._total_label.setStyleSheet(f"color: {DIM}; font-size: 11px;")
        queue_header.addWidget(self._total_label)
        queue_layout.addLayout(queue_header)

        self._queue_list = QListWidget()
        self._queue_list.setStyleSheet(
            "background: #0f0f23; color: #d4c5a9; border: 1px solid #2a2a4a; font-size: 11px;"
        )
        queue_layout.addWidget(self._queue_list)

        btn_row = QHBoxLayout()
        done_btn = QPushButton("Mark Done")
        done_btn.clicked.connect(self._mark_done)
        remove_btn = QPushButton("Remove")
        remove_btn.setStyleSheet(f"color: {RED};")
        remove_btn.clicked.connect(self._remove_task)
        btn_row.addWidget(done_btn)
        btn_row.addWidget(remove_btn)
        queue_layout.addLayout(btn_row)

        splitter.addWidget(queue_widget)
        layout.addWidget(splitter)

        # Add-to-queue form (item name + qty)
        form_row = QHBoxLayout()
        self._item_name_input = QLineEdit()
        self._item_name_input.setPlaceholderText("Item name / goal")
        self._item_name_input.setStyleSheet("background: #0f0f23; color: #d4c5a9; border: 1px solid #2a2a4a; border-radius: 3px; padding: 3px;")
        self._qty_spin = QSpinBox()
        self._qty_spin.setRange(1, 1000)
        self._qty_spin.setValue(1)
        self._qty_spin.setStyleSheet("background: #0f0f23; color: #d4c5a9; border: 1px solid #2a2a4a; border-radius: 3px;")
        form_row.addWidget(QLabel("Goal:"))
        form_row.addWidget(self._item_name_input, 1)
        form_row.addWidget(QLabel("×"))
        form_row.addWidget(self._qty_spin)
        layout.addLayout(form_row)

    # ------------------------------------------------------------------
    # Cheat sheet methods
    # ------------------------------------------------------------------

    def _refresh_methods(self):
        self._method_combo.clear()
        self._methods = self._crafting.list_methods()
        for m in self._methods:
            self._method_combo.addItem(m["name"], m["id"])

    def _on_method_selected(self, index: int):
        if index < 0 or index >= len(self._methods):
            return
        m = self._methods[index]
        cost = self._crafting.get_method_cost(m["id"])

        lines = []
        lines.append(f"<b style='color:#e2b96f'>{m['name']}</b>")
        lines.append(f"<i style='color:#8a7a65'>{m.get('description','')}</i>")
        lines.append("")
        lines.append(f"<b>Steps:</b>")
        for i, step in enumerate(m.get("steps", []), 1):
            lines.append(f"  {i}. {step}")
        lines.append("")
        lines.append(f"<b>Materials (estimated cost: {cost.get('total_chaos', 0):.1f}c):</b>")
        for item in cost.get("line_items", []):
            acquire = ", ".join(item["acquire_via"][:2])
            lines.append(f"  • {item['name']} ×{item['qty']}  = {item['chaos_total']:.1f}c  [{acquire}]")

        if notes := m.get("notes"):
            lines.append(f"<br><i style='color:#8a7a65'>Note: {notes}</i>")

        self._method_detail.setHtml("<br>".join(lines))

    # ------------------------------------------------------------------
    # Task queue
    # ------------------------------------------------------------------

    def _add_to_queue(self):
        method_id = self._method_combo.currentData()
        item_name = self._item_name_input.text().strip() or "Unnamed item"
        qty = self._qty_spin.value()
        if method_id:
            self._crafting.add_task(item_name, method_id, qty)
            self._item_name_input.clear()

    def _refresh_queue(self):
        self._queue_list.clear()
        for i, task in enumerate(self._crafting.get_queue()):
            cost = task.get("cost", {})
            total_c = cost.get("total_chaos", 0)
            done_mark = "✓ " if task.get("completed") else ""
            method_name = cost.get("method_name") or task.get("method_id", "?")
            text = (
                f"{done_mark}[{i+1}] {task['item_name']}  "
                f"({method_name} ×{task.get('quantity',1)})  "
                f"~{total_c:.0f}c"
            )
            item = QListWidgetItem(text)
            if task.get("completed"):
                item.setForeground(Qt.GlobalColor.darkGray)
            self._queue_list.addItem(item)

        totals = self._crafting.get_total_queue_cost()
        self._total_label.setText(
            f"Total: {totals['total_chaos']:.0f}c  ({totals['pending_tasks']} pending)"
        )

    def _mark_done(self):
        row = self._queue_list.currentRow()
        if row >= 0:
            self._crafting.complete_task(row)

    def _remove_task(self):
        row = self._queue_list.currentRow()
        if row >= 0:
            self._crafting.remove_task(row)
