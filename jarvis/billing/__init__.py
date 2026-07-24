"""Payments → automatic license issuance.

Two entry points feed :class:`~jarvis.billing.service.BillingService`:

* the Telegram bot's ``/buy`` flow (Telegram Stars) — after a successful
  payment the bot creates the account + license and DMs the credentials;
* ``POST /billing/webhook`` — an HMAC-signed hook for external payment
  processors (Stripe, Payme, …) relayed by your own backend.

Every payment is recorded by its charge id, so retries and duplicate webhooks
can never issue a second license.
"""

from jarvis.billing.plans import (
    FREE,
    PLUS,
    PRO,
    TIER_ORDER,
    Plan,
    build_plans,
    default_plans,
    resolve_plan,
    tier_for,
)
from jarvis.billing.service import BillingService, Fulfillment

__all__ = [
    "BillingService", "Fulfillment",
    "Plan", "FREE", "PLUS", "PRO", "TIER_ORDER",
    "build_plans", "default_plans", "resolve_plan", "tier_for",
]
