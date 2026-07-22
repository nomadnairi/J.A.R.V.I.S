"""
Sandboxed file operations.

Every path is resolved and confined to ``workspace_root`` — attempts to escape
it (``..``, absolute paths outside the root, symlinks) raise a
:class:`SecurityError`. Reads and writes are gated by the
:class:`~jarvis.security.manager.SecurityManager`, and sizes are capped.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from jarvis.security.manager import SecurityManager
from jarvis.security.policy import Capability
from jarvis.utils.exceptions import SecurityError
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)

_MAX_READ_BYTES = 200_000
_MAX_WRITE_BYTES = 500_000
_MAX_LIST = 200
_MAX_MATCHES = 100


class FileManager:
    """Read/write/list/search files, sandboxed to a workspace root."""

    def __init__(self, root: str, security: SecurityManager) -> None:
        self.root = Path(root).resolve()
        self.security = security

    # -- path safety --------------------------------------------------------

    def _safe_path(self, path: str) -> Path:
        candidate = (self.root / path).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise SecurityError(f"Path escapes the workspace: {path!r}")
        return candidate

    def _rel(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.root))
        except ValueError:  # pragma: no cover - defensive
            return str(path)

    # -- operations (sync bodies; async wrappers below) --------------------

    def _read(self, path: str) -> str:
        self.security.require(Capability.FILE_READ, f"read {path}")
        target = self._safe_path(path)
        if not target.is_file():
            return f"No such file: {path}"
        data = target.read_bytes()[:_MAX_READ_BYTES]
        text = data.decode("utf-8", errors="replace")
        suffix = "\n…(truncated)" if target.stat().st_size > _MAX_READ_BYTES else ""
        return text + suffix

    def _write(self, path: str, content: str) -> str:
        self.security.require(Capability.FILE_WRITE, f"write {path}")
        if len(content.encode("utf-8")) > _MAX_WRITE_BYTES:
            return "Refusing to write: content too large."
        target = self._safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} chars to {self._rel(target)}."

    def _list(self, path: str = ".") -> str:
        self.security.require(Capability.FILE_READ, f"list {path}")
        target = self._safe_path(path)
        if not target.is_dir():
            return f"Not a directory: {path}"
        entries = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name))
        names = [f"{p.name}/" if p.is_dir() else p.name for p in entries[:_MAX_LIST]]
        more = "" if len(entries) <= _MAX_LIST else f" (+{len(entries) - _MAX_LIST} more)"
        return "\n".join(names) + more if names else "(empty)"

    def _search(self, query: str, glob: str = "**/*") -> str:
        self.security.require(Capability.FILE_READ, f"search {query!r}")
        if not query:
            return "Please provide a search query."
        matches: list[str] = []
        for path in self.root.glob(glob):
            if not path.is_file():
                continue
            try:
                for i, line in enumerate(
                    path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1
                ):
                    if query in line:
                        matches.append(f"{self._rel(path)}:{i}: {line.strip()[:120]}")
                        if len(matches) >= _MAX_MATCHES:
                            return "\n".join(matches) + "\n…(more matches)"
            except OSError:
                continue
        return "\n".join(matches) if matches else f"No matches for {query!r}."

    def _read_document(self, path: str) -> str:
        """Extract text from a document (PDF / DOCX / text), sandboxed + gated."""
        from jarvis.files.documents import extract_text
        self.security.require(Capability.FILE_READ, f"read document {path}")
        target = self._safe_path(path)
        if not target.is_file():
            return f"No such file: {path}"
        return extract_text(target, max_chars=_MAX_READ_BYTES)

    # -- async API ----------------------------------------------------------

    async def read(self, path: str) -> str:
        return await asyncio.to_thread(self._read, path)

    async def read_document(self, path: str) -> str:
        return await asyncio.to_thread(self._read_document, path)

    async def write(self, path: str, content: str) -> str:
        return await asyncio.to_thread(self._write, path, content)

    async def list_dir(self, path: str = ".") -> str:
        return await asyncio.to_thread(self._list, path)

    async def search(self, query: str, glob: str = "**/*") -> str:
        return await asyncio.to_thread(self._search, query, glob)
