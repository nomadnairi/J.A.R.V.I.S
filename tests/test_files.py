"""Tests for the sandboxed file manager."""

from __future__ import annotations

import pytest

from jarvis.config.settings import Settings
from jarvis.files.manager import FileManager
from jarvis.security.manager import SecurityManager
from jarvis.utils.exceptions import PermissionDenied, SecurityError


def _security(write: bool = True) -> SecurityManager:
    return SecurityManager.from_settings(
        Settings(allow_file_read=True, allow_file_write=write, audit_log_path="")
    )


def _fm(tmp_path, write: bool = True) -> FileManager:
    return FileManager(str(tmp_path), _security(write))


@pytest.mark.asyncio
async def test_write_then_read(tmp_path):
    fm = _fm(tmp_path)
    await fm.write("notes/todo.txt", "buy milk")
    assert "buy milk" in await fm.read("notes/todo.txt")


@pytest.mark.asyncio
async def test_read_missing_file(tmp_path):
    fm = _fm(tmp_path)
    assert "No such file" in await fm.read("nope.txt")


@pytest.mark.asyncio
async def test_list_dir(tmp_path):
    fm = _fm(tmp_path)
    await fm.write("a.txt", "1")
    await fm.write("b.txt", "2")
    listing = await fm.list_dir(".")
    assert "a.txt" in listing and "b.txt" in listing


@pytest.mark.asyncio
async def test_search(tmp_path):
    fm = _fm(tmp_path)
    await fm.write("code.py", "def hello():\n    return 42")
    result = await fm.search("hello")
    assert "code.py" in result


@pytest.mark.asyncio
async def test_sandbox_blocks_escape(tmp_path):
    fm = _fm(tmp_path)
    with pytest.raises(SecurityError):
        await fm.read("../../etc/passwd")


@pytest.mark.asyncio
async def test_write_denied_when_disabled(tmp_path):
    fm = _fm(tmp_path, write=False)
    with pytest.raises(PermissionDenied):
        await fm.write("x.txt", "data")


@pytest.mark.asyncio
async def test_file_tools_report_permission_error(tmp_path):
    from jarvis.files.tools import WriteFileSkill

    skill = WriteFileSkill(_fm(tmp_path, write=False))
    result = await skill.execute(path="x.txt", content="data")
    assert "Cannot write file" in result.text  # error surfaced, not raised
