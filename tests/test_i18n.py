"""Tests for the i18n translation layer."""

from __future__ import annotations

from jarvis.i18n import DEFAULT_LOCALE, language_name, normalize_locale, t


def test_translates_known_key():
    assert "персональный" in t("welcome", "ru", name="X")
    assert "yordamchi" in t("welcome", "uz", name="X")
    assert "personal assistant" in t("welcome", "en", name="X")


def test_formats_placeholders():
    assert "J.A.R.V.I.S." in t("welcome", "en", name="J.A.R.V.I.S.")


def test_unknown_locale_falls_back_to_english():
    assert t("reset_done", "fr") == t("reset_done", "en")


def test_unknown_key_returns_key():
    assert t("no_such_key", "en") == "no_such_key"


def test_normalize_locale():
    assert normalize_locale("ru-RU") == "ru"
    assert normalize_locale("de") == DEFAULT_LOCALE
    assert normalize_locale(None) == DEFAULT_LOCALE


def test_language_name():
    assert language_name("ru") == "Russian"
    assert language_name("uz") == "Uzbek"
    assert language_name(None) == "English"
