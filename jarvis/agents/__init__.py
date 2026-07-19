"""
Agent system.

An autonomous sub-agent that takes a task and works toward it in multiple
steps — calling tools, observing results, and iterating — until it produces a
final answer. The main assistant can delegate complex, multi-step work to it
via the ``run_agent`` tool.
"""

from jarvis.agents.agent import Agent, AgentResult

__all__ = ["Agent", "AgentResult"]
