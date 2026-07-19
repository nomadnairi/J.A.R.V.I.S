"""
``POST /billing/webhook`` — HMAC-signed hook for external payment processors.

Your payment relay (Stripe/Payme/… backend) confirms a payment and calls this
endpoint with a JSON body and an ``X-Signature`` header containing the
hex-encoded HMAC-SHA256 of the **raw request body** keyed with
``BILLING_WEBHOOK_SECRET``. Requests without a valid signature are rejected;
the endpoint does not exist at all unless billing, accounts and the secret
are configured.

Body::

    {
        "charge_id": "unique-payment-id",        (required)
        "telegram_user_id": 123456789,           (optional)
        "username": "tony",                      (optional)
        "plan": "standard",                      (optional)
        "valid_days": 365                        (optional, omit = server default)
    }

The response includes the one-time password only when a brand-new account was
created — deliver it to the buyer over a secure channel.
"""

import hashlib
import hmac

from jarvis.billing import BillingService
from jarvis.config.settings import Settings
from jarvis.licensing import AuthError, LicenseService
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


def verify_signature(secret: str, body: bytes, signature: str | None) -> bool:
    """Constant-time check of the webhook HMAC."""
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.strip().lower())


def install_billing_routes(app, settings: Settings,
                        license_service: LicenseService) -> None:
    """Register /billing/webhook (only call when billing is fully configured)."""
    from fastapi import HTTPException, Request as HttpRequest

    billing = BillingService(license_service, settings.auth_db_path)

    @app.post("/billing/webhook")
    async def billing_webhook(request: HttpRequest) -> dict:
        body = await request.body()
        signature = request.headers.get("X-Signature")
        if not verify_signature(settings.billing_webhook_secret, body, signature):
            raise HTTPException(status_code=403, detail="Invalid signature.")

        import json
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Invalid JSON.") from exc

        charge_id = str(payload.get("charge_id", "")).strip()
        if not charge_id:
            raise HTTPException(status_code=400, detail="charge_id is required.")

        telegram_user_id = payload.get("telegram_user_id")
        if telegram_user_id is not None and not isinstance(telegram_user_id, int):
            raise HTTPException(status_code=400,
                                detail="telegram_user_id must be an integer.")
        valid_days = payload.get("valid_days",
                                settings.billing_plan_days or None)
        if valid_days is not None and (not isinstance(valid_days, int)
                                    or valid_days <= 0):
            raise HTTPException(status_code=400,
                                detail="valid_days must be a positive integer.")

        try:
            fulfillment = billing.process_payment(
                charge_id,
                telegram_user_id=telegram_user_id,
                username=payload.get("username"),
                plan=str(payload.get("plan") or settings.billing_plan),
                valid_days=valid_days,
            )
        except AuthError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if fulfillment is None:
            return {"status": "duplicate"}
        out = {
            "status": "fulfilled",
            "username": fulfillment.username,
            "license_key": fulfillment.license_key,
            "plan": fulfillment.plan,
            "created_account": fulfillment.created_account,
        }
        if fulfillment.password is not None:
            out["password"] = fulfillment.password
        return out
