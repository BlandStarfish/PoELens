"""
ExileHUD GUI Installer
======================
Self-contained .exe. No Python required on target machine.

Flow:
  1. Pick install folder
  2. Download Python 3.11 embeddable runtime (~11 MB) — silent, no system install
  3. Download app source from GitHub
  4. pip install dependencies to the embedded runtime
  5. Download passive tree data
  6. Create Desktop / Start Menu shortcuts
  7. Launch button

Compile with:  build_installer.bat
"""

import os, sys, json, shutil, zipfile, threading, urllib.request
import subprocess, tempfile, tkinter as tk
from tkinter import ttk, filedialog

# ─────────────────────────────────────────────────────────────────────────────
# Constants — edit GITHUB_TOKEN before building for private repo support
# ─────────────────────────────────────────────────────────────────────────────

GITHUB_OWNER  = "BlandStarfish"
GITHUB_REPO   = "ExileHUD"
GITHUB_BRANCH = "master"
GITHUB_TOKEN  = ""   # ← paste a fine-grained read-only PAT here before building
                     #   leave blank once the repo is public

APP_NAME      = "ExileHUD"
DEFAULT_DEST  = os.path.join(os.path.expanduser("~"), APP_NAME)

PYTHON_EMBED_URL = (
    "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
)
GETPIP_URL = "https://bootstrap.pypa.io/get-pip.py"
TREE_URL   = (
    "https://raw.githubusercontent.com/grindinggear/"
    "skilltree-export/master/data.json"
)

# ─────────────────────────────────────────────────────────────────────────────
# Style
# ─────────────────────────────────────────────────────────────────────────────

BG = "#1a1a2e"; PANEL = "#16213e"; GOLD = "#e2b96f"
TEXT = "#d4c5a9"; DIM = "#8a7a65"; GREEN = "#5cba6e"; RED = "#e05050"

# ─────────────────────────────────────────────────────────────────────────────
# GitHub helpers
# ─────────────────────────────────────────────────────────────────────────────

