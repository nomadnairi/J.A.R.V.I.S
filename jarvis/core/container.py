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
from jarvis.goals.manager import GoalManager
from jarvis.integrations.manager import IntegrationManager
from jarvis.llm.client import LLMClient
from jarvis.llm.prompts import PromptBuilder
from jarvis.memory.manager import MemoryManager
from jarvis.security.manager import SecurityManager
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
        integrations: IntegrationManager | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._event_bus_override = event_bus
        self._llm_override = llm_client
        self._skills_override = skill_registry
        self._metrics_override = metrics
        self._memory_override = memory
        self._integrations_override = integrations
        self._integrations_set = integrations is not None

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
        return MemoryManager.from_settings(self._settings, llm=self.llm)

    @cached_property
    def security(self) -> SecurityManager:
        return SecurityManager.from_settings(self._settings)

    @cached_property
    def files(self):
        if not self._settings.files_enabled:
            return None
        from jarvis.files.manager import FileManager
        return FileManager(self._settings.workspace_root, self.security)

    @cached_property
    def shell(self):
        if not self._settings.coding_enabled:
            return None
        from jarvis.coding.runner import ShellRunner
        return ShellRunner(self._settings.workspace_root, self.security,
                        timeout=self._settings.shell_timeout)

    @cached_property
    def goals(self) -> GoalManager | None:
        if not self._settings.goals_enabled:
            return None
        return GoalManager.from_settings(self._settings)

    @cached_property
    def integrations(self) -> IntegrationManager | None:
        if self._integrations_set:
            return self._integrations_override
        if not self._settings.integrations_enabled:
            return None
        return self._build_integrations()

    def _build_integrations(self) -> IntegrationManager:
        from jarvis.integrations.homeassistant import HomeAssistantIntegration
        from jarvis.integrations.weather import WeatherIntegration

        manager = IntegrationManager()
        if self._settings.weather_enabled:
            manager.register(WeatherIntegration(enabled=True))
        manager.register(
            HomeAssistantIntegration(
                self._settings.homeassistant_url,
                self._settings.homeassistant_token,
            )
        )
        return manager

    @cached_property
    def router(self):
        from jarvis.routing.router import AIRouter
        return AIRouter.from_settings(self._settings)

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
        # Expose goal tools.
        if self.goals is not None:
            from jarvis.goals.tools import goal_skills
            registry.register_many(goal_skills(self.goals))
        # Expose file tools.
        if self.files is not None:
            from jarvis.files.tools import file_skills
            registry.register_many(file_skills(self.files))
        # Expose coding tools (run command/tests).
        if self.shell is not None:
            from jarvis.coding.tools import coding_skills
            registry.register_many(
                coding_skills(self.shell, self._settings.test_command)
            )
        # Expose the run_agent tool (delegating to an autonomous sub-agent).
        if self._settings.agents_enabled:
            from jarvis.agents.tools import RunAgentSkill
            registry.register(
                RunAgentSkill(self.llm, registry, self._settings.max_agent_steps)
            )
        # Expose configured integrations' actions as tools.
        if self.integrations is not None:
            self.integrations.install_tools(registry)
        logger.debug("Registered %d skills (incl. integration tools)", len(registry))
        return registry
