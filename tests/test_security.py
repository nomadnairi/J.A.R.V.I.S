"""Tests for the security module."""

from __future__ import annotations

import pytest

from jarvis.config.settings import Settings
from jarvis.security.manager import SecurityManager
from jarvis.security.policy import Capability
from jarvis.utils.exceptions import PermissionDenied


def _manager(**allow) -> SecurityManager:
    settings = Settings(
        allow_file_read=allow.get("read", True),
        allow_file_write=allow.get("write", False),
        allow_shell=allow.get("shell", False),
        allow_desktop_control=allow.get("desktop", False),
        audit_log_path="",  # no file in tests
    )
    return SecurityManager.from_settings(settings)


def test_defaults_are_safe():
    sm = _manager()
    assert sm.is_allowed(Capability.FILE_READ) is True
    assert sm.is_allowed(Capability.FILE_WRITE) is False
    assert sm.is_allowed(Capability.SHELL_EXEC) is False
    assert sm.is_allowed(Capability.DESKTOP_CONTROL) is False


def test_require_denies_by_default():
    sm = _manager()
    with pytest.raises(PermissionDenied):
        sm.require(Capability.SHELL_EXEC, "rm -rf /")


def test_require_allows_when_enabled():
    sm = _manager(shell=True)
    sm.require(Capability.SHELL_EXEC, "ls")  # must not raise


def test_attempts_are_audited():
    sm = _manager()
    with pytest.raises(PermissionDenied):
        sm.require(Capability.FILE_WRITE, "write secret.txt")
    trail = sm.audit_trail
    assert len(trail) == 1
    assert trail[0].allowed is False
    assert trail[0].capability == Capability.FILE_WRITE


def test_audit_redacts_secrets():
    sm = _manager(shell=True)
    sm.require(Capability.SHELL_EXEC, "curl -H 'token=sk-abcdef0123456789abcdef' x")
    assert "sk-abcdef" not in sm.audit_trail[0].action
