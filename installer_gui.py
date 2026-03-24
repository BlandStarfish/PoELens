"""
ExileHUD GUI Installer
======================
Compile to a standalone .exe with:
    pip install pyinstaller
    pyinstaller --onefile --noconsole --name "ExileHUD-Setup" installer_gui.py

Distribute ExileHUD-Setup.exe. When run, it:
  1. Lets the user pick an install folder
  2. Downloads the repo ZIP from GitHub
  3. Extracts it
  4. Installs Python deps (using the bundled pip / system Python)
  5. Downloads the passive tree data
  6. Creates a Desktop shortcut and Start Menu entry
  7. Shows a "Launch now" button when done
"""

import os
import sys
import json
import shutil
import zipfile
import threading
import urllib.request
import subprocess
import tempfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

REPO_ZIP     = "https://github.com/BlandStarfish/ExileHUD/archive/refs/heads/master.zip"
REPO_SUBDIR  = "ExileHUD-master"   # name of the folder inside the ZIP
APP_NAME     = "ExileHUD"
TREE_FALLBACK = "https://raw.githubusercontent.com/grindinggear/skilltree-export/master/data.json"

DEFAULT_INSTALL = os.path.join(os.path.expanduser("~"), "ExileHUD")

# ─────────────────────────────────────────────────────────────────────────────
# Colours / style
# ─────────────────────────────────────────────────────────────────────────────

BG      = "#1a1a2e"
PANEL   = "#16213e"
GOLD    = "#e2b96f"
TEXT    = "#d4c5a9"
DIM     = "#8a7a65"
GREEN   = "#5cba6e"
RED     = "#e05050"

# ─────────────────────────────────────────────────────────────────────────────
# Main installer window
# ─────────────────────────────────────────────────────────────────────────────

