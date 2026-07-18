"""
Telegram interface for J.A.R.V.I.S.

Each Telegram user gets their own persistent session (``tg-<user_id>``), so the
memory subsystem gives every user independent history and recall. The bot is a
thin adapter over :class:`~jarvis.core.engine.JarvisEngine`; the conversational
logic lives in the engine, not here.

Features: a localized command menu, an inline language picker (English /
Russian / Uzbek), HTML-formatted UI, and per-user language that the assistant
replies in.

Run it with:

    python -m jarvis.interfaces.telegram_bot     # or: jarvis-bot

``aiogram`` is an optional dependency, imported lazily so the rest of the
package works without it.
"""

from __future__ import annotations

import asyncio

from jarvis.config.settings import Settings, get_settings
from jarvis.core.engine import JarvisEngine
from jarvis.i18n import (
    DEFAULT_LOCALE,
    SUPPORTED_LOCALES,
    normalize_locale,
    t,
)
from jarvis.interfaces.user_prefs import UserPreferences
from jarvis.utils.exceptions import ConfigError, JarvisError
from jarvis.utils.logger import get_logger, setup_logging

logger = get_logger(__name__)

# Telegram hard-caps messages at 4096 characters.
_TELEGRAM_MAX = 4096

# Labels for the language-picker buttons (shown in each language natively).
_LANGUAGE_LABELS = {
    "en": "🇬🇧 English",
    "ru": "🇷🇺 Русский",
    "uz": "🇺🇿 O'zbek",
}


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


async def generate_reply(engine: JarvisEngine, user_id: int, text: str,
                        locale: str | None = None) -> str:
    """Produce the assistant's reply for a Telegram user (testable core).

    When ``locale`` is given, the assistant is asked to reply in that language.
    """
    session_id = session_id_for(user_id)
    if locale:
        engine.session(session_id).scratch["language"] = locale
    try:
        return await engine.ask(text, session_id=session_id)
    except JarvisError as exc:
        logger.error("Reply failed for user %s: %s", user_id, exc)
        return t("error", locale, error=str(exc))


def _is_allowed(settings: Settings, user_id: int) -> bool:
    allowlist = settings.telegram_allowlist()
    return not allowlist or user_id in allowlist


def _resolve_locale(prefs: UserPreferences, user) -> str:
    """User's stored language, else a guess from their Telegram client."""
    stored = prefs.get_language(user.id)
    if stored:
        return stored
    return normalize_locale(getattr(user, "language_code", None))


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
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ChatAction, ParseMode
        from aiogram.filters import Command, CommandStart
        from aiogram.types import (
            BotCommand,
            CallbackQuery,
            InlineKeyboardButton,
            InlineKeyboardMarkup,
            Message,
        )
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise ConfigError(
            "The 'aiogram' package is required for the Telegram bot. "
            "Install it with: pip install aiogram"
        ) from exc

    engine = JarvisEngine(settings)
    await engine.start()
    prefs = UserPreferences(settings.memory_db_path)

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    def _language_keyboard() -> "InlineKeyboardMarkup":
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=_LANGUAGE_LABELS[loc], callback_data=f"lang:{loc}")
            for loc in SUPPORTED_LOCALES
        ]])

    async def _guard(message: "Message", locale: str) -> bool:
        if _is_allowed(settings, message.from_user.id):
            return True
        await message.answer(t("not_authorized", locale))
        return False

    @dp.message(CommandStart())
    async def _start(message: "Message") -> None:
        locale = _resolve_locale(prefs, message.from_user)
        if not await _guard(message, locale):
            return
        if prefs.get_language(message.from_user.id) is None:
            await message.answer(t("choose_language", locale),
                                reply_markup=_language_keyboard())
        else:
            await message.answer(t("welcome", locale, name=settings.assistant_name))

    @dp.message(Command("help"))
    async def _help(message: "Message") -> None:
        locale = _resolve_locale(prefs, message.from_user)
        if not await _guard(message, locale):
            return
        await message.answer(t("welcome", locale, name=settings.assistant_name))

    @dp.message(Command("language"))
    async def _language(message: "Message") -> None:
        locale = _resolve_locale(prefs, message.from_user)
        if not await _guard(message, locale):
            return
        await message.answer(t("choose_language", locale),
                            reply_markup=_language_keyboard())

    @dp.callback_query(F.data.startswith("lang:"))
    async def _pick_language(callback: "CallbackQuery") -> None:
        locale = normalize_locale(callback.data.split(":", 1)[1])
        prefs.set_language(callback.from_user.id, locale)
        engine.session(session_id_for(callback.from_user.id)).scratch["language"] = locale
        await callback.message.answer(t("language_set", locale))
        await callback.message.answer(
            t("welcome", locale, name=settings.assistant_name)
        )
        await callback.answer()

    @dp.message(Command("reset"))
    async def _reset(message: "Message") -> None:
        locale = _resolve_locale(prefs, message.from_user)
        if not await _guard(message, locale):
            return
        await engine.reset(session_id_for(message.from_user.id))
        await message.answer(t("reset_done", locale))

    @dp.message(Command("forget"))
    async def _forget(message: "Message") -> None:
        locale = _resolve_locale(prefs, message.from_user)
        if not await _guard(message, locale):
            return
        await engine.forget(session_id_for(message.from_user.id))
        await message.answer(t("forget_done", locale))

    @dp.message(F.text)
    async def _chat(message: "Message") -> None:
        locale = _resolve_locale(prefs, message.from_user)
        if not await _guard(message, locale):
            return
        await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        reply = await generate_reply(engine, message.from_user.id, message.text, locale)
        # LLM output is plain text — disable HTML parsing to avoid entity errors.
        for chunk in split_message(reply):
            await message.answer(chunk, parse_mode=None)

    async def _set_commands() -> None:
        for loc in SUPPORTED_LOCALES:
            commands = [
                BotCommand(command="help", description=t("cmd_help", loc)),
                BotCommand(command="language", description=t("cmd_language", loc)),
                BotCommand(command="reset", description=t("cmd_reset", loc)),
                BotCommand(command="forget", description=t("cmd_forget", loc)),
            ]
            if loc == DEFAULT_LOCALE:
                await bot.set_my_commands(commands)
            else:
                await bot.set_my_commands(commands, language_code=loc)

    await _set_commands()
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
