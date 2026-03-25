"""
Minimal overlay stub — used by the overlay z-order test.

Uses IDENTICAL window flags to the real PoELens HUD:
    WindowStaysOnTopHint | FramelessWindowHint | Tool

Painted a solid distinctive red (#CC2244) so screenshots can confirm
it is visible above the dummy game window.

Usage (called as a subprocess by the test):
    python overlay_stub.py [--duration N]
"""

import argparse
import sys

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication, QLabel


OVERLAY_COLOR  = "#CC2244"   # distinctive red — must NOT appear in the game background
OVERLAY_TITLE  = "PoELens Overlay Stub"
OVERLAY_TEXT   = "POENLS_OVERLAY_VISIBLE"

# Position and size — chosen to sit well within the top-left of any display
OVERLAY_X      = 80
OVERLAY_Y      = 80
OVERLAY_W      = 320
OVERLAY_H      = 100


def main():
    parser = argparse.ArgumentParser(description="Minimal overlay stub for z-order tests")
    parser.add_argument("--duration", type=float, default=10,
                        help="Seconds to stay open (default: 10)")
    args = parser.parse_args()

    app = QApplication(sys.argv)

    label = QLabel(OVERLAY_TEXT)
    label.setWindowTitle(OVERLAY_TITLE)

    # Exact same flags as the real HUD (ui/hud.py)
    label.setWindowFlags(
        Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.WindowStaysOnTopHint
        | Qt.WindowType.Tool
    )
    label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
    label.setStyleSheet(
        f"background-color: {OVERLAY_COLOR}; color: white;"
        "font-size: 16px; font-weight: bold; padding: 24px;"
    )
    label.setFixedSize(OVERLAY_W, OVERLAY_H)
    label.move(OVERLAY_X, OVERLAY_Y)
    label.show()

    QTimer.singleShot(int(args.duration * 1000), app.quit)
    app.exec()


if __name__ == "__main__":
    main()
