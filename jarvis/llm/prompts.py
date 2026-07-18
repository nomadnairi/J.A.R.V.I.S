"""
Prompt construction.

Centralises the assistant's persona and any system-prompt scaffolding so the
"voice" of J.A.R.V.I.S. lives in one place rather than being scattered across
the codebase.
"""

from __future__ import annotations

from datetime import datetime


class PromptBuilder:
    """Builds system prompts for the assistant."""

    def __init__(self, assistant_name: str, user_name: str) -> None:
        self.assistant_name = assistant_name
        self.user_name = user_name

    def persona(self) -> str:
        """The core persona / behaviour contract."""
        return (
            f"You are {self.assistant_name}, a highly capable, witty, and "
            f"unfailingly loyal personal AI assistant modelled after Tony "
            f"Stark's J.A.R.V.I.S.\n"
            f"You address the user as '{self.user_name}'.\n\n"
            "Principles:\n"
            "- Be concise, precise, and proactive.\n"
            "- Offer the most useful next action, not just an answer.\n"
            "- If you are unsure or lack data, say so plainly — never invent "
            "facts.\n"
            "- Keep a dry, understated wit; never be obsequious.\n"
        )

    def system_prompt(self, *, extra_context: str | None = None,
                    include_time: bool = True) -> str:
        """Assemble the full system prompt.

        Args:
            extra_context: Optional additional context (e.g. retrieved memory,
                available skills) appended to the persona.
            include_time: Whether to inject the current date/time.
        """
        parts = [self.persona()]
        if include_time:
            now = datetime.now().strftime("%A, %d %B %Y, %H:%M")
            parts.append(f"Current date and time: {now}.")
        if extra_context:
            parts.append(extra_context.strip())
        return "\n\n".join(parts)
