"""Tests for the desktop theme helpers (pure, no Qt)."""

from __future__ import annotations

import pytest

from jarvis.desktop_app.theme import (
    DEFAULT_THEME,
    THEMES,
    bubble_html,
    stylesheet,
    theme_names,
)


def test_every_theme_builds_a_stylesheet():
    for name in THEMES:
        css = stylesheet(name)
        assert "QPushButton" in css and "QMainWindow" in css
        assert THEMES[name]["accent"] in css


def test_unknown_theme_falls_back():
    assert stylesheet("does-not-exist") == stylesheet(DEFAULT_THEME)


def test_theme_names_pairs():
    names = theme_names()
    keys = {k for k, _ in names}
    assert keys == set(THEMES)
    assert all(label for _, label in names)


def test_all_themes_share_the_same_keys():
    ref = set(THEMES[DEFAULT_THEME])
    for name, palette in THEMES.items():
        assert set(palette) == ref, name


@pytest.mark.parametrize("theme", list(THEMES))
def test_bubble_html_per_theme(theme):
    user = bubble_html("user", "hi", theme)
    assistant = bubble_html("assistant", "yo", theme)
    assert "right" in user and "left" in assistant
    assert THEMES[theme]["panel"] in assistant


def test_bubble_html_escapes_and_keeps_newlines():
    out = bubble_html("assistant", "<script>x</script>\nsecond")
    assert "<script>" not in out
    assert "&lt;script&gt;" in out and "<br>" in out
