"""Regression tests for security hardening (URL scheme, bot resilience)."""

from __future__ import annotations

import pytest

from jarvis.desktop_app.api_client import ApiError, JarvisApiClient


def test_api_client_rejects_non_http_schemes():
    for bad in ("file:///etc/passwd", "ftp://host/x", "gopher://h",
                "javascript:alert(1)", "/etc/passwd", ""):
        with pytest.raises(ApiError):
            JarvisApiClient(bad)


def test_api_client_accepts_http_and_https():
    assert JarvisApiClient("http://localhost:8000").base_url == "http://localhost:8000"
    assert JarvisApiClient("https://x/").base_url == "https://x"


def test_android_client_rejects_non_http(monkeypatch):
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "clients/android/jarvis_client.py"
    spec = importlib.util.spec_from_file_location("android_jarvis_client", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with pytest.raises(module.ApiError):
        module.JarvisApiClient("file:///etc/passwd")
    assert module.JarvisApiClient("https://s").base_url == "https://s"


def test_poll_backoff_constants_are_bounded():
    from jarvis.interfaces import telegram_bot

    assert telegram_bot._POLL_BACKOFF_INITIAL > 0
    assert telegram_bot._POLL_BACKOFF_MAX >= telegram_bot._POLL_BACKOFF_INITIAL


def test_embedding_hash_is_non_security_and_stable():
    from jarvis.memory.embeddings import HashingEmbedder

    embedder = HashingEmbedder(dimensions=64)
    v1 = embedder.embed("hello world")
    v2 = embedder.embed("hello world")
    assert v1 == v2  # deterministic
    assert len(v1) == 64
