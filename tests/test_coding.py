"""Tests for the coding assistant (shell runner + tools)."""

from __future__ import annotations

import pytest

from jarvis.coding.runner import ShellRunner
from jarvis.coding.tools import RunCommandSkill, RunTestsSkill
from jarvis.config.settings import Settings
from jarvis.security.manager import SecurityManager
from jarvis.utils.exceptions import PermissionDenied


def _security(shell: bool) -> SecurityManager:
    return SecurityManager.from_settings(
        Settings(allow_shell=shell, audit_log_path="")
    )


@pytest.mark.asyncio
async def test_run_command_when_allowed(tmp_path):
    runner = ShellRunner(str(tmp_path), _security(True))
    result = await runner.run("echo hello-jarvis")
    assert "hello-jarvis" in result
    assert "exit code 0" in result


@pytest.mark.asyncio
async def test_run_command_denied_by_default(tmp_path):
    runner = ShellRunner(str(tmp_path), _security(False))
    with pytest.raises(PermissionDenied):
        await runner.run("echo nope")


@pytest.mark.asyncio
async def test_empty_command(tmp_path):
    runner = ShellRunner(str(tmp_path), _security(True))
    assert "No command" in await runner.run("   ")


@pytest.mark.asyncio
async def test_timeout(tmp_path):
    runner = ShellRunner(str(tmp_path), _security(True), timeout=0.5)
    result = await runner.run("sleep 5")
    assert "timed out" in result


@pytest.mark.asyncio
async def test_run_command_tool_surfaces_denial(tmp_path):
    skill = RunCommandSkill(ShellRunner(str(tmp_path), _security(False)))
    result = await skill.execute(command="echo hi")
    assert "Cannot run command" in result.text


@pytest.mark.asyncio
async def test_run_tests_tool(tmp_path):
    runner = ShellRunner(str(tmp_path), _security(True))
    skill = RunTestsSkill(runner, test_command="echo tests-ran")
    result = await skill.execute()
    assert "tests-ran" in result.text
