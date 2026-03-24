"""
OAuth 2.1 PKCE flow manager for GGG's Path of Exile OAuth API.

To use the stash tab API, register a client_id by emailing oauth@grindinggear.com.
Once registered, add it to state/config.json:
    {"oauth_client_id": "your_client_id_here"}

Required in-app disclaimer (shown in currency panel when connected):
  "This product isn't affiliated with or endorsed by Grinding Gear Games in any way."

Scopes used: account:stashes account:characters

Tokens are stored in state/oauth_tokens.json (gitignored — never committed).
"""

import base64
import hashlib
import json
import os
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

_AUTH_URL      = "https://www.pathofexile.com/oauth/authorize"
_TOKEN_URL     = "https://www.pathofexile.com/oauth/token"
_REDIRECT_HOST = "localhost"
_REDIRECT_PORT = 64738
_SCOPES        = "account:stashes account:characters"
_AUTH_TIMEOUT  = 120  # seconds user has to authorize in browser
_TOKENS_PATH   = os.path.join(os.path.dirname(__file__), "..", "state", "oauth_tokens.json")


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _pkce_pair() -> tuple[str, str]:
    """Generate (code_verifier, code_challenge) using PKCE S256 method."""
    verifier = _b64url(secrets.token_bytes(32))
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    return verifier, challenge


