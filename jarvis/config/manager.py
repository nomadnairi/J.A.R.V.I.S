"""
Configuration Manager — validates a :class:`Settings` instance and reports
misconfigurations in one place, so the app never has to re-check "is this key
set?" in scattered spots.

Pydantic already enforces *types and ranges* at load time; this layer checks
*cross-field consistency* ("provider is openrouter but no key", "image mode on
but no image key") and surfaces the results as a list of graded issues that the
startup banner, the ``/doctor`` diagnostics and the desktop app can display.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from jarvis.config.settings import Settings
from jarvis.llm.providers.local_provider import LOCAL_BACKENDS

Level = Literal["error", "warning", "info"]


@dataclass(frozen=True)
class ConfigIssue:
    """A single configuration finding."""

    level: Level
    key: str
    message: str

    @property
    def icon(self) -> str:
        return {"error": "❌", "warning": "⚠️", "info": "ℹ️"}[self.level]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.icon} [{self.key}] {self.message}"


class ConfigManager:
    """Cross-field validation over :class:`Settings`."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    # -- validation --------------------------------------------------------

    def validate(self) -> list[ConfigIssue]:
        issues: list[ConfigIssue] = []
        self._check_llm(issues)
        self._check_image(issues)
        self._check_search(issues)
        self._check_telegram(issues)
        return issues

    @property
    def ok(self) -> bool:
        """True when no error-level issues are present (warnings are fine)."""
        return not any(i.level == "error" for i in self.validate())

    def errors(self) -> list[ConfigIssue]:
        return [i for i in self.validate() if i.level == "error"]

    # -- individual checks -------------------------------------------------

    def _check_llm(self, issues: list[ConfigIssue]) -> None:
        s = self.settings
        provider = s.llm_provider
        if provider == "anthropic" and not s.anthropic_api_key:
            issues.append(ConfigIssue(
                "error", "ANTHROPIC_API_KEY",
                "LLM_PROVIDER=anthropic but no Anthropic key is set."))
        elif provider == "openai" and not s.openai_api_key:
            issues.append(ConfigIssue(
                "error", "OPENAI_API_KEY",
                "LLM_PROVIDER=openai but no OpenAI key is set."))
        elif provider == "openrouter":
            if not s.openrouter_api_key:
                issues.append(ConfigIssue(
                    "error", "OPENROUTER_API_KEY",
                    "LLM_PROVIDER=openrouter but no OpenRouter key is set."))
            if not s.openrouter_model:
                issues.append(ConfigIssue(
                    "error", "OPENROUTER_MODEL",
                    "OpenRouter needs a model slug (e.g. anthropic/claude-3.7-sonnet)."))
        elif provider == "local":
            if not s.local_llm_model:
                issues.append(ConfigIssue(
                    "error", "LOCAL_LLM_MODEL",
                    "LLM_PROVIDER=local but no model name is set."))
            if s.local_llm_backend == "custom" and not s.local_llm_base_url:
                issues.append(ConfigIssue(
                    "error", "LOCAL_LLM_BASE_URL",
                    "LOCAL_LLM_BACKEND=custom requires LOCAL_LLM_BASE_URL."))
            elif s.local_llm_backend in LOCAL_BACKENDS and not s.local_llm_base_url:
                url = LOCAL_BACKENDS[s.local_llm_backend]
                issues.append(ConfigIssue(
                    "info", "LOCAL_LLM_BASE_URL",
                    f"Using the {s.local_llm_backend} preset endpoint {url}."))

    def _check_image(self, issues: list[ConfigIssue]) -> None:
        s = self.settings
        if s.image_enabled and not (s.image_api_key or s.openai_api_key):
            issues.append(ConfigIssue(
                "warning", "IMAGE_API_KEY",
                "IMAGE_ENABLED=true but no image key (IMAGE_API_KEY / "
                "OPENAI_API_KEY) is set — image mode will fail."))

    def _check_search(self, issues: list[ConfigIssue]) -> None:
        s = self.settings
        if not s.search_enabled:
            return
        provider = s.search_provider
        keyed = {
            "tavily": s.tavily_api_key, "exa": s.exa_api_key,
            "brave": s.brave_api_key, "serpapi": s.serpapi_key,
            "google": s.google_cse_key, "perplexity": s.perplexity_api_key,
        }
        if provider in keyed and not keyed[provider]:
            issues.append(ConfigIssue(
                "warning", "SEARCH_PROVIDER",
                f"SEARCH_PROVIDER={provider} but its key is not set — "
                "search will fall back to DuckDuckGo (keyless)."))

    def _check_telegram(self, issues: list[ConfigIssue]) -> None:
        s = self.settings
        if not s.telegram_bot_token:
            issues.append(ConfigIssue(
                "warning", "TELEGRAM_BOT_TOKEN",
                "No bot token set — the Telegram bot will not start."))
        # An allowlist that omits every admin locks the owner out.
        allow = s.telegram_allowlist()
        admins = s.telegram_admins()
        if allow and admins and not (admins & allow):
            issues.append(ConfigIssue(
                "warning", "TELEGRAM_ALLOWED_USERS",
                "TELEGRAM_ALLOWED_USERS is set but excludes every admin ID — "
                "admins will be locked out. Add them or clear the allowlist."))
