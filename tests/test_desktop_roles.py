"""Owner (admin) vs signed-in guest (user) desktop tab visibility."""

from __future__ import annotations

from jarvis.desktop_app.app import visible_tabs


def test_admin_sees_everything():
    tabs = visible_tabs("admin")
    for t in ("deck", "chat", "voice", "general", "capabilities", "logs"):
        assert t in tabs
    # Command Deck is first.
    assert tabs[0] == "deck"


def test_user_is_limited():
    tabs = visible_tabs("user")
    assert set(tabs) == {"deck", "chat", "voice", "memory"}
    # No engine/API config, capabilities or logs for guests.
    for hidden in ("general", "capabilities", "integrations", "logs", "assistant"):
        assert hidden not in tabs


def test_config_defaults_to_admin():
    from jarvis.desktop_app.config import AppConfig
    assert AppConfig().role == "admin"