class OAuthManager:
    def __init__(self, client_id: str):
        self._client_id = client_id
        self._tokens: dict = self._load_tokens()

    @property
    def is_configured(self) -> bool:
        """True if a client_id has been set in config."""
        return bool(self._client_id)

    @property
    def is_authenticated(self) -> bool:
        """True if valid tokens are stored (not necessarily unexpired)."""
        return bool(self._tokens.get("access_token"))

    @property
    def account_name(self) -> str | None:
        """PoE account name from token response, or None."""
        return self._tokens.get("username")

    def get_access_token(self) -> str | None:
        """
        Return a valid access token, refreshing automatically if near expiry.
        Returns None if not authenticated or if refresh fails.
        """
        if not self._tokens.get("access_token"):
            return None
        exp = self._tokens.get("expires_at", 0)
        if time.time() >= exp - 60:  # refresh 60s before expiry
            if not self._do_refresh():
                return None
        return self._tokens.get("access_token")

    def start_auth_flow(self, on_complete=None, on_error=None):
        """
        Open the browser to GGG's OAuth authorization page and wait for callback.

        Starts a local HTTP server on port 64738 to receive the authorization code.
        The browser is opened automatically. The user has 2 minutes to authorize.

        on_complete(tokens: dict) — called from background thread on success.
        on_error(message: str)   — called from background thread on failure.
        """
        if not self._client_id:
            if on_error:
                on_error("No client_id configured. Add oauth_client_id to state/config.json.")
            return

        verifier, challenge = _pkce_pair()
        state_nonce = secrets.token_urlsafe(16)
        redirect_uri = f"http://{_REDIRECT_HOST}:{_REDIRECT_PORT}/callback"

        params = {
            "client_id":             self._client_id,
            "response_type":         "code",
            "scope":                 _SCOPES,
            "redirect_uri":          redirect_uri,
            "state":                 state_nonce,
            "code_challenge":        challenge,
            "code_challenge_method": "S256",
        }
        auth_url = f"{_AUTH_URL}?{urllib.parse.urlencode(params)}"

        threading.Thread(
            target=self._run_auth_server,
            args=(auth_url, state_nonce, redirect_uri, verifier, on_complete, on_error),
            daemon=True,
        ).start()

    def revoke(self):
        """Clear stored tokens (log out)."""
        self._tokens = {}
        self._save_tokens({})

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run_auth_server(self, auth_url, state_nonce, redirect_uri, verifier, on_complete, on_error):
        """Background thread: run local HTTP server, wait for OAuth callback."""
        result: dict = {}
        done = threading.Event()

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                if parsed.path == "/callback":
                    qs = urllib.parse.parse_qs(parsed.query)
                    if qs.get("state", [""])[0] != state_nonce:
                        result["error"] = "State mismatch — possible CSRF attack"
                    elif "code" in qs:
                        result["code"] = qs["code"][0]
                    else:
                        desc = qs.get("error_description", qs.get("error", ["Authorization cancelled"]))
                        result["error"] = desc[0] if desc else "Authorization cancelled"
                    html = (
                        b"<html><body style='font-family:sans-serif;"
                        b"background:#1a1a2e;color:#d4c5a9;padding:40px'>"
                        b"<h2 style='color:#e2b96f'>ExileHUD</h2>"
                        b"<p>Authentication complete. You may close this tab.</p>"
                        b"<p style='color:#8a7a65;font-size:12px'>"
                        b"This product isn't affiliated with or endorsed by "
                        b"Grinding Gear Games in any way.</p>"
                        b"</body></html>"
                    )
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.send_header("Content-Length", str(len(html)))
                    self.end_headers()
                    self.wfile.write(html)
                    done.set()
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, *_):
                pass  # suppress HTTP server access logs

        try:
            srv = HTTPServer((_REDIRECT_HOST, _REDIRECT_PORT), _Handler)
        except OSError as e:
            if on_error:
                on_error(f"Could not start local server on port {_REDIRECT_PORT}: {e}")
            return

        webbrowser.open(auth_url)
        srv.timeout = 1.0
        deadline = time.time() + _AUTH_TIMEOUT

        while not done.is_set() and time.time() < deadline:
            srv.handle_request()
        srv.server_close()

        if not done.is_set():
            if on_error:
                on_error(f"Authorization timed out — no response within {_AUTH_TIMEOUT}s.")
            return

        if "code" not in result:
            if on_error:
                on_error(result.get("error", "Authorization failed"))
            return

        tokens = self._exchange_code(result["code"], redirect_uri, verifier)
        if tokens:
            self._save_tokens(tokens)
            if on_complete:
                on_complete(tokens)
        else:
            if on_error:
                on_error("Token exchange failed — check your network connection.")

    def _exchange_code(self, code: str, redirect_uri: str, verifier: str) -> dict | None:
        body = urllib.parse.urlencode({
            "grant_type":    "authorization_code",
            "client_id":     self._client_id,
            "code":          code,
            "redirect_uri":  redirect_uri,
            "code_verifier": verifier,
        }).encode()
        req = urllib.request.Request(_TOKEN_URL, data=body, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        req.add_header("User-Agent", "ExileHUD/1.0")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                tokens = json.loads(resp.read())
            tokens["expires_at"] = time.time() + tokens.get("expires_in", 3600)
            return tokens
        except urllib.error.HTTPError as e:
            body_text = ""
            try:
                body_text = e.read().decode()[:200]
            except Exception:
                pass
            print(f"[OAuth] Token exchange HTTP {e.code}: {body_text}")
            return None
        except Exception as e:
            print(f"[OAuth] Token exchange failed: {e}")
            return None

    def _do_refresh(self) -> bool:
        refresh_token = self._tokens.get("refresh_token")
        if not refresh_token:
            return False
        body = urllib.parse.urlencode({
            "grant_type":    "refresh_token",
            "client_id":     self._client_id,
            "refresh_token": refresh_token,
        }).encode()
        req = urllib.request.Request(_TOKEN_URL, data=body, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        req.add_header("User-Agent", "ExileHUD/1.0")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                tokens = json.loads(resp.read())
            tokens["expires_at"] = time.time() + tokens.get("expires_in", 3600)
            # Preserve refresh token if not rotated by server
            if "refresh_token" not in tokens:
                tokens["refresh_token"] = refresh_token
            self._save_tokens(tokens)
            return True
        except Exception as e:
            print(f"[OAuth] Token refresh failed: {e}")
            return False

    def _load_tokens(self) -> dict:
        if os.path.exists(_TOKENS_PATH):
            try:
                with open(_TOKENS_PATH, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_tokens(self, tokens: dict):
        os.makedirs(os.path.dirname(_TOKENS_PATH), exist_ok=True)
        with open(_TOKENS_PATH, "w") as f:
            json.dump(tokens, f, indent=2)
        self._tokens = dict(tokens)
