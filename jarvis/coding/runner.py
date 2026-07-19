"""
Security-gated shell runner.

Runs shell commands inside the workspace with a timeout and captured output.
Every command requires the ``SHELL_EXEC`` capability (off by default) and is
audited, so the assistant cannot run arbitrary commands unless explicitly
enabled.
"""

from __future__ import annotations

import asyncio

from jarvis.security.manager import SecurityManager
from jarvis.security.policy import Capability

_MAX_OUTPUT = 20_000


class ShellRunner:
    """Runs shell commands in the workspace, gated by the security module."""

    def __init__(self, cwd: str, security: SecurityManager, timeout: float = 60.0) -> None:
        self.cwd = cwd
        self.security = security
        self.timeout = timeout

    async def run(self, command: str) -> str:
        """Execute ``command`` and return a formatted result."""
        command = (command or "").strip()
        if not command:
            return "No command provided."
        # Raises PermissionDenied if shell execution is disabled (and audits it).
        self.security.require(Capability.SHELL_EXEC, command)

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=self.cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
        except OSError as exc:
            return f"Failed to start command: {exc}"

        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), self.timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()  # reap the process to avoid dangling transports
            return f"Command timed out after {self.timeout:.0f}s."

        output = stdout.decode("utf-8", errors="replace")[:_MAX_OUTPUT]
        return f"(exit code {proc.returncode})\n{output}".rstrip()
