"""
Capability Manager — a single, unified view of every high-level feature and
whether it is Enabled, Disabled or Restricted.

The project has two layers of gating that used to be read in scattered spots:

* a master switch per feature (``FILES_ENABLED``, ``VOICE_ENABLED``, …), and
* fine-grained permissions for dangerous actions (``ALLOW_FILE_WRITE``,
  ``ALLOW_SHELL``, ``ALLOW_DESKTOP_CONTROL``) plus required credentials.

This manager collapses both into one tri-state per capability so the bot's
About screen, ``/doctor`` and logs can describe the deployment consistently:

* **enabled**    — on and fully usable,
* **restricted** — on but limited (read-only, missing a key, or a dangerous
  sub-action is off), and
* **disabled**   — turned off by its master switch.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from jarvis.config.settings import Settings


class CapabilityState(str, Enum):
    ENABLED = "enabled"
    RESTRICTED = "restricted"
    DISABLED = "disabled"

    @property
    def icon(self) -> str:
        return {"enabled": "✅", "restricted": "🔶", "disabled": "❌"}[self.value]


@dataclass(frozen=True)
class CapabilityInfo:
    """The resolved state of one capability, with a human reason."""

    id: str
    label: str
    state: CapabilityState
    detail: str = ""

    @property
    def enabled(self) -> bool:
        return self.state is not CapabilityState.DISABLED


class CapabilityManager:
    """Resolves capability states purely from :class:`Settings`."""

    def __init__(self, settings: Settings) -> None:
        self._s = settings

    # -- resolution --------------------------------------------------------

    def all(self) -> list[CapabilityInfo]:
        return [
            self._files(), self._coding(), self._desktop(), self._agents(),
            self._memory(), self._goals(), self._voice(), self._images(),
            self._search(), self._integrations(), self._mcp(),
        ]

    def get(self, cap_id: str) -> CapabilityInfo | None:
        return next((c for c in self.all() if c.id == cap_id), None)

    def state_of(self, cap_id: str) -> CapabilityState:
        info = self.get(cap_id)
        return info.state if info else CapabilityState.DISABLED

    # -- individual capabilities ------------------------------------------

    @staticmethod
    def _mk(cap_id, label, on, *, restricted=False, detail="") -> CapabilityInfo:
        if not on:
            state = CapabilityState.DISABLED
        elif restricted:
            state = CapabilityState.RESTRICTED
        else:
            state = CapabilityState.ENABLED
        return CapabilityInfo(cap_id, label, state, detail)

    def _files(self) -> CapabilityInfo:
        s = self._s
        # Enabled but write-off = read-only (restricted).
        read_only = s.allow_file_read and not s.allow_file_write
        detail = ("read-only (ALLOW_FILE_WRITE off)" if read_only
                else "read + write" if s.allow_file_write else "no file access")
        return self._mk("files", "📂 Files", s.files_enabled and s.allow_file_read,
                        restricted=read_only, detail=detail)

    def _coding(self) -> CapabilityInfo:
        s = self._s
        # Coding tools without shell exec are restricted (analysis only).
        return self._mk("coding", "💻 Coding", s.coding_enabled,
                        restricted=not s.allow_shell,
                        detail=("shell enabled" if s.allow_shell
                                else "no shell (ALLOW_SHELL off)"))

    def _desktop(self) -> CapabilityInfo:
        s = self._s
        return self._mk("desktop", "🖱 Desktop control", s.desktop_enabled,
                        restricted=not s.allow_desktop_control,
                        detail=("control allowed" if s.allow_desktop_control
                                else "gated (ALLOW_DESKTOP_CONTROL off)"))

    def _agents(self) -> CapabilityInfo:
        return self._mk("agents", "🤝 Sub-agents", self._s.agents_enabled)

    def _memory(self) -> CapabilityInfo:
        return self._mk("memory", "🧠 Memory", self._s.memory_enabled)

    def _goals(self) -> CapabilityInfo:
        return self._mk("goals", "🎯 Goals", self._s.goals_enabled)

    def _voice(self) -> CapabilityInfo:
        return self._mk("voice", "🎙 Voice", self._s.voice_enabled)

    def _images(self) -> CapabilityInfo:
        s = self._s
        has_key = bool(s.image_api_key or s.openai_api_key)
        return self._mk("images", "🎨 Image generation", s.image_enabled,
                        restricted=not has_key,
                        detail=("ready" if has_key else "no image key set"))

    def _search(self) -> CapabilityInfo:
        s = self._s
        # DuckDuckGo is keyless, so search is functional whenever enabled; it's
        # "restricted" only if a keyed provider is selected but its key is empty.
        keyed = {
            "tavily": s.tavily_api_key, "exa": s.exa_api_key,
            "brave": s.brave_api_key, "serpapi": s.serpapi_key,
            "google": s.google_cse_key, "perplexity": s.perplexity_api_key,
        }
        needs_key = s.search_provider in keyed and not keyed[s.search_provider]
        return self._mk("search", "🌍 Web search", s.search_enabled,
                        restricted=needs_key,
                        detail=("DuckDuckGo fallback" if needs_key
                                else s.search_provider))

    def _integrations(self) -> CapabilityInfo:
        return self._mk("integrations", "🔗 Integrations",
                        self._s.integrations_enabled)

    def _mcp(self) -> CapabilityInfo:
        s = self._s
        # Enabled but no servers configured = restricted (nothing to mount).
        has_servers = bool(s.mcp_config_path or s.mcp_servers)
        return self._mk("mcp", "🧩 MCP tools", s.mcp_enabled,
                        restricted=not has_servers,
                        detail=("servers configured" if has_servers
                                else "no servers configured"))

    # -- summaries --------------------------------------------------------

    def summary_lines(self) -> list[str]:
        return [f"{c.state.icon} {c.label}: {c.state.value}"
                + (f" — {c.detail}" if c.detail else "")
                for c in self.all()]
