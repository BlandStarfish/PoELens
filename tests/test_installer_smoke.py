"""
Installer smoke tests — no display required, runs on any platform.

Covers:
  - Release artifact structure  (PoELens-Setup.zip contains the exe)
  - Syntax validity             (installer_gui.py compiles cleanly)
  - Key build constants         (APP_NAME, repo, branch are correct)
  - Password gate logic         (_check_password rejects bad inputs)
  - Uninstaller content         (bat script contains required commands)
  - Analytics guard             (reporting never raises)
"""

import ast
import py_compile
import sys
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent


# ─────────────────────────────────────────────────────────────────────────────
# Release artifact
# ─────────────────────────────────────────────────────────────────────────────

class TestReleaseZip:
    def test_zip_exists(self):
        assert (ROOT / "PoELens-Setup.zip").exists(), (
            "PoELens-Setup.zip not found — run build_installer.bat to produce it."
        )

    def test_zip_contains_exe(self):
        with zipfile.ZipFile(ROOT / "PoELens-Setup.zip") as zf:
            names = zf.namelist()
        assert "PoELens-Setup.exe" in names, (
            f"PoELens-Setup.exe missing from zip. Contents: {names}"
        )

    def test_zip_not_empty(self):
        with zipfile.ZipFile(ROOT / "PoELens-Setup.zip") as zf:
            info = zf.getinfo("PoELens-Setup.exe")
        assert info.file_size > 1_000_000, (
            f"PoELens-Setup.exe suspiciously small: {info.file_size} bytes"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Source validity
# ─────────────────────────────────────────────────────────────────────────────

class TestInstallerSource:
    GUI = ROOT / "installer_gui.py"

    def test_syntax_valid(self):
        """installer_gui.py must compile without errors."""
        py_compile.compile(str(self.GUI), doraise=True)

    def test_app_name_constant(self):
        """APP_NAME must be 'PoELens' — used in shortcuts, window titles, uninstaller."""
        src = self.GUI.read_text(encoding="utf-8")
        tree = ast.parse(src)
        app_name = None
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "APP_NAME":
                        if isinstance(node.value, ast.Constant):
                            app_name = node.value.value
        assert app_name == "PoELens", f"APP_NAME is '{app_name}', expected 'PoELens'"

    def test_github_owner_constant(self):
        src = self.GUI.read_text(encoding="utf-8")
        assert 'GITHUB_OWNER  = "BlandStarfish"' in src or \
               'GITHUB_OWNER = "BlandStarfish"' in src, \
               "GITHUB_OWNER must be 'BlandStarfish'"

    def test_github_repo_constant(self):
        src = self.GUI.read_text(encoding="utf-8")
        assert 'GITHUB_REPO   = "PoELens"' in src or \
               'GITHUB_REPO = "PoELens"' in src, \
               "GITHUB_REPO must be 'PoELens'"

    def test_report_token_placeholder_present(self):
        """GITHUB_REPORT_TOKEN must exist so inject_password.py can patch it."""
        src = self.GUI.read_text(encoding="utf-8")
        assert "GITHUB_REPORT_TOKEN" in src, (
            "GITHUB_REPORT_TOKEN constant missing — inject_password.py won't be able to inject it"
        )

    def test_no_hardcoded_secrets(self):
        """No actual GitHub tokens should ever appear in the committed source."""
        src = self.GUI.read_text(encoding="utf-8")
        # Fine-grained PATs start with "github_pat_"; classic tokens are 40 hex chars
        import re
        assert not re.search(r'github_pat_[A-Za-z0-9_]{20,}', src), \
            "Hardcoded fine-grained PAT found in installer_gui.py!"
        assert not re.search(r'ghp_[A-Za-z0-9]{36}', src), \
            "Hardcoded classic GitHub token found in installer_gui.py!"


# ─────────────────────────────────────────────────────────────────────────────
# Password gate logic (pure function — no display needed)
# ─────────────────────────────────────────────────────────────────────────────

class TestPasswordGate:
    def test_wrong_password_rejected(self, installer_module):
        assert not installer_module._check_password("wrong_password")

    def test_empty_password_rejected(self, installer_module):
        assert not installer_module._check_password("")

    def test_sql_injection_rejected(self, installer_module):
        assert not installer_module._check_password("' OR '1'='1")

    def test_null_bytes_rejected(self, installer_module):
        assert not installer_module._check_password("\x00\x00\x00")

    def test_known_correct_hash_accepts(self, installer_module):
        """
        Verify that _check_password correctly validates a known good hash.
        We test the hash round-trip rather than a specific password so we
        don't embed the real password in the test suite.
        """
        import hashlib, secrets
        salt    = secrets.token_hex(16)
        pw      = "test_password_for_hash_roundtrip"
        hashed  = hashlib.sha256((salt + pw).encode()).hexdigest()

        # Temporarily patch the constants
        original_salt = installer_module._PW_SALT
        original_hash = installer_module._PW_HASH
        try:
            installer_module._PW_SALT = salt
            installer_module._PW_HASH = hashed
            assert installer_module._check_password(pw)
            assert not installer_module._check_password(pw + "x")
        finally:
            installer_module._PW_SALT = original_salt
            installer_module._PW_HASH = original_hash


# ─────────────────────────────────────────────────────────────────────────────
# Uninstaller content  (source inspection — platform independent)
#
# Installer inherits from tk.Tk, which under the tkinter mock cannot be
# instantiated via object.__new__.  Instead we extract the method source
# and verify the bat-script template contains the required commands.
# ─────────────────────────────────────────────────────────────────────────────

def _uninstaller_method_src() -> str:
    """Return the source text of the _write_uninstaller method."""
    import re
    src = (ROOT / "installer_gui.py").read_text(encoding="utf-8")
    # Match from 'def _write_uninstaller' up to (but not including) the next
    # method definition at the same indentation level.
    match = re.search(
        r"(    def _write_uninstaller\b.*?)(?=\n    def |\Z)",
        src,
        re.DOTALL,
    )
    assert match, "_write_uninstaller method not found in installer_gui.py"
    return match.group(1)


class TestUninstaller:
    def test_uninstaller_method_present(self):
        src = (ROOT / "installer_gui.py").read_text(encoding="utf-8")
        assert "_write_uninstaller" in src, \
            "_write_uninstaller method missing from installer_gui.py"

    def test_uninstaller_called_from_do_install(self):
        src = (ROOT / "installer_gui.py").read_text(encoding="utf-8")
        assert "self._write_uninstaller(dest)" in src, \
            "_write_uninstaller must be called from _do_install"

    def test_uninstaller_filename(self):
        src = _uninstaller_method_src()
        assert "Uninstall PoELens.bat" in src, \
            "Uninstaller bat file must be named 'Uninstall PoELens.bat'"

    def test_uninstaller_kills_processes(self):
        src = _uninstaller_method_src()
        assert "taskkill" in src.lower(), \
            "Uninstaller must kill running processes"

    def test_uninstaller_removes_shortcuts(self):
        src = _uninstaller_method_src()
        assert "del" in src and "PoELens.bat" in src, \
            "Uninstaller must remove Desktop/Start Menu shortcuts"

    def test_uninstaller_removes_install_dir(self):
        src = _uninstaller_method_src()
        assert "rd /s /q" in src, \
            "Uninstaller must recursively delete the install directory"

    def test_uninstaller_prompts_before_deleting(self):
        src = _uninstaller_method_src()
        assert "CONFIRM" in src, \
            "Uninstaller must ask the user for confirmation before deleting"

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only — requires real tkinter")
    def test_uninstaller_file_written_at_runtime(self):
        """End-to-end: actually call _write_uninstaller and verify the file."""
        import types, installer_gui as ig  # noqa: PLC0415

        inst = types.SimpleNamespace(after=lambda *a, **kw: None)
        with tempfile.TemporaryDirectory() as tmp:
            ig.Installer._write_uninstaller(inst, tmp)
            bat = Path(tmp) / "Uninstall PoELens.bat"
            assert bat.exists(), "Uninstall PoELens.bat was not created at runtime"
            content = bat.read_text()
        assert "taskkill" in content.lower()
        assert "rd /s /q" in content


# ─────────────────────────────────────────────────────────────────────────────
# Analytics / reporting guard  (source inspection + Windows runtime check)
# ─────────────────────────────────────────────────────────────────────────────

def _reporting_method_src() -> str:
    import re
    src = (ROOT / "installer_gui.py").read_text(encoding="utf-8")
    match = re.search(
        r"(    def _report_to_github\b.*?)(?=\n    def |\Z)",
        src,
        re.DOTALL,
    )
    assert match, "_report_to_github method not found in installer_gui.py"
    return match.group(1)


class TestReportingGuard:
    def test_report_method_present(self):
        src = (ROOT / "installer_gui.py").read_text(encoding="utf-8")
        assert "_report_to_github" in src

    def test_token_guard_present(self):
        """Method must return early when GITHUB_REPORT_TOKEN is empty."""
        src = _reporting_method_src()
        assert "not GITHUB_REPORT_TOKEN" in src or \
               "if not GITHUB_REPORT_TOKEN" in src, \
               "_report_to_github must return early when token is empty"

    def test_exception_swallowed(self):
        """Network errors must be silently swallowed — never crash the installer."""
        src = _reporting_method_src()
        assert "except Exception" in src and "pass" in src, \
            "_report_to_github must have except Exception: pass to silence errors"

    def test_path_sanitization_present(self):
        """Windows file paths must be stripped before being sent to GitHub."""
        src = _reporting_method_src()
        assert "re.sub" in src and "<path>" in src, \
            "_report_to_github must sanitize Windows paths before reporting"

    def test_called_on_failure(self):
        src = (ROOT / "installer_gui.py").read_text(encoding="utf-8")
        import re
        error_method = re.search(
            r"(    def _error\(self.*?)(?=\n    def |\Z)", src, re.DOTALL
        )
        assert error_method and "_report_to_github" in error_method.group(), \
            "_error() must call _report_to_github"

    def test_called_on_success(self):
        src = (ROOT / "installer_gui.py").read_text(encoding="utf-8")
        import re
        done_method = re.search(
            r"(    def _done\(self.*?)(?=\n    def |\Z)", src, re.DOTALL
        )
        assert done_method and "_report_to_github" in done_method.group(), \
            "_done() must call _report_to_github"

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_reporting_skipped_when_no_token(self, installer_module):
        """_report_to_github must silently do nothing when GITHUB_REPORT_TOKEN is empty."""
        import types, installer_gui as ig  # noqa: PLC0415

        inst = types.SimpleNamespace(
            _current_step="test",
            _is_reinstall=False,
            _folder=MagicMock(),
        )
        inst._folder.get.return_value = "C:\\FakeInstallDir"

        original = ig.GITHUB_REPORT_TOKEN
        try:
            ig.GITHUB_REPORT_TOKEN = ""
            ig.Installer._report_to_github(inst, "install_failure", "test error")
        finally:
            ig.GITHUB_REPORT_TOKEN = original

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_reporting_swallows_network_errors(self, installer_module):
        """_report_to_github must never crash the installer on network failure."""
        import types, installer_gui as ig  # noqa: PLC0415

        inst = types.SimpleNamespace(
            _current_step="test",
            _is_reinstall=False,
            _folder=MagicMock(),
        )
        inst._folder.get.return_value = "C:\\FakeInstallDir"

        with patch.object(ig, "GITHUB_REPORT_TOKEN", "fake_token_for_test"):
            with patch("urllib.request.urlopen", side_effect=OSError("network down")):
                ig.Installer._report_to_github(inst, "install_failure", "test")
