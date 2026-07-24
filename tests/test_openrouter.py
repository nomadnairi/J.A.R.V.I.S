"""The OpenAI provider must honour a custom base_url (OpenRouter, gateways)."""

from __future__ import annotations


from jarvis.config.settings import Settings
from jarvis.llm.client import LLMClient
from jarvis.llm.providers.openai_provider import OpenAIProvider


def test_base_url_passed_to_client(monkeypatch):
    captured = {}

    class FakeAsyncOpenAI:
        def __init__(self, *, api_key, base_url):
            captured["api_key"] = api_key
            captured["base_url"] = base_url

    import openai
    monkeypatch.setattr(openai, "AsyncOpenAI", FakeAsyncOpenAI)

    provider = OpenAIProvider(api_key="sk-or-x", model="anthropic/claude-3.7-sonnet",
                            base_url="https://openrouter.ai/api/v1")
    provider._ensure_client()
    assert captured["api_key"] == "sk-or-x"
    assert captured["base_url"] == "https://openrouter.ai/api/v1"


def test_no_base_url_defaults_to_none(monkeypatch):
    captured = {}

    class FakeAsyncOpenAI:
        def __init__(self, *, api_key, base_url):
            captured["base_url"] = base_url

    import openai
    monkeypatch.setattr(openai, "AsyncOpenAI", FakeAsyncOpenAI)

    OpenAIProvider(api_key="k", model="gpt-4o")._ensure_client()
    assert captured["base_url"] is None  # official OpenAI API


def test_openrouter_key_without_base_url_is_auto_routed(monkeypatch):
    # An sk-or-* key with no base URL would 401 against OpenAI; route it to
    # OpenRouter instead of guaranteeing a failure.
    captured = {}

    class FakeAsyncOpenAI:
        def __init__(self, *, api_key, base_url):
            captured["base_url"] = base_url

    import openai
    monkeypatch.setattr(openai, "AsyncOpenAI", FakeAsyncOpenAI)

    OpenAIProvider(api_key="sk-or-v1-abc",
                model="nvidia/nemotron-3-ultra:free")._ensure_client()
    assert captured["base_url"] == "https://openrouter.ai/api/v1"


def test_settings_wire_base_url_into_openai_provider():
    settings = Settings(
        anthropic_api_key="", openai_api_key="sk-or-x", log_file="",
        llm_provider="openai", llm_model="anthropic/claude-3.7-sonnet",
        openai_base_url="https://openrouter.ai/api/v1",
    )
    client = LLMClient.from_settings(settings)
    assert client.primary.base_url == "https://openrouter.ai/api/v1"
    assert client.primary.model == "anthropic/claude-3.7-sonnet"


def test_openrouter_is_a_standalone_provider():
    # LLM_PROVIDER=openrouter builds an OpenRouter primary with its own key,
    # model and endpoint — no OpenAI settings involved.
    settings = Settings(
        anthropic_api_key="", openai_api_key="", log_file="",
        llm_provider="openrouter",
        openrouter_api_key="sk-or-x",
        openrouter_model="nvidia/nemotron-3-ultra-550b-a55b:free",
    )
    client = LLMClient.from_settings(settings)
    assert client.primary.name == "openrouter"
    assert client.primary.model == "nvidia/nemotron-3-ultra-550b-a55b:free"
    assert client.primary.base_url == "https://openrouter.ai/api/v1"
    # The anthropic LLM_MODEL default must NOT leak onto OpenRouter.
    assert client.primary.model != settings.llm_model


def test_openrouter_and_openai_are_separate_profiles():
    settings = Settings(
        anthropic_api_key="", log_file="", llm_provider="openai",
        openai_api_key="sk-openai", openrouter_api_key="sk-or-y",
        openrouter_model="openai/gpt-4o-mini",
    )
    client = LLMClient.from_settings(settings)
    # Distinct providers, distinct endpoints.
    assert client.profiles["gpt"].name == "openai"
    assert client.profiles["gpt"].base_url in ("", None)
    assert client.profiles["openrouter"].name == "openrouter"
    assert client.profiles["openrouter"].base_url == "https://openrouter.ai/api/v1"


def test_anthropic_provider_ignores_openai_base_url():
    settings = Settings(
        anthropic_api_key="k", openai_api_key="", log_file="",
        llm_provider="anthropic", openai_base_url="https://openrouter.ai/api/v1",
    )
    client = LLMClient.from_settings(settings)
    # Anthropic is primary; base_url is an OpenAI-only concept here.
    assert client.primary.name == "anthropic"
