"""
Owner admin panel for the Telegram bot (aiogram-free, fully testable).

Regular buyers see the sales bot (/buy, /link, chat). Telegram user IDs listed
in ``TELEGRAM_ADMIN_USERS`` additionally get ``/admin`` and the ``/admin_*``
commands handled here. Every function takes the services and returns the reply
text; the bot layer only wires messages in and out.

Commands:
    /admin                      — panel: stats + recent users + payments
    /admin_add <name> [pass]    — create an account (password shown once)
    /admin_lic <name> [days]    — issue a license (no days = perpetual)
    /admin_info <name>          — account details + licenses
    /admin_block <name>         — disable an account (login stops working)
    /admin_unblock <name>       — re-enable an account
    /admin_revoke <key>         — revoke a license by its key
    /admin_post <text>          — publish a post to the configured channel
"""

from __future__ import annotations

import html
import secrets
import time
from datetime import datetime, timezone

from jarvis.billing import BillingService
from jarvis.licensing import AuthError, LicenseService


def _esc(value: object) -> str:
    return html.escape(str(value), quote=False)


def _fmt_ts(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%d.%m.%Y")


def panel_text(licenses: LicenseService,
            billing: BillingService | None) -> str:
    """The /admin overview: stats, recent users, recent payments, commands."""
    stats = licenses.stats()
    lines = [
        "🛠 <b>J.A.R.V.I.S. — admin</b>",
        "",
        "📊 <b>Stats</b>",
        f"• Users: {stats['accounts']} (active: {stats['active_accounts']})",
        f"• Telegram linked: {stats['telegram_linked']}",
        f"• With active license: {stats['licensed_accounts']}",
    ]
    if billing is not None:
        pay = billing.stats()
        lines.append(
            f"• Payments: {pay['payments']} (30d: {pay['payments_30d']})")

    accounts = licenses.list_accounts(limit=10)
    if accounts:
        lines += ["", "👥 <b>Recent users</b>"]
        for acc in accounts:
            flags = []
            if not acc.active:
                flags.append("⛔️")
            if acc.telegram_verified:
                flags.append("🔗")
            if licenses.has_active_license(acc.id):
                flags.append("✅")
            suffix = f" {' '.join(flags)}" if flags else ""
            lines.append(
                f"• <code>{_esc(acc.username)}</code>"
                f" — {_fmt_ts(acc.created_at)}{suffix}")

    if billing is not None:
        payments = billing.recent_payments(limit=5)
        if payments:
            lines += ["", "💳 <b>Recent payments</b>"]
            for p in payments:
                lines.append(
                    f"• {_fmt_ts(p['created_at'])} — "
                    f"<code>{_esc(p['username'])}</code> ({_esc(p['plan'])})")

    lines += [
        "",
        "⌨️ <b>Commands</b>",
        "/admin_add name [password] — create user",
        "/admin_lic name [days] — issue license",
        "/admin_info name — user details",
        "/admin_block name · /admin_unblock name",
        "/admin_revoke key — revoke license",
        "/admin_post text — post to the channel",
    ]
    return "\n".join(lines)


def user_info_text(licenses: LicenseService, username: str) -> str:
    account = licenses.get_account(username)
    if account is None:
        return f"❌ User <code>{_esc(username)}</code> not found."
    lines = [
        f"👤 <b>{_esc(account.username)}</b> (id={account.id})",
        f"• Status: {'active ✅' if account.active else 'blocked ⛔️'}",
        f"• Telegram: "
        f"{account.telegram_user_id if account.telegram_verified else 'not linked'}",
        f"• Created: {_fmt_ts(account.created_at)}",
    ]
    licenses_list = licenses.list_licenses(account.id)
    if licenses_list:
        lines.append("• Licenses:")
        now = time.time()
        for lic in licenses_list:
            if lic.revoked:
                state = "revoked ⛔️"
            elif lic.expires_at is None:
                state = "perpetual ✅"
            elif lic.expires_at > now:
                state = f"{int((lic.expires_at - now) // 86400)}d left ✅"
            else:
                state = "expired"
            lines.append(f"   · #{lic.id} {_esc(lic.plan)} — {state}")
    else:
        lines.append("• Licenses: none")
    return "\n".join(lines)


def create_user_text(licenses: LicenseService, username: str,
                    password: str = "") -> str:
    password = password or secrets.token_urlsafe(9)
    try:
        account = licenses.create_account(username, password)
    except AuthError as exc:
        return f"❌ {_esc(exc)}"
    return (
        f"✅ User created.\n"
        f"• Login: <code>{_esc(account.username)}</code>\n"
        f"• Password: <code>{_esc(password)}</code>\n"
        f"Shown once — send it to the buyer over a secure channel."
    )


def issue_license_text(licenses: LicenseService, username: str,
                    days: int | None = None,
                    plan: str = "standard") -> str:
    account = licenses.get_account(username)
    if account is None:
        return f"❌ User <code>{_esc(username)}</code> not found."
    key = licenses.issue_license(account.id, plan=plan, valid_days=days)
    term = f"{days} days" if days else "perpetual"
    return (
        f"✅ License issued to <code>{_esc(account.username)}</code>"
        f" ({_esc(plan)}, {term}).\n"
        f"Key (shown once): <code>{_esc(key)}</code>"
    )


def set_active_text(licenses: LicenseService, username: str,
                    active: bool) -> str:
    if licenses.get_account(username) is None:
        return f"❌ User <code>{_esc(username)}</code> not found."
    licenses.set_active(username, active)
    return (f"✅ <code>{_esc(username)}</code> unblocked." if active
            else f"⛔️ <code>{_esc(username)}</code> blocked.")


def revoke_license_text(licenses: LicenseService, key: str) -> str:
    if licenses.revoke_license_by_key(key):
        return "✅ License revoked."
    return "❌ License key not found."


def handle_admin_command(licenses: LicenseService,
                        billing: BillingService | None,
                        text: str) -> str | None:
    """Route an /admin* message to its handler; ``None`` = not an admin command.

    ``/admin_post`` is intentionally NOT handled here — it needs the bot to
    actually send the post, so the bot layer implements it.
    """
    parts = (text or "").strip().split(maxsplit=2)
    if not parts:
        return None
    command = parts[0].split("@", 1)[0].lower()
    args = parts[1:]

    if command == "/admin":
        return panel_text(licenses, billing)
    if command == "/admin_add":
        if not args:
            return "Usage: /admin_add name [password]"
        return create_user_text(licenses, args[0],
                                args[1] if len(args) > 1 else "")
    if command == "/admin_lic":
        if not args:
            return "Usage: /admin_lic name [days]"
        days: int | None = None
        if len(args) > 1:
            if not args[1].isdigit() or int(args[1]) <= 0:
                return "Days must be a positive number."
            days = int(args[1])
        return issue_license_text(licenses, args[0], days)
    if command == "/admin_info":
        if not args:
            return "Usage: /admin_info name"
        return user_info_text(licenses, args[0])
    if command == "/admin_block":
        if not args:
            return "Usage: /admin_block name"
        return set_active_text(licenses, args[0], active=False)
    if command == "/admin_unblock":
        if not args:
            return "Usage: /admin_unblock name"
        return set_active_text(licenses, args[0], active=True)
    if command == "/admin_revoke":
        if not args:
            return "Usage: /admin_revoke key"
        return revoke_license_text(licenses, args[0])
    return None
