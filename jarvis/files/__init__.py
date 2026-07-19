"""
File manager.

Sandboxed file access for the assistant: read, write, list and search files —
all confined to a configured workspace root and gated by the security module
(writes are off by default). Exposed to the LLM as tools.
"""

from jarvis.files.manager import FileManager

__all__ = ["FileManager"]
