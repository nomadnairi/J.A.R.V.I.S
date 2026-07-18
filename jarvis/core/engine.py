"""
The J.A.R.V.I.S. engine — the async orchestrator that ties every layer together.

Flow of a single turn:

    Request
      → pipeline (normalise, log, …)
        → skill registry     (fast path: handle locally if a skill matches)
        → LLM agentic loop   (otherwise reason with the model, calling tools)
      → Response
      → events + telemetry

The engine owns the session manager, the state machine, and the wiring
provided by the :class:`~jarvis.core.container.ServiceContainer`.
"""

from __future__ import annotations

from typing import AsyncIterator

from jarvis.config.constants import AssistantState, EventType, ResponseType
from jarvis.config.settings import Settings
from jarvis.core.container import ServiceContainer
from jarvis.core.context import SessionContext
from jarvis.core.pipeline import (
    LoggingMiddleware,
    NormalizeMiddleware,
    Pipeline,
)
from jarvis.core.session import SessionManager
from jarvis.core.state import StateMachine
from jarvis.llm.tools import ToolResult
from jarvis.models.response import Request, Response
from jarvis.utils.exceptions import JarvisError
from jarvis.utils.logger import get_logger
from jarvis.utils.text import normalize
from jarvis.utils.timing import measure

logger = get_logger(__name__)


