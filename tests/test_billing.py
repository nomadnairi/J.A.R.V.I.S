"""Tests for payments → automatic license issuance."""

from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from jarvis.billing import BillingService
from jarvis.config.settings import Settings
from jarvis.licensing import AuthError, LicenseService


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


def test_new_buyer_gets_account_and_license(billing, licenses):
    out = billing.process_payment("charge-1", telegram_user_id=42)
    assert out is not None and out.created_account
    assert out.username == "user42"
    assert out.password  # one-time password for a fresh account
    assert out.license_key.startswith("JVS-")
    # The account can actually sign in, and Telegram is linked.
    assert licenses.authenticate("user42", out.password).id
    assert licenses.get_account_by_telegram(42).username == "user42"


def test_duplicate_charge_is_ignored(billing):
    assert billing.process_payment("charge-1", telegram_user_id=1) is not None
    assert billing.process_payment("charge-1", telegram_user_id=1) is None


def test_existing_telegram_account_extends_license(billing, licenses):
    first = billing.process_payment("charge-1", telegram_user_id=7)
    second = billing.process_payment("charge-2", telegram_user_id=7)
    assert second is not None
    assert not second.created_account
    assert second.password is None
    assert second.username == first.username
    assert len(licenses.list_licenses(
        licenses.get_account(first.username).id)) == 2


def test_existing_username_reused(billing, licenses):
    acc = licenses.create_account("tony", "arcreactor")
    out = billing.process_payment("charge-9", username="tony")
    assert out is not None and not out.created_account
    assert licenses.has_active_license(acc.id)


def test_username_collision_gets_suffix(billing, licenses):
    licenses.create_account("user5", "x")
    out = billing.process_payment("charge-5", telegram_user_id=5)
    assert out.username == "user52"  # user5 taken → suffixed


def test_empty_charge_id_rejected(billing):
    with pytest.raises(AuthError):
        billing.process_payment("")


def test_valid_days_flow(billing, licenses):
    import time
    out = billing.process_payment("charge-3", telegram_user_id=3, valid_days=30)
    account = licenses.get_account(out.username)
    assert licenses.has_active_license(account.id)
    assert not licenses.has_active_license(
        account.id, now=time.time() + 31 * 86400)


# -- bot payment handler ---------------------------------------------------


def test_handle_successful_payment_messages(billing):
    from jarvis.interfaces.telegram_bot import handle_successful_payment

    settings = Settings(anthropic_api_key="k", log_file="",
                        billing_plan="standard", billing_plan_days=365)
    first = handle_successful_payment(billing, settings, 42, "tg-charge-1", "ru")
    assert "Логин" in first and "user42" in first
    # The same charge delivered twice → generic "extended" reply, no crash.
    dup = handle_successful_payment(billing, settings, 42, "tg-charge-1", "ru")
    assert "продлена" in dup
    # A second real purchase extends without leaking a password.
    second = handle_successful_payment(billing, settings, 42, "tg-charge-2", "en")
    assert "extended" in second and "Password" not in second


# -- webhook -----------------------------------------------------------------


def _sig(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _webhook_app():
    pytest.importorskip("fastapi")
    from jarvis.api.app import create_app
    from jarvis.core.container import ServiceContainer
    from jarvis.core.engine import JarvisEngine
    from jarvis.llm.client import LLMClient
    from tests.conftest import FakeProvider

    settings = Settings(
        anthropic_api_key="k", log_file="", memory_enabled=False,
        integrations_enabled=False, goals_enabled=False, rate_limit_enabled=False,
        auth_enabled=True, auth_db_path=":memory:",
        billing_enabled=True, billing_webhook_secret="hook-secret",
    )
    engine = JarvisEngine(container=ServiceContainer(
        settings, llm_client=LLMClient(primary=FakeProvider())))
    return create_app(engine=engine, settings=settings)


def test_webhook_rejects_bad_signature():
    from fastapi.testclient import TestClient

    with TestClient(_webhook_app()) as client:
        body = json.dumps({"charge_id": "c1"}).encode()
        assert client.post("/billing/webhook", content=body).status_code == 403
        assert client.post("/billing/webhook", content=body,
                        headers={"X-Signature": "wrong"}).status_code == 403


def test_webhook_fulfills_and_deduplicates():
    from fastapi.testclient import TestClient

    with TestClient(_webhook_app()) as client:
        body = json.dumps({"charge_id": "c1", "telegram_user_id": 99,
                        "valid_days": 30}).encode()
        headers = {"X-Signature": _sig("hook-secret", body)}
        first = client.post("/billing/webhook", content=body, headers=headers)
        assert first.status_code == 200, first.text
        data = first.json()
        assert data["status"] == "fulfilled" and data["created_account"]
        assert data["password"] and data["license_key"].startswith("JVS-")

        again = client.post("/billing/webhook", content=body, headers=headers)
        assert again.json() == {"status": "duplicate"}


def test_webhook_validates_payload():
    from fastapi.testclient import TestClient

    with TestClient(_webhook_app()) as client:
        def post(payload: dict):
            body = json.dumps(payload).encode()
            return client.post("/billing/webhook", content=body,
                            headers={"X-Signature": _sig("hook-secret", body)})

        assert post({}).status_code == 400  # no charge_id
        assert post({"charge_id": "x", "telegram_user_id": "abc"}
                    ).status_code == 400
        assert post({"charge_id": "x", "valid_days": -5}).status_code == 400


def test_webhook_absent_when_billing_disabled():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from jarvis.api.app import create_app
    from jarvis.core.container import ServiceContainer
    from jarvis.core.engine import JarvisEngine
    from jarvis.llm.client import LLMClient
    from tests.conftest import FakeProvider

    settings = Settings(
        anthropic_api_key="k", log_file="", memory_enabled=False,
        integrations_enabled=False, goals_enabled=False, rate_limit_enabled=False,
        auth_enabled=True, auth_db_path=":memory:",
    )
    engine = JarvisEngine(container=ServiceContainer(
        settings, llm_client=LLMClient(primary=FakeProvider())))
    with TestClient(create_app(engine=engine, settings=settings)) as client:
        assert client.post("/billing/webhook", content=b"{}").status_code == 404
