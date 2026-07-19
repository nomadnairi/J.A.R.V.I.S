"""Tests for the sales report (revenue tracking + /admin_sales)."""

from __future__ import annotations

import time

import pytest

from jarvis.billing import BillingService
from jarvis.interfaces.admin_panel import handle_admin_command, sales_report_text
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


def _backdate(billing: BillingService, charge_id: str, days: float) -> None:
    billing._conn.execute(
        "UPDATE payments SET created_at = ? WHERE charge_id = ?",
        (time.time() - days * 86400, charge_id),
    )
    billing._conn.commit()


def test_amount_and_currency_recorded(billing):
    billing.process_payment("c1", telegram_user_id=1, amount=2500,
                            currency="xtr")
    payment = billing.recent_payments(1)[0]
    assert payment["amount"] == 2500
    assert payment["currency"] == "XTR"  # normalised to upper case


def test_sales_report_numbers(billing):
    billing.process_payment("c1", telegram_user_id=1, amount=2500,
                            currency="XTR")
    billing.process_payment("c2", telegram_user_id=1, amount=2500,
                            currency="XTR")           # same buyer again
    billing.process_payment("c3", telegram_user_id=2, amount=100,
                            currency="USD", plan="pro")
    _backdate(billing, "c3", days=10)                  # outside 7d window

    report = billing.sales_report()
    assert report["buyers"] == 2
    assert report["periods"]["all"]["payments"] == 3
    assert report["periods"]["7d"]["payments"] == 2
    assert report["periods"]["today"]["payments"] == 2
    assert report["periods"]["all"]["revenue"] == {"XTR": 5000, "USD": 100}
    assert report["periods"]["7d"]["revenue"] == {"XTR": 5000}
    assert report["plans"] == {"standard": 2, "pro": 1}


def test_sales_report_text_rendering(licenses, billing):
    billing.process_payment("c1", telegram_user_id=42, amount=2500,
                            currency="XTR")
    text = sales_report_text(licenses, billing)
    assert "Sales report" in text
    assert "Buyers (paid at least once): 1" in text
    assert "⭐ 2500" in text          # Stars formatting
    assert "user42" in text
    assert "standard: 1" in text


def test_sales_report_without_billing(licenses):
    assert "BILLING_ENABLED" in sales_report_text(licenses, None)


def test_admin_sales_route(licenses, billing):
    billing.process_payment("c1", telegram_user_id=7, amount=10,
                            currency="XTR")
    out = handle_admin_command(licenses, billing, "/admin_sales")
    assert "Sales report" in out
    # And the panel mentions the new command.
    assert "/admin_sales" in handle_admin_command(licenses, billing, "/admin")


def test_migration_adds_columns(licenses, tmp_path):
    """A payments table from the previous schema gains amount/currency."""
    import sqlite3

    db = tmp_path / "billing.db"
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE payments (charge_id TEXT PRIMARY KEY, "
        "telegram_user_id INTEGER, username TEXT, plan TEXT NOT NULL, "
        "created_at REAL NOT NULL)"
    )
    conn.execute("INSERT INTO payments VALUES ('old1', 5, 'user5', "
                "'standard', 1700000000.0)")
    conn.commit()
    conn.close()

    service = BillingService(licenses, str(db))
    try:
        assert service.already_processed("old1")
        old = service.recent_payments(1)[0]
        assert old["amount"] == 0 and old["currency"] == ""
        service.process_payment("new1", telegram_user_id=6, amount=50,
                                currency="XTR")
        assert service.sales_report()["periods"]["all"]["payments"] == 2
    finally:
        service.close()


def test_handle_successful_payment_records_amount(billing):
    from jarvis.config.settings import Settings
    from jarvis.interfaces.telegram_bot import handle_successful_payment

    settings = Settings(anthropic_api_key="k", log_file="")
    handle_successful_payment(billing, settings, 42, "tg-1", "en",
                            amount=2500, currency="XTR")
    assert billing.sales_report()["periods"]["all"]["revenue"] == {"XTR": 2500}


def test_webhook_records_amount(licenses):
    pytest.importorskip("fastapi")
    import hashlib
    import hmac as hmac_mod
    import json

    from fastapi.testclient import TestClient

    from jarvis.api.app import create_app
    from jarvis.config.settings import Settings
    from jarvis.core.container import ServiceContainer
    from jarvis.core.engine import JarvisEngine
    from jarvis.llm.client import LLMClient
    from tests.conftest import FakeProvider

    settings = Settings(
        anthropic_api_key="k", log_file="", memory_enabled=False,
        integrations_enabled=False, goals_enabled=False, rate_limit_enabled=False,
        auth_enabled=True, auth_db_path=":memory:",
        billing_enabled=True, billing_webhook_secret="s3",
    )
    engine = JarvisEngine(container=ServiceContainer(
        settings, llm_client=LLMClient(primary=FakeProvider())))
    with TestClient(create_app(engine=engine, settings=settings)) as client:
        body = json.dumps({"charge_id": "w1", "username": "tony",
                        "amount": 999, "currency": "usd"}).encode()
        sig = hmac_mod.new(b"s3", body, hashlib.sha256).hexdigest()
        resp = client.post("/billing/webhook", content=body,
                        headers={"X-Signature": sig})
        assert resp.status_code == 200, resp.text
        # Bad amount rejected.
        bad = json.dumps({"charge_id": "w2", "amount": -1}).encode()
        sig = hmac_mod.new(b"s3", bad, hashlib.sha256).hexdigest()
        assert client.post("/billing/webhook", content=bad,
                        headers={"X-Signature": sig}).status_code == 400
