"""
Language-code helpers for the voice layer.

Whisper reports the spoken language either as a full English name ("russian")
or an ISO-639-1 code ("ru") depending on backend; TTS engines want a 2-letter
code. :func:`lang_code` normalises either form.
"""

from __future__ import annotations

_NAME_TO_CODE = {
    "english": "en",
    "russian": "ru",
    "uzbek": "uz",
    "kazakh": "kk",
    "turkish": "tr",
    "ukrainian": "uk",
    "german": "de",
    "french": "fr",
    "spanish": "es",
    "italian": "it",
    "arabic": "ar",
    "chinese": "zh",
    "japanese": "ja",
    "korean": "ko",
    "hindi": "hi",
    "portuguese": "pt",
}


def lang_code(language: str | None, default: str = "en") -> str:
    """Return a 2-letter language code from a name or code (best-effort)."""
    if not language:
        return default
    value = language.strip().lower()
    if value in _NAME_TO_CODE:
        return _NAME_TO_CODE[value]
    if len(value) == 2:
        return value
    # e.g. "ru-RU" -> "ru"
    return value.split("-")[0][:2] or default
