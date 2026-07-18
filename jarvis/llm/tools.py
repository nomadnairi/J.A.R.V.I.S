"""
Provider-neutral tool-calling types.

The LLM layer speaks in these types; each provider converts them to/from its
own wire format (Anthropic ``tool_use`` blocks, OpenAI ``tool_calls``). This
keeps tool/function calling vendor-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ToolSpec:
    """A tool the model may call.

    Attributes:
        name: Unique tool name.
        description: What the tool does (the model reads this to decide).
        parameters: JSON-Schema object describing the tool's arguments.
    """

    name: str
    description: str
    parameters: dict = field(default_factory=lambda: {"type": "object", "properties": {}})

    # -- provider conversions ----------------------------------------------

    def to_anthropic(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters,
        }

    def to_openai(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass
class ToolCall:
    """A concrete request from the model to invoke a tool."""

    id: str
    name: str
    arguments: dict = field(default_factory=dict)


@dataclass
class ToolResult:
    """The outcome of executing a :class:`ToolCall`, fed back to the model."""

    call_id: str
    name: str
    content: str
    is_error: bool = False
