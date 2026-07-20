"""
Inline-menu content for the Telegram bot (aiogram-free, testable).

Builds the main menu layout as plain data — a list of button rows, each button
a ``(label, callback_data)`` pair — plus the text for the profile, token-usage
and subscription screens. The bot layer turns the rows into an
``InlineKeyboardMarkup`` and sends the text.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from jarvis.i18n import t

# Callback data prefixes (kept short — Telegram caps callback_data at 64 bytes).
CB = "m"  # e.g. "m:profile", "m:usage", "m:model", …


def _btn(label_key: str, action: str, locale: str) -> tuple[str, str]:
    return (t(label_key, locale), f"{CB}:{action}")


def main_menu(locale: str, *, is_admin: bool = False,
            billing_on: bool = False, accounts_on: bool = False,
            multi_model: bool = False) -> list[list[tuple[str, str]]]:
    """Return the main-menu keyboard as rows of (label, callback_data)."""
    rows: list[list[tuple[str, str]]] = [
        [_btn("menu_profile", "profile", locale),
        _btn("menu_usage", "usage", locale)],
    ]
    row2: list[tuple[str, str]] = []
    if multi_model:
        row2.append(_btn("cmd_model", "model", locale))
    row2.append(_btn("cmd_language", "language", locale))
    rows.append(row2)
    if billing_on:
        rows.append([_btn("menu_subscription", "subscription", locale),
                    _btn("cmd_buy", "buy", locale)])
    if accounts_on:
        rows.append([_btn("cmd_link", "link", locale)])
    rows.append([_btn("mem_reset", "reset", locale),
                _btn("mem_forget", "forget", locale)])
    rows.append([_btn("menu_help", "help", locale)])
    if is_admin:
        rows.append([_btn("cmd_admin", "admin", locale)])
    return rows


def _fmt_num(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def profile_text(locale: str, *, telegram_id: int, name: str,
                language: str, model: str, account: str | None,
                telegram_verified: bool, stats: dict) -> str:
    """Detailed, nicely formatted profile card."""
    model_label = model or "auto"
    account_line = (f"🔓 <b>{account}</b>" if account
                    else t("profile_no_account", locale))
    verified = "✅" if telegram_verified else "—"
    return "\n".join([
        f"👤 <b>{t('profile_title', locale)}</b>",
        "",
        f"🆔 ID: <code>{telegram_id}</code>",
        f"📛 {t('profile_name', locale)}: {name}",
        f"🔗 {t('profile_account', locale)}: {account_line}",
        f"✔️ {t('profile_verified', locale)}: {verified}",
        f"🌐 {t('profile_language', locale)}: {language}",
        f"🤖 {t('profile_model', locale)}: {model_label}",
        "",
        f"💬 {t('profile_messages', locale)}: {_fmt_num(stats['messages'])}",
        f"🔢 {t('profile_tokens', locale)}: {_fmt_num(stats['tokens'])}",
    ])


def usage_text(locale: str, stats: dict) -> str:
    """Detailed token/message report (today / 30 days / all time)."""
    return "\n".join([
        f"📊 <b>{t('usage_title', locale)}</b>",
        "",
        f"📅 {t('usage_today', locale)}:",
        f"   💬 {_fmt_num(stats['messages_today'])}  ·  "
        f"🔢 {_fmt_num(stats['tokens_today'])} {t('usage_tokens', locale)}",
        "",
        f"🗓 {t('usage_month', locale)}:",
        f"   💬 {_fmt_num(stats['messages_month'])}  ·  "
        f"🔢 {_fmt_num(stats['tokens_month'])} {t('usage_tokens', locale)}",
        "",
        f"♾ {t('usage_all', locale)}:",
        f"   💬 {_fmt_num(stats['messages'])}  ·  "
        f"🔢 {_fmt_num(stats['tokens'])} {t('usage_tokens', locale)}",
    ])


def subscription_text(locale: str, *, account: str | None,
                    licenses: list, now: float | None = None) -> str:
    """Subscription / license status card."""
    now = time.time() if now is None else now
    if account is None:
        return "\n".join([
            f"💳 <b>{t('sub_title', locale)}</b>", "",
            t("sub_none", locale),
        ])
    active = None
    for lic in licenses:
        if lic.is_valid(now=now):
            active = lic
            break
    lines = [f"💳 <b>{t('sub_title', locale)}</b>", "",
            f"🔓 {t('profile_account', locale)}: <b>{account}</b>"]
    if active is None:
        lines.append(f"⚠️ {t('sub_inactive', locale)}")
    else:
        lines.append(f"✅ {t('sub_active', locale)}: {active.plan}")
        if active.expires_at is None:
            lines.append(f"♾ {t('sub_perpetual', locale)}")
        else:
            days = max(0, int((active.expires_at - now) // 86400))
            until = datetime.fromtimestamp(
                active.expires_at, tz=timezone.utc).strftime("%d.%m.%Y")
            lines.append(f"⏳ {t('sub_until', locale)}: {until} ({days} "
                        f"{t('sub_days', locale)})")
    return "\n".join(lines)
