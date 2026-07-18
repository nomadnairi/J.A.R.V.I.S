"""
Telegram interface for J.A.R.V.I.S.

Each Telegram user gets their own persistent session (``tg-<user_id>``), so the
memory subsystem gives every user independent history and recall. The bot is a
thin adapter over :class:`~jarvis.core.engine.JarvisEngine`; the conversational
logic lives in the engine, not here.

Run it with:

    python -m jarvis.interfaces.telegram_bot     # or: jarvis-bot

``aiogram`` is an optional dependency, imported lazily so the rest of the
package works without it.
"""

from __future__ import annotations

import asyncio

from jarvis.config.settings import Settings, get_settings
from jarvis.core.engine import JarvisEngine
from jarvis.utils.exceptions import ConfigError, JarvisError
from jarvis.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)

# Telegram hard-caps messages at 4096 characters.
_TELEGRAM_MAX = 4096

_WELCOME = (
    "Hello, Sir. I am {name} — your personal assistant.\n\n"
    "Just talk to me naturally. I remember our conversations.\n\n"
    "Commands:\n"
    "/reset — clear our current conversation\n"
    "/forget — wipe everything I remember about you\n"
    "/help — show this message"
)


def session_id_for(user_id: int) -> str:
    """Stable per-user session id."""
    return f"tg-{user_id}"


def split_message(text: str, limit: int = _TELEGRAM_MAX) -> list[str]:
    """Split ``text`` into Telegram-sized chunks on line boundaries."""
    text = text or "…"
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current = ""
    for line in text.split("\n"):
        while len(line) > limit:  # a single very long line
            chunks.append(line[:limit])
            line = line[limit:]
        if len(current) + len(line) + 1 > limit:
            chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)
    return chunks


async def generate_reply(engine: JarvisEngine, user_id: int, text: str) -> str:
    """Produce the assistant's reply for a Telegram user (testable core)."""
    try:
        return await engine.ask(text, session_id=session_id_for(user_id))
    except JarvisError as exc:
        logger.error("Reply failed for user %s: %s", user_id, exc)
        return f"I ran into a problem: {exc}"


def _is_allowed(settings: Settings, user_id: int) -> bool:
    allowlist = settings.telegram_allowlist()
    return not allowlist or user_id in allowlist


async def run(settings: Settings | None = None) -> None:
    """Start the Telegram bot (long-polling)."""
    settings = settings or get_settings()
    setup_logging(level=settings.log_level, log_file=settings.log_file)

    if not settings.telegram_bot_token:
        raise ConfigError(
            "TELEGRAM_BOT_TOKEN is not set. Add it to your .env file "
            "(get a token from @BotFather)."
        )

    try:
        from aiogram import Bot, Dispatcher, F
        from aiogram.enums import ChatAction
        from aiogram.filters import Command, CommandStart
        from aiogram.types import Message
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ConfigError(
            "The 'aiogram' package is required for the Telegram bot. "
            "Install it with: pip install aiogram"
        ) from exc

    engine = JarvisEngine(settings)
    await engine.start()

    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()

    async def _guard(message: "Message") -> bool:
        if _is_allowed(settings, message.from_user.id):
            return True
        await message.answer("Sorry, you're not authorised to use this bot.")
        return False

    @dp.message(CommandStart())
    async def _start(message: "Message") -> None:
        if not await _guard(message):
            return
        await message.answer(_WELCOME.format(name=settings.assistant_name))

    @dp.message(Command("help"))
    async def _help(message: "Message") -> None:
        if not await _guard(message):
            return
        await message.answer(_WELCOME.format(name=settings.assistant_name))

    @dp.message(Command("reset"))
    async def _reset(message: "Message") -> None:
        if not await _guard(message):
            return
        await engine.reset(session_id_for(message.from_user.id))
        await message.answer("Conversation cleared. I still remember key facts.")

    @dp.message(Command("forget"))
    async def _forget(message: "Message") -> None:
        if not await _guard(message):
            return
        await engine.forget(session_id_for(message.from_user.id))
        await message.answer("Done — I've wiped everything I remembered about you.")

    @dp.message(F.text)
    async def _chat(message: "Message") -> None:
        if not await _guard(message):
            return
        await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        reply = await generate_reply(engine, message.from_user.id, message.text)
        for chunk in split_message(reply):
            await message.answer(chunk)

    logger.info("Telegram bot starting (long-polling)…")
    try:
        await dp.start_polling(bot)
    finally:
        await engine.shutdown()
        await bot.session.close()


def main() -> int:
    try:
        asyncio.run(run())
        return 0
    except ConfigError as exc:
        logger.error("%s", exc)
        return 1
    except KeyboardInterrupt:  # pragma: no cover
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
