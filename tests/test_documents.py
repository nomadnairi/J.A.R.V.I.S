"""Tests for document text extraction + File Manager document reading."""

from __future__ import annotations

import pytest

from jarvis.config.settings import Settings
from jarvis.files.documents import (
    SUPPORTED_SUFFIXES,
    extract_text,
    is_supported,
    kind_of,
)
from jarvis.files.manager import FileManager
from jarvis.security.manager import SecurityManager


def test_kind_and_support():
    assert kind_of("a.pdf") == "pdf"
    assert kind_of("a.docx") == "docx"
    assert kind_of("a.md") == "text"
    assert kind_of("a.bin") == "binary"
    assert is_supported("notes.txt") and not is_supported("image.png")
    assert ".pdf" in SUPPORTED_SUFFIXES and ".docx" in SUPPORTED_SUFFIXES


def test_extract_text_reads_plain(tmp_path):
    f = tmp_path / "note.md"
    f.write_text("# Hello\nworld", encoding="utf-8")
    assert "Hello" in extract_text(f)


def test_extract_text_missing_file(tmp_path):
    assert "No such file" in extract_text(tmp_path / "nope.txt")


def test_extract_pdf_without_lib_gives_hint(tmp_path):
    # No pypdf installed in CI -> actionable message, not a crash.
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"%PDF-1.4 fake")
    out = extract_text(f)
    assert "pypdf" in out


def test_extract_unsupported_binary(tmp_path):
    f = tmp_path / "image.png"
    f.write_bytes(b"\x89PNG")
    assert "Unsupported file type" in extract_text(f)


@pytest.mark.asyncio
async def test_file_manager_read_document(tmp_path):
    (tmp_path / "readme.txt").write_text("hello docs", encoding="utf-8")
    fm = FileManager(str(tmp_path),
                    SecurityManager.from_settings(Settings(log_file="")))
    assert "hello docs" in await fm.read_document("readme.txt")
