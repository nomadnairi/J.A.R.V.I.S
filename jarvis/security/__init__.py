"""
Security module.

A single policy point that governs dangerous capabilities (file writes, shell
execution, desktop control) and keeps an audit trail. Powerful tools ask the
:class:`SecurityManager` for permission before acting, so the assistant is
**safe by default** — nothing risky runs unless it's explicitly enabled.
"""

from jarvis.security.manager import SecurityManager
from jarvis.security.policy import Capability

__all__ = ["SecurityManager", "Capability"]
