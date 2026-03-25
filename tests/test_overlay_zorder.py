"""
Overlay z-order integration test — Windows only.

Verifies that the PoELens overlay window appears on top of a simulated
fullscreen game window (the same scenario as PoE in Windowed Fullscreen mode).

Two complementary assertions are made:

  1. Win32 API check (authoritative)
     Queries the WS_EX_TOPMOST extended window style flag on the overlay
     stub window via ctypes.  This confirms the OS-level z-order property
     is correctly set, independent of rendering or DPI.

  2. Screenshot pixel check (visual confirmation)
     Takes a screenshot with mss and samples pixels at the overlay's known
     position.  Confirms the overlay's distinctive color is visible on screen,
     meaning it was actually painted on top of the game window.
     The screenshot is saved to tests/screenshots/ and uploaded as a CI
     artifact so you can eyeball it after every run.

Requirements:
  - Windows (ctypes.windll only exists on Win32)
  - PyQt6 (overlay_stub.py)
  - mss + Pillow (screenshot sampling)
"""

import ctypes
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

HERE        = Path(__file__).resolve().parent
HELPERS     = HERE / "helpers"
SCREENSHOTS = HERE / "screenshots"

# Colors must match dummy_game.py and overlay_stub.py exactly
GAME_COLOR_RGB    = (0, 204, 68)    # #00CC44  — the "game" background
OVERLAY_COLOR_RGB = (204, 34, 68)   # #CC2244  — the overlay stub

# Pixel inside the overlay's bounding box to sample
OVERLAY_SAMPLE_X = 80 + 60   # OVERLAY_X + offset
OVERLAY_SAMPLE_Y = 80 + 30   # OVERLAY_Y + offset

COLOR_TOLERANCE = 30          # ±30 per channel to handle anti-aliasing / DPI scaling

# Win32 constants
GWL_EXSTYLE   = -20
WS_EX_TOPMOST = 0x00000008


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _find_hwnd(title: str) -> int:
    """Return the HWND for a window with the given title, or 0 if not found."""
    return ctypes.windll.user32.FindWindowW(None, title)


def _wait_for_window(title: str, timeout: float = 15.0, interval: float = 0.25) -> int:
    """Poll until a window with the given title is visible, or 0 on timeout.

    More reliable than a fixed sleep — CI runners vary in startup speed.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        hwnd = _find_hwnd(title)
        if hwnd != 0:
            return hwnd
        time.sleep(interval)
    return 0


def _is_topmost(hwnd: int) -> bool:
    """Return True if the window has WS_EX_TOPMOST set."""
    exstyle = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    return bool(exstyle & WS_EX_TOPMOST)


def _colors_match(pixel: tuple, expected: tuple, tol: int = COLOR_TOLERANCE) -> bool:
    """Return True if pixel is within tolerance of expected (R, G, B)."""
    return all(abs(pixel[i] - expected[i]) <= tol for i in range(3))


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only: ctypes Win32 API required")
class TestOverlayZOrder:
    """
    Launches both helper processes and keeps them alive for the duration of
    all tests in this class, then cleans up in teardown.
    """

    game_proc    = None
    overlay_proc = None
    DURATION     = 20   # seconds — long enough for all assertions + screenshot

    @classmethod
    def setup_class(cls):
        """Launch dummy game then overlay stub; wait until both windows are visible."""
        cls.game_proc = subprocess.Popen(
            [sys.executable, str(HELPERS / "dummy_game.py"),
             "--duration", str(cls.DURATION)],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        # Poll for the game window rather than sleeping a fixed duration
        game_hwnd = _wait_for_window("PoELens DummyGame", timeout=15.0)
        if game_hwnd == 0:
            stderr = cls.game_proc.stderr.read(500) if cls.game_proc.stderr else b""
            pytest.fail(f"Dummy game window never appeared. stderr: {stderr.decode(errors='replace')}")

        cls.overlay_proc = subprocess.Popen(
            [sys.executable, str(HELPERS / "overlay_stub.py"),
             "--duration", str(cls.DURATION)],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        # Poll for the overlay window
        overlay_hwnd = _wait_for_window("PoELens Overlay Stub", timeout=15.0)
        if overlay_hwnd == 0:
            stderr = cls.overlay_proc.stderr.read(500) if cls.overlay_proc.stderr else b""
            pytest.fail(f"Overlay window never appeared. stderr: {stderr.decode(errors='replace')}")

    @classmethod
    def teardown_class(cls):
        for proc in (cls.overlay_proc, cls.game_proc):
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()

    # ── Assertion 1: Win32 WS_EX_TOPMOST flag ────────────────────────────────

    def test_overlay_window_found(self):
        """The overlay stub window must be discoverable by title."""
        hwnd = _find_hwnd("PoELens Overlay Stub")
        assert hwnd != 0, (
            "Could not find overlay window 'PoELens Overlay Stub'. "
            "The process may have crashed — check overlay_stub.py output."
        )

    def test_overlay_has_topmost_flag(self):
        """Overlay window must have WS_EX_TOPMOST set (Win32 z-order property)."""
        hwnd = _find_hwnd("PoELens Overlay Stub")
        assert hwnd != 0, "Overlay window not found — cannot check WS_EX_TOPMOST"
        assert _is_topmost(hwnd), (
            "WS_EX_TOPMOST is NOT set on the overlay window.\n"
            "Qt.WindowType.WindowStaysOnTopHint must set this flag."
        )

    def test_game_window_not_topmost(self):
        """The game window must NOT have WS_EX_TOPMOST — overlay must beat it."""
        hwnd = _find_hwnd("PoELens DummyGame")
        if hwnd == 0:
            pytest.skip("Dummy game window not found — possibly not supported in this environment")
        assert not _is_topmost(hwnd), (
            "Dummy game window has WS_EX_TOPMOST set — the test fixture is misconfigured."
        )

    # ── Assertion 2: Screenshot pixel verification ────────────────────────────

    def test_overlay_visible_in_screenshot(self):
        """
        Overlay's distinctive color must appear at its expected screen position.
        Saves the screenshot to tests/screenshots/ for manual inspection.
        """
        try:
            import mss
            from PIL import Image
        except ImportError:
            pytest.skip("mss or Pillow not installed")

        SCREENSHOTS.mkdir(exist_ok=True)
        screenshot_path = SCREENSHOTS / "zorder_test_result.png"

        with mss.mss() as sct:
            monitor   = sct.monitors[1]   # primary monitor
            sct_img   = sct.grab(monitor)
            img       = Image.frombytes("RGB", (sct_img.width, sct_img.height), sct_img.rgb)

        img.save(str(screenshot_path))

        # Verify the overlay's pixel is the overlay color, not the game color
        pixel = img.getpixel((OVERLAY_SAMPLE_X, OVERLAY_SAMPLE_Y))

        assert _colors_match(pixel, OVERLAY_COLOR_RGB), (
            f"Expected overlay color ~{OVERLAY_COLOR_RGB} at "
            f"({OVERLAY_SAMPLE_X}, {OVERLAY_SAMPLE_Y}), got {pixel}.\n"
            f"The overlay appears to be BEHIND the game window.\n"
            f"Screenshot saved to: {screenshot_path}"
        )

    def test_screenshot_saved_as_artifact(self):
        """Screenshot file must exist after the visual test runs."""
        screenshot_path = SCREENSHOTS / "zorder_test_result.png"
        assert screenshot_path.exists(), (
            "Screenshot was not saved — test_overlay_visible_in_screenshot may have been skipped."
        )
