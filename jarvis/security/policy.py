"""Security capabilities and audit records."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class Capability(str, Enum):
    """Categories of potentially dangerous actions the assistant can take."""

    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    SHELL_EXEC = "shell_exec"
    DESKTOP_CONTROL = "desktop_control"
    NETWORK = "network"


@dataclass
class AuditRecord:
    """A single audited action attempt."""

    capability: Capability
    action: str
    allowed: bool
    detail: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def format(self) -> str:
        verdict = "ALLOW" if self.allowed else "DENY"
        return (
            f"{self.timestamp.isoformat()} | {verdict:5} | "
            f"{self.capability.value} | {self.action} | {self.detail}"
        )
