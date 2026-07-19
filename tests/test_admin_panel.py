"""Tests for the Telegram admin panel core (no aiogram)."""

from __future__ import annotations

import pytest

from jarvis.billing import BillingService
from jarvis.config.settings import Settings
from jarvis.interfaces.admin_panel import handle_admin_command, panel_text
from jarvis.licensing import LicenseService


@pytest.fixture()
def licenses() -> LicenseService:
    service = LicenseService(":memory:", token_ttl_hours=1)
    yield service
    service.close()


@pytest.fixture()
def billing(licenses: LicenseService) -> BillingService:
    service = BillingService(licenses, ":memory:")
    yield service
    service.close()


def test_admins_parser():
    settings = Settings(anthropic_api_key="k", log_file="",
                        telegram_admin_users="123, 456,abc,")
    assert settings.telegram_admins() == {123, 456}
    assert Settings(anthropic_api_key="k",
                    log_file="").telegram_admins() == set()


def test_panel_shows_stats_users_and_payments(licenses, billing):
    billing.process_payment("c1", telegram_user_id=42)
    licenses.create_account("pepper", "rescue")
    licenses.set_active("pepper", False)

    text = panel_text(licenses, billing)
    assert "Users: 2" in text
    assert "active: 1" in text
    assert "Payments: 1" in text
    assert "user42" in text and "pepper" in text
    assert "⛔️" in text          # blocked flag on pepper
    assert "/admin_add" in text  # command help present
    assert panel_text(licenses, None)  # works without billing too


def test_full_admin_command_flow(licenses, billing):
    # Create
    out = handle_admin_command(licenses, billing, "/admin_add tony secretpw")
    assert "tony" in out and "secretpw" in out
    assert licenses.get_account("tony") is not None
    # Duplicate
    assert "❌" in handle_admin_command(licenses, billing, "/admin_add tony")
    # License with days
    out = handle_admin_command(licenses, billing, "/admin_lic tony 30")
    assert "30 days" in out and "JVS-" in out
    assert licenses.authenticate("tony", "secretpw")
    # Info
    out = handle_admin_command(licenses, billing, "/admin_info tony")
    assert "tony" in out and "d left ✅" in out
    # Block → login stops working
    assert "⛔️" in handle_admin_command(licenses, billing, "/admin_block tony")
    with pytest.raises(Exception):
        licenses.authenticate("tony", "secretpw")
    assert "unblocked" in handle_admin_command(
        licenses, billing, "/admin_unblock tony")
    assert licenses.authenticate("tony", "secretpw")


def test_admin_revoke_by_key(licenses, billing):
    out = handle_admin_command(licenses, billing, "/admin_add nat")
    handle_admin_command(licenses, billing, "/admin_lic nat")
    info = handle_admin_command(licenses, billing, "/admin_info nat")
    assert "perpetual" in info
    # Extract the key from the issue reply.
    out = handle_admin_command(licenses, billing, "/admin_lic nat 10")
    key = out.split("<code>")[-1].split("</code>")[0]
    assert "revoked" in handle_admin_command(
        licenses, billing, f"/admin_revoke {key}")
    assert "❌" in handle_admin_command(licenses, billing,
                                        "/admin_revoke JVS-nope")


def test_admin_generated_password_and_usage(licenses, billing):
    out = handle_admin_command(licenses, billing, "/admin_add happy")
    assert "Password: <code>" in out
    assert "Usage" in handle_admin_command(licenses, billing, "/admin_add")
    assert "Usage" in handle_admin_command(licenses, billing, "/admin_lic")
    assert "positive" in handle_admin_command(licenses, billing,
                                            "/admin_lic happy zero")
    assert "not found" in handle_admin_command(licenses, billing,
                                            "/admin_info ghost")


def test_admin_routing(licenses, billing):
    assert handle_admin_command(licenses, billing, "hello") is None
    assert handle_admin_command(licenses, billing, "") is None
    # /admin@BotName works too.
    assert "Stats" in handle_admin_command(licenses, billing,
                                        "/admin@jarvis_bot")
    # Unknown /admin_* command falls through to None (bot replies "unknown").
    assert handle_admin_command(licenses, billing, "/admin_xyz") is None


def test_panel_escapes_html(licenses, billing):
    licenses.create_account("<b>evil</b>", "x")
    text = panel_text(licenses, billing)
    assert "<b>evil</b>" not in text
    assert "&lt;b&gt;evil&lt;/b&gt;" in text
