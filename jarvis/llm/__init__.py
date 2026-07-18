"""
LLM package.

Public surface:
    LLMClient     — unified async client with retry, fallback & streaming.
    LLMProvider   — abstract base every provider implements.
    LLMResult     — normalised completion result (may carry tool calls).
    PromptBuilder — persona / system-prompt construction.
    ToolSpec / ToolCall / ToolResult — provider-neutral tool-calling types.
"""

from jarvis.llm.base import LLMProvider, LLMResult
from jarvis.llm.client import LLMClient
from jarvis.llm.prompts import PromptBuilder
from jarvis.llm.tools import ToolCall, ToolResult, ToolSpec

__all__ = [
    "LLMClient",
    "LLMProvider",
    "LLMResult",
    "PromptBuilder",
    "ToolSpec",
    "ToolCall",
    "ToolResult",
]
