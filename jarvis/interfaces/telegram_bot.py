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
from jarvis.voice import VoiceService

logger = get_logger(__name__)

# Telegram hard-caps messages at 4096 characters.
_TELEGRAM_MAX = 4096

# Reconnect backoff for the always-on polling loop (seconds).
_POLL_BACKOFF_INITIAL = 3.0
_POLL_BACKOFF_MAX = 300.0

# Labels for the language-picker buttons (shown in each language natively).
_LANGUAGE_LABELS = {
    "en": "🇬🇧 English",
    "ru": "🇷🇺 Русский",
    "uz": "🇺🇿 O'zbek",
}

# Labels for the model/AI-picker buttons.
_MODEL_LABELS = {
    "claude": "🧠 Claude (Anthropic)",
    "gpt": "💬 ChatGPT (OpenAI)",
    "openrouter": "🌐 OpenRouter",
    "auto": "⚙️ Auto",
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
                        locale: str | None = None, *,
                        match_input_language: bool = False,
                        model_profile: str | None = None,
                        usage=None) -> str:
    """Produce the assistant's reply for a Telegram user (testable core).

    When ``locale`` is given (and ``match_input_language`` is False), the
    assistant is asked to reply in that language. For voice, set
    ``match_input_language=True`` so the reply matches the language the user
    actually spoke, whatever it is. ``model_profile`` picks the user's chosen
    AI. If a ``usage`` store is given, the turn's token count is recorded.
    """
    from jarvis.models.response import Request

    session_id = session_id_for(user_id)
    session = engine.session(session_id)
    if match_input_language:
        session.scratch.pop("language", None)
    elif locale:
        session.scratch["language"] = locale
    if model_profile:
        session.scratch["model_profile"] = model_profile
    try:
        response = await engine.process(Request(text=text, session_id=session_id))
        if usage is not None:
            usage.record(user_id, tokens=response.tokens)
        return response.text
    except JarvisError as exc:
        logger.error("Reply failed for user %s: %s", user_id, exc)
        return t("error", locale, error=str(exc))


def _is_allowed(settings: Settings, user_id: int) -> bool:
    allowlist = settings.telegram_allowlist()
    return not allowlist or user_id in allowlist


def handle_successful_payment(billing, settings: Settings, telegram_user_id: int,
                            charge_id: str, locale: str, *,
                            amount: int = 0, currency: str = "") -> str:
    """Fulfil a paid Telegram invoice and return the reply text (testable core)."""
    days = settings.billing_plan_days or None
    fulfillment = billing.process_payment(
        charge_id,
        telegram_user_id=telegram_user_id,
        plan=settings.billing_plan,
        valid_days=days,
        amount=amount,
        currency=currency,
    )
    if fulfillment is None:  # duplicate delivery of the same charge
        return t("buy_thanks_existing", locale, username="—")
    if fulfillment.created_account:
        return t("buy_thanks_new", locale, username=fulfillment.username,
                password=fulfillment.password)
    return t("buy_thanks_existing", locale, username=fulfillment.username)


