"""
Currency Flip Calculator panel.

Displays profitable currency exchange opportunities calculated from poe.ninja data.
Buy low, sell high — shows the spread between buy and sell prices for each currency.

No API calls beyond what poe.ninja already fetches for price checking.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QScrollArea, QHBoxLayout, QFrame,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

ACCENT = "#e2b96f"
TEXT   = "#d4c5a9"
DIM    = "#8a7a65"
GREEN  = "#5cba6e"
ORANGE = "#e8864a"
RED    = "#e05050"


def _margin_color(margin_pct: float) -> str:
    if margin_pct >= 5.0:
        return GREEN
    if margin_pct >= 2.0:
        return ACCENT
    return ORANGE


class _FlipWorker(QThread):
    """Background thread for calculating flips (poe.ninja fetch may block)."""
    done = pyqtSignal(list)

    def __init__(self, flip_module):
        super().__init__()
        self._flip = flip_module

    def run(self):
        try:
            results = self._flip.calculate_flips()
        except Exception as e:
            print(f"[CurrencyFlipPanel] calculation error: {e}")
            results = []
        self.done.emit(results)


class CurrencyFlipPanel(QWidget):
    def __init__(self, currency_flip):
        """
        currency_flip — CurrencyFlip module instance
        """
        super().__init__()
        self._flip   = currency_flip
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # Header row
        header_row = QHBoxLayout()
        header = QLabel("Currency Flip Calculator")
        header.setStyleSheet(f"color: {ACCENT}; font-weight: bold; font-size: 13px;")
        header_row.addWidget(header)
        header_row.addStretch()

        self._refresh_btn = QPushButton("Calculate")
        self._refresh_btn.setFixedWidth(80)
        self._refresh_btn.clicked.connect(self._start_calculate)
        header_row.addWidget(self._refresh_btn)
        layout.addLayout(header_row)

        # Status label
        self._status = QLabel("Press Calculate to find profitable flips.")
        self._status.setStyleSheet(f"color: {DIM}; font-size: 11px;")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        # Scrollable results
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        self._result_container = QWidget()
        self._result_layout    = QVBoxLayout(self._result_container)
        self._result_layout.setContentsMargins(0, 0, 0, 0)
        self._result_layout.setSpacing(3)
        self._result_layout.addStretch()
        scroll.setWidget(self._result_container)
        layout.addWidget(scroll)

        note = QLabel(
            "Buy price = chaos you pay. Sell price = chaos you receive. "
            "Margin = profit per unit. Data from poe.ninja."
        )
        note.setStyleSheet(f"color: {DIM}; font-size: 10px;")
        note.setWordWrap(True)
        layout.addWidget(note)

    def _start_calculate(self):
        if self._worker and self._worker.isRunning():
            return
        self._refresh_btn.setEnabled(False)
        self._status.setStyleSheet(f"color: {DIM}; font-size: 11px;")
        self._status.setText("Fetching poe.ninja data…")
        self._worker = _FlipWorker(self._flip)
        self._worker.done.connect(self._on_results)
        self._worker.start()

    def _on_results(self, flips: list[dict]):
        self._refresh_btn.setEnabled(True)
        self._clear_results()

        if not flips:
            self._status.setStyleSheet(f"color: {DIM}; font-size: 11px;")
            self._status.setText(
                "No profitable flips found. Market may be efficient, "
                "or poe.ninja data is unavailable."
            )
            return

        self._status.setStyleSheet(f"color: {GREEN}; font-size: 11px;")
        self._status.setText(f"Found {len(flips)} profitable flip{'s' if len(flips) != 1 else ''}.")

        for flip in flips:
            card = self._make_flip_card(flip)
            self._result_layout.insertWidget(self._result_layout.count() - 1, card)

    def _clear_results(self):
        while self._result_layout.count() > 1:
            item = self._result_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _make_flip_card(self, flip: dict) -> QWidget:
        margin_pct = flip["margin_pct"]
        color      = _margin_color(margin_pct)

        card = QWidget()
        card.setStyleSheet(f"background: #0f0f23; border-left: 3px solid {color}; border-radius: 2px;")
        row = QHBoxLayout(card)
        row.setContentsMargins(8, 5, 8, 5)
        row.setSpacing(8)

        # Currency name
        name_lbl = QLabel(flip["name"])
        name_lbl.setStyleSheet(f"color: {ACCENT}; font-size: 11px; font-weight: bold;")
        row.addWidget(name_lbl, 1)

        # Buy / Sell prices
        price_lbl = QLabel(f"Buy {flip['buy']}c → Sell {flip['sell']}c")
        price_lbl.setStyleSheet(f"color: {TEXT}; font-size: 11px;")
        row.addWidget(price_lbl)

        # Margin badge
        margin_lbl = QLabel(f"+{margin_pct}%")
        margin_lbl.setStyleSheet(
            f"color: {color}; font-size: 11px; font-weight: bold; "
            f"background: #1a1a3a; border-radius: 2px; padding: 1px 5px;"
        )
        row.addWidget(margin_lbl)

        # Listing count
        listings_lbl = QLabel(f"{flip['listing_count']} listings")
        listings_lbl.setStyleSheet(f"color: {DIM}; font-size: 10px;")
        row.addWidget(listings_lbl)

        return card
