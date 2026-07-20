"""
Inline-menu content for the Telegram bot (aiogram-free, testable).

The bot is fully button-driven — users never type commands. Every screen is
returned here as ``(text, rows)`` where ``rows`` is a list of button rows and
each button is a ``(label, callback_data)`` pair. The bot layer turns rows into
an ``InlineKeyboardMarkup`` and edits the same message in place, so navigating
feels like a little app.

Callback scheme (kept short — Telegram caps callback_data at 64 bytes):
    m:main  m:profile  m:usage  m:subscription  m:settings  m:memory
    m:model  m:language  m:help  m:link  m:buy  m:reset  m:forget  m:admin
    m:setmodel:<name|auto>   m:setlang:<locale>
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from jarvis.i18n import t

CB = "m"

Rows = list[list[tuple[str, str]]]

# AI-picker labels.
MODEL_LABELS = {
    "claude": "🧠 Claude", "gpt": "💬 ChatGPT", "openrouter": "🌐 OpenRouter",
    "auto": "⚙️ Auto",
}
LANG_LABELS = {"en": "🇬🇧 English", "ru": "🇷🇺 Русский", "uz": "🇺🇿 O'zbek"}


def _b(label: str, action: str) -> tuple[str, str]:
    return (label, f"{CB}:{action}")


def _back(locale: str) -> list[tuple[str, str]]:
    return [_b(t("menu_back", locale), "main")]


def _fmt_num(n: int) -> str:
    return f"{n:,}".replace(",", " ")


# -- screens ------------------------------------------------------------------

def screen_main(locale: str, *, is_admin: bool = False, billing_on: bool = False,
                accounts_on: bool = False, multi_model: bool = False,
                voice_on: bool = False, channel: str = "", name: str = "Sir",
                ) -> tuple[str, Rows]:
    text = (
        f"🤖 <b>J.A.R.V.I.S.</b>\n"
        f"<i>{t('menu_greeting', locale, name=name)}</i>\n\n"
        f"{t('menu_pick', locale)}"
    )
    rows: Rows = [
        [_b(t("menu_profile", locale), "profile"),
        _b(t("menu_usage", locale), "usage")],
        [_b(t("menu_settings", locale), "settings"),
        _b(t("menu_memory", locale), "memory")],
    ]
    third = [_b(t("menu_language", locale), "language")]
    if voice_on:
        third.insert(0, _b(t("menu_voice", locale), "voice"))
    rows.append(third)
    if billing_on:
        rows.append([_b(t("menu_subscription", locale), "subscription"),
                    _b(t("menu_buy", locale), "buy")])
    if accounts_on:
        rows.append([_b(t("menu_link", locale), "link")])
    last = [_b(t("menu_help", locale), "help")]
    if channel:
        last.append((t("menu_channel", locale), channel_url(channel)))
    rows.append(last)
    if is_admin:
        rows.append([_b(t("menu_admin", locale), "admin")])
    return text, rows


def channel_url(channel: str) -> str:
    """Turn '@name' / 'name' / a full link into a t.me URL (used as a button)."""
    channel = channel.strip()
    if channel.startswith("http"):
        return channel
    return f"https://t.me/{channel.lstrip('@')}"


def screen_voice(locale: str) -> tuple[str, Rows]:
    text = f"🎙 <b>{t('voice_title', locale)}</b>\n\n{t('voice_body', locale)}"
    return text, [_back(locale)]


def gate_screen(locale: str, channel: str) -> tuple[str, Rows]:
    """The subscription gate shown until the user joins the channel."""
    text = f"{t('gate_title', locale)}\n\n{t('gate_body', locale)}"
    rows: Rows = [
        [(t("gate_subscribe", locale), channel_url(channel))],
        [_b(t("gate_check", locale), "checksub")],
    ]
    return text, rows


def screen_settings(locale: str, *, multi_model: bool) -> tuple[str, Rows]:
    text = f"⚙️ <b>{t('settings_title', locale)}</b>\n\n{t('settings_hint', locale)}"
    rows: Rows = []
    if multi_model:
        rows.append([_b(t("menu_model", locale), "model")])
    rows.append([_b(t("menu_language", locale), "language")])
    rows.append(_back(locale))
    return text, rows


def screen_memory(locale: str) -> tuple[str, Rows]:
    text = f"🧠 <b>{t('memory_title', locale)}</b>\n\n{t('memory_hint', locale)}"
    rows: Rows = [
        [_b(t("menu_reset", locale), "reset")],
        [_b(t("menu_forget", locale), "forget")],
        _back(locale),
    ]
    return text, rows


def screen_model(locale: str, profiles: list[str], current: str) -> tuple[str, Rows]:
    text = f"🤖 <b>{t('menu_model', locale)}</b>\n\n{t('model_choose', locale)}"
    rows: Rows = []
    for name in profiles:
        mark = "✅ " if name == current else ""
        rows.append([_b(mark + MODEL_LABELS.get(name, name), f"setmodel:{name}")])
    mark = "✅ " if not current else ""
    rows.append([_b(mark + MODEL_LABELS["auto"], "setmodel:auto")])
    rows.append([_b(t("menu_back", locale), "settings")])
    return text, rows


def screen_language(locale: str, current: str) -> tuple[str, Rows]:
    text = f"🌐 <b>{t('menu_language', locale)}</b>\n\n{t('choose_language', locale)}"
    rows: Rows = []
    for loc, label in LANG_LABELS.items():
        mark = "✅ " if loc == current else ""
        rows.append([_b(mark + label, f"setlang:{loc}")])
    rows.append([_b(t("menu_back", locale), "settings")])
    return text, rows


def screen_help(locale: str) -> tuple[str, Rows]:
    text = f"❓ <b>{t('help_title', locale)}</b>\n\n{t('help_body', locale)}"
    return text, [_back(locale)]


def screen_link(locale: str) -> tuple[str, Rows]:
    text = f"🔗 <b>{t('menu_link', locale)}</b>\n\n{t('link_usage', locale)}"
    return text, [_back(locale)]


# -- info cards (text only; the bot appends a Back button) --------------------

def profile_text(locale: str, *, telegram_id: int, name: str, language: str,
                model: str, account: str | None, telegram_verified: bool,
                stats: dict) -> str:
    model_label = MODEL_LABELS.get(model, model) if model else "⚙️ Auto"
    account_line = (f"🔓 <b>{account}</b>" if account
                    else t("profile_no_account", locale))
    verified = "✅" if telegram_verified else "—"
    lang_label = LANG_LABELS.get(language, language)
    return "\n".join([
        f"👤 <b>{t('profile_title', locale)}</b>",
        "━━━━━━━━━━━━━━",
        f"🆔 <code>{telegram_id}</code>",
        f"📛 {t('profile_name', locale)}: <b>{name}</b>",
        f"🔗 {t('profile_account', locale)}: {account_line}",
        f"✔️ {t('profile_verified', locale)}: {verified}",
        f"🌐 {t('profile_language', locale)}: {lang_label}",
        f"🤖 {t('profile_model', locale)}: {model_label}",
        "━━━━━━━━━━━━━━",
        f"💬 {t('profile_messages', locale)}: <b>{_fmt_num(stats['messages'])}</b>",
        f"🔢 {t('profile_tokens', locale)}: <b>{_fmt_num(stats['tokens'])}</b>",
    ])


def usage_text(locale: str, stats: dict) -> str:
    tok = t("usage_tokens", locale)
    return "\n".join([
        f"📊 <b>{t('usage_title', locale)}</b>",
        "━━━━━━━━━━━━━━",
        f"📅 {t('usage_today', locale)}",
        f"    💬 {_fmt_num(stats['messages_today'])}   "
        f"🔢 {_fmt_num(stats['tokens_today'])} {tok}",
        "",
        f"🗓 {t('usage_month', locale)}",
        f"    💬 {_fmt_num(stats['messages_month'])}   "
        f"🔢 {_fmt_num(stats['tokens_month'])} {tok}",
        "",
        f"♾ {t('usage_all', locale)}",
        f"    💬 {_fmt_num(stats['messages'])}   "
        f"🔢 {_fmt_num(stats['tokens'])} {tok}",
    ])


def subscription_text(locale: str, *, account: str | None, licenses: list,
                    now: float | None = None) -> str:
    now = time.time() if now is None else now
    if account is None:
        return "\n".join([f"💳 <b>{t('sub_title', locale)}</b>",
                        "━━━━━━━━━━━━━━", t("sub_none", locale)])
    active = next((lic for lic in licenses if lic.is_valid(now=now)), None)
    lines = [f"💳 <b>{t('sub_title', locale)}</b>", "━━━━━━━━━━━━━━",
            f"🔓 {t('profile_account', locale)}: <b>{account}</b>"]
    if active is None:
        lines.append(f"⚠️ {t('sub_inactive', locale)}")
    else:
        lines.append(f"✅ {t('sub_active', locale)}: <b>{active.plan}</b>")
        if active.expires_at is None:
            lines.append(f"♾ {t('sub_perpetual', locale)}")
        else:
            days = max(0, int((active.expires_at - now) // 86400))
            until = datetime.fromtimestamp(
                active.expires_at, tz=timezone.utc).strftime("%d.%m.%Y")
            lines.append(f"⏳ {t('sub_until', locale)}: <b>{until}</b> "
                        f"({days} {t('sub_days', locale)})")
    return "\n".join(lines)
