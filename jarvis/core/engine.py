"""
The J.A.R.V.I.S. engine — the orchestrator that ties every layer together.

Flow of a single turn:

    Request
      → pipeline (normalise, log, …)
        → skill registry  (handle locally if a skill matches)
        → LLM client      (otherwise reason with the language model)
      → Response
      → events + telemetry

The engine owns the session context, the state machine, and the wiring
provided by the :class:`~jarvis.core.container.ServiceContainer`.
"""

from __future__ import annotations

from jarvis.config.constants import AssistantState, EventType, ResponseType
from jarvis.config.settings import Settings
from jarvis.core.container import ServiceContainer
from jarvis.core.context import SessionContext
from jarvis.core.pipeline import (
    LoggingMiddleware,
    NormalizeMiddleware,
    Pipeline,
)
from jarvis.core.state import StateMachine
from jarvis.models.response import Request, Response
from jarvis.utils.exceptions import JarvisError
from jarvis.utils.logger import get_logger
from jarvis.utils.timing import measure

logger = get_logger(__name__)


class JarvisEngine:
    """Central coordinator for a J.A.R.V.I.S. session."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        container: ServiceContainer | None = None,
    ) -> None:
        self.container = container or ServiceContainer(settings)
        self.settings = self.container.settings

        # Shared services (constructed lazily by the container).
        self.bus = self.container.event_bus
        self.metrics = self.container.metrics
        self.llm = self.container.llm
        self.skills = self.container.skills
        self.prompts = self.container.prompts

        # Per-engine state.
        self.state = StateMachine(self.bus)
        self.session = SessionContext(session_id="default")
        self.pipeline = Pipeline([NormalizeMiddleware(), LoggingMiddleware()])

        self.bus.emit(EventType.STARTUP, source="engine")
        logger.info(
            "%s online (provider=%s, model=%s, skills=%d)",
            self.settings.assistant_name,
            self.settings.llm_provider,
            self.settings.llm_model,
            len(self.skills),
        )

    # -- public API ---------------------------------------------------------

    def ask(self, user_input: str) -> str:
        """Process one user message and return the assistant's reply text."""
        return self.process(
            Request(text=user_input, session_id=self.session.session_id)
        ).text

    def process(self, request: Request) -> Response:
        """Process a structured :class:`Request` through the full pipeline."""
        self.bus.emit(EventType.USER_INPUT, source="engine", text=request.text)
        try:
            response = self.pipeline.run(request, self._handle)
        except JarvisError as exc:
            self.state.transition(AssistantState.ERROR)
            self.bus.emit(EventType.ERROR, source="engine", error=str(exc))
            logger.error("Turn failed: %s", exc)
            response = Response.system_message(
                f"I ran into a problem: {exc}",
                request_id=request.request_id,
            )
        finally:
            self.state.transition(AssistantState.IDLE)

        self.bus.emit(
            EventType.RESPONSE_READY,
            source=response.source or "engine",
            latency_ms=response.latency_ms,
            tokens=response.tokens,
            via_skill=response.type == ResponseType.SKILL,
        )
        return response

    # -- core handler (wrapped by the pipeline) ----------------------------

    def _handle(self, request: Request) -> Response:
        text = request.text
        if not text:
            return Response.system_message("", request_id=request.request_id)

        # 1) Try a local skill first.
        response = self._try_skill(request)
        if response is not None:
            return response

        # 2) Fall back to the language model.
        return self._ask_llm(request)

    def _try_skill(self, request: Request) -> Response | None:
        self.state.transition(AssistantState.THINKING)

        skill = self.skills.find(request.text)
        if skill is None:
            return None

        try:
            result = skill.handle(request.text, self.session.scratch)
        except Exception as exc:  # noqa: BLE001 - degrade to LLM on skill failure
            self.bus.emit(EventType.SKILL_FAILED, source=skill.name, error=str(exc))
            logger.warning("Skill %r failed (%s) — falling back to LLM", skill.name, exc)
            return None

        if not result.handled:
            return None

        self.bus.emit(EventType.SKILL_MATCHED, source=skill.name)
        # Skill turns are still recorded in history for continuity.
        self.session.conversation.add_user(request.text)
        self.session.conversation.add_assistant(result.text)
        return Response.from_skill(
            result.text,
            skill_name=skill.name,
            request_id=request.request_id,
            metadata=result.metadata,
        )

    def _ask_llm(self, request: Request) -> Response:
        self.state.transition(AssistantState.THINKING)
        self.session.conversation.add_user(request.text)
        system = self.prompts.system_prompt()

        self.bus.emit(EventType.LLM_REQUEST, source=self.settings.llm_provider)
        with measure() as sw:
            result = self.llm.complete(
                self.session.conversation.to_provider_format(),
                system=system,
            )
        self.bus.emit(EventType.LLM_RESPONSE, source=result.provider,
                    tokens=result.total_tokens)

        self.session.conversation.add_assistant(result.text)
        self.state.transition(AssistantState.SPEAKING)
        return Response.from_llm(
            result.text,
            provider=result.provider,
            request_id=request.request_id,
            latency_ms=sw.elapsed_ms,
            tokens=result.total_tokens,
        )

    # -- session management -------------------------------------------------

    def reset(self) -> None:
        """Clear the conversation history for the current session."""
        self.session.reset()
        self.state.reset()
        logger.debug("Session reset.")

    def shutdown(self) -> None:
        """Emit shutdown and release resources."""
        self.bus.emit(EventType.SHUTDOWN, source="engine")

    # -- convenience --------------------------------------------------------

    @property
    def stats(self) -> dict:
        """Telemetry snapshot for the current process."""
        return self.metrics.summary()
