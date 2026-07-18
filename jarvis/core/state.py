"""
Assistant state machine.

Tracks the high-level lifecycle state of the assistant (idle → listening →
thinking → speaking → …) and emits a ``STATE_CHANGED`` event on every
transition so the UI and telemetry can react.
"""

from __future__ import annotations

from jarvis.config.constants import AssistantState, EventType
from jarvis.events.bus import EventBus
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)

#: Allowed transitions. ERROR and IDLE are reachable from anywhere.
_TRANSITIONS: dict[AssistantState, set[AssistantState]] = {
    AssistantState.IDLE: {AssistantState.LISTENING, AssistantState.THINKING},
    AssistantState.LISTENING: {AssistantState.THINKING, AssistantState.IDLE},
    AssistantState.THINKING: {AssistantState.SPEAKING, AssistantState.EXECUTING,
                            AssistantState.IDLE},
    AssistantState.EXECUTING: {AssistantState.SPEAKING, AssistantState.IDLE},
    AssistantState.SPEAKING: {AssistantState.IDLE, AssistantState.LISTENING},
    AssistantState.ERROR: {AssistantState.IDLE},
}


class StateMachine:
    """Manages :class:`AssistantState` transitions."""

    def __init__(self, bus: EventBus | None = None) -> None:
        self._state = AssistantState.IDLE
        self._bus = bus

    @property
    def state(self) -> AssistantState:
        return self._state

    def can_transition(self, target: AssistantState) -> bool:
        if target in (AssistantState.ERROR, AssistantState.IDLE):
            return True
        return target in _TRANSITIONS.get(self._state, set())

    def transition(self, target: AssistantState) -> None:
        """Move to ``target`` if the transition is allowed."""
        if target == self._state:
            return
        if not self.can_transition(target):
            logger.debug(
                "Ignoring invalid transition %s → %s", self._state, target
            )
            return
        previous, self._state = self._state, target
        logger.debug("State %s → %s", previous, target)
        if self._bus is not None:
            self._bus.emit(
                EventType.STATE_CHANGED,
                source="state_machine",
                previous=previous.value,
                current=target.value,
            )

    def reset(self) -> None:
        self.transition(AssistantState.IDLE)
