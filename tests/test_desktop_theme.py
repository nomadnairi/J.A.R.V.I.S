"""Tests for the desktop theme helpers (pure, no Qt)."""

from __future__ import annotations

from jarvis.desktop_app.theme import ACCENT, bubble_html, stylesheet


def test_stylesheet_is_populated():
    css = stylesheet()
    assert "QPushButton" in css
    assert ACCENT in css
    assert "QMainWindow" in css


def test_bubble_html_roles():
    user = bubble_html("user", "hi")
    assistant = bubble_html("assistant", "hello")
    system = bubble_html("system", "note")
    assert "right" in user
    assert "left" in assistant
    assert "note" in system


def test_bubble_html_escapes_and_keeps_newlines():
    out = bubble_html("assistant", "<script>alert(1)</script>\nsecond")
    assert "<script>" not in out
    assert "&lt;script&gt;" in out
    assert "<br>" in out
