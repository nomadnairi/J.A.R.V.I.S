"""
Standalone J.A.R.V.I.S. API client for the Android app.

A copy of jarvis/desktop_app/api_client.py kept dependency-free (standard
library only) so the .apk does not need to bundle the whole jarvis package.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request


class ApiError(Exception):
    """The server rejected a request (carries the HTTP status)."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


class JarvisApiClient:
    """Talk to a remote J.A.R.V.I.S. server."""

    def __init__(self, base_url: str, *, token: str = "",
                timeout: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._timeout = timeout

    def _request(self, method: str, path: str,
                body: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(url, data=data, method=method)
        request.add_header("Content-Type", "application/json")
        if self.token:
            request.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                payload = json.loads(exc.read() or b"{}")
                detail = str(payload.get("detail", ""))
            except (json.JSONDecodeError, OSError):
                pass
            raise ApiError(exc.code, detail or f"HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise ApiError(0, f"Cannot reach server: {exc.reason}") from exc

    def login(self, username: str, password: str) -> str:
        out = self._request("POST", "/auth/login",
                            {"username": username, "password": password})
        self.token = out["token"]
        return self.token

    def me(self) -> dict:
        return self._request("GET", "/auth/me")

    def logout(self) -> None:
        try:
            self._request("POST", "/auth/logout")
        finally:
            self.token = ""

    def pairing_code(self) -> str:
        return self._request("POST", "/auth/pairing-code")["code"]

    def chat(self, message: str, session_id: str = "android") -> str:
        out = self._request("POST", "/chat",
                            {"message": message, "session_id": session_id})
        return out["reply"]
