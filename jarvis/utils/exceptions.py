"""
Central exception hierarchy for J.A.R.V.I.S.

Every layer raises a subclass of :class:`JarvisError` so callers can catch
errors at whatever granularity they need — a single ``except JarvisError``
at the top level, or precise handling per subsystem.
"""

from __future__ import annotations


class JarvisError(Exception):
    """Base class for all J.A.R.V.I.S. errors.

    Attributes:
        message: Human-readable description.
        details: Optional structured context for logging / telemetry.
    """

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:  # pragma: no cover - trivial
        if self.details:
            return f"{self.message} | {self.details}"
        return self.message


# --- Configuration -------------------------------------------------------
class ConfigError(JarvisError):
    """Invalid or missing configuration."""


# --- LLM layer -----------------------------------------------------------
class LLMError(JarvisError):
    """Base class for LLM-related failures."""


class LLMConfigError(LLMError):
    """Missing credentials or unknown provider/model."""


class LLMRequestError(LLMError):
    """The provider returned an error or the request failed."""


class LLMTimeoutError(LLMError):
    """The provider did not respond within the allotted time."""


class AllProvidersFailedError(LLMError):
    """Every configured provider (primary + fallbacks) failed."""


# --- Skills / plugins ----------------------------------------------------
class SkillError(JarvisError):
    """Base class for skill/plugin errors."""


class SkillNotFoundError(SkillError):
    """No registered skill matched the request."""


class SkillExecutionError(SkillError):
    """A skill raised an error while handling a request."""


class SkillRegistrationError(SkillError):
    """A skill could not be registered (duplicate name, bad definition)."""


# --- Memory (Stage 2) ----------------------------------------------------
class MemoryError(JarvisError):
    """Base class for memory-subsystem errors."""


# --- Integrations (Stage 4) ---------------------------------------------
class IntegrationError(JarvisError):
    """Base class for third-party integration errors."""


# --- Events --------------------------------------------------------------
class EventError(JarvisError):
    """Base class for event-bus errors."""
