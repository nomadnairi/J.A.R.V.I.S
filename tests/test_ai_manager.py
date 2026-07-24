"""Tests for local model provider + AI Manager summary."""

from __future__ import annotations

from jarvis.config.settings import Settings
from jarvis.llm.ai_manager import AIManager
from jarvis.llm.client import LLMClient
from jarvis.llm.providers import PROVIDER_REGISTRY
from jarvis.llm.providers.local_provider import LOCAL_BACKENDS, LocalProvider


# -- local provider -----------------------------------------------------------


def test_local_provider_registered():
    assert PROVIDER_REGISTRY["local"] is LocalProvider


def test_local_backend_presets_used():
    p = LocalProvider("", "llama3", backend="ollama")
    assert p._effective_base_url() == LOCAL_BACKENDS["ollama"]
    p2 = LocalProvider("", "qwen2.5", backend="lmstudio")
    assert p2._effective_base_url() == LOCAL_BACKENDS["lmstudio"]


def test_local_custom_base_url_overrides():
    p = LocalProvider("", "m", base_url="http://box:9000/v1", backend="custom")
    assert p._effective_base_url() == "http://box:9000/v1"


def test_local_available_without_cloud_key():
    # No cloud key required — a model + endpoint is enough.
    assert LocalProvider("", "llama3", backend="vllm").is_available() is True
    assert LocalProvider("", "", backend="vllm").is_available() is False


def test_local_unknown_backend_falls_back_to_ollama():
    p = LocalProvider("", "m", backend="nonsense")
    assert p.backend == "ollama"


# -- client wiring ------------------------------------------------------------


def test_client_builds_local_primary():
    s = Settings(log_file="", llm_provider="local",
                local_llm_backend="vllm", local_llm_model="qwen2.5")
    client = LLMClient.from_settings(s)
    assert client.primary.name == "local"
    assert client.primary.model == "qwen2.5"
    # And it's a switchable profile.
    assert "local" in client.list_profiles()


def test_local_not_auto_added_as_fallback():
    # With Anthropic as primary and no explicit local endpoint, local must not
    # silently join the fallback chain (the server may be offline).
    s = Settings(log_file="", llm_provider="anthropic",
                anthropic_api_key="k")
    client = LLMClient.from_settings(s)
    assert "local" not in [p.name for p in client.fallbacks]


# -- AI manager ---------------------------------------------------------------


def test_ai_manager_reports_configured_providers():
    s = Settings(log_file="", llm_provider="openrouter",
                openrouter_api_key="k", openrouter_model="x/y")
    mgr = AIManager(s)
    ids = [st.id for st in mgr.configured()]
    assert ids and ids[0] == "openrouter"     # default first
    assert mgr.default().id == "openrouter"
    assert mgr.has_any() is True


def test_ai_manager_summary_marks_default_and_missing():
    s = Settings(log_file="", llm_provider="anthropic", anthropic_api_key="k")
    lines = AIManager(s).summary_lines()
    joined = "\n".join(lines)
    assert "⭐default" in joined
    assert "Anthropic" in joined and "OpenAI" in joined
