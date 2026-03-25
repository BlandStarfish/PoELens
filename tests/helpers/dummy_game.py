"""
Dummy fullscreen game window — used by the overlay z-order test.

Simulates Path of Exile running in Windowed Fullscreen mode:
a borderless, maximized window that fills the primary display.

The window is painted a solid distinctive green (#00CC44) so
screenshots can verify whether the overlay is on top of it.

Usage (called as a subprocess by the test):
    python dummy_game.py [--duration N]
"""

import argparse
import sys
import tkinter as tk


BACKGROUND_COLOR = "#00CC44"   # distinctive green — must NOT appear in the overlay stub
WINDOW_TITLE     = "PoELens DummyGame"


def main():
    parser = argparse.ArgumentParser(description="Dummy game window for z-order tests")
    parser.add_argument("--duration", type=float, default=10,
                        help="Seconds to stay open (default: 10)")
    args = parser.parse_args()

    root = tk.Tk()
    root.title(WINDOW_TITLE)
    root.configure(bg=BACKGROUND_COLOR)

    # Borderless + positioned to cover the full screen — mirrors PoE Windowed Fullscreen
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    root.geometry(f"{screen_w}x{screen_h}+0+0")
    root.overrideredirect(True)   # no title bar / borders
    root.attributes("-topmost", False)  # normal z-order — overlay must beat this

    tk.Label(
        root,
        text="DUMMY GAME WINDOW\n(PoE Windowed Fullscreen simulation)",
        bg=BACKGROUND_COLOR,
        fg="#ffffff",
        font=("Arial", 20, "bold"),
    ).pack(expand=True)

    root.after(int(args.duration * 1000), root.destroy)
    root.mainloop()


if __name__ == "__main__":
    main()
