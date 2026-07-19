"""
Centralised, type-safe configuration for J.A.R.V.I.S.

All settings are loaded from environment variables (and an optional `.env`
file) and validated with pydantic. Access them via :func:`get_settings`,
which returns a cached singleton so the environment is parsed only once.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from the environment / `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- LLM providers ---
    anthropic_api_key: str = Field(default="", description="Anthropic API key.")
    openai_api_key: str = Field(default="", description="OpenAI API key.")

    llm_provider: Literal["anthropic", "openai"] = "anthropic"
    llm_model: str = "claude-sonnet-4-20250514"
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=2048, gt=0)

    # --- AI router (model-tier routing) ---
    #: Route simple turns to a fast model and complex ones to a strong model.
    ai_router_enabled: bool = False
    #: Fast/strong model names (empty → use llm_model). Must match the provider.
    llm_model_fast: str = ""
    llm_model_strong: str = ""
    #: Word count at/above which a turn is routed to the strong model.
    router_word_threshold: int = Field(default=40, gt=0)

    #: Max agentic tool-calling rounds before returning to the user.
    max_tool_rounds: int = Field(default=5, gt=0, le=20)
    #: Max concurrent sessions kept in memory (LRU-evicted beyond this).
    max_sessions: int = Field(default=1000, gt=0)

    # --- Assistant persona ---
    assistant_name: str = "J.A.R.V.I.S."
    user_name: str = "Sir"

    # --- Logging ---
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_file: str = "logs/jarvis.log"

    # --- Storage ---
    database_url: str = "sqlite:///data/jarvis.db"
    redis_url: str = "redis://localhost:6379/0"
    vector_store_path: str = "chroma_db"

    # --- Memory ---
    memory_enabled: bool = True
    #: Vector backend: "sqlite" (default, persistent) | "memory" | "chroma".
    memory_backend: Literal["sqlite", "memory", "chroma"] = "sqlite"
    #: Embedding backend: "hashing" (offline) | "local" (semantic) | "openai".
    embedding_backend: Literal["hashing", "local", "openai"] = "hashing"
    #: Local (fastembed) embedding model when embedding_backend="local".
    local_embedding_model: str = "BAAI/bge-small-en-v1.5"
    #: How many memories to recall and inject into the prompt per turn.
    memory_recall_limit: int = Field(default=4, ge=0, le=20)
    #: Minimum cosine similarity for a memory to be recalled.
    memory_min_score: float = Field(default=0.15, ge=0.0, le=1.0)
    #: Weight of recency vs. similarity in recall scoring (0..1).
    memory_recency_weight: float = Field(default=0.15, ge=0.0, le=1.0)
    #: Extract durable facts via the LLM instead of storing raw transcripts.
    memory_fact_extraction: bool = True
    #: Max semantic memories kept per session (0 = unlimited); oldest evicted.
    memory_max_per_session: int = Field(default=200, ge=0)
    #: Skip storing a new memory this similar to an existing one (0/1 = off).
    memory_dedup_threshold: float = Field(default=0.95, ge=0.0, le=1.0)
    #: Redact secrets (tokens, keys, card numbers) before storing memory.
    memory_redact_secrets: bool = True
    #: SQLite file for persistent conversation history and vectors.
    memory_db_path: str = "data/jarvis.db"
    #: JSON file backing the "memory" vector backend (when selected).
    memory_vector_path: str = "data/memory.json"

    # --- Voice (pluggable STT / TTS) ---
    #: Enable voice messages in the Telegram bot.
    voice_enabled: bool = True
    #: Speech-to-text backend: "openai" (Whisper API, paid) or
    #: "local" (open-source Whisper, free/offline, needs openai-whisper).
    stt_backend: Literal["openai", "local"] = "openai"
    #: Text-to-speech backend: "openai" (paid), "edge" (free, edge-tts),
    #: or "gtts" (free, gTTS).
    tts_backend: Literal["openai", "edge", "gtts"] = "openai"
    #: OpenAI STT/TTS model + voice (when the OpenAI backend is selected).
    stt_model: str = "whisper-1"
    tts_model: str = "tts-1"
    tts_voice: str = "alloy"
    #: Local Whisper model size (tiny | base | small | medium | large).
    local_whisper_model: str = "base"
    #: Whether the bot also replies with a spoken (TTS) voice/audio message.
    voice_replies: bool = True

    # --- Security (dangerous capabilities are OFF by default) ---
    #: Root directory file/coding tools are sandboxed to.
    workspace_root: str = "."
    allow_file_read: bool = True
    allow_file_write: bool = False
    allow_shell: bool = False
    allow_desktop_control: bool = False
    #: Audit log file for dangerous-capability attempts ("" disables it).
    audit_log_path: str = "logs/audit.log"

    # --- Files & coding ---
    #: Expose sandboxed file tools (read on; write gated by security).
    files_enabled: bool = True
    #: Expose coding tools (run command/tests; shell gated by security).
    coding_enabled: bool = True
    #: Command used by the run_tests tool.
    test_command: str = "pytest -q"
    #: Timeout (seconds) for shell commands.
    shell_timeout: float = 60.0

    # --- Goals ---
    #: Track goals/tasks and surface open ones to the assistant.
    goals_enabled: bool = True

    # --- Integrations ---
    #: Master switch for the integrations subsystem.
    integrations_enabled: bool = True
    #: Weather integration (Open-Meteo, free, no key).
    weather_enabled: bool = True
    #: Home Assistant (smart home) — both are required to enable it.
    homeassistant_url: str = ""
    homeassistant_token: str = ""

    # --- Telegram bot ---
    telegram_bot_token: str = Field(default="", description="Bot token from @BotFather.")
    #: Optional comma-separated allowlist of Telegram user IDs (empty = open).
    telegram_allowed_users: str = ""

    def telegram_allowlist(self) -> set[int]:
        """Parsed set of allowed Telegram user IDs (empty = everyone)."""
        ids: set[int] = set()
        for part in self.telegram_allowed_users.split(","):
            part = part.strip()
            if part.isdigit():
                ids.add(int(part))
        return ids

    def active_api_key(self) -> str:
        """Return the API key for the currently selected provider."""
        return (
            self.anthropic_api_key
            if self.llm_provider == "anthropic"
            else self.openai_api_key
        )

    def has_llm_credentials(self) -> bool:
        """Whether an API key is configured for the active provider."""
        return bool(self.active_api_key())


@lru_cache
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance."""
    return Settings()
