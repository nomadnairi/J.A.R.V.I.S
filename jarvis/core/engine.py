"""
The J.A.R.V.I.S. engine — the orchestrator that ties the layers together.

At Stage 1 the engine is intentionally small: it owns the assistant persona,
keeps a short in-memory conversation history, and routes user input through
the :class:`~jarvis.core.llm.LLMClient`. Later stages plug memory,
integrations, and task automation into this same object.
"""

from __future__ import annotations

from jarvis.config.settings import Settings, get_settings
from jarvis.core.llm import LLMClient, Message
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class JarvisEngine:
    """Central coordinator for a J.A.R.V.I.S. session."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.llm = LLMClient(self.settings)
        self._history: list[Message] = []
        logger.info(
            "%s engine initialised (provider=%s, model=%s)",
            self.settings.assistant_name,
            self.settings.llm_provider,
            self.settings.llm_model,
        )

    # -- persona ------------------------------------------------------------

    @property
    def system_prompt(self) -> str:
        """The persona / behaviour contract sent to the LLM."""
        return (
            f"You are {self.settings.assistant_name}, a highly capable, "
            f"witty, and loyal personal AI assistant modelled after Tony "
            f"Stark's J.A.R.V.I.S. You address the user as "
            f"'{self.settings.user_name}'. Be concise, proactive, and precise. "
            f"When you are unsure, say so plainly rather than inventing facts."
        )

    # -- conversation -------------------------------------------------------

    def ask(self, user_input: str) -> str:
        """Process one user message and return the assistant's reply.

        The exchange is appended to the in-memory history so the model has
        conversational context on subsequent turns.
        """
        self._history.append(Message(role="user", content=user_input))
        reply = self.llm.chat(self._history, system=self.system_prompt)
        self._history.append(Message(role="assistant", content=reply))
        return reply

    def reset(self) -> None:
        """Clear the conversation history."""
        self._history.clear()
        logger.debug("Conversation history cleared.")

    @property
    def history(self) -> list[Message]:
        """A copy of the current conversation history."""
        return list(self._history)
