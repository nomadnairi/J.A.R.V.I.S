"""Tests for self-diagnostics."""

from __future__ import annotations

from jarvis.config.settings import Settings
from jarvis.core.container import ServiceContainer
from jarvis.core.diagnostics import all_ok, diagnose
from jarvis.core.engine import JarvisEngine
from jarvis.llm.client import LLMClient
from tests.conftest import FakeProvider


def _engine(**overrides) -> JarvisEngine:
    settings = Settings(
        log_file="", memory_enabled=False, integrations_enabled=False,
        goals_enabled=False, rate_limit_enabled=False, memory_db_path=":memory:",
        anthropic_api_key="k", telegram_bot_token="t",
        **overrides,
    )
    return JarvisEngine(container=ServiceContainer(
        settings, llm_client=LLMClient(primary=FakeProvider())))


def test_diagnose_reports_llm_ok():
    checks = {c.name: c for c in diagnose(_engine())}
    assert checks["llm"].ok is True
    assert "fake" in checks["llm"].detail


def test_diagnose_flags_missing_llm():
    engine = JarvisEngine(container=ServiceContainer(
        Settings(anthropic_api_key="", openai_api_key="", log_file="",
                memory_enabled=False, integrations_enabled=False,
                goals_enabled=False, rate_limit_enabled=False)))
    checks = {c.name: c for c in diagnose(engine)}
    assert checks["llm"].ok is False


def test_diagnose_reports_tools_and_security():
    checks = {c.name: c for c in diagnose(_engine())}
    assert checks["tools"].ok is True
    assert "safe defaults" in checks["security"].detail


def test_all_ok_helper():
    assert all_ok(diagnose(_engine())) is True


def test_config_check_present_and_clean():
    checks = {c.name: c for c in diagnose(_engine())}
    assert "config" in checks
    assert checks["config"].ok is True
    assert "no issues" in checks["config"].detail
