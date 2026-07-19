"""Tests for the desktop app's headless parts (config, API client, engine
thread, UI strings). The Qt GUI itself is not exercised here."""

from __future__ import annotations

import json

import pytest

from jarvis.config.settings import Settings
from jarvis.desktop_app.api_client import ApiError, JarvisApiClient
from jarvis.desktop_app.config import AppConfig
from jarvis.desktop_app.engine_thread import EngineThread
from jarvis.desktop_app.strings import STRINGS, tr
from jarvis.llm.client import LLMClient
from tests.conftest import FakeProvider


# -- AppConfig ------------------------------------------------------------------


def test_config_roundtrip(tmp_path):
    config = AppConfig(language="ru", mode="remote", server_url="http://x",
                    allow_shell=True)
    path = config.save(tmp_path)
    assert path.exists()
    loaded = AppConfig.load(tmp_path)
    assert loaded.language == "ru"
    assert loaded.mode == "remote"
    assert loaded.allow_shell is True


def test_config_defaults_when_missing(tmp_path):
    config = AppConfig.load(tmp_path)
    assert config.language == "en"
    assert config.mode == "local"
    # Dangerous capabilities are off by default.
    assert not config.allow_file_write
    assert not config.allow_shell
    assert not config.allow_desktop_control


def test_config_ignores_unknown_keys(tmp_path):
    payload = {"language": "uz", "hacked_field": "x"}
    (tmp_path / "desktop.json").write_text(json.dumps(payload))
    config = AppConfig.load(tmp_path)
    assert config.language == "uz"
    assert not hasattr(config, "hacked_field") or "hacked_field" not in (
        config.__dataclass_fields__
    )


def test_config_survives_corrupt_file(tmp_path):
    (tmp_path / "desktop.json").write_text("{not json")
    assert AppConfig.load(tmp_path).language == "en"


def test_settings_overrides_map_to_engine_settings():
    config = AppConfig(anthropic_api_key="k", allow_shell=True,
                    telegram_send_enabled=True, telegram_channel="@ch",
                    workspace_root="/tmp/ws", llm_model="custom")
    settings = Settings(**config.to_settings_overrides())
    assert settings.allow_shell is True
    assert settings.telegram_send_enabled is True
    assert settings.telegram_channel == "@ch"
    assert settings.workspace_root == "/tmp/ws"
    assert settings.llm_model == "custom"


# -- UI strings -------------------------------------------------------------


def test_strings_cover_all_locales():
    keys = set(STRINGS["en"])
    for locale in ("ru", "uz"):
        assert set(STRINGS[locale]) == keys


def test_tr_fallback_and_format():
    assert tr("app_title", "de") == STRINGS["en"]["app_title"]
    assert "boom" in tr("error", "ru", error="boom")


# -- API client ---------------------------------------------------------------


def test_api_client_against_real_api():
    pytest.importorskip("fastapi")
    import threading

    import uvicorn

    from jarvis.api.app import create_app
    from jarvis.core.container import ServiceContainer
    from jarvis.core.engine import JarvisEngine

    settings = Settings(
        anthropic_api_key="k", log_file="", memory_enabled=False,
        integrations_enabled=False, goals_enabled=False,
        rate_limit_enabled=False, api_key="", auth_enabled=True,
        auth_db_path=":memory:", auth_admin_key="adm",
    )
    engine = JarvisEngine(container=ServiceContainer(
        settings, llm_client=LLMClient(primary=FakeProvider())))
    app = create_app(engine=engine, settings=settings)

    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8765,
                                        log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    import time
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    assert server.started

    try:
        # Seed an account through the license service directly.
        svc = app.state.license_service
        acc = svc.create_account("tony", "arcreactor")
        svc.issue_license(acc.id)

        client = JarvisApiClient("http://127.0.0.1:8765")
        assert client.info()["name"] == "J.A.R.V.I.S."

        with pytest.raises(ApiError) as excinfo:
            client.login("tony", "wrong")
        assert excinfo.value.status == 401

        client.login("tony", "arcreactor")
        assert client.me()["username"] == "tony"
        assert client.chat("hello") == "Certainly, Sir."
        assert len(client.pairing_code()) == 8
        client.logout()
        with pytest.raises(ApiError):
            client.me()
    finally:
        server.should_exit = True
        thread.join(timeout=5)


# -- EngineThread ---------------------------------------------------------------


def test_engine_thread_ask_and_stop():
    from jarvis.core.container import ServiceContainer
    from jarvis.core.engine import JarvisEngine

    settings = Settings(
        anthropic_api_key="k", log_file="", memory_enabled=False,
        integrations_enabled=False, goals_enabled=False, rate_limit_enabled=False,
    )
    thread = EngineThread(settings)
    # Swap in a fake-LLM engine before starting.
    thread._engine = None

    # Build with the fake provider by monkeypatching construction:
    original_run = thread._run

    def _run_with_fake():
        import asyncio
        thread._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(thread._loop)
        thread._engine = JarvisEngine(container=ServiceContainer(
            settings, llm_client=LLMClient(primary=FakeProvider())))
        thread._loop.run_until_complete(thread._engine.start())
        thread._started.set()
        thread._loop.run_forever()
        thread._loop.run_until_complete(thread._engine.shutdown())
        thread._loop.close()

    thread._run = _run_with_fake
    thread._thread = __import__("threading").Thread(target=thread._run,
                                                    daemon=True)
    thread.start()
    try:
        assert thread.ask("hello", timeout=30) == "Certainly, Sir."

        results: list = []
        done = __import__("threading").Event()

        def on_done(reply, error):
            results.append((reply, error))
            done.set()

        thread.ask_async("again", on_done=on_done)
        assert done.wait(30)
        assert results[0][0] == "Certainly, Sir."
        assert results[0][1] is None
    finally:
        thread.stop()
    assert original_run is not None
