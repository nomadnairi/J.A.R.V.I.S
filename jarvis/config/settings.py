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

    # --- Storage (used from Stage 2 onward) ---
    database_url: str = "sqlite:///data/jarvis.db"
    redis_url: str = "redis://localhost:6379/0"
    vector_store_path: str = "chroma_db"

    # --- Voice (used from Stage 3 onward) ---
    speech_recognition_engine: str = "whisper"
    text_to_speech_engine: str = "gtts"
    voice_language: str = "en-US"

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
