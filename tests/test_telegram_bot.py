"""Tests for the Telegram interface's testable core (no network / no aiogram)."""

from __future__ import annotations

import pytest

from jarvis.config.settings import Settings
from jarvis.interfaces.telegram_bot import (
    _is_allowed,
    generate_reply,
    session_id_for,
    split_message,
)


def test_session_id_is_per_user():
    assert session_id_for(42) == "tg-42"
    assert session_id_for(1) != session_id_for(2)


def test_split_message_short_passthrough():
    assert split_message("hello") == ["hello"]


def test_split_message_respects_limit():
    text = "\n".join(f"line {i}" for i in range(1000))
    chunks = split_message(text, limit=100)
    assert all(len(c) <= 100 for c in chunks)
    assert "".join(chunks).replace("\n", "") == text.replace("\n", "")


def test_split_message_handles_one_very_long_line():
    chunks = split_message("x" * 250, limit=100)
    assert len(chunks) == 3
    assert "".join(chunks) == "x" * 250


def test_allowlist_open_by_default():
    s = Settings(telegram_allowed_users="")
    assert _is_allowed(s, 12345) is True


def test_allowlist_restricts():
    s = Settings(telegram_allowed_users="111, 222")
    assert _is_allowed(s, 111) is True
    assert _is_allowed(s, 999) is False


@pytest.mark.asyncio
async def test_generate_reply_routes_to_engine(engine):
    reply = await generate_reply(engine, user_id=7, text="hello there")
    assert reply == "Certainly, Sir."


@pytest.mark.asyncio
async def test_generate_reply_uses_per_user_session(engine):
    await generate_reply(engine, user_id=1, text="I am user one")
    await generate_reply(engine, user_id=2, text="I am user two")
    assert engine.session(session_id_for(1)) is not engine.session(session_id_for(2))
    assert len(engine.session(session_id_for(1)).conversation) == 2
