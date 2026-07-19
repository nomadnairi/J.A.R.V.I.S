"""Tests for the outbound Telegram integration (send / channel post)."""

from __future__ import annotations


from jarvis.integrations.http import HttpError
from jarvis.integrations.telegram_channel import TelegramIntegration

FAKE_TOKEN = "1234567890:AAFfakefakefakefakefakefakefakefake00"


class FakeHttp:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.posts: list[tuple[str, dict]] = []

    async def get_json(self, url, **kwargs):
        if self.fail:
            raise HttpError("boom")
        return {"result": {"username": "jarvis_bot"}}

    async def post_json(self, url, *, json=None, **kwargs):
        if self.fail:
            raise HttpError("boom")
        self.posts.append((url, json))
        return {"ok": True}


def test_unconfigured_without_token_or_flag():
    assert not TelegramIntegration("", enabled=True).is_configured()
    assert not TelegramIntegration(FAKE_TOKEN, enabled=False).is_configured()
    assert TelegramIntegration(FAKE_TOKEN, enabled=True).is_configured()


async def test_connect_reports_bot_username():
    integration = TelegramIntegration(FAKE_TOKEN, enabled=True, http=FakeHttp())
    status = await integration.connect()
    assert status.detail == "@jarvis_bot"


async def test_connect_error_marks_error():
    integration = TelegramIntegration(FAKE_TOKEN, enabled=True,
                                    http=FakeHttp(fail=True))
    status = await integration.connect()
    assert status.state.value == "error"


async def test_send_message():
    http = FakeHttp()
    integration = TelegramIntegration(FAKE_TOKEN, enabled=True, http=http)
    out = await integration.send(chat_id="@somebody", text="hello")
    assert "sent" in out.lower()
    url, payload = http.posts[0]
    assert "sendMessage" in url
    assert payload == {"chat_id": "@somebody", "text": "hello"}
    # The token appears only in the URL path (Telegram's API shape), never logged.


async def test_send_requires_args():
    integration = TelegramIntegration(FAKE_TOKEN, enabled=True, http=FakeHttp())
    assert "required" in await integration.send(chat_id="", text="hi")
    assert "required" in await integration.send(chat_id="@x", text="")


async def test_post_uses_default_channel():
    http = FakeHttp()
    integration = TelegramIntegration(FAKE_TOKEN, enabled=True,
                                    default_channel="@jar_v1_s", http=http)
    out = await integration.post(text="News!")
    assert "@jar_v1_s" in out
    assert http.posts[0][1]["chat_id"] == "@jar_v1_s"


async def test_post_without_channel():
    integration = TelegramIntegration(FAKE_TOKEN, enabled=True, http=FakeHttp())
    assert "No channel" in await integration.post(text="x")


def test_actions_expose_post_only_with_channel():
    without = TelegramIntegration(FAKE_TOKEN, enabled=True)
    names = {a.name for a in without.actions()}
    assert names == {"telegram_send"}
    with_channel = TelegramIntegration(FAKE_TOKEN, enabled=True,
                                    default_channel="@ch")
    names = {a.name for a in with_channel.actions()}
    assert names == {"telegram_send", "telegram_post"}


async def test_send_failure_is_reported_not_raised():
    integration = TelegramIntegration(FAKE_TOKEN, enabled=True,
                                    http=FakeHttp(fail=True))
    out = await integration.send(chat_id="@x", text="hi")
    assert "failed" in out.lower()
