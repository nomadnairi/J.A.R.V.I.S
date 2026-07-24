"""File tools — expose sandboxed file operations to the LLM."""

from __future__ import annotations

from jarvis.files.manager import FileManager
from jarvis.skills.base import BaseSkill, SkillResult
from jarvis.utils.exceptions import JarvisError

_PATH = {
    "type": "object",
    "properties": {"path": {"type": "string", "description": "Path within the workspace."}},
    "required": ["path"],
}


class _FileSkill(BaseSkill):
    priority = 25

    def __init__(self, files: FileManager) -> None:
        self.files = files

    def can_handle(self, text: str) -> bool:
        return False

    async def handle(self, text: str, context: dict | None = None) -> SkillResult:
        return SkillResult.not_handled()

    @staticmethod
    def _guard(result: str) -> SkillResult:
        return SkillResult(text=result)


class ReadFileSkill(_FileSkill):
    name = "read_file"
    description = "Read a text file from the workspace."
    parameters = _PATH

    async def execute(self, path: str = "", **_: object) -> SkillResult:
        try:
            return SkillResult(text=await self.files.read(path))
        except JarvisError as exc:
            return SkillResult(text=f"Cannot read file: {exc}")


class ReadDocumentSkill(_FileSkill):
    name = "read_document"
    description = ("Extract text from a document in the workspace "
                "(PDF, DOCX, or plain text) for reading or summarising.")
    parameters = _PATH

    async def execute(self, path: str = "", **_: object) -> SkillResult:
        try:
            return SkillResult(text=await self.files.read_document(path))
        except JarvisError as exc:
            return SkillResult(text=f"Cannot read document: {exc}")


class WriteFileSkill(_FileSkill):
    name = "write_file"
    description = "Write text to a file in the workspace (may be disabled by policy)."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path within the workspace."},
            "content": {"type": "string", "description": "The text to write."},
        },
        "required": ["path", "content"],
    }

    async def execute(self, path: str = "", content: str = "", **_: object) -> SkillResult:
        try:
            return SkillResult(text=await self.files.write(path, content))
        except JarvisError as exc:
            return SkillResult(text=f"Cannot write file: {exc}")


class ListFilesSkill(_FileSkill):
    name = "list_files"
    description = "List files and folders in a workspace directory."
    parameters = {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "Directory (default '.')."}},
    }

    async def execute(self, path: str = ".", **_: object) -> SkillResult:
        try:
            return SkillResult(text=await self.files.list_dir(path or "."))
        except JarvisError as exc:
            return SkillResult(text=f"Cannot list directory: {exc}")


class SearchFilesSkill(_FileSkill):
    name = "search_files"
    description = "Search the workspace for a text string across files."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Text to search for."},
            "glob": {"type": "string", "description": "Optional glob, e.g. '**/*.py'."},
        },
        "required": ["query"],
    }

    async def execute(self, query: str = "", glob: str = "**/*", **_: object) -> SkillResult:
        try:
            return SkillResult(text=await self.files.search(query, glob or "**/*"))
        except JarvisError as exc:
            return SkillResult(text=f"Cannot search: {exc}")


def file_skills(files: FileManager) -> list[BaseSkill]:
    return [
        ReadFileSkill(files),
        ReadDocumentSkill(files),
        WriteFileSkill(files),
        ListFilesSkill(files),
        SearchFilesSkill(files),
    ]
