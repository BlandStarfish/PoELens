"""
Global hotkey manager using the `keyboard` library.
Hotkeys fire even when PoE has focus.
"""

import keyboard
from typing import Callable


class HotkeyManager:
    def __init__(self, hotkeys: dict):
        """
        hotkeys: dict mapping action name -> key combo string
        e.g. {"price_check": "ctrl+d", "toggle_hud": "ctrl+shift+h"}
        """
        self._hotkeys = hotkeys
        self._registered: list[str] = []

    def register(self, action: str, callback: Callable):
        combo = self._hotkeys.get(action)
        if not combo:
            return
        keyboard.add_hotkey(combo, callback, suppress=False)
        self._registered.append(combo)

    def unregister_all(self):
        for combo in self._registered:
            try:
                keyboard.remove_hotkey(combo)
            except Exception:
                pass
        self._registered.clear()
