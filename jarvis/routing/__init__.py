"""
AI router.

Chooses which model tier handles each turn — a fast, cheap model for simple
requests and a stronger model for complex ones — using transparent heuristics.
Saves cost and latency without a config change per message.
"""

from jarvis.routing.router import AIRouter, ModelTier

__all__ = ["AIRouter", "ModelTier"]
