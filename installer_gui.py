"""
PoELens GUI Installer
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

import hashlib, os, sys, json, shutil, time, zipfile, threading, urllib.request, socket, platform
import subprocess, tempfile, tkinter as tk
from tkinter import ttk, filedialog
from datetime import datetime, timezone

# ─────────────────────────────────────────────────────────────────────────────
# Build constants
# ─────────────────────────────────────────────────────────────────────────────

GITHUB_OWNER  = "BlandStarfish"
GITHUB_REPO   = "PoELens"
GITHUB_BRANCH = "master"
GITHUB_TOKEN  = ""   # empty = public repo (no auth needed)

APP_NAME      = "PoELens"
DEFAULT_DEST  = os.path.join(os.path.expanduser("~"), APP_NAME)

# Discord webhook for anonymous install analytics (see README for disclosure).
# Set to "" to disable analytics in the build.
ANALYTICS_WEBHOOK_URL = ""

# ─────────────────────────────────────────────────────────────────────────────
# Password protection
# ─────────────────────────────────────────────────────────────────────────────

_PW_SALT = "e36a127b9e4d4dacdbf4c888a412c597"
_PW_HASH = "195f1db775f438a4d64271385eb4b44e0d944d65e58bdca20127c76b7837a78d"

def _check_password(entered: str) -> bool:
    h = hashlib.sha256((_PW_SALT + entered).encode("utf-8")).hexdigest()
    return h == _PW_HASH


# ─────────────────────────────────────────────────────────────────────────────
# Password gate — shown before the main installer window
# ─────────────────────────────────────────────────────────────────────────────

class PasswordGate(tk.Tk):
    """Blocks access until the correct password is entered."""

    MAX_ATTEMPTS = 3

    def __init__(self):
        super().__init__()
        self.title("PoELens Setup")
        self.resizable(False, False)
        self.configure(bg=BG)
        self._attempts = 0
        self.granted = False
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"340x220+{(sw-340)//2}+{(sh-220)//2}")
        self._build()

    def _build(self):
        tk.Frame(self, bg=PANEL, height=56).pack(fill="x")
        hdr = self.children[list(self.children)[-1]]
        tk.Label(hdr, text="PoELens Setup", font=("Segoe UI", 16, "bold"),
                 bg=PANEL, fg=GOLD).pack(side="left", padx=16, pady=8)
        tk.Label(hdr, text="Access Required", font=("Segoe UI", 10),
                 bg=PANEL, fg=DIM).pack(side="left", pady=12)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=16)

        tk.Label(body, text="Enter installer password:",
                 bg=BG, fg=TEXT, font=("Segoe UI", 10)).pack(anchor="w")

        self._pw_var = tk.StringVar()
        pw_entry = tk.Entry(body, textvariable=self._pw_var, show="•",
                            bg=PANEL, fg=TEXT, insertbackground=TEXT,
                            relief="flat", font=("Segoe UI", 12))
        pw_entry.pack(fill="x", pady=(4, 8))
        pw_entry.focus_set()
        pw_entry.bind("<Return>", lambda _: self._submit())

        self._msg = tk.Label(body, text="", bg=BG, fg=RED,
                             font=("Segoe UI", 9))
        self._msg.pack(anchor="w")

        btn_row = tk.Frame(body, bg=BG)
        btn_row.pack(fill="x", pady=(8, 0))
        tk.Button(btn_row, text="Cancel", command=self.destroy,
                  bg="#2a2a4a", fg=TEXT, relief="flat", padx=12, pady=5,
                  cursor="hand2").pack(side="right", padx=(6, 0))
        tk.Button(btn_row, text="Continue →", command=self._submit,
                  bg=GOLD, fg="#1a1a2e", font=("Segoe UI", 10, "bold"),
                  relief="flat", padx=12, pady=5,
                  cursor="hand2").pack(side="right")

    def _submit(self):
        pw = self._pw_var.get()
        if _check_password(pw):
            self.granted = True
            self.destroy()
        else:
            self._attempts += 1
            remaining = self.MAX_ATTEMPTS - self._attempts
            if remaining <= 0:
                self.destroy()
            else:
                self._msg.configure(
                    text=f"Incorrect password. {remaining} attempt{'s' if remaining > 1 else ''} remaining."
                )
                self._pw_var.set("")

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

def _send_analytics(event: str):
    """Fire-and-forget anonymous install analytics. See README for full disclosure."""
    if not ANALYTICS_WEBHOOK_URL:
        return
    try:
        anon_id = hashlib.sha256(
            socket.gethostname().encode("utf-8")
        ).hexdigest()[:16]
        os_info = f"{platform.system()} {platform.release()}"
        payload = {
            "embeds": [{
                "title": f"{APP_NAME} — {event}",
                "color": 0xe2b96f,
                "fields": [
                    {"name": "event",     "value": event,   "inline": True},
                    {"name": "anon_id",   "value": anon_id, "inline": True},
                    {"name": "os",        "value": os_info, "inline": True},
                    {"name": "timestamp", "value": datetime.now(timezone.utc).isoformat(), "inline": True},
                ],
            }]
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            ANALYTICS_WEBHOOK_URL, data=body,
            headers={"Content-Type": "application/json", "User-Agent": f"{APP_NAME}/installer"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


def _gh_headers() -> dict:
    h = {"User-Agent": "PoELens-Installer/1.0", "Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h

def github_zip_url() -> str:
    # Use the GitHub API zipball endpoint — supports Bearer token auth for private repos.
    # The web archive URL (github.com/…/archive/…zip) requires browser session cookies
    # and does NOT support Authorization header auth.
    return (
        f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"
        f"/zipball/{GITHUB_BRANCH}"
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
        self._center(560, 520)
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
        tk.Label(hdr, text="PoELens", font=("Segoe UI", 22, "bold"),
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

        tk.Label(body, text="League:", bg=BG, fg=TEXT,
                 font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w", pady=4)
        self._league = tk.StringVar(value="Mirage")
        tk.Entry(body, textvariable=self._league, width=24, bg=PANEL, fg=TEXT,
                 insertbackground=TEXT, relief="flat",
                 font=("Segoe UI", 10)).grid(row=1, column=1, padx=8, sticky="w")
        tk.Label(body, text="(current league name)", bg=BG, fg=DIM,
                 font=("Segoe UI", 9)).grid(row=1, column=2, sticky="w")

        tk.Label(body, text="OAuth client_id:", bg=BG, fg=TEXT,
                 font=("Segoe UI", 10)).grid(row=2, column=0, sticky="w", pady=4)
        self._oauth_client_id = tk.StringVar(value="")
        tk.Entry(body, textvariable=self._oauth_client_id, width=32, bg=PANEL, fg=TEXT,
                 insertbackground=TEXT, relief="flat",
                 font=("Segoe UI", 10)).grid(row=2, column=1, padx=8, sticky="ew")
        tk.Label(body, text="(optional, for stash auto-fill)", bg=BG, fg=DIM,
                 font=("Segoe UI", 9)).grid(row=2, column=2, sticky="w")

        self._shortcut  = tk.BooleanVar(value=True)
        self._startmenu = tk.BooleanVar(value=True)
        for i, (var, label) in enumerate([
            (self._shortcut,  "Create Desktop shortcut"),
            (self._startmenu, "Add to Start Menu"),
        ], 3):
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
            bf, text="Launch PoELens  ▶", command=self._launch,
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
        tmp     = tempfile.mkdtemp()

        # Extract Python runtime into tmp first — dest will be wiped when the
        # app archive is installed, so we can't put the runtime there yet.
        runtime_tmp = os.path.join(tmp, ".runtime")
        python_tmp  = os.path.join(runtime_tmp, "python.exe")

        try:
            # ── 1. Download embedded Python runtime ───────────────────
            self._ui("Downloading Python runtime (~11 MB)...", 3)
            embed_zip = os.path.join(tmp, "python_embed.zip")
            self._download(PYTHON_EMBED_URL, embed_zip, 3, 20)

            self._ui("Extracting Python runtime...", 20)
            os.makedirs(runtime_tmp, exist_ok=True)
            with zipfile.ZipFile(embed_zip, "r") as zf:
                zf.extractall(runtime_tmp)
            self.after(0, lambda: self._log("Python runtime ready."))

            # Enable site-packages in the embeddable distro
            pth_files = [f for f in os.listdir(runtime_tmp) if f.endswith("._pth")]
            for pf in pth_files:
                path = os.path.join(runtime_tmp, pf)
                content = open(path).read()
                if "#import site" in content:
                    open(path, "w").write(content.replace("#import site", "import site"))

            # ── 2. Bootstrap pip into the embedded runtime ────────────
            self._ui("Bootstrapping package manager...", 22)
            getpip = os.path.join(tmp, "get-pip.py")
            self._download(GETPIP_URL, getpip, 22, 26)
            r = subprocess.run(
                [python_tmp, getpip, "--quiet"],
                capture_output=True, text=True, timeout=120
            )
            if r.returncode != 0:
                raise RuntimeError(f"pip bootstrap failed:\n{r.stderr[:300]}")
            self.after(0, lambda: self._log("pip ready."))

            # ── 3. Download app source from GitHub ────────────────────
            self._ui("Downloading PoELens from GitHub...", 28)
            app_zip = os.path.join(tmp, "app.zip")
            try:
                self._download(github_zip_url(), app_zip, 28, 45,
                               extra_headers=_gh_headers())
            except urllib.error.HTTPError as e:
                if e.code in (401, 403):
                    raise RuntimeError(
                        f"GitHub returned {e.code} — access denied.\n"
                        "The repository is private and the embedded token was rejected.\n"
                        "Contact the developer for an updated installer."
                    )
                if e.code == 404:
                    raise RuntimeError(
                        "Repository not found (404). "
                        "Contact the developer for an updated installer."
                    )
                raise

            self._ui("Extracting app files...", 45)
            with zipfile.ZipFile(app_zip, "r") as zf:
                zf.extractall(tmp)
            # GitHub's zipball API names the root dir {owner}-{repo}-{sha} — find it dynamically
            subdirs = [d for d in os.listdir(tmp)
                       if os.path.isdir(os.path.join(tmp, d)) and d != ".runtime"]
            if not subdirs:
                raise RuntimeError("App archive has unexpected structure — no directory found.")
            extracted = os.path.join(tmp, subdirs[0])
            if os.path.exists(dest):
                # Terminate any running PoELens processes before wiping the folder.
                # If python.exe has files open under dest, rmtree will silently fail
                # and the subsequent copytree will crash with FileExistsError.
                self.after(0, lambda: self._log("Stopping any running PoELens processes..."))
                subprocess.run(
                    ["taskkill", "/F", "/IM", "python.exe", "/FI",
                     f"WINDOWTITLE eq PoELens*"],
                    capture_output=True,
                )
                # Also check for a compiled PoELens.exe in case future builds exist
                subprocess.run(
                    ["taskkill", "/F", "/IM", "PoELens.exe"],
                    capture_output=True,
                )
                time.sleep(1)   # let OS release file handles after process termination

                shutil.rmtree(dest, ignore_errors=False)

            shutil.copytree(extracted, dest)
            self.after(0, lambda: self._log(f"App files installed to: {dest}"))

            # ── Move runtime into dest now that the app tree is in place ──
            runtime = os.path.join(dest, ".runtime")
            python  = os.path.join(runtime, "python.exe")
            shutil.copytree(runtime_tmp, runtime)

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
            main_py = os.path.join(dest, "main.py")
            with open(bat, "w") as f:
                # set "VAR=VALUE" syntax handles spaces in paths on Windows.
                # cd /d ensures relative imports resolve correctly.
                f.write(
                    f'@echo off\n'
                    f'cd /d "{dest}"\n'
                    f'set "PYTHONPATH={runtime}\\Lib\\site-packages"\n'
                    f'"{python}" "{main_py}"\n'
                    f'if %errorlevel% neq 0 (\n'
                    f'    echo PoELens exited with an error. Check state\\crash_log.jsonl for details.\n'
                    f'    pause\n'
                    f')\n'
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
        headers = {"User-Agent": "PoELens-Installer/1.0"}
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
        config_data = {
            "poe_version": "poe1",
            "client_log_path": log_path,
            "league": self._league.get().strip() or "Mirage",
            "overlay_screen": 0,
            "overlay_opacity": 0.92,
            "hotkeys": {
                "price_check":    "ctrl+c",
                "toggle_hud":     "ctrl+shift+h",
                "passive_tree":   "ctrl+shift+p",
                "crafting_queue": "ctrl+shift+c",
                "map_overlay":    "ctrl+shift+m",
            },
            "price_refresh_interval": 300,
        }
        client_id = self._oauth_client_id.get().strip()
        if client_id:
            config_data["oauth_client_id"] = client_id
        with open(cfg, "w") as f:
            json.dump(config_data, f, indent=2)
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
        threading.Thread(target=_send_analytics, args=("install",), daemon=True).start()

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
    gate = PasswordGate()
    gate.mainloop()
    if not gate.granted:
        sys.exit(0)
    Installer().mainloop()
