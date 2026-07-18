"""Tests for the skill system and built-in skills."""

from __future__ import annotations

from jarvis.skills.base import BaseSkill, SkillResult
from jarvis.skills.builtin.datetime_skill import DateTimeSkill
from jarvis.skills.builtin.system_skill import SystemSkill
from jarvis.skills.registry import SkillRegistry
from jarvis.utils.exceptions import SkillRegistrationError


class _EchoSkill(BaseSkill):
    name = "echo"
    description = "Echo the input."
    priority = 10

    def can_handle(self, text: str) -> bool:
        return text.startswith("echo ")

    def handle(self, text: str, context=None) -> SkillResult:
        return SkillResult(text=text[len("echo "):])


def test_register_and_dispatch():
    reg = SkillRegistry()
    reg.register(_EchoSkill())
    result = reg.dispatch("echo hello")
    assert result.handled is True
    assert result.text == "hello"


def test_no_match_returns_not_handled():
    reg = SkillRegistry()
    reg.register(_EchoSkill())
    assert reg.dispatch("something else").handled is False


def test_duplicate_registration_rejected():
    reg = SkillRegistry()
    reg.register(_EchoSkill())
    try:
        reg.register(_EchoSkill())
    except SkillRegistrationError:
        pass
    else:  # pragma: no cover
        raise AssertionError("expected SkillRegistrationError")


def test_priority_ordering():
    reg = SkillRegistry()

    class _Low(_EchoSkill):
        name = "low"
        priority = 1

    class _High(_EchoSkill):
        name = "high"
        priority = 100

    reg.register(_Low())
    reg.register(_High())
    assert reg.find("echo x").name == "high"


def test_datetime_skill_matches_time_question():
    skill = DateTimeSkill()
    assert skill.can_handle("what time is it")
    assert not skill.can_handle("tell me a joke")


def test_system_skill_reports_version():
    skill = SystemSkill()
    assert skill.can_handle("system status")
    result = skill.handle("system status")
    assert "Version" in result.text
