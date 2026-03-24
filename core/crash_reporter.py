"""
Crash and error reporter.

Catches unhandled exceptions, logs them to state/crash_log.jsonl,
and shows a user-friendly dialog instead of a silent crash.

Logs contain: timestamp, exception type/message, traceback, app version,
platform info. No personally identifiable information is collected.

To wire in: call install() once at the top of main.py.
"""

import datetime
import json
import os
import platform
import sys
import traceback

_HERE      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOG_PATH  = os.path.join(_HERE, "state", "crash_log.jsonl")
_VER_PATH  = os.path.join(_HERE, "state", "version.json")
_MAX_LINES = 500   # rotate after this many crash entries


def _get_version() -> str:
    try:
        with open(_VER_PATH) as f:
            return json.load(f).get("sha", "unknown")[:8]
    except Exception:
        return "unknown"


def _write_entry(exc_type, exc_value, tb):
    os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
    entry = {
        "time":      datetime.datetime.now().isoformat(),
        "version":   _get_version(),
        "platform":  platform.version(),
        "python":    sys.version,
        "type":      exc_type.__name__,
        "message":   str(exc_value),
        "traceback": traceback.format_exception(exc_type, exc_value, tb),
    }
    # Append as JSONL
    with open(_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    # Rotate: keep only the last _MAX_LINES entries
    try:
        with open(_LOG_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) > _MAX_LINES:
            with open(_LOG_PATH, "w", encoding="utf-8") as f:
                f.writelines(lines[-_MAX_LINES:])
    except Exception:
        pass

    return entry


def _show_crash_dialog(entry: dict):
    """Show a PyQt6 crash dialog if Qt is running, else print to stderr."""
    try:
        from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit
        app = QApplication.instance()
        if not app:
            raise RuntimeError("No QApplication")

        dlg = QDialog()
        dlg.setWindowTitle("ExileHUD — Unexpected Error")
        dlg.setFixedWidth(480)
        dlg.setStyleSheet(
            "QDialog { background: #1a1a2e; color: #d4c5a9; font-family: 'Segoe UI'; }"
            "QLabel  { background: transparent; }"
            "QPushButton { background: #2a2a4a; color: #d4c5a9; border: none;"
            "  border-radius: 4px; padding: 6px 16px; }"
            "QPushButton:hover { background: #3a3a5a; }"
        )
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        layout.addWidget(QLabel(
            "<b style='color:#e05050'>ExileHUD encountered an unexpected error.</b>"
        ))
        layout.addWidget(QLabel(
            f"<span style='color:#8a7a65'>{entry['type']}: {entry['message']}</span>"
        ))

        detail = QTextEdit()
        detail.setReadOnly(True)
        detail.setFixedHeight(160)
        detail.setStyleSheet(
            "background: #0f0f23; color: #8a7a65; font-family: Consolas; font-size: 10px; border: none;"
        )
        detail.setPlainText("".join(entry["traceback"]))
        layout.addWidget(detail)

        layout.addWidget(QLabel(
            f"<span style='color:#8a7a65'>Crash log saved to: {_LOG_PATH}</span>"
        ))

        btns_layout = QHBoxLayout()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.accept)
        restart_btn = QPushButton("Restart ExileHUD")
        restart_btn.setStyleSheet(
            "QPushButton { background: #e2b96f; color: #1a1a2e; font-weight: bold; }"
        )

        def do_restart():
            dlg.accept()
            import subprocess
            subprocess.Popen([sys.executable] + sys.argv)
            sys.exit(1)

        restart_btn.clicked.connect(do_restart)
        btns_layout.addWidget(close_btn)
        btns_layout.addStretch()
        btns_layout.addWidget(restart_btn)
        layout.addLayout(btns_layout)

        dlg.exec()

    except Exception:
        # Qt not available — print to stderr
        print(f"\n[ExileHUD CRASH] {entry['type']}: {entry['message']}", file=sys.stderr)
        print("".join(entry["traceback"]), file=sys.stderr)
        print(f"Crash log: {_LOG_PATH}", file=sys.stderr)


def _excepthook(exc_type, exc_value, tb):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, tb)
        return
    entry = _write_entry(exc_type, exc_value, tb)
    _show_crash_dialog(entry)


def install():
    """Install the crash reporter as the global exception handler."""
    sys.excepthook = _excepthook


def get_recent_crashes(n: int = 10) -> list[dict]:
    """Return the last n crash entries from the log."""
    if not os.path.exists(_LOG_PATH):
        return []
    try:
        with open(_LOG_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        entries = []
        for line in reversed(lines):
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    pass
            if len(entries) >= n:
                break
        return entries
    except Exception:
        return []
