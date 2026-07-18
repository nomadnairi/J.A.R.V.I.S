"""
LLM package.

Public surface:
    LLMClient  — unified, provider-agnostic client with retry & fallback.
    LLMProvider — abstract base every provider implements.
    LLMResult  — normalised completion result.
    PromptBuilder — persona / system-prompt construction.
"""

from jarvis.llm.base import LLMProvider, LLMResult
from jarvis.llm.client import LLMClient
from jarvis.llm.prompts import PromptBuilder

__all__ = ["LLMClient", "LLMProvider", "LLMResult", "PromptBuilder"]
