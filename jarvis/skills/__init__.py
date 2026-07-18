"""
Skill (plugin) system.

Skills let J.A.R.V.I.S. handle certain requests locally and deterministically
— the current time, system diagnostics, help — before (and instead of)
calling the LLM. This is the foundation of the plugin ecosystem: memory,
smart-home, and automation skills register through the same registry.
"""

from jarvis.skills.base import BaseSkill, SkillResult
from jarvis.skills.registry import SkillRegistry

__all__ = ["BaseSkill", "SkillResult", "SkillRegistry"]
