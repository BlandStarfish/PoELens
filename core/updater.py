"""
Auto-updater — checks GitHub for new commits on startup.

Reads state/version.json (written by installer) to know the installed commit SHA.
Compares against the latest commit on GitHub via the API.
If an update is available, shows a small PyQt6 dialog asking the user to confirm.
On confirmation: downloads the new ZIP, extracts it (preserving state/), restarts.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.request
import zipfile

GITHUB_OWNER  = "BlandStarfish"
GITHUB_REPO   = "ExileHUD"
GITHUB_BRANCH = "master"
GITHUB_TOKEN  = ""   # ← same token as installer_gui.py

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VERSION_PATH = os.path.join(_HERE, "state", "version.json")
_HEADERS = {"User-Agent": "ExileHUD/1.0"}


def _gh_headers() -> dict:
    h = dict(_HEADERS)
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


def get_installed_sha() -> str:
    try:
        with open(_VERSION_PATH) as f:
            return json.load(f).get("sha", "")
    except Exception:
        return ""


def get_remote_sha() -> str | None:
    """Fetch the latest commit SHA from GitHub API. Returns None on failure."""
    url = (
        f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"
        f"/commits/{GITHUB_BRANCH}"
    )
    try:
        req = urllib.request.Request(url, headers={
            **_gh_headers(), "Accept": "application/vnd.github.v3+json"
        })
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
        return data.get("sha")
    except Exception:
        return None


def _save_sha(sha: str):
    os.makedirs(os.path.dirname(_VERSION_PATH), exist_ok=True)
    with open(_VERSION_PATH, "w") as f:
        json.dump({"sha": sha, "branch": GITHUB_BRANCH}, f)


def _do_update(progress_callback=None) -> bool:
    """
    Download and apply the update in-place.
    Preserves state/ directory (user config, quest progress, etc.)
    Returns True on success.
    """
    def emit(msg):
        if progress_callback:
            progress_callback(msg)

    zip_url = (
        f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}"
        f"/archive/refs/heads/{GITHUB_BRANCH}.zip"
    )
    tmp = tempfile.mkdtemp()
    try:
        emit("Downloading update...")
        zip_path = os.path.join(tmp, "update.zip")
        req = urllib.request.Request(zip_url, headers=_gh_headers())
        with urllib.request.urlopen(req, timeout=60) as resp:
            with open(zip_path, "wb") as f:
                f.write(resp.read())

        emit("Extracting...")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp)

        extracted = os.path.join(tmp, f"{GITHUB_REPO}-{GITHUB_BRANCH}")

        # Back up state/ before overwriting
        state_backup = os.path.join(tmp, "state_backup")
        state_dir = os.path.join(_HERE, "state")
        if os.path.exists(state_dir):
            shutil.copytree(state_dir, state_backup)

        # Overwrite app files (skip state/ and .runtime/)
        for item in os.listdir(extracted):
            src = os.path.join(extracted, item)
            dst = os.path.join(_HERE, item)
            if item in ("state", ".runtime"):
                continue
            if os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

        # Restore state/
        if os.path.exists(state_backup):
            if os.path.exists(state_dir):
                shutil.rmtree(state_dir)
            shutil.copytree(state_backup, state_dir)

        # Update version record
        remote_sha = get_remote_sha() or "updated"
        _save_sha(remote_sha)

        emit("Update applied. Restarting...")
        return True

    except Exception as e:
        emit(f"Update failed: {e}")
        return False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _restart():
    """Restart the app process."""
    subprocess.Popen([sys.executable] + sys.argv)
    sys.exit(0)


# ─────────────────────────────────────────────────────────────────────────────
# PyQt6 update dialog — called from main.py after QApplication exists
# ─────────────────────────────────────────────────────────────────────────────

def check_and_prompt(parent=None):
    """
    Check for updates in a background thread.
    If one is found, show a confirmation dialog on the main thread.
    Call this once at startup after QApplication is created.
    """
    def _check():
        installed = get_installed_sha()
        if not installed:
            return   # freshly cloned, no version file — skip
        remote = get_remote_sha()
        if not remote or remote == installed:
            return   # up to date or offline
        # Schedule dialog on main thread
        from PyQt6.QtCore import QMetaObject, Qt
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.update_sha = remote   # type: ignore[attr-defined]
            QMetaObject.invokeMethod(app, "_show_update_dialog",
                                     Qt.ConnectionType.QueuedConnection)

    threading.Thread(target=_check, daemon=True).start()


def show_update_dialog(remote_sha: str, parent=None):
    """Show the update confirmation dialog (call on main thread)."""
    from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QProgressBar
    from PyQt6.QtCore import Qt, QThread, pyqtSignal

    class UpdateWorker(QThread):
        progress = pyqtSignal(str)
        done     = pyqtSignal(bool)
        def run(self):
            ok = _do_update(lambda m: self.progress.emit(m))
            self.done.emit(ok)

    dlg = QDialog(parent)
    dlg.setWindowTitle("ExileHUD Update Available")
    dlg.setFixedWidth(380)
    dlg.setStyleSheet(
        "QDialog { background: #1a1a2e; color: #d4c5a9; font-family: 'Segoe UI'; }"
        "QLabel  { background: transparent; }"
        "QPushButton { background: #2a2a4a; color: #d4c5a9; border: none;"
        "  border-radius: 4px; padding: 6px 16px; }"
        "QPushButton:hover { background: #3a3a5a; }"
        "QProgressBar { background: #16213e; border: none; }"
        "QProgressBar::chunk { background: #e2b96f; }"
    )

    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(20, 16, 20, 16)
    layout.setSpacing(10)

    lbl = QLabel("A new version of ExileHUD is available.\nInstall now? Your settings will be preserved.")
    lbl.setWordWrap(True)
    layout.addWidget(lbl)

    bar = QProgressBar()
    bar.setRange(0, 0)
    bar.setFixedHeight(4)
    bar.hide()
    layout.addWidget(bar)

    status = QLabel("")
    status.setStyleSheet("color: #8a7a65; font-size: 11px;")
    status.hide()
    layout.addWidget(status)

    btn_row = QHBoxLayout()
    later_btn = QPushButton("Later")
    later_btn.clicked.connect(dlg.reject)
    update_btn = QPushButton("Update Now")
    update_btn.setStyleSheet(
        "QPushButton { background: #e2b96f; color: #1a1a2e; font-weight: bold; }"
        "QPushButton:hover { background: #c8a84b; }"
    )
    btn_row.addWidget(later_btn)
    btn_row.addStretch()
    btn_row.addWidget(update_btn)
    layout.addLayout(btn_row)

    worker = UpdateWorker()

    def start_update():
        update_btn.setEnabled(False)
        later_btn.setEnabled(False)
        bar.show()
        status.show()
        worker.start()

    def on_progress(msg):
        status.setText(msg)

    def on_done(ok):
        bar.hide()
        if ok:
            status.setText("Update complete! Restarting...")
            dlg.accept()
            _restart()
        else:
            status.setText("Update failed — continuing with current version.")
            later_btn.setEnabled(True)

    update_btn.clicked.connect(start_update)
    worker.progress.connect(on_progress)
    worker.done.connect(on_done)

    dlg.exec()
