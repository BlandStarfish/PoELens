"""
Price check panel — displays results from the last price check hotkey press.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QHBoxLayout
from PyQt6.QtCore import Qt, QMetaObject, Q_ARG, pyqtSlot

ACCENT = "#e2b96f"
TEXT   = "#d4c5a9"
DIM    = "#8a7a65"
RED    = "#e05050"


class PricePanel(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        hint = QLabel("Press Ctrl+C while hovering an item in PoE to copy and price check simultaneously.")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {DIM}; font-size: 11px;")
        layout.addWidget(hint)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2a2a4a;")
        layout.addWidget(sep)

        self._item_name = QLabel("—")
        self._item_name.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 13px;")
        layout.addWidget(self._item_name)

        self._ninja_row = self._make_row("poe.ninja:", "—")
        layout.addWidget(self._ninja_row[0])

        self._trade_label = QLabel("Live listings:")
        self._trade_label.setStyleSheet(f"color: {DIM}; font-size: 11px;")
        layout.addWidget(self._trade_label)

        self._trade_prices = QLabel("—")
        self._trade_prices.setStyleSheet(f"color: {TEXT};")
        layout.addWidget(self._trade_prices)

        self._trade_link = QLabel()
        self._trade_link.setOpenExternalLinks(True)
        self._trade_link.setStyleSheet(f"color: #6a9fd8; font-size: 11px;")
        layout.addWidget(self._trade_link)

        self._error_label = QLabel()
        self._error_label.setWordWrap(True)
        self._error_label.setStyleSheet(f"color: {RED};")
        layout.addWidget(self._error_label)

        layout.addStretch()

    def _make_row(self, label: str, value: str):
        row = QWidget()
        hl = QHBoxLayout(row)
        hl.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {DIM}; font-size: 11px; min-width: 90px;")
        val = QLabel(value)
        val.setStyleSheet(f"color: {TEXT};")
        hl.addWidget(lbl)
        hl.addWidget(val, 1)
        return row, val

    def show_result(self, result: dict):
        """Called (from background thread) when a price check completes."""
        # Qt UI updates must happen on the main thread
        QMetaObject.invokeMethod(self, "_update_ui",
                                 Qt.ConnectionType.QueuedConnection,
                                 Q_ARG("PyQt_PyObject", result))

    @pyqtSlot("PyQt_PyObject")
    def _update_ui(self, result: dict):
        self._error_label.setText("")
        self._trade_link.setText("")

        if err := result.get("error"):
            self._error_label.setText(err)
            self._item_name.setText("—")
            return

        item = result.get("item", {})
        name = item.get("name") or item.get("base_type") or "Unknown"
        rarity = item.get("rarity", "")
        self._item_name.setText(f"{name}  [{rarity}]")

        ninja_price = result.get("ninja_price")
        cat = result.get("ninja_category", "")
        if ninja_price is not None:
            self._ninja_row[1].setText(f"{ninja_price:.1f}c  [{cat}]")
        else:
            self._ninja_row[1].setText("Not found")

        listings = result.get("trade_listings", [])
        if listings:
            self._trade_prices.setText("  |  ".join(f"{p:.0f}c" for p in listings[:5]))
        else:
            self._trade_prices.setText("No listings found")

        url = result.get("trade_url", "")
        if url:
            self._trade_link.setText(f'<a href="{url}">View on trade site</a>')
