"""Tests for the Capability Manager tri-state resolution."""

from __future__ import annotations

from jarvis.config.settings import Settings
from jarvis.core.capabilities import CapabilityManager, CapabilityState


def _mgr(**overrides):
    return CapabilityManager(Settings(log_file="", **overrides))


def test_files_read_only_is_restricted():
    cap = _mgr(files_enabled=True, allow_file_read=True,
            allow_file_write=False).get("files")
    assert cap.state is CapabilityState.RESTRICTED
    assert "read-only" in cap.detail


def test_files_read_write_is_enabled():
    cap = _mgr(files_enabled=True, allow_file_read=True,
            allow_file_write=True).get("files")
    assert cap.state is CapabilityState.ENABLED


def test_files_master_off_is_disabled():
    cap = _mgr(files_enabled=False).get("files")
    assert cap.state is CapabilityState.DISABLED
    assert cap.enabled is False


def test_coding_without_shell_is_restricted():
    cap = _mgr(coding_enabled=True, allow_shell=False).get("coding")
    assert cap.state is CapabilityState.RESTRICTED
    cap2 = _mgr(coding_enabled=True, allow_shell=True).get("coding")
    assert cap2.state is CapabilityState.ENABLED


def test_desktop_gated_is_restricted():
    cap = _mgr(desktop_enabled=True, allow_desktop_control=False).get("desktop")
    assert cap.state is CapabilityState.RESTRICTED


def test_images_without_key_is_restricted():
    cap = _mgr(image_enabled=True, image_api_key="", openai_api_key="").get("images")
    assert cap.state is CapabilityState.RESTRICTED
    cap2 = _mgr(image_enabled=True, openai_api_key="k").get("images")
    assert cap2.state is CapabilityState.ENABLED


def test_search_keyed_without_key_falls_back():
    cap = _mgr(search_enabled=True, search_provider="tavily",
            tavily_api_key="").get("search")
    assert cap.state is CapabilityState.RESTRICTED
    assert "DuckDuckGo" in cap.detail


def test_state_of_shortcut_and_summary():
    mgr = _mgr(memory_enabled=True, goals_enabled=False)
    assert mgr.state_of("memory") is CapabilityState.ENABLED
    assert mgr.state_of("goals") is CapabilityState.DISABLED
    assert mgr.state_of("nonexistent") is CapabilityState.DISABLED
    lines = mgr.summary_lines()
    assert len(lines) == len(mgr.all())
    assert any("Memory" in line for line in lines)
