"""
Service container (dependency injection).

A tiny, explicit DI container that wires the framework's singletons together:
settings, event bus, LLM client, skill registry, telemetry, and prompt
builder. Everything is constructed once here and shared, which keeps the engine
constructor small and makes components easy to swap in tests.
"""

from __future__ import annotations

from functools import cached_property

from jarvis.config.settings import Settings, get_settings
from jarvis.events.bus import EventBus
from jarvis.llm.client import LLMClient
from jarvis.llm.prompts import PromptBuilder
from jarvis.memory.manager import MemoryManager
from jarvis.skills.builtin import DEFAULT_SKILLS
from jarvis.skills.builtin.help_skill import HelpSkill
from jarvis.skills.registry import SkillRegistry
from jarvis.telemetry.metrics import MetricsCollector
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class ServiceContainer:
    """Lazily constructs and holds shared services.

    Each service is a ``cached_property`` so it is built on first access and
    reused thereafter. Pass a custom :class:`Settings` (or pre-built services
    via the constructor) to override defaults in tests.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        event_bus: EventBus | None = None,
        llm_client: LLMClient | None = None,
        skill_registry: SkillRegistry | None = None,
        metrics: MetricsCollector | None = None,
        memory: MemoryManager | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._event_bus_override = event_bus
        self._llm_override = llm_client
        self._skills_override = skill_registry
        self._metrics_override = metrics
        self._memory_override = memory

    @property
    def settings(self) -> Settings:
        return self._settings

    @cached_property
    def event_bus(self) -> EventBus:
        return self._event_bus_override or EventBus()

    @cached_property
    def metrics(self) -> MetricsCollector:
        collector = self._metrics_override or MetricsCollector()
        collector.attach(self.event_bus)
        return collector

    @cached_property
    def llm(self) -> LLMClient:
        return self._llm_override or LLMClient.from_settings(self._settings)

    @cached_property
    def memory(self) -> MemoryManager | None:
        if self._memory_override is not None:
            return self._memory_override
        if not self._settings.memory_enabled:
            return None
        return MemoryManager.from_settings(self._settings)

    @cached_property
    def prompts(self) -> PromptBuilder:
        return PromptBuilder(
            assistant_name=self._settings.assistant_name,
            user_name=self._settings.user_name,
        )

    @cached_property
    def skills(self) -> SkillRegistry:
        if self._skills_override is not None:
            return self._skills_override
        registry = SkillRegistry()
        instances = [skill_cls() for skill_cls in DEFAULT_SKILLS]
        registry.register_many(instances)
        # Wire the help skill so it can enumerate its siblings.
        for skill in instances:
            if isinstance(skill, HelpSkill):
                skill.registry = registry
        logger.debug("Registered %d built-in skills", len(registry))
        return registry
