"""Tests for secret redaction."""

from __future__ import annotations

from jarvis.utils.redaction import contains_secret, redact_secrets


def test_redacts_telegram_bot_token():
    # A syntactically-valid but entirely fake token.
    text = "my token is 1234567890:AAFfakefakefakefakefakefakefakefake00 ok"
    out = redact_secrets(text)
    assert "1234567890" not in out
    assert "[REDACTED]" in out


def test_redacts_openai_key():
    out = redact_secrets("key sk-abcdef0123456789abcdef here")
    assert "sk-abcdef" not in out


def test_redacts_key_value_pair():
    out = redact_secrets("API_KEY=supersecretvalue123")
    assert "supersecretvalue123" not in out


def test_redacts_card_like_number():
    out = redact_secrets("card 4111 1111 1111 1111 please")
    assert "4111" not in out


def test_leaves_normal_text_untouched():
    text = "Remind me to call mom at 5 pm about the trip."
    assert redact_secrets(text) == text
    assert contains_secret(text) is False


def test_contains_secret_true():
    assert contains_secret("sk-ant-abcdef0123456789abcdef") is True
