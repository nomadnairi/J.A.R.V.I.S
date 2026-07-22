"""
Document text extraction for the File Manager.

Plain text files are decoded directly; richer formats (PDF, DOCX) are parsed
with optional libraries when they're installed. Everything degrades gracefully:
a missing parser library returns a clear, actionable message instead of raising,
so the assistant can tell the user what to install.
"""

from __future__ import annotations

from pathlib import Path

#: Extensions handled as UTF-8 text (decoded, never parsed).
TEXT_SUFFIXES = {
    ".txt", ".md", ".markdown", ".csv", ".tsv", ".json", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".log", ".py", ".js", ".ts", ".html", ".htm",
    ".xml", ".sh", ".rst",
}
#: Extensions with a dedicated parser (below).
DOC_SUFFIXES = {".pdf", ".docx"}

#: All extensions this module can extract text from.
SUPPORTED_SUFFIXES = TEXT_SUFFIXES | DOC_SUFFIXES


def is_supported(path: str | Path) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_SUFFIXES


def kind_of(path: str | Path) -> str:
    """Return 'text', 'pdf', 'docx' or 'binary' for ``path``."""
    suffix = Path(path).suffix.lower()
    if suffix in TEXT_SUFFIXES:
        return "text"
    if suffix == ".pdf":
        return "pdf"
    if suffix == ".docx":
        return "docx"
    return "binary"


def extract_text(path: str | Path, *, max_chars: int = 200_000) -> str:
    """Extract readable text from a document, truncated to ``max_chars``.

    Never raises for a supported-but-unparseable file; returns a message the
    assistant can relay (e.g. "install pypdf").
    """
    p = Path(path)
    if not p.is_file():
        return f"No such file: {p.name}"
    kind = kind_of(p)
    if kind == "pdf":
        text = _extract_pdf(p)
    elif kind == "docx":
        text = _extract_docx(p)
    elif kind == "text":
        text = p.read_text(encoding="utf-8", errors="replace")
    else:
        return (f"Unsupported file type '{p.suffix}'. Supported: "
                f"{', '.join(sorted(SUPPORTED_SUFFIXES))}.")
    if len(text) > max_chars:
        return text[:max_chars] + "\n…(truncated)"
    return text


def _extract_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except Exception:  # noqa: BLE001 - optional dependency
        return ("This is a PDF. Install 'pypdf' to read it: pip install pypdf")
    try:
        reader = PdfReader(str(path))
        pages = [(page.extract_text() or "") for page in reader.pages]
    except Exception as exc:  # noqa: BLE001
        return f"Could not read PDF: {exc}"
    return "\n\n".join(pages).strip() or "(no extractable text — may be scanned)"


def _extract_docx(path: Path) -> str:
    try:
        import docx  # python-docx
    except Exception:  # noqa: BLE001 - optional dependency
        return ("This is a DOCX. Install 'python-docx' to read it: "
                "pip install python-docx")
    try:
        document = docx.Document(str(path))
        parts = [para.text for para in document.paragraphs]
    except Exception as exc:  # noqa: BLE001
        return f"Could not read DOCX: {exc}"
    return "\n".join(parts).strip() or "(empty document)"
