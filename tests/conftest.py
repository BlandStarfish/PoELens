"""
Shared pytest fixtures and helpers for the PoELens test suite.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Project root — makes imports in tests work regardless of cwd
ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Absolute path to the project root (C:/POE Stuff)."""
    return ROOT


@pytest.fixture(scope="session")
def installer_module():
    """
    Import installer_gui, mocking tkinter only where necessary.

    On Windows, tkinter is native and can be imported without a display
    (a display is only required when Tk() is actually called).  We leave
    it unmocked there so Windows-only runtime tests can use real classes.

    On Linux/macOS (CI smoke runners), tkinter requires a display even to
    import on some distros, so we replace it with MagicMock.  This means
    installer_gui.Installer will be a MagicMock on those platforms —
    runtime method tests must be skipped or handled accordingly.
    """
    if sys.platform != "win32":
        # Only mock on non-Windows to avoid display requirement
        for mod in ("tkinter", "tkinter.ttk", "tkinter.filedialog"):
            sys.modules.setdefault(mod, MagicMock())

    sys.path.insert(0, str(ROOT))
    import installer_gui  # noqa: PLC0415  (import not at top — intentional)
    return installer_gui
