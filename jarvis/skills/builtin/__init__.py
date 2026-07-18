"""Built-in skills shipped with J.A.R.V.I.S."""

from jarvis.skills.builtin.calculator_skill import CalculatorSkill
from jarvis.skills.builtin.datetime_skill import DateTimeSkill
from jarvis.skills.builtin.help_skill import HelpSkill
from jarvis.skills.builtin.system_skill import SystemSkill

#: Skills that are registered by default at startup.
DEFAULT_SKILLS = [DateTimeSkill, SystemSkill, CalculatorSkill, HelpSkill]

__all__ = [
    "DateTimeSkill",
    "SystemSkill",
    "CalculatorSkill",
    "HelpSkill",
    "DEFAULT_SKILLS",
]
