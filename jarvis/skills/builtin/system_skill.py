"""A skill that reports basic host/system diagnostics."""

from __future__ import annotations

import platform
import sys
from datetime import datetime

from jarvis import __version__
from jarvis.skills.base import BaseSkill, SkillResult
from jarvis.utils.text import tokenize_words

_TRIGGERS = {"status", "diagnostics", "system", "version", "health"}

# Recorded once at import so the skill can report process uptime.
_STARTED_AT = datetime.now()


class SystemSkill(BaseSkill):
    """Handles 'system status' / 'diagnostics' / 'version' requests."""

    name = "system"
    description = "Report assistant version and host diagnostics."
    priority = 40

    def can_handle(self, text: str) -> bool:
        return bool(_TRIGGERS & set(tokenize_words(text)))

    def handle(self, text: str, context: dict | None = None) -> SkillResult:
        uptime = datetime.now() - _STARTED_AT
        minutes = int(uptime.total_seconds() // 60)
        report = (
            f"All systems nominal.\n"
            f"• Version: {__version__}\n"
            f"• Python: {platform.python_version()} ({sys.platform})\n"
            f"• Host: {platform.node()}\n"
            f"• Uptime: {minutes} min"
        )
        return SkillResult(text=report, metadata={"uptime_min": minutes})
