"""
Self-diagnostics.

A quick health report — LLM credentials, memory, integrations, security posture
and available tools — surfaced via the CLI ``/doctor`` command so misconfiguration
is obvious at a glance.
"""

from __future__ import annotations

from dataclasses import dataclass

from jarvis.security.policy import Capability


@dataclass
class Check:
    """One diagnostic result."""

    name: str
    ok: bool
    detail: str = ""


def diagnose(engine) -> list[Check]:
    """Run health checks against a constructed engine and return the results."""
    checks: list[Check] = []

    # LLM credentials / providers.
    providers = engine.llm.available_providers()
    checks.append(Check(
        "llm",
        bool(providers),
        f"providers: {', '.join(providers)}" if providers
        else "no API key configured — only local skills/tools will work",
    ))

    # Memory.
    checks.append(Check("memory", True,
                        "enabled" if engine.memory else "disabled"))

    # Goals.
    checks.append(Check("goals", True,
                        "enabled" if engine.goals else "disabled"))

    # Integrations.
    if engine.integrations is not None:
        for status in engine.integrations.statuses():
            checks.append(Check(
                f"integration:{status.name}",
                status.state.value not in ("error",),
                status.state.value + (f" ({status.detail})" if status.detail else ""),
            ))

    # Security posture (informational — off is the safe default).
    enabled = [c.value for c in (
        Capability.FILE_WRITE, Capability.SHELL_EXEC, Capability.DESKTOP_CONTROL)
        if engine.security.is_allowed(c)]
    checks.append(Check(
        "security", True,
        f"dangerous capabilities enabled: {', '.join(enabled)}" if enabled
        else "safe defaults (file write / shell / desktop OFF)",
    ))

    # Tools.
    count = engine.tools.count()
    checks.append(Check("tools", count > 0, f"{count} tools available"))

    # Configuration Manager — cross-field validation (errors fail the check).
    from jarvis.config.manager import ConfigManager
    issues = ConfigManager(engine.settings).validate()
    errors = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]
    if errors:
        detail = "; ".join(f"{i.key}: {i.message}" for i in errors)
    elif warnings:
        detail = "warnings — " + "; ".join(i.key for i in warnings)
    else:
        detail = "no issues"
    checks.append(Check("config", not errors, detail))

    return checks


def all_ok(checks: list[Check]) -> bool:
    return all(c.ok for c in checks)
