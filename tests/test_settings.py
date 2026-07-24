"""Tests for configuration loading and helpers."""

from __future__ import annotations

from jarvis.config.settings import Settings


def test_defaults():
    s = Settings(anthropic_api_key="", openai_api_key="")
    assert s.assistant_name == "KER"
    assert s.llm_provider == "anthropic"
    assert s.llm_temperature == 0.7


def test_alias_list_parses_and_dedups():
    s = Settings(anthropic_api_key="", openai_api_key="",
                 assistant_name="KER", assistant_aliases="Jarvis, ker , Friday")
    # Comma-split, trimmed, and the name itself is dropped (case-insensitive).
    assert s.alias_list() == ["Jarvis", "Friday"]
    assert Settings(anthropic_api_key="", openai_api_key="").alias_list() == []


def test_active_api_key_follows_provider():
    s = Settings(anthropic_api_key="A", openai_api_key="B", llm_provider="openai")
    assert s.active_api_key() == "B"
    assert s.has_llm_credentials() is True


def test_missing_credentials_detected():
    s = Settings(anthropic_api_key="", openai_api_key="", llm_provider="anthropic")
    assert s.has_llm_credentials() is False
