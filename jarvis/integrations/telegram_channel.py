"""
Telegram messaging integration — lets the assistant SEND messages via your bot.

This is the outbound half of Telegram: from any surface (desktop app, CLI,
API), J.A.R.V.I.S. can post to a channel or write to a chat through the same
bot the Telegram interface runs on. It is safe to use while the bot is
polling — only ``getUpdates`` conflicts between processes, ``sendMessage``
does not.

Exposed tools:
    telegram_post     — post to the configured channel (announcements).
    telegram_send     — send a message to an explicit chat id.

Both are gated: the integration only activates when a bot token is configured
AND ``telegram_send_enabled`` is on, so the assistant cannot message anyone
unless you explicitly allow it.
"""

from __future__ import annotations

from jarvis.integrations.base import (
    BaseIntegration,
    IntegrationAction,
    IntegrationStatus,
)
from jarvis.integrations.http import HttpClient, HttpError
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)

_API = "https://api.telegram.org"


class TelegramIntegration(BaseIntegration):
    """Send messages/posts through the Telegram bot."""

    name = "telegram"
    description = "Send messages and channel posts via the Telegram bot."

    def __init__(
        self,
        token: str,
        *,
        enabled: bool = False,
        default_channel: str = "",
        http: HttpClient | None = None,
    ) -> None:
        super().__init__()
        self._token = token
        self._enabled = enabled
        self._default_channel = default_channel.strip()
        self._http = http or HttpClient()

    def is_configured(self) -> bool:
        return bool(self._token) and self._enabled

    async def connect(self) -> IntegrationStatus:
        try:
            me = await self._http.get_json(f"{_API}/bot{self._token}/getMe")
        except HttpError as exc:
            return self._mark_error(str(exc))
        username = me.get("result", {}).get("username", "?")
        return self._mark_connected(f"@{username}")

    def actions(self) -> list[IntegrationAction]:
        actions = [
            IntegrationAction(
                name="telegram_send",
                description=(
                    "Send a text message to a Telegram chat via the bot. "
                    "Use only when the user asks you to message someone."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "chat_id": {
                            "type": "string",
                            "description": "Target chat id or @channelusername.",
                        },
                        "text": {"type": "string", "description": "Message text."},
                    },
                    "required": ["chat_id", "text"],
                },
                handler=self.send,
            ),
        ]
        if self._default_channel:
            actions.append(
                IntegrationAction(
                    name="telegram_post",
                    description=(
                        "Publish a post to the configured Telegram channel "
                        f"({self._default_channel}). Use when the user asks "
                        "to post/announce something on the channel."
                    ),
                    parameters={
                        "type": "object",
                        "properties": {
                            "text": {"type": "string",
                                    "description": "Post text."},
                        },
                        "required": ["text"],
                    },
                    handler=self.post,
                )
            )
        return actions

    # -- handlers -------------------------------------------------------------

    async def send(self, chat_id: str = "", text: str = "", **_: object) -> str:
        chat_id = str(chat_id).strip()
        text = (text or "").strip()
        if not chat_id or not text:
            return "Both chat_id and text are required."
        try:
            await self._http.post_json(
                f"{_API}/bot{self._token}/sendMessage",
                json={"chat_id": chat_id, "text": text},
            )
        except HttpError as exc:
            logger.warning("telegram_send failed: %s", exc)
            return f"Sending failed: {exc}"
        return f"Message sent to {chat_id}."

    async def post(self, text: str = "", **_: object) -> str:
        if not self._default_channel:
            return "No channel configured (set TELEGRAM_CHANNEL)."
        return await self.send(chat_id=self._default_channel, text=text)
