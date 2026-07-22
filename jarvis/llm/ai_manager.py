"""
AI Manager — a single place that describes the configured AI providers.

The engine talks to :class:`~jarvis.llm.client.LLMClient` for *inference*; this
module answers the higher-level question "what providers does this deployment
have, and are they usable?" for diagnostics, the startup banner and the bot's
model picker. It never makes network calls — it reasons purely from settings.
"""

from __future__ import annotations

from dataclasses import dataclass

from jarvis.config.settings import Settings
from jarvis.llm.providers.local_provider import LOCAL_BACKENDS

#: Human labels for each provider id.
PROVIDER_LABELS: dict[str, str] = {
    "anthropic": "🧠 Anthropic (Claude)",
    "openai": "💬 OpenAI (ChatGPT)",
    "openrouter": "🌐 OpenRouter",
    "local": "🖥 Local model",
}

#: Kind of provider — cloud API vs. a self-hosted server.
PROVIDER_KIND: dict[str, str] = {
    "anthropic": "cloud",
    "openai": "cloud",
    "openrouter": "cloud",
    "local": "local",
}


@dataclass(frozen=True)
class ProviderStatus:
    """A configured provider and whether it is ready to serve."""

    id: str
    label: str
    kind: str
    model: str
    available: bool
    is_default: bool
    detail: str = ""


class AIManager:
    """Read-only view over the provider configuration."""

    def __init__(self, settings: Settings) -> None:
        self._s = settings

    # -- per-provider readiness -------------------------------------------

    def _status(self, pid: str) -> ProviderStatus:
        s = self._s
        default = s.llm_provider == pid
        label = PROVIDER_LABELS.get(pid, pid)
        kind = PROVIDER_KIND.get(pid, "cloud")
        if pid == "anthropic":
            return ProviderStatus(pid, label, kind, s.llm_model,
                                bool(s.anthropic_api_key), default)
        if pid == "openai":
            return ProviderStatus(pid, label, kind, "gpt-4o-mini",
                                bool(s.openai_api_key), default)
        if pid == "openrouter":
            return ProviderStatus(pid, label, kind, s.openrouter_model,
                                bool(s.openrouter_api_key), default)
        if pid == "local":
            url = s.local_llm_base_url or LOCAL_BACKENDS.get(
                s.local_llm_backend, "")
            # Local is "available" when it's the chosen engine or explicitly
            # pointed at an endpoint; we can't ping it here.
            avail = bool(s.local_llm_model) and (default or bool(s.local_llm_base_url))
            return ProviderStatus(pid, label, kind, s.local_llm_model,
                                avail, default, detail=f"{s.local_llm_backend} · {url}")
        return ProviderStatus(pid, label, kind, "", False, default)

    def all_statuses(self) -> list[ProviderStatus]:
        return [self._status(pid) for pid in PROVIDER_LABELS]

    def configured(self) -> list[ProviderStatus]:
        """Providers that are ready to serve (default first)."""
        ready = [st for st in self.all_statuses() if st.available]
        ready.sort(key=lambda st: (not st.is_default, st.id))
        return ready

    def default(self) -> ProviderStatus:
        return self._status(self._s.llm_provider)

    def has_any(self) -> bool:
        return bool(self.configured())

    # -- summaries --------------------------------------------------------

    def summary_lines(self) -> list[str]:
        """One line per provider for logs / the About screen."""
        lines = []
        for st in self.all_statuses():
            mark = "✅" if st.available else "❌"
            star = " ⭐default" if st.is_default else ""
            tail = f" — {st.detail}" if st.detail else ""
            lines.append(f"{mark} {st.label}: {st.model}{star}{tail}")
        return lines
