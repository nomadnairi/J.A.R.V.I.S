"""
Security self-audit.

A settings-only review of the deployment's security posture: which dangerous
capabilities are enabled, whether outward-facing surfaces are protected, and
whether secret-handling safeguards are on. Findings are graded so the startup
banner and ``/doctor`` can highlight anything that widens the attack surface.

This never inspects secret *values* — only whether protections are configured.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from jarvis.config.settings import Settings

Severity = Literal["high", "medium", "low", "info"]


@dataclass(frozen=True)
class SecurityFinding:
    severity: Severity
    area: str
    message: str

    @property
    def icon(self) -> str:
        return {"high": "🔴", "medium": "🟠", "low": "🟡", "info": "🔵"}[self.severity]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.icon} [{self.area}] {self.message}"


def audit_settings(settings: Settings) -> list[SecurityFinding]:
    """Return security findings for ``settings`` (most severe first)."""
    s = settings
    out: list[SecurityFinding] = []

    # Dangerous capabilities — off by default; flag when on.
    if s.allow_shell:
        out.append(SecurityFinding(
            "high", "shell",
            "ALLOW_SHELL is ON — the assistant can run shell commands."))
    if s.allow_desktop_control:
        out.append(SecurityFinding(
            "high", "desktop",
            "ALLOW_DESKTOP_CONTROL is ON — the assistant can control the desktop."))
    if s.allow_file_write:
        out.append(SecurityFinding(
            "medium", "files",
            "ALLOW_FILE_WRITE is ON — the assistant can modify files."))
    if s.allow_file_write and s.workspace_root in (".", ""):
        out.append(SecurityFinding(
            "medium", "sandbox",
            "File write is on and WORKSPACE_ROOT is the project dir — "
            "set it to a dedicated folder to limit blast radius."))

    # Outward-facing API without a key.
    if not s.api_key:
        out.append(SecurityFinding(
            "medium", "api",
            "API_KEY is empty — the HTTP API is unauthenticated. Set one for "
            "any non-local deployment."))
    if s.auth_enabled and not s.auth_admin_key:
        out.append(SecurityFinding(
            "low", "auth",
            "AUTH_ENABLED but AUTH_ADMIN_KEY is empty — admin HTTP endpoints "
            "are disabled (use the CLI)."))

    # Secret handling.
    if not s.memory_redact_secrets:
        out.append(SecurityFinding(
            "medium", "memory",
            "MEMORY_REDACT_SECRETS is OFF — tokens/keys in chat may be stored."))

    # Outbound Telegram posting.
    if s.telegram_send_enabled:
        out.append(SecurityFinding(
            "low", "telegram",
            "TELEGRAM_SEND_ENABLED is ON — the assistant can post to Telegram."))

    # Public bot (no allowlist).
    if s.telegram_bot_token and not s.telegram_allowlist():
        out.append(SecurityFinding(
            "info", "telegram",
            "No TELEGRAM_ALLOWED_USERS — the bot is open to everyone."))

    order = {"high": 0, "medium": 1, "low": 2, "info": 3}
    out.sort(key=lambda f: order[f.severity])
    return out


def worst_severity(findings: list[SecurityFinding]) -> Severity | None:
    for level in ("high", "medium", "low", "info"):
        if any(f.severity == level for f in findings):
            return level  # type: ignore[return-value]
    return None