class JarvisEngine:
    """Central async coordinator for J.A.R.V.I.S."""

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
        self.sessions = SessionManager(max_sessions=self.settings.max_sessions)
        self.pipeline = Pipeline([NormalizeMiddleware(), LoggingMiddleware()])

        logger.info(
            "%s ready (provider=%s, model=%s, skills=%d, tools=%d)",
            self.settings.assistant_name,
            self.settings.llm_provider,
            self.settings.llm_model,
            len(self.skills),
            len(self.skills.tool_specs()),
        )

    # -- lifecycle ----------------------------------------------------------

    async def start(self) -> None:
        await self.bus.emit(EventType.STARTUP, source="engine")

    async def shutdown(self) -> None:
        await self.bus.emit(EventType.SHUTDOWN, source="engine")

    # -- public API ---------------------------------------------------------

    async def ask(self, user_input: str, *, session_id: str = "default") -> str:
        """Process one user message and return the assistant's reply text."""
        response = await self.process(
            Request(text=user_input, session_id=session_id)
        )
        return response.text

    async def process(self, request: Request) -> Response:
        """Process a structured :class:`Request` through the full pipeline."""
        await self.bus.emit(EventType.USER_INPUT, source="engine", text=request.text)
        try:
            response = await self.pipeline.run(request, self._handle)
        except JarvisError as exc:
            await self.state.transition(AssistantState.ERROR)
            await self.bus.emit(EventType.ERROR, source="engine", error=str(exc))
            logger.error("Turn failed: %s", exc)
            response = Response.system_message(
                f"I ran into a problem: {exc}",
                request_id=request.request_id,
            )
        finally:
            await self.state.transition(AssistantState.IDLE)

        await self.bus.emit(
            EventType.RESPONSE_READY,
            source=response.source or "engine",
            latency_ms=response.latency_ms,
            tokens=response.tokens,
            via_skill=response.type == ResponseType.SKILL,
        )
        return response

    async def stream(self, request: Request) -> AsyncIterator[str]:
        """Stream a reply as text chunks.

        Skills are still tried first (their reply is emitted as one chunk);
        otherwise the LLM response is streamed token by token. Tool calling is
        not available on the streaming path — use :meth:`process` for that.
        """
        request.text = normalize(request.text)
        session = self.sessions.get_or_create(request.session_id)
        await self.bus.emit(EventType.USER_INPUT, source="engine", text=request.text)

        skill = self.skills.find(request.text)
        if skill is not None:
            result = await skill.handle(request.text, session.scratch)
            if result.handled:
                session.conversation.add_user(request.text)
                session.conversation.add_assistant(result.text)
                await self.bus.emit(EventType.SKILL_MATCHED, source=skill.name)
                await self.bus.emit(EventType.RESPONSE_READY, source=skill.name,
                                    via_skill=True)
                yield result.text
                await self.state.transition(AssistantState.IDLE)
                return

        # LLM streaming path.
        session.conversation.add_user(request.text)
        system = self.prompts.system_prompt()
        await self.state.transition(AssistantState.THINKING)
        await self.bus.emit(EventType.LLM_REQUEST, source=self.settings.llm_provider)

        chunks: list[str] = []
        async for chunk in self.llm.stream(
            session.conversation.to_provider_format(), system=system
        ):
            chunks.append(chunk)
            yield chunk

        full = "".join(chunks).strip()
        session.conversation.add_assistant(full)
        await self.bus.emit(EventType.RESPONSE_READY, source=self.settings.llm_provider)
        await self.state.transition(AssistantState.IDLE)

    # -- core handler (wrapped by the pipeline) ----------------------------

    async def _handle(self, request: Request) -> Response:
        session = self.sessions.get_or_create(request.session_id)
        if not request.text:
            return Response.system_message("", request_id=request.request_id)

        # 1) Try a local skill first (fast path).
        response = await self._try_skill(request, session)
        if response is not None:
            return response

        # 2) Fall back to the LLM agentic loop.
        return await self._ask_llm(request, session)

    async def _try_skill(
        self, request: Request, session: SessionContext
    ) -> Response | None:
        await self.state.transition(AssistantState.THINKING)

        skill = self.skills.find(request.text)
        if skill is None:
            return None

        try:
            result = await skill.handle(request.text, session.scratch)
        except Exception as exc:  # noqa: BLE001 - degrade to LLM on skill failure
            await self.bus.emit(EventType.SKILL_FAILED, source=skill.name, error=str(exc))
            logger.warning("Skill %r failed (%s) — falling back to LLM", skill.name, exc)
            return None

        if not result.handled:
            return None

        await self.bus.emit(EventType.SKILL_MATCHED, source=skill.name)
        session.conversation.add_user(request.text)
        session.conversation.add_assistant(result.text)
        return Response.from_skill(
            result.text,
            skill_name=skill.name,
            request_id=request.request_id,
            metadata=result.metadata,
        )

    async def _ask_llm(
        self, request: Request, session: SessionContext
    ) -> Response:
        """Run the agentic loop: complete → run tools → repeat → final text."""
        await self.state.transition(AssistantState.THINKING)
        session.conversation.add_user(request.text)

        system = self.prompts.system_prompt()
        tools = self.skills.tool_specs()
        messages = session.conversation.to_provider_format()
        total_tokens = 0
        result = None

        with measure() as sw:
            await self.bus.emit(EventType.LLM_REQUEST, source=self.settings.llm_provider)
            for _ in range(self.settings.max_tool_rounds):
                result = await self.llm.complete(messages, system=system, tools=tools)
                total_tokens += result.total_tokens

                if not result.wants_tools:
                    break

                await self.state.transition(AssistantState.EXECUTING)
                tool_results = await self._run_tools(result)
                messages = messages + self.llm.continuation_messages(result, tool_results)
                await self.state.transition(AssistantState.THINKING)

        assert result is not None
        await self.bus.emit(EventType.LLM_RESPONSE, source=result.provider,
                            tokens=total_tokens)
        session.conversation.add_assistant(result.text)
        await self.state.transition(AssistantState.SPEAKING)
        return Response.from_llm(
            result.text,
            provider=result.provider,
            request_id=request.request_id,
            latency_ms=sw.elapsed_ms,
            tokens=total_tokens,
        )

    async def _run_tools(self, result) -> list[ToolResult]:
        """Execute every tool call requested by the model."""
        tool_results: list[ToolResult] = []
        for call in result.tool_calls:
            await self.bus.emit(EventType.TOOL_CALL, source=call.name,
                                arguments=call.arguments)
            try:
                skill_result = await self.skills.invoke_tool(call.name, call.arguments)
                content, is_error = skill_result.text, False
            except JarvisError as exc:
                content, is_error = f"Tool error: {exc}", True
                await self.bus.emit(EventType.SKILL_FAILED, source=call.name,
                                    error=str(exc))
            tool_results.append(
                ToolResult(call_id=call.id, name=call.name, content=content,
                        is_error=is_error)
            )
            await self.bus.emit(EventType.TOOL_RESULT, source=call.name)
        return tool_results

    # -- session management -------------------------------------------------

    async def reset(self, session_id: str = "default") -> None:
        """Clear the conversation history for a session."""
        self.sessions.reset(session_id)
        await self.state.reset()
        logger.debug("Session %r reset.", session_id)

    def session(self, session_id: str = "default") -> SessionContext:
        """Return (creating if needed) the context for a session."""
        return self.sessions.get_or_create(session_id)

    # -- convenience --------------------------------------------------------

    @property
    def stats(self) -> dict:
        """Telemetry snapshot for the current process."""
        return self.metrics.summary()
