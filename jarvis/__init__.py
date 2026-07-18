"""
J.A.R.V.I.S. — Just A Rather Very Intelligent System.

A personal AI assistant framework with a modular, layered architecture:
voice interface, an LLM-powered intelligence core, memory, integrations,
and task automation.
"""

__version__ = "0.1.0"
__author__ = "nomadnairi"

from jarvis.config.settings import get_settings

__all__ = ["get_settings", "__version__"]
