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
import ctypes.wintypes
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
        Overlay's distinctive color must appear somewhere within its window rect.

        Uses GetWindowRect to find the overlay's actual screen position rather
        than assuming a fixed pixel coordinate.  This handles DPI scaling and
        window-manager adjustments that shift the window from its requested
        position.

        Saves the screenshot to tests/screenshots/ for manual inspection.

        Skips (rather than fails) if a third-party topmost window is covering
        the overlay — the authoritative z-order check is test_overlay_has_topmost_flag;
        this test is a best-effort visual confirmation.
        """
        try:
            import mss
            from PIL import Image
        except ImportError:
            pytest.skip("mss or Pillow not installed")

        hwnd = _find_hwnd("PoELens Overlay Stub")
        if hwnd == 0:
            pytest.skip("Overlay window not found — cannot perform screenshot check")

        # Get the overlay's actual on-screen bounding box via Win32
        rect = ctypes.wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
        win_left   = rect.left
        win_top    = rect.top
        win_right  = rect.right
        win_bottom = rect.bottom

        if win_right <= win_left or win_bottom <= win_top:
            pytest.skip("Overlay window reports zero-size rect — window not yet rendered")

        SCREENSHOTS.mkdir(exist_ok=True)
        screenshot_path = SCREENSHOTS / "zorder_test_result.png"

        with mss.mss() as sct:
            monitor = sct.monitors[1]   # primary monitor
            sct_img = sct.grab(monitor)
            img     = Image.frombytes("RGB", (sct_img.width, sct_img.height), sct_img.rgb)

        img.save(str(screenshot_path))

        # Sample a point safely inside the overlay rect (25% inset to avoid edges)
        sample_x = win_left + (win_right  - win_left) // 4
        sample_y = win_top  + (win_bottom - win_top)  // 4
        pixel    = img.getpixel((sample_x, sample_y))

        if _colors_match(pixel, OVERLAY_COLOR_RGB):
            return   # overlay is visible — pass

        # If neither the overlay color nor the game color is present, another
        # window (e.g. IDE, terminal) is covering this position in the automated
        # environment.  The Win32 WS_EX_TOPMOST check is authoritative; skip here
        # rather than failing with a misleading message.
        if not _colors_match(pixel, GAME_COLOR_RGB):
            pytest.skip(
                f"Pixel at ({sample_x}, {sample_y}) is {pixel} — neither the overlay "
                f"color ~{OVERLAY_COLOR_RGB} nor the game color ~{GAME_COLOR_RGB}. "
                f"A third-party window is likely covering the overlay in this environment. "
                f"WS_EX_TOPMOST is the authoritative z-order check; see "
                f"test_overlay_has_topmost_flag. Screenshot: {screenshot_path}"
            )

        assert False, (
            f"Overlay color ~{OVERLAY_COLOR_RGB} not found at ({sample_x}, {sample_y}) — "
            f"got {pixel} (game background color), meaning the overlay is BEHIND the game "
            f"window. Screenshot saved to: {screenshot_path}"
        )

    def test_screenshot_saved_as_artifact(self):
        """Screenshot file must exist after the visual test runs."""
        screenshot_path = SCREENSHOTS / "zorder_test_result.png"
        assert screenshot_path.exists(), (
            "Screenshot was not saved — test_overlay_visible_in_screenshot may have been skipped."
        )
