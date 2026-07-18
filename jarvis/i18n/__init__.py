"""
Lightweight internationalisation for user-facing text.

Message catalogs live in :mod:`jarvis.i18n.catalog`. Use :func:`t` to look up a
key for a locale, with automatic fallback to English and ``str.format``
substitution:

    t("welcome", "ru", name="J.A.R.V.I.S.")
"""

from jarvis.i18n.catalog import (
    DEFAULT_LOCALE,
    LANGUAGE_NAMES,
    SUPPORTED_LOCALES,
    CATALOG,
)


def normalize_locale(locale: str | None) -> str:
    """Return a supported locale code, falling back to the default."""
    if not locale:
        return DEFAULT_LOCALE
    code = locale.split("-")[0].lower()
    return code if code in SUPPORTED_LOCALES else DEFAULT_LOCALE


def t(key: str, locale: str | None = DEFAULT_LOCALE, **kwargs: object) -> str:
    """Translate ``key`` into ``locale``, formatting with ``kwargs``.

    Falls back to the default locale, then to the key itself, so a missing
    translation degrades gracefully instead of raising.
    """
    code = normalize_locale(locale)
    text = CATALOG.get(code, {}).get(key)
    if text is None:
        text = CATALOG[DEFAULT_LOCALE].get(key, key)
    try:
        return text.format(**kwargs) if kwargs else text
    except (KeyError, IndexError):
        return text


def language_name(locale: str | None) -> str:
    """Human-readable language name for the given locale (for LLM prompts)."""
    return LANGUAGE_NAMES.get(normalize_locale(locale), "English")


__all__ = [
    "t",
    "normalize_locale",
    "language_name",
    "SUPPORTED_LOCALES",
    "DEFAULT_LOCALE",
    "LANGUAGE_NAMES",
]
