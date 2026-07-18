"""Tests for the per-user preferences store."""

from __future__ import annotations

from jarvis.interfaces.user_prefs import UserPreferences


def test_get_returns_none_when_unset():
    prefs = UserPreferences(":memory:")
    assert prefs.get_language(123) is None


def test_set_and_get_language():
    prefs = UserPreferences(":memory:")
    prefs.set_language(123, "ru")
    assert prefs.get_language(123) == "ru"


def test_set_language_upserts():
    prefs = UserPreferences(":memory:")
    prefs.set_language(123, "ru")
    prefs.set_language(123, "uz")
    assert prefs.get_language(123) == "uz"


def test_users_are_isolated():
    prefs = UserPreferences(":memory:")
    prefs.set_language(1, "ru")
    prefs.set_language(2, "uz")
    assert prefs.get_language(1) == "ru"
    assert prefs.get_language(2) == "uz"