def handle_link(service, text: str, telegram_user_id: int, locale: str) -> str:
    """Process ``/link <code>`` and return the reply text (testable core).

    ``service`` is a :class:`~jarvis.licensing.service.LicenseService` or
    ``None`` when accounts are disabled on this server.
    """
    if service is None:
        return t("link_disabled", locale)
    parts = (text or "").split(maxsplit=1)
    code = parts[1].strip() if len(parts) > 1 else ""
    if not code:
        return t("link_usage", locale)
    account = service.confirm_pairing(code, telegram_user_id)
    if account is None:
        return t("link_invalid", locale)
    return t("link_success", locale, username=account.username)


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
            BufferedInputFile,
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
    voice = VoiceService.from_settings(settings) if settings.voice_enabled else None
    license_service = None
    if settings.auth_enabled:
        from jarvis.licensing import LicenseService
        license_service = LicenseService(
            settings.auth_db_path, token_ttl_hours=settings.auth_token_ttl_hours
        )
    billing = None
    if settings.billing_enabled and license_service is not None:
        from jarvis.billing import BillingService
        billing = BillingService(license_service, settings.auth_db_path)
    from jarvis.interfaces.usage import UsageStore
    usage = UsageStore(settings.memory_db_path)

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

    def _button(label: str, data: str) -> "InlineKeyboardButton":
        # A "data" that looks like a URL becomes a link button, else a callback.
        if data.startswith("http"):
            return InlineKeyboardButton(text=label, url=data)
        return InlineKeyboardButton(text=label, callback_data=data)

    def _markup(rows) -> "InlineKeyboardMarkup":
        return InlineKeyboardMarkup(inline_keyboard=[
            [_button(label, data) for label, data in row] for row in rows
        ])

    def _main_screen(user_id: int, locale: str):
        from jarvis.interfaces.bot_menu import screen_main
        return screen_main(
            locale,
            is_admin=user_id in settings.telegram_admins(),
            billing_on=billing is not None,
            accounts_on=license_service is not None,
            multi_model=len(engine.llm.list_profiles()) > 1,
            voice_on=voice is not None and voice.stt_available(),
            channel=settings.telegram_channel,
            name=settings.user_name,
        )

    async def _is_subscribed(user_id: int) -> bool:
        """True if the user is in the required channel (or none is configured)."""
        channel = settings.telegram_required_channel
        if not channel:
            return True
        try:
            member = await bot.get_chat_member(channel, user_id)
            return member.status not in ("left", "kicked")
        except Exception as exc:  # noqa: BLE001 - treat lookup errors as blocked
            logger.debug("Subscription check failed for %s: %s", user_id, exc)
            return False

    async def _show_gate(message: "Message", locale: str) -> None:
        from jarvis.interfaces.bot_menu import gate_screen
        text, rows = gate_screen(locale, settings.telegram_required_channel)
        await message.answer(text, reply_markup=_markup(rows))

    async def _guard(message: "Message", locale: str) -> bool:
        if _is_allowed(settings, message.from_user.id):
            return True
        await message.answer(t("not_authorized", locale))
        return False

    async def _open_menu(message: "Message", user_id: int, locale: str) -> None:
        text, rows = _main_screen(user_id, locale)
        await message.answer(text, reply_markup=_markup(rows))

    @dp.message(CommandStart())
    async def _start(message: "Message") -> None:
        locale = _resolve_locale(prefs, message.from_user)
        if not await _guard(message, locale):
            return
        if not await _is_subscribed(message.from_user.id):
            await _show_gate(message, locale)
            return
        if prefs.get_language(message.from_user.id) is None:
            await message.answer(t("choose_language", locale),
                                reply_markup=_language_keyboard())
        else:
            await _open_menu(message, message.from_user.id, locale)

    def _profile_message(user, locale: str) -> str:
        from jarvis.interfaces.bot_menu import profile_text
        account, verified = None, False
        if license_service is not None:
            acc = license_service.get_account_by_telegram(user.id)
            if acc is not None:
                account, verified = acc.username, acc.telegram_verified
        return profile_text(
            locale, telegram_id=user.id,
            name=user.full_name or user.username or "—",
            language=locale, model=prefs.get_model(user.id) or "",
            account=account, telegram_verified=verified,
            stats=usage.stats(user.id),
        )

    async def _edit(callback: "CallbackQuery", text: str, rows) -> None:
        """Edit the menu message in place (fall back to a new message)."""
        try:
            await callback.message.edit_text(text, reply_markup=_markup(rows))
        except Exception:  # noqa: BLE001 - message unchanged / too old
            await callback.message.answer(text, reply_markup=_markup(rows))

    @dp.callback_query(F.data.startswith("m:"))
    async def _menu_cb(callback: "CallbackQuery") -> None:
        import jarvis.interfaces.bot_menu as bm
        user = callback.from_user
        locale = _resolve_locale(prefs, user)
        parts = callback.data.split(":")
        action = parts[1]
        await callback.answer()
        back = [[(t("menu_back", locale), "m:main")]]

        if action == "checksub":
            if await _is_subscribed(user.id):
                text, rows = _main_screen(user.id, locale)
                await _edit(callback, text, rows)
            else:
                await callback.answer(t("gate_not_yet", locale), show_alert=True)
            return

        if action == "main":
            text, rows = _main_screen(user.id, locale)
            await _edit(callback, text, rows)
        elif action == "voice":
            await _edit(callback, *bm.screen_voice(locale))
        elif action == "settings":
            text, rows = bm.screen_settings(
                locale, multi_model=len(engine.llm.list_profiles()) > 1)
            await _edit(callback, text, rows)
        elif action == "memory":
            await _edit(callback, *bm.screen_memory(locale))
        elif action == "help":
            await _edit(callback, *bm.screen_help(locale))
        elif action == "link":
            await _edit(callback, *bm.screen_link(locale))
        elif action == "model":
            await _edit(callback, *bm.screen_model(
                locale, engine.llm.list_profiles(), prefs.get_model(user.id) or ""))
        elif action == "language":
            await _edit(callback, *bm.screen_language(locale, locale))
        elif action == "profile":
            await _edit(callback, _profile_message(user, locale), back)
        elif action == "usage":
            await _edit(callback, bm.usage_text(locale, usage.stats(user.id)), back)
        elif action == "subscription":
            account, lics = None, []
            if license_service is not None:
                acc = license_service.get_account_by_telegram(user.id)
                if acc is not None:
                    account, lics = acc.username, license_service.list_licenses(acc.id)
            await _edit(callback, bm.subscription_text(
                locale, account=account, licenses=lics), back)
        elif action == "setmodel":
            choice = parts[2]
            if choice == "auto":
                prefs.set_model(user.id, "")
            else:
                prefs.set_model(user.id, choice)
            await _edit(callback, *bm.screen_settings(
                locale, multi_model=len(engine.llm.list_profiles()) > 1))
        elif action == "setlang":
            new_locale = normalize_locale(parts[2])
            prefs.set_language(user.id, new_locale)
            engine.session(session_id_for(user.id)).scratch["language"] = new_locale
            await _edit(callback, *bm.screen_settings(
                new_locale, multi_model=len(engine.llm.list_profiles()) > 1))
        elif action == "reset":
            await engine.reset(session_id_for(user.id))
            await _edit(callback, "🧹 " + t("reset_done", locale), back)
        elif action == "forget":
            await engine.forget(session_id_for(user.id))
            await _edit(callback, "🗑 " + t("forget_done", locale), back)
        elif action == "buy":
            await _send_invoice(callback.message, locale)
        elif action == "admin":
            await callback.message.answer("🛠 /admin  ·  /admin_sales")

    async def _send_invoice(message: "Message", locale: str) -> None:
        if billing is None:
            await message.answer(t("buy_disabled", locale))
            return
        from aiogram.types import LabeledPrice
        await message.bot.send_invoice(
            chat_id=message.chat.id,
            title=t("buy_invoice_title", locale),
            description=t("buy_invoice_desc", locale),
            payload="jarvis-license",
            currency="XTR",
            prices=[LabeledPrice(label=t("buy_invoice_title", locale),
                                amount=settings.billing_price_stars)],
        )

    @dp.callback_query(F.data.startswith("lang:"))
    async def _pick_language(callback: "CallbackQuery") -> None:
        locale = normalize_locale(callback.data.split(":", 1)[1])
        prefs.set_language(callback.from_user.id, locale)
        engine.session(session_id_for(callback.from_user.id)).scratch["language"] = locale
        await callback.answer()
        text, rows = _main_screen(callback.from_user.id, locale)
        try:
            await callback.message.edit_text(text, reply_markup=_markup(rows))
        except Exception:  # noqa: BLE001
            await callback.message.answer(text, reply_markup=_markup(rows))

    def _model_keyboard(current: str | None) -> "InlineKeyboardMarkup":
        rows = []
        for name in engine.llm.list_profiles():
            mark = "✅ " if name == current else ""
            rows.append([InlineKeyboardButton(
                text=f"{mark}{_MODEL_LABELS.get(name, name)}",
                callback_data=f"model:{name}")])
        # "Auto" clears the pin → provider default + fallback chain.
        auto_mark = "✅ " if not current else ""
        rows.append([InlineKeyboardButton(
            text=f"{auto_mark}{_MODEL_LABELS['auto']}", callback_data="model:auto")])
        return InlineKeyboardMarkup(inline_keyboard=rows)

    @dp.message(Command("model"))
    async def _model(message: "Message") -> None:
        locale = _resolve_locale(prefs, message.from_user)
        if not await _guard(message, locale):
            return
        if not engine.llm.list_profiles():
            await message.answer(t("model_none", locale))
            return
        current = prefs.get_model(message.from_user.id)
        await message.answer(t("model_choose", locale),
                            reply_markup=_model_keyboard(current))

    @dp.callback_query(F.data.startswith("model:"))
    async def _pick_model(callback: "CallbackQuery") -> None:
        locale = _resolve_locale(prefs, callback.from_user)
        choice = callback.data.split(":", 1)[1]
        session = engine.session(session_id_for(callback.from_user.id))
        if choice == "auto":
            prefs.set_model(callback.from_user.id, "")
            session.scratch.pop("model_profile", None)
            label = _MODEL_LABELS["auto"]
        else:
            prefs.set_model(callback.from_user.id, choice)
            session.scratch["model_profile"] = choice
            label = _MODEL_LABELS.get(choice, choice)
        await callback.message.answer(t("model_set", locale, model=label))
        await callback.answer()

    @dp.message(Command("buy"))
    async def _buy(message: "Message") -> None:
        locale = _resolve_locale(prefs, message.from_user)
        if not await _guard(message, locale):
            return
        if billing is None:
            await message.answer(t("buy_disabled", locale))
            return
        from aiogram.types import LabeledPrice
        await message.bot.send_invoice(
            chat_id=message.chat.id,
            title=t("buy_invoice_title", locale),
            description=t("buy_invoice_desc", locale),
            payload="jarvis-license",
            currency="XTR",  # Telegram Stars
            prices=[LabeledPrice(label=t("buy_invoice_title", locale),
                                amount=settings.billing_price_stars)],
        )

    @dp.pre_checkout_query()
    async def _pre_checkout(query) -> None:
        await query.answer(ok=billing is not None)

    @dp.message(F.successful_payment)
    async def _paid(message: "Message") -> None:
        locale = _resolve_locale(prefs, message.from_user)
        if billing is None:
            return
        payment = message.successful_payment
        reply = handle_successful_payment(
            billing, settings, message.from_user.id,
            payment.telegram_payment_charge_id, locale,
            amount=payment.total_amount, currency=payment.currency,
        )
        await message.answer(reply)

    @dp.message(Command("link"))
    async def _link(message: "Message") -> None:
        locale = _resolve_locale(prefs, message.from_user)
        if not await _guard(message, locale):
            return
        reply = handle_link(license_service, message.text or "",
                            message.from_user.id, locale)
        await message.answer(reply)

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

    admins = settings.telegram_admins()

    @dp.message(F.text.startswith("/admin"))
    async def _admin(message: "Message") -> None:
        locale = _resolve_locale(prefs, message.from_user)
        if message.from_user.id not in admins:
            await message.answer(t("not_authorized", locale))
            return
        if license_service is None:
            await message.answer(t("admin_needs_auth", locale))
            return
        from jarvis.interfaces.admin_panel import handle_admin_command

        text = message.text or ""
        command = text.split(maxsplit=1)[0].split("@", 1)[0].lower()
        if command == "/admin_post":
            content = text.split(maxsplit=1)[1] if " " in text else ""
            if not content.strip():
                await message.answer(t("admin_post_usage", locale))
                return
            if not settings.telegram_channel:
                await message.answer(t("admin_no_channel", locale))
                return
            await message.bot.send_message(settings.telegram_channel,
                                        content, parse_mode=None)
            await message.answer(
                t("admin_posted", locale, channel=settings.telegram_channel))
            return
        reply = handle_admin_command(license_service, billing, text)
        await message.answer(reply if reply is not None
                            else t("admin_unknown", locale))

    @dp.message(F.text)
    async def _chat(message: "Message") -> None:
        locale = _resolve_locale(prefs, message.from_user)
        if not await _guard(message, locale):
            return
        if not await _is_subscribed(message.from_user.id):
            await _show_gate(message, locale)
            return
        await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        reply = await generate_reply(
            engine, message.from_user.id, message.text, locale,
            model_profile=prefs.get_model(message.from_user.id),
            usage=usage,
        )
        # LLM output is plain text — disable HTML parsing to avoid entity errors.
        for chunk in split_message(reply):
            await message.answer(chunk, parse_mode=None)

    @dp.message(F.voice)
    async def _voice(message: "Message") -> None:
        locale = _resolve_locale(prefs, message.from_user)
        if not await _guard(message, locale):
            return
        if not await _is_subscribed(message.from_user.id):
            await _show_gate(message, locale)
            return
        if voice is None or not voice.stt_available():
            await message.answer(t("voice_unavailable", locale))
            return

        await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        try:
            file = await message.bot.get_file(message.voice.file_id)
            buffer = await message.bot.download_file(file.file_path)
            transcription = await voice.transcribe(buffer.read())
        except Exception as exc:  # noqa: BLE001 - surface STT failures to the user
            logger.error("Voice transcription failed: %s", exc)
            await message.answer(t("error", locale, error=str(exc)), parse_mode=None)
            return

        if not transcription.text:
            return

        # Reply in whatever language the user actually spoke.
        reply = await generate_reply(
            engine, message.from_user.id, transcription.text, locale,
            match_input_language=True,
            model_profile=prefs.get_model(message.from_user.id),
            usage=usage,
        )
        for chunk in split_message(reply):
            await message.answer(chunk, parse_mode=None)

        if settings.voice_replies and voice.tts_available():
            try:
                audio = await voice.synthesize(reply, transcription.language)
                out = BufferedInputFile(audio, f"reply.{voice.tts_ext}")
                if voice.tts_is_voice_note:
                    await message.answer_voice(out)
                else:
                    await message.answer_audio(out)
            except Exception as exc:  # noqa: BLE001 - text reply already delivered
                logger.warning("Voice synthesis failed: %s", exc)

    async def _set_commands() -> None:
        # Fully button-driven — no user commands at all. /start is implicit and
        # opens the menu; everything else is inline buttons.
        await bot.set_my_commands([])

        # Admins additionally see the owner commands — only in their own chat.
        from aiogram.types import BotCommandScopeChat
        admin_extra = [
            BotCommand(command="admin", description=t("cmd_admin", DEFAULT_LOCALE)),
            BotCommand(command="admin_sales",
                    description=t("cmd_admin_sales", DEFAULT_LOCALE)),
        ]
        base: list = []
        for admin_id in admins:
            try:
                await bot.set_my_commands(
                    base + admin_extra,
                    scope=BotCommandScopeChat(chat_id=admin_id),
                )
            except Exception as exc:  # noqa: BLE001 - admin hasn't /start-ed yet
                logger.debug("Admin menu for %s skipped: %s", admin_id, exc)

    await _set_commands()
    logger.info("Telegram bot starting (long-polling)…")
    try:
        # Keep the sales bot up 24/7: if polling dies (network drop, Telegram
        # hiccup), reconnect with exponential backoff instead of exiting.
        # aiogram already retries transient errors internally; this loop is
        # the belt-and-braces layer on top, and systemd/Docker restart the
        # whole process if even this fails.
        backoff = _POLL_BACKOFF_INITIAL
        while True:
            try:
                await dp.start_polling(bot)
                break  # clean stop (SIGINT/SIGTERM handled by aiogram)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - keep the bot alive
                logger.error("Polling crashed: %s — reconnecting in %.0fs",
                            exc, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, _POLL_BACKOFF_MAX)
            else:  # pragma: no cover - defensive
                break
    finally:
        await engine.shutdown()
        if license_service is not None:
            license_service.close()
        usage.close()
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