def _gh_headers() -> dict:
    h = {"User-Agent": "ExileHUD-Installer/1.0"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h

def github_zip_url() -> str:
    return (
        f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/"
        f"archive/refs/heads/{GITHUB_BRANCH}.zip"
    )

# ─────────────────────────────────────────────────────────────────────────────
# Main window
# ─────────────────────────────────────────────────────────────────────────────

class Installer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} Setup")
        self.resizable(False, False)
        self.configure(bg=BG)
        self._center(560, 450)
        self._install_dest = None
        self._build()

    def _center(self, w, h):
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        hdr = tk.Frame(self, bg=PANEL, height=72)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr, text="ExileHUD", font=("Segoe UI", 22, "bold"),
                 bg=PANEL, fg=GOLD).pack(side="left", padx=20, pady=10)
        tk.Label(hdr, text="Path of Exile Overlay", font=("Segoe UI", 11),
                 bg=PANEL, fg=DIM).pack(side="left", pady=16)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=12)

        tk.Label(body, text="Install to:", bg=BG, fg=TEXT,
                 font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", pady=4)
        self._folder = tk.StringVar(value=DEFAULT_DEST)
        tk.Entry(body, textvariable=self._folder, width=40, bg=PANEL, fg=TEXT,
                 insertbackground=TEXT, relief="flat",
                 font=("Segoe UI", 10)).grid(row=0, column=1, padx=8, sticky="ew")
        tk.Button(body, text="Browse…", command=self._browse, bg="#2a2a4a",
                  fg=TEXT, relief="flat", activebackground="#3a3a5a",
                  cursor="hand2").grid(row=0, column=2)

        self._shortcut  = tk.BooleanVar(value=True)
        self._startmenu = tk.BooleanVar(value=True)
        for i, (var, label) in enumerate([
            (self._shortcut,  "Create Desktop shortcut"),
            (self._startmenu, "Add to Start Menu"),
        ], 1):
            tk.Checkbutton(body, text=label, variable=var, bg=BG, fg=TEXT,
                           selectcolor=PANEL, activebackground=BG,
                           activeforeground=GOLD, font=("Segoe UI", 10)
                           ).grid(row=i, column=0, columnspan=3, sticky="w", pady=1)
        body.columnconfigure(1, weight=1)

        pf = tk.Frame(self, bg=BG)
        pf.pack(fill="x", padx=24)
        self._status = tk.Label(pf, text="Ready to install.", anchor="w",
                                bg=BG, fg=DIM, font=("Segoe UI", 9))
        self._status.pack(fill="x")
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("G.Horizontal.TProgressbar",
                        troughcolor=PANEL, background=GOLD, borderwidth=0)
        self._bar = ttk.Progressbar(pf, style="G.Horizontal.TProgressbar",
                                    length=512, mode="determinate")
        self._bar.pack(fill="x", pady=3)

        self._log_box = tk.Text(self, bg=PANEL, fg=DIM, font=("Consolas", 9),
                                height=8, relief="flat", state="disabled",
                                wrap="word", padx=6, pady=4)
        self._log_box.pack(fill="x", padx=24, pady=(0, 6))

        bf = tk.Frame(self, bg=BG)
        bf.pack(fill="x", padx=24, pady=(0, 14))

        self._install_btn = tk.Button(
            bf, text="Install", command=self._start, bg=GOLD, fg="#1a1a2e",
            font=("Segoe UI", 11, "bold"), relief="flat", padx=24, pady=6,
            activebackground="#c8a84b", cursor="hand2")
        self._install_btn.pack(side="right", padx=(8, 0))

        self._cancel_btn = tk.Button(
            bf, text="Cancel", command=self.destroy, bg="#2a2a4a", fg=TEXT,
            font=("Segoe UI", 10), relief="flat", padx=16, pady=6,
            activebackground="#3a3a5a", cursor="hand2")
        self._cancel_btn.pack(side="right")

        self._launch_btn = tk.Button(
            bf, text="Launch ExileHUD  ▶", command=self._launch,
            bg=GREEN, fg="#0a1a0a", font=("Segoe UI", 11, "bold"),
            relief="flat", padx=24, pady=6, cursor="hand2")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _browse(self):
        path = filedialog.askdirectory(initialdir=os.path.expanduser("~"))
        if path:
            self._folder.set(os.path.normpath(path) + os.sep + APP_NAME)

    def _log(self, msg: str):
        self._log_box.configure(state="normal")
        self._log_box.insert("end", msg + "\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _ui(self, msg: str, pct: float):
        self.after(0, lambda: [
            self._status.configure(text=msg),
            self._bar.configure(value=pct),
            self._log(msg),
        ])

    def _set_pct(self, pct: float):
        self.after(0, lambda: self._bar.configure(value=pct))

    # ------------------------------------------------------------------
    # Install
    # ------------------------------------------------------------------

    def _start(self):
        self._install_btn.configure(state="disabled")
        self._cancel_btn.configure(state="disabled")
        threading.Thread(target=self._thread, daemon=True).start()

    def _thread(self):
        try:
            self._do_install()
            self.after(0, self._done)
        except Exception as e:
            self.after(0, self._error, str(e))

    def _do_install(self):
        dest    = self._folder.get()
        runtime = os.path.join(dest, ".runtime")   # embedded Python lives here
        python  = os.path.join(runtime, "python.exe")
        tmp     = tempfile.mkdtemp()

        try:
            # ── 1. Download embedded Python runtime ───────────────────
            self._ui("Downloading Python runtime (~11 MB)...", 3)
            embed_zip = os.path.join(tmp, "python_embed.zip")
            self._download(PYTHON_EMBED_URL, embed_zip, 3, 20)

            self._ui("Extracting Python runtime...", 20)
            os.makedirs(runtime, exist_ok=True)
            with zipfile.ZipFile(embed_zip, "r") as zf:
                zf.extractall(runtime)
            self.after(0, lambda: self._log("Python runtime ready."))

            # Enable site-packages in the embeddable distro
            pth_files = [f for f in os.listdir(runtime) if f.endswith("._pth")]
            for pf in pth_files:
                path = os.path.join(runtime, pf)
                content = open(path).read()
                if "#import site" in content:
                    open(path, "w").write(content.replace("#import site", "import site"))

            # ── 2. Bootstrap pip into the embedded runtime ────────────
            self._ui("Bootstrapping package manager...", 22)
            getpip = os.path.join(tmp, "get-pip.py")
            self._download(GETPIP_URL, getpip, 22, 26)
            r = subprocess.run(
                [python, getpip, "--quiet"],
                capture_output=True, text=True, timeout=120
            )
            if r.returncode != 0:
                raise RuntimeError(f"pip bootstrap failed:\n{r.stderr[:300]}")
            self.after(0, lambda: self._log("pip ready."))

            # ── 3. Download app source from GitHub ────────────────────
            self._ui("Downloading ExileHUD from GitHub...", 28)
            app_zip = os.path.join(tmp, "app.zip")
            req = urllib.request.Request(github_zip_url(), headers=_gh_headers())
            # Test for 404 early and give a clear message
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    if resp.status == 404:
                        raise RuntimeError(
                            "Could not access the ExileHUD repository (404).\n"
                            "The repo may be private. Contact the developer for access."
                        )
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    raise RuntimeError(
                        "Repository access denied (404). "
                        "If this is a private repo, a valid GITHUB_TOKEN must be embedded in this installer."
                    )
                raise
            self._download(github_zip_url(), app_zip, 28, 45,
                           extra_headers=_gh_headers())

            self._ui("Extracting app files...", 45)
            with zipfile.ZipFile(app_zip, "r") as zf:
                zf.extractall(tmp)
            # GitHub ZIP extracts to REPO-BRANCH/ subfolder
            extracted = os.path.join(tmp, f"{GITHUB_REPO}-{GITHUB_BRANCH}")
            if os.path.exists(dest):
                # Preserve .runtime and state/ if updating
                shutil.rmtree(dest, ignore_errors=True)
            shutil.copytree(extracted, dest)
            # Restore runtime (we extracted it above, before dest was wiped)
            if not os.path.exists(runtime):
                os.makedirs(runtime, exist_ok=True)
            self.after(0, lambda: self._log(f"App files installed to: {dest}"))

            # ── 4. Install Python packages ────────────────────────────
            self._ui("Installing packages (this takes ~1 min first time)...", 48)
            req_file = os.path.join(dest, "requirements.txt")
            pip = os.path.join(runtime, "Scripts", "pip.exe")
            r = subprocess.run(
                [pip, "install", "-r", req_file, "--quiet",
                 f"--prefix={runtime}"],
                capture_output=True, text=True, timeout=300
            )
            if r.returncode != 0:
                raise RuntimeError(f"Package install failed:\n{r.stderr[:500]}")
            self._ui("Packages installed.", 70)

            # ── 5. Write config + run.bat ─────────────────────────────
            self._ui("Writing config...", 72)
            self._write_config(dest)
            bat = os.path.join(dest, "run.bat")
            with open(bat, "w") as f:
                f.write(
                    f'@echo off\n'
                    f'set PYTHONPATH={runtime}\\Lib\\site-packages\n'
                    f'"{python}" "{os.path.join(dest, "main.py")}"\n'
                )
            # Write version file for updater
            self._write_version(dest)

            # ── 6. Passive tree data ──────────────────────────────────
            self._ui("Downloading passive tree data...", 75)
            tree_path = os.path.join(dest, "data", "passive_tree.json")
            if not os.path.exists(tree_path):
                try:
                    self._download(TREE_URL, tree_path, 75, 92)
                    self.after(0, lambda: self._log("Passive tree data saved."))
                except Exception as e:
                    self.after(0, lambda: self._log(f"Warning: tree download failed: {e}"))
            self._ui("Tree data ready.", 93)

            # ── 7. Shortcuts ──────────────────────────────────────────
            if self._shortcut.get():
                self._make_shortcut(dest, "Desktop")
            if self._startmenu.get():
                self._make_shortcut(dest, "StartMenu")

            self._install_dest = dest

        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        self._ui("Done!", 100)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _download(self, url, path, p0, p1, extra_headers=None):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        headers = {"User-Agent": "ExileHUD-Installer/1.0"}
        if extra_headers:
            headers.update(extra_headers)
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=120) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            done = 0
            with open(path, "wb") as f:
                while chunk := resp.read(16384):
                    f.write(chunk)
                    done += len(chunk)
                    if total:
                        self._set_pct(p0 + (done / total) * (p1 - p0))

    def _write_config(self, dest):
        state_dir = os.path.join(dest, "state")
        os.makedirs(state_dir, exist_ok=True)
        cfg = os.path.join(state_dir, "config.json")
        if os.path.exists(cfg):
            return
        candidates = [
            r"C:\Program Files (x86)\Grinding Gear Games\Path of Exile\logs\Client.txt",
            r"C:\Program Files\Grinding Gear Games\Path of Exile\logs\Client.txt",
            os.path.expanduser(r"~\AppData\Local\Path of Exile\Client.txt"),
        ]
        log_path = next((p for p in candidates if os.path.exists(p)), candidates[0])
        with open(cfg, "w") as f:
            json.dump({
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
            }, f, indent=2)
        self.after(0, lambda: self._log(f"Config written (PoE log: {log_path})"))

    def _write_version(self, dest):
        """Fetch current commit SHA and write to state/version.json for updater."""
        try:
            api_url = (
                f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"
                f"/commits/{GITHUB_BRANCH}"
            )
            req = urllib.request.Request(api_url, headers={
                **_gh_headers(), "Accept": "application/vnd.github.v3+json"
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            sha = data.get("sha", "unknown")
        except Exception:
            sha = "unknown"
        ver_path = os.path.join(dest, "state", "version.json")
        with open(ver_path, "w") as f:
            json.dump({"sha": sha, "branch": GITHUB_BRANCH}, f)

    def _make_shortcut(self, dest, location):
        try:
            folder = (
                os.path.join(os.path.expanduser("~"), "Desktop")
                if location == "Desktop"
                else os.path.join(
                    os.environ.get("APPDATA", ""),
                    "Microsoft", "Windows", "Start Menu", "Programs"
                )
            )
            os.makedirs(folder, exist_ok=True)
            sc = os.path.join(folder, f"{APP_NAME}.bat")
            bat = os.path.join(dest, "run.bat")
            with open(sc, "w") as f:
                f.write(f'@echo off\nstart "" "{bat}"\n')
            self.after(0, lambda: self._log(f"Shortcut: {sc}"))
        except Exception as e:
            self.after(0, lambda: self._log(f"Warning: shortcut failed ({location}): {e}"))

    def _done(self):
        self._status.configure(text="Installation complete!", fg=GREEN)
        self._install_btn.pack_forget()
        self._launch_btn.pack(side="right", padx=(8, 0))
        self._cancel_btn.configure(text="Close", state="normal")

    def _error(self, msg):
        self._status.configure(text="Installation failed — see log below", fg=RED)
        self._log(f"\nFAILED: {msg}")
        self._install_btn.configure(state="normal", text="Retry")
        self._cancel_btn.configure(state="normal")

    def _launch(self):
        if self._install_dest:
            subprocess.Popen(
                [os.path.join(self._install_dest, "run.bat")], shell=True
            )
        self.destroy()


if __name__ == "__main__":
    Installer().mainloop()
