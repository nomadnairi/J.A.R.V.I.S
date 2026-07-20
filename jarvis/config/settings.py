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
    #: Custom OpenAI-compatible endpoint (e.g. OpenRouter:
    #: https://openrouter.ai/api/v1). Empty = the official OpenAI API.
    openai_base_url: str = ""
    #: OpenRouter API key — enables a separate "openrouter" model profile so
    #: users can switch between Claude / GPT / OpenRouter at runtime.
    openrouter_api_key: str = ""
    #: Default model used for the OpenRouter profile.
    openrouter_model: str = "anthropic/claude-3.7-sonnet"
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

    # --- Rate limiting (per session) ---
    rate_limit_enabled: bool = True
    rate_limit_capacity: int = Field(default=20, gt=0)
    rate_limit_window_seconds: float = Field(default=60.0, gt=0)

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
    #: Expose desktop-control tools (gated by allow_desktop_control).
    desktop_enabled: bool = True

    # --- Agents ---
    #: Expose the run_agent tool (delegate multi-step tasks to a sub-agent).
    agents_enabled: bool = True
    #: Max steps an autonomous sub-agent may take.
    max_agent_steps: int = Field(default=8, gt=0, le=30)

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

    # --- API server ---
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, gt=0, le=65535)
    #: Bearer / X-API-Key required to call the API (empty = open, dev only).
    api_key: str = ""

    # --- Accounts & licensing (per-user login for exe/apk clients) ---
    #: Enable username/password accounts + license checks on the API.
    #: When off, the API falls back to the shared ``api_key`` only.
    auth_enabled: bool = False
    #: SQLite file holding accounts, licenses, tokens and pairings.
    auth_db_path: str = "data/auth.db"
    #: Admin key required to create accounts / issue licenses (empty = disabled).
    auth_admin_key: str = ""
    #: Lifetime of an issued login token, in hours.
    auth_token_ttl_hours: int = Field(default=720, gt=0)
    #: Require a linked+verified Telegram account before login succeeds.
    auth_require_telegram: bool = False

    # --- Billing (payments → automatic license issuance) ---
    #: Enable the /buy flow in the bot and the /billing/webhook endpoint.
    billing_enabled: bool = False
    #: Price of a license in Telegram Stars (XTR).
    billing_price_stars: int = Field(default=2500, gt=0)
    #: Plan name written on issued licenses.
    billing_plan: str = "standard"
    #: License validity in days (0 = perpetual).
    billing_plan_days: int = Field(default=365, ge=0)
    #: HMAC-SHA256 secret for POST /billing/webhook (empty = webhook disabled).
    billing_webhook_secret: str = ""

    # --- Telegram bot ---
    telegram_bot_token: str = Field(default="", description="Bot token from @BotFather.")
    #: Optional comma-separated allowlist of Telegram user IDs (empty = open).
    telegram_allowed_users: str = ""
    #: Comma-separated Telegram user IDs with access to the bot's admin panel.
    telegram_admin_users: str = ""
    #: Allow the assistant to SEND Telegram messages/posts as a tool (outbound).
    telegram_send_enabled: bool = False
    #: Default channel (@channelusername or chat id) for the telegram_post tool.
    telegram_channel: str = ""

    def telegram_allowlist(self) -> set[int]:
        """Parsed set of allowed Telegram user IDs (empty = everyone)."""
        ids: set[int] = set()
        for part in self.telegram_allowed_users.split(","):
            part = part.strip()
            if part.isdigit():
                ids.add(int(part))
        return ids

    def telegram_admins(self) -> set[int]:
        """Parsed set of Telegram user IDs allowed to use the admin panel."""
        ids: set[int] = set()
        for part in self.telegram_admin_users.split(","):
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
