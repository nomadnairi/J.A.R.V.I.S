"""Tests for the Configuration Manager cross-field validation."""

from __future__ import annotations

from jarvis.config.manager import ConfigManager
from jarvis.config.settings import Settings


def _keys(issues):
    return {i.key for i in issues}


def test_missing_anthropic_key_is_error():
    mgr = ConfigManager(Settings(log_file="", llm_provider="anthropic",
                                anthropic_api_key=""))
    assert "ANTHROPIC_API_KEY" in _keys(mgr.errors())
    assert mgr.ok is False


def test_openrouter_requires_key_and_model():
    mgr = ConfigManager(Settings(log_file="", llm_provider="openrouter",
                                openrouter_api_key="", openrouter_model=""))
    keys = _keys(mgr.errors())
    assert "OPENROUTER_API_KEY" in keys and "OPENROUTER_MODEL" in keys


def test_local_custom_needs_base_url():
    mgr = ConfigManager(Settings(log_file="", llm_provider="local",
                                local_llm_backend="custom",
                                local_llm_base_url="", local_llm_model="m"))
    assert "LOCAL_LLM_BASE_URL" in _keys(mgr.errors())


def test_local_preset_is_ok_with_info():
    mgr = ConfigManager(Settings(log_file="", llm_provider="local",
                                local_llm_backend="ollama",
                                local_llm_model="llama3"))
    assert mgr.ok is True                       # no errors
    assert "LOCAL_LLM_BASE_URL" in _keys(mgr.validate())  # info note present


def test_image_enabled_without_key_warns():
    mgr = ConfigManager(Settings(log_file="", llm_provider="anthropic",
                                anthropic_api_key="k",
                                image_enabled=True, image_api_key="",
                                openai_api_key=""))
    warnings = [i for i in mgr.validate() if i.level == "warning"]
    assert any(i.key == "IMAGE_API_KEY" for i in warnings)
    assert mgr.ok is True                       # only a warning, not an error


def test_search_provider_without_key_warns_but_ok():
    mgr = ConfigManager(Settings(log_file="", llm_provider="anthropic",
                                anthropic_api_key="k",
                                search_enabled=True, search_provider="tavily",
                                tavily_api_key=""))
    assert any(i.key == "SEARCH_PROVIDER" for i in mgr.validate())
    assert mgr.ok is True


def test_allowlist_excluding_admin_warns():
    mgr = ConfigManager(Settings(log_file="", llm_provider="anthropic",
                                anthropic_api_key="k",
                                telegram_bot_token="t",
                                telegram_allowed_users="111,222",
                                telegram_admin_users="999"))
    assert "TELEGRAM_ALLOWED_USERS" in _keys(mgr.validate())


def test_clean_config_has_no_errors():
    mgr = ConfigManager(Settings(log_file="", llm_provider="anthropic",
                                anthropic_api_key="k",
                                telegram_bot_token="t"))
    assert mgr.ok is True
    assert mgr.errors() == []