class Installer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} Setup")
        self.resizable(False, False)
        self.configure(bg=BG)
        self._center(560, 420)
        self._build()

    def _center(self, w, h):
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        # Header
        header = tk.Frame(self, bg=PANEL, height=72)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="ExileHUD", font=("Segoe UI", 22, "bold"),
                 bg=PANEL, fg=GOLD).pack(side="left", padx=20, pady=10)
        tk.Label(header, text="Path of Exile Overlay",
                 font=("Segoe UI", 11), bg=PANEL, fg=DIM).pack(side="left", pady=16)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=16)

        # Install folder row
        tk.Label(body, text="Install to:", bg=BG, fg=TEXT,
                 font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", pady=4)
        self._folder_var = tk.StringVar(value=DEFAULT_INSTALL)
        folder_entry = tk.Entry(body, textvariable=self._folder_var, width=42,
                                bg=PANEL, fg=TEXT, insertbackground=TEXT,
                                relief="flat", font=("Segoe UI", 10))
        folder_entry.grid(row=0, column=1, padx=8, sticky="ew")
        tk.Button(body, text="Browse…", command=self._browse,
                  bg="#2a2a4a", fg=TEXT, relief="flat", font=("Segoe UI", 9),
                  activebackground="#3a3a5a", activeforeground=TEXT,
                  cursor="hand2").grid(row=0, column=2)

        # Checkboxes
        self._shortcut_var  = tk.BooleanVar(value=True)
        self._startmenu_var = tk.BooleanVar(value=True)
        tk.Checkbutton(body, text="Create Desktop shortcut",
                       variable=self._shortcut_var,
                       bg=BG, fg=TEXT, selectcolor=PANEL,
                       activebackground=BG, activeforeground=GOLD,
                       font=("Segoe UI", 10)).grid(row=1, column=0, columnspan=3, sticky="w", pady=2)
        tk.Checkbutton(body, text="Add to Start Menu",
                       variable=self._startmenu_var,
                       bg=BG, fg=TEXT, selectcolor=PANEL,
                       activebackground=BG, activeforeground=GOLD,
                       font=("Segoe UI", 10)).grid(row=2, column=0, columnspan=3, sticky="w", pady=2)

        body.columnconfigure(1, weight=1)

        # Progress area
        prog_frame = tk.Frame(self, bg=BG)
        prog_frame.pack(fill="x", padx=24)

        self._status = tk.Label(prog_frame, text="Ready to install.",
                                bg=BG, fg=DIM, font=("Segoe UI", 9),
                                anchor="w")
        self._status.pack(fill="x")

        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("Gold.Horizontal.TProgressbar",
                        troughcolor=PANEL, background=GOLD, borderwidth=0)
        self._bar = ttk.Progressbar(prog_frame, style="Gold.Horizontal.TProgressbar",
                                    length=512, mode="determinate")
        self._bar.pack(fill="x", pady=4)

        self._log = tk.Text(self, bg=PANEL, fg=DIM, font=("Consolas", 9),
                            height=8, relief="flat", state="disabled",
                            wrap="word", padx=6, pady=4)
        self._log.pack(fill="x", padx=24, pady=(0, 8))

        # Buttons
        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(fill="x", padx=24, pady=(0, 16))

        self._install_btn = tk.Button(
            btn_frame, text="Install", command=self._start_install,
            bg=GOLD, fg="#1a1a2e", font=("Segoe UI", 11, "bold"),
            relief="flat", padx=24, pady=6,
            activebackground="#c8a84b", activeforeground="#1a1a2e",
            cursor="hand2"
        )
        self._install_btn.pack(side="right", padx=(8, 0))

        self._cancel_btn = tk.Button(
            btn_frame, text="Cancel", command=self.destroy,
            bg="#2a2a4a", fg=TEXT, font=("Segoe UI", 10),
            relief="flat", padx=16, pady=6,
            activebackground="#3a3a5a", activeforeground=TEXT,
            cursor="hand2"
        )
        self._cancel_btn.pack(side="right")

        self._launch_btn = tk.Button(
            btn_frame, text="Launch ExileHUD", command=self._launch,
            bg=GREEN, fg="#0a1a0a", font=("Segoe UI", 11, "bold"),
            relief="flat", padx=24, pady=6,
            activebackground="#4aaa5e", activeforeground="#0a1a0a",
            cursor="hand2"
        )
        # Hidden until install completes

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------

    def _browse(self):
        path = filedialog.askdirectory(title="Choose install folder",
                                       initialdir=os.path.expanduser("~"))
        if path:
            self._folder_var.set(os.path.normpath(path) + os.sep + APP_NAME)

    def _log_line(self, text: str):
        self._log.configure(state="normal")
        self._log.insert("end", text + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def _set_status(self, text: str, color: str = DIM):
        self._status.configure(text=text, fg=color)

    def _set_progress(self, pct: float):
        self._bar["value"] = pct

    # ------------------------------------------------------------------
    # Install flow
    # ------------------------------------------------------------------

    def _start_install(self):
        self._install_btn.configure(state="disabled")
        self._cancel_btn.configure(state="disabled")
        threading.Thread(target=self._install_thread, daemon=True).start()

    def _install_thread(self):
        try:
            dest = self._folder_var.get()
            self._run(dest)
            self.after(0, self._on_success, dest)
        except Exception as exc:
            self.after(0, self._on_error, str(exc))

    def _run(self, dest: str):
        # ── Step 1: download repo ZIP ──────────────────────────────────
        self._ui("Downloading ExileHUD…", 5)
        tmp = tempfile.mkdtemp()
        zip_path = os.path.join(tmp, "exilehud.zip")
        self._download(REPO_ZIP, zip_path, progress_start=5, progress_end=40)

        # ── Step 2: extract ────────────────────────────────────────────
        self._ui("Extracting files…", 40)
        if os.path.exists(dest):
            shutil.rmtree(dest)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp)
        extracted = os.path.join(tmp, REPO_SUBDIR)
        shutil.copytree(extracted, dest)
        shutil.rmtree(tmp)
        self._log_line(f"Installed to: {dest}")
        self._ui("Files extracted.", 45)

        # ── Step 3: install Python deps ────────────────────────────────
        self._ui("Installing Python dependencies…", 47)
        req_file = os.path.join(dest, "requirements.txt")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", req_file, "--quiet"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"pip install failed:\n{result.stderr[:400]}")
        self._log_line("Dependencies installed.")
        self._ui("Dependencies ready.", 65)

        # ── Step 4: write config ───────────────────────────────────────
        self._ui("Writing config…", 67)
        self._write_config(dest)

        # ── Step 5: write run.bat ──────────────────────────────────────
        bat_path = os.path.join(dest, "run.bat")
        with open(bat_path, "w") as f:
            f.write(f'@echo off\n"{sys.executable}" "{os.path.join(dest, "main.py")}"\n')

        # ── Step 6: passive tree data ─────────────────────────────────
        self._ui("Downloading passive tree data…", 70)
        tree_path = os.path.join(dest, "data", "passive_tree.json")
        if not os.path.exists(tree_path):
            try:
                self._download(TREE_FALLBACK, tree_path, progress_start=70, progress_end=90)
                self._log_line("Passive tree data downloaded.")
            except Exception as e:
                self._log_line(f"Warning: could not download tree data: {e}")
                self._log_line("Run 'python -m modules.passive_tree --download' later.")
        else:
            self._log_line("Passive tree data already present.")
        self._ui("Tree data ready.", 90)

        # ── Step 7: shortcuts ─────────────────────────────────────────
        if self._shortcut_var.get():
            self._create_shortcut(dest, "Desktop")
        if self._startmenu_var.get():
            self._create_shortcut(dest, "StartMenu")
        self._ui("Done!", 100)

    def _download(self, url: str, dest_path: str, progress_start=0, progress_end=100):
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "ExileHUD-Installer/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk = 8192
            with open(dest_path, "wb") as f:
                while True:
                    block = resp.read(chunk)
                    if not block:
                        break
                    f.write(block)
                    downloaded += len(block)
                    if total:
                        frac = downloaded / total
                        pct = progress_start + frac * (progress_end - progress_start)
                        self.after(0, self._set_progress, pct)

    def _write_config(self, dest: str):
        state_dir = os.path.join(dest, "state")
        os.makedirs(state_dir, exist_ok=True)
        config_path = os.path.join(state_dir, "config.json")
        if os.path.exists(config_path):
            return
        candidates = [
            r"C:\Program Files (x86)\Grinding Gear Games\Path of Exile\logs\Client.txt",
            r"C:\Program Files\Grinding Gear Games\Path of Exile\logs\Client.txt",
            os.path.expanduser(r"~\AppData\Local\Path of Exile\Client.txt"),
        ]
        log_path = next((p for p in candidates if os.path.exists(p)), candidates[0])
        defaults = {
            "poe_version": "poe1",
            "client_log_path": log_path,
            "league": "Standard",
            "overlay_screen": 0,
            "overlay_opacity": 0.92,
            "hotkeys": {
                "price_check":    "ctrl+d",
                "toggle_hud":     "ctrl+shift+h",
                "passive_tree":   "ctrl+shift+p",
                "crafting_queue": "ctrl+shift+c",
                "map_overlay":    "ctrl+shift+m",
            },
            "price_refresh_interval": 300,
        }
        with open(config_path, "w") as f:
            json.dump(defaults, f, indent=2)
        self._log_line(f"Config written. Log path: {log_path}")

    def _create_shortcut(self, dest: str, location: str):
        """Create a .bat launcher shortcut in Desktop or Start Menu."""
        try:
            if location == "Desktop":
                folder = os.path.join(os.path.expanduser("~"), "Desktop")
            else:
                folder = os.path.join(
                    os.environ.get("APPDATA", ""),
                    "Microsoft", "Windows", "Start Menu", "Programs"
                )
            os.makedirs(folder, exist_ok=True)
            sc_path = os.path.join(folder, f"{APP_NAME}.bat")
            bat = os.path.join(dest, "run.bat")
            with open(sc_path, "w") as f:
                f.write(f'@echo off\nstart "" "{bat}"\n')
            self._log_line(f"Shortcut created: {sc_path}")
        except Exception as e:
            self._log_line(f"Warning: could not create {location} shortcut: {e}")

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _ui(self, status: str, pct: float):
        self.after(0, self._set_status, status, DIM)
        self.after(0, self._set_progress, pct)
        self.after(0, self._log_line, status)

    def _on_success(self, dest: str):
        self._set_status("Installation complete!", GREEN)
        self._log_line(f"\nExileHUD is ready at: {dest}")
        self._install_btn.pack_forget()
        self._launch_btn.pack(side="right", padx=(8, 0))
        self._cancel_btn.configure(text="Close", state="normal")
        self._install_dest = dest

    def _on_error(self, msg: str):
        self._set_status(f"Error: {msg}", RED)
        self._log_line(f"\nInstall failed: {msg}")
        self._install_btn.configure(state="normal", text="Retry")
        self._cancel_btn.configure(state="normal")

    def _launch(self):
        bat = os.path.join(self._install_dest, "run.bat")
        subprocess.Popen([bat], shell=True)
        self.destroy()


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = Installer()
    app.mainloop()
