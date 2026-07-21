"""
Inline-menu content for the Telegram bot (aiogram-free, testable).

The bot is fully button-driven — users never type commands. Every screen is
returned here as ``(text, rows)`` where ``rows`` is a list of button rows and
each button is a ``(label, callback_data)`` pair. The bot layer turns rows into
an ``InlineKeyboardMarkup`` and edits the same message in place, so navigating
feels like a little app.

Callback scheme (kept short — Telegram caps callback_data at 64 bytes):
    m:main  m:profile  m:usage  m:subscription  m:settings  m:memory
    m:model  m:language  m:help  m:link  m:plans  m:reset  m:forget  m:admin
    m:setmodel:<name|auto>   m:setlang:<locale>   m:buy[:<tier>]
    m:catalog[:<page>]   m:setcat:<index>
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


def card_rows(locale: str, refresh_action: str) -> Rows:
    """Buttons for an info card: a Refresh (re-open the same screen) + Back.

    ``refresh_action`` is a bare action name (e.g. ``"profile"``); the ``m:``
    prefix is added here.
    """
    return [
        [_b(t("menu_refresh", locale), refresh_action)],
        _back(locale),
    ]


def _fmt_num(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def _yn(value: bool) -> str:
    return "✅" if value else "❌"


# -- screens ------------------------------------------------------------------

def plan_status(locale: str, plan, used_today: int) -> str:
    """One-line tier badge for the main menu (e.g. '🆓 Free · 7/10 today')."""
    name = t(f"plan_{plan.name}", locale)
    if plan.unlimited:
        tail = t("plan_unlimited", locale)
    else:
        tail = t("plan_left_today", locale,
                n=plan.remaining_daily(used_today), total=plan.daily_messages)
    return f"{plan.emoji} <b>{name}</b> · {tail}"


def screen_main(locale: str, *, is_admin: bool = False, billing_on: bool = False,
                accounts_on: bool = False, multi_model: bool = False,
                voice_on: bool = False, channel: str = "", name: str = "Sir",
                plan=None, used_today: int = 0,
                image_on: bool = False) -> tuple[str, Rows]:
    header = (
        f"🤖 <b>J.A.R.V.I.S.</b>\n"
        f"<i>{t('menu_greeting', locale, name=name)}</i>"
    )
    if plan is not None:
        header += f"\n{plan_status(locale, plan, used_today)}"
    text = f"{header}\n\n{t('menu_pick', locale)}"
    rows: Rows = [
        [_b(t("menu_profile", locale), "profile"),
        _b(t("menu_usage", locale), "usage")],
        [_b(t("menu_settings", locale), "settings"),
        _b(t("menu_memory", locale), "memory")],
    ]
    third = [_b(t("menu_language", locale), "language")]
    if voice_on:
        third.insert(0, _b(t("menu_voice", locale), "voice"))
    if image_on:
        third.insert(0, _b(t("menu_image", locale), "image"))
    rows.append(third)
    if billing_on:
        rows.append([_b(t("menu_plans", locale), "plans"),
                    _b(t("menu_subscription", locale), "subscription")])
    if accounts_on:
        rows.append([_b(t("menu_link", locale), "link")])
    last = [_b(t("menu_help", locale), "help")]
    if channel:
        last.append((t("menu_channel", locale), channel_url(channel)))
    rows.append(last)
    if is_admin:
        rows.append([_b(t("menu_admin", locale), "admin")])
    return text, rows


def plan_card(locale: str, plan, *, current: bool = False) -> str:
    """A comparison block for one tier, used inside the Tariffs screen."""
    head = f"{plan.emoji} <b>{t(f'plan_{plan.name}', locale)}</b>"
    if plan.price_stars:
        head += f" — ⭐{plan.price_stars}"
    if current:
        head += f"  · {t('plan_current', locale)}"
    daily = (t("plan_unlimited", locale) if plan.unlimited
            else t("plan_per_day", locale, n=plan.daily_messages))
    models = (t("plan_models_all", locale) if plan.all_models
            else t("plan_models_basic", locale))
    return "\n".join([
        head,
        f"   💬 {daily}",
        f"   🧠 {models}",
        f"   🎨 {t('plan_feat_images', locale)}: {_yn(plan.images)}",
        f"   🔌 {t('plan_feat_api', locale)}: {_yn(plan.api_access)}",
        f"   🛟 {t('plan_feat_support', locale)}: {t(f'support_{plan.support}', locale)}",
    ])


def screen_plans(locale: str, plans: dict, current_tier: str) -> tuple[str, Rows]:
    """The Tariffs screen — Free / Plus / Pro side by side with buy buttons."""
    from jarvis.billing import TIER_ORDER

    blocks = [f"💎 <b>{t('plans_title', locale)}</b>", t("plans_hint", locale), ""]
    for tier in TIER_ORDER:
        blocks.append(plan_card(locale, plans[tier], current=(tier == current_tier)))
        blocks.append("")
    # Only offer upgrades — tiers strictly above the current one.
    current_rank = TIER_ORDER.index(current_tier) if current_tier in TIER_ORDER else 0
    rows: Rows = []
    for tier in ("plus", "pro"):
        if TIER_ORDER.index(tier) <= current_rank:
            continue
        p = plans[tier]
        rows.append([_b(
            t("plan_buy", locale, plan=t(f"plan_{tier}", locale), price=p.price_stars),
            f"buy:{tier}")])
    rows.append(_back(locale))
    return "\n".join(blocks).strip(), rows


def limit_screen(locale: str, plan) -> tuple[str, Rows]:
    """Shown when a user hits their daily message limit."""
    text = (f"🚦 <b>{t('limit_title', locale)}</b>\n\n"
            f"{t('limit_body', locale, n=plan.daily_messages)}")
    rows: Rows = [[_b(t("menu_plans", locale), "plans")], _back(locale)]
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


def screen_settings(locale: str, *, multi_model: bool,
                    catalog_on: bool = False) -> tuple[str, Rows]:
    text = f"⚙️ <b>{t('settings_title', locale)}</b>\n\n{t('settings_hint', locale)}"
    rows: Rows = []
    if catalog_on:
        rows.append([_b(t("menu_catalog", locale), "catalog")])
    if multi_model:
        rows.append([_b(t("menu_model", locale), "model")])
    rows.append([_b(t("menu_language", locale), "language")])
    rows.append([_b(t("menu_byok", locale), "byok")])
    rows.append(_back(locale))
    return text, rows


BYOK_PROVIDERS = (("openai", "🔷 OpenAI"), ("openrouter", "🌐 OpenRouter"),
                ("anthropic", "🧠 Anthropic"))


def screen_byok(locale: str, current_provider: str | None = None) -> tuple[str, Rows]:
    """Bring-your-own-key: connect a personal provider key (removes limits)."""
    status = (t("byok_active", locale, provider=current_provider)
            if current_provider else t("byok_none", locale))
    text = (f"🔑 <b>{t('byok_title', locale)}</b>\n\n"
            f"{t('byok_hint', locale)}\n\n{status}")
    rows: Rows = []
    for prov, label in BYOK_PROVIDERS:
        mark = "✅ " if prov == current_provider else ""
        rows.append([_b(mark + label, f"byokset:{prov}")])
    if current_provider:
        rows.append([_b(t("byok_disconnect", locale), "byokoff")])
    rows.append([_b(t("menu_back", locale), "settings")])
    return text, rows


def screen_catalog(locale: str, user_tier: str, current_slug: str,
                page: int = 0) -> tuple[str, Rows]:
    """A paginated, tier-gated catalog of models (served via OpenRouter)."""
    from jarvis.interfaces import model_catalog as mc

    text = (f"🗂 <b>{t('catalog_title', locale)}</b>\n\n"
            f"{t('catalog_hint', locale)}")
    rows: Rows = []
    for idx, model in mc.page(page):
        locked = not mc.unlocked(model, user_tier)
        mark = "✅ " if model.slug == current_slug else ("🔒 " if locked else "")
        label = f"{mark}{model.emoji} {model.name}"
        if model.note:
            label += f" · {model.note}"
        rows.append([_b(label, f"setcat:{idx}")])
    pages = mc.page_count()
    if pages > 1:
        rows.append([
            _b("◀️", f"catalog:{(page - 1) % pages}"),
            _b(f"{page + 1}/{pages}", f"catalog:{page}"),
            _b("▶️", f"catalog:{(page + 1) % pages}"),
        ])
    rows.append([_b(t("menu_back", locale), "settings")])
    return text, rows


def screen_memory(locale: str) -> tuple[str, Rows]:
    text = f"🧠 <b>{t('memory_title', locale)}</b>\n\n{t('memory_hint', locale)}"
    rows: Rows = [
        [_b(t("menu_reset", locale), "reset")],
        [_b(t("menu_forget", locale), "forget")],
        _back(locale),
    ]
    return text, rows


def screen_confirm(locale: str, kind: str) -> tuple[str, Rows]:
    """Confirmation step for a destructive action ('reset' or 'forget')."""
    text = f"⚠️ <b>{t('confirm_title', locale)}</b>\n\n{t(f'confirm_{kind}', locale)}"
    rows: Rows = [
        [_b(t("confirm_yes", locale), f"{kind}_do")],
        [_b(t("menu_back", locale), "memory")],
    ]
    return text, rows


def screen_admin(locale: str, *, billing_on: bool = False) -> tuple[str, Rows]:
    """Owner admin hub — opens the full panel and the sales report inline."""
    text = f"🛠 <b>{t('admin_title', locale)}</b>\n\n{t('admin_hint', locale)}"
    rows: Rows = [[_b(t("admin_open_panel", locale), "adminpanel")]]
    if billing_on:
        rows.append([_b(t("admin_open_sales", locale), "adminsales")])
    rows.append(_back(locale))
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
