"""Coding tools — run commands and tests (security-gated)."""

from __future__ import annotations

from jarvis.coding.runner import ShellRunner
from jarvis.skills.base import BaseSkill, SkillResult
from jarvis.utils.exceptions import JarvisError


class _CodingSkill(BaseSkill):
    priority = 25

    def __init__(self, runner: ShellRunner, test_command: str = "pytest -q") -> None:
        self.runner = runner
        self.test_command = test_command

    def can_handle(self, text: str) -> bool:
        return False

    async def handle(self, text: str, context: dict | None = None) -> SkillResult:
        return SkillResult.not_handled()


class RunCommandSkill(_CodingSkill):
    name = "run_command"
    description = (
        "Run a shell command in the workspace and return its output. "
        "May be disabled by policy (shell execution is off by default)."
    )
    parameters = {
        "type": "object",
        "properties": {"command": {"type": "string", "description": "The shell command."}},
        "required": ["command"],
    }

    async def execute(self, command: str = "", **_: object) -> SkillResult:
        try:
            return SkillResult(text=await self.runner.run(command))
        except JarvisError as exc:
            return SkillResult(text=f"Cannot run command: {exc}")


class RunTestsSkill(_CodingSkill):
    name = "run_tests"
    description = "Run the project's test suite and return the result."
    parameters = {"type": "object", "properties": {}}

    async def execute(self, **_: object) -> SkillResult:
        try:
            return SkillResult(text=await self.runner.run(self.test_command))
        except JarvisError as exc:
            return SkillResult(text=f"Cannot run tests: {exc}")


def coding_skills(runner: ShellRunner, test_command: str = "pytest -q") -> list[BaseSkill]:
    return [
        RunCommandSkill(runner, test_command),
        RunTestsSkill(runner, test_command),
    ]
