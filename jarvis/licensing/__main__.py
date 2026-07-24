"""
Operator CLI for accounts and licenses: ``python -m jarvis.licensing`` (or
``jarvis-admin``).

Typical flow after a purchase::

    jarvis-admin create-user tony                 # prompts for a password
    jarvis-admin issue-license tony --days 365
    jarvis-admin list tony

The user then signs in from the desktop/mobile client with that username and
password; ``/auth/login`` checks the password *and* that an active license
exists.
"""

from __future__ import annotations

import argparse
import getpass
import secrets
import sys
import time

from jarvis.config.settings import get_settings
from jarvis.licensing import AuthError, LicenseService


def _service() -> LicenseService:
    settings = get_settings()
    return LicenseService(
        settings.auth_db_path, token_ttl_hours=settings.auth_token_ttl_hours
    )


def _cmd_create_user(args: argparse.Namespace) -> int:
    svc = _service()
    password = args.password or secrets.token_urlsafe(12)
    try:
        account = svc.create_account(args.username, password)
    except AuthError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Account created: {account.username} (id={account.id})")
    if not args.password:
        print(f"Generated password: {password}")
        print("Share it with the user over a secure channel; it is not stored "
            "in plaintext and cannot be recovered later.")
    return 0


def _cmd_issue_license(args: argparse.Namespace) -> int:
    svc = _service()
    account = svc.get_account(args.username)
    if account is None:
        print("error: account not found", file=sys.stderr)
        return 1
    key = svc.issue_license(account.id, plan=args.plan, valid_days=args.days)
    print(f"License issued to {account.username} (plan={args.plan}"
        f"{f', {args.days} days' if args.days else ', perpetual'})")
    print(f"Key (shown once): {key}")
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    svc = _service()
    account = svc.get_account(args.username)
    if account is None:
        print("error: account not found", file=sys.stderr)
        return 1
    tg = (f"telegram={account.telegram_user_id}" if account.telegram_verified
        else "telegram=not linked")
    state = "active" if account.active else "disabled"
    print(f"{account.username} (id={account.id}, {state}, {tg})")
    for lic in svc.list_licenses(account.id):
        if lic.revoked:
            status = "revoked"
        elif lic.expires_at is None:
            status = "valid (perpetual)"
        elif lic.expires_at > time.time():
            days = int((lic.expires_at - time.time()) // 86400)
            status = f"valid ({days} days left)"
        else:
            status = "expired"
        print(f"  license #{lic.id}: plan={lic.plan}, {status}")
    return 0


def _cmd_set_password(args: argparse.Namespace) -> int:
    svc = _service()
    if svc.get_account(args.username) is None:
        print("error: account not found", file=sys.stderr)
        return 1
    password = args.password or getpass.getpass("New password: ")
    try:
        svc.change_password(args.username, password)
    except AuthError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print("Password updated.")
    return 0


def _cmd_disable(args: argparse.Namespace) -> int:
    svc = _service()
    if svc.get_account(args.username) is None:
        print("error: account not found", file=sys.stderr)
        return 1
    svc.set_active(args.username, args.enable)
    print(f"Account {'enabled' if args.enable else 'disabled'}.")
    return 0


def _cmd_revoke_license(args: argparse.Namespace) -> int:
    svc = _service()
    if svc.revoke_license_by_key(args.key):
        print("License revoked.")
        return 0
    print("error: license key not found", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jarvis-admin", description="Manage J.A.R.V.I.S. accounts & licenses."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("create-user", help="Create a user account")
    p.add_argument("username")
    p.add_argument("--password", default="",
                help="Password (omitted → a random one is generated and shown)")
    p.set_defaults(func=_cmd_create_user)

    p = sub.add_parser("issue-license", help="Issue a license to a user")
    p.add_argument("username")
    p.add_argument("--plan", default="standard")
    p.add_argument("--days", type=int, default=None,
                help="Validity in days (omitted → perpetual)")
    p.set_defaults(func=_cmd_issue_license)

    p = sub.add_parser("list", help="Show a user's account and licenses")
    p.add_argument("username")
    p.set_defaults(func=_cmd_list)

    p = sub.add_parser("set-password", help="Change a user's password")
    p.add_argument("username")
    p.add_argument("--password", default="",
                help="New password (omitted → prompted interactively)")
    p.set_defaults(func=_cmd_set_password)

    p = sub.add_parser("disable", help="Disable a user account")
    p.add_argument("username")
    p.set_defaults(func=_cmd_disable, enable=False)

    p = sub.add_parser("enable", help="Re-enable a user account")
    p.add_argument("username")
    p.set_defaults(func=_cmd_disable, enable=True)

    p = sub.add_parser("revoke-license", help="Revoke a license by its key")
    p.add_argument("key")
    p.set_defaults(func=_cmd_revoke_license)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
