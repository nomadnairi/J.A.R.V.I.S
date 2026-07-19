"""
Coding assistant.

Gives the assistant a developer's hands: it reads and searches code through the
file manager, and can run shell commands and the project's tests through a
security-gated shell runner (shell execution is off by default).
"""

from jarvis.coding.runner import ShellRunner

__all__ = ["ShellRunner"]
