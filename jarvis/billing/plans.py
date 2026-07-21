"""
Subscription tiers for the Telegram bot (Free / Plus / Pro).

Each tier bundles usage limits and feature entitlements — how many messages a
day, which models are unlocked, whether image generation and personal API
access are available, and the support level. A user's tier is derived from
their active licence plan; anyone without an active licence is **Free**.

The design is "hybrid": a paid tier grants a generous daily allowance, and a
user who wants no limits at all can connect their own provider API key (BYOK),
which bypasses the counter entirely because they pay the provider directly.

This module is framework-free and fully testable — the bot layer only reads
the resolved :class:`Plan` and renders it.
"""

from __future__ import annotations

from dataclasses import dataclass

FREE = "free"
PLUS = "plus"
PRO = "pro"

#: Order used when rendering the tier comparison, cheapest first.
TIER_ORDER = (FREE, PLUS, PRO)

# Licence plan names (as stored on a licence) mapped to a tier. Unknown but
# present plans are treated as at least Plus — the user did pay for something.
_ALIASES = {
    "free": FREE,
    "basic": FREE,
    "plus": PLUS,
    "standard": PLUS,
    "premium": PRO,
    "pro": PRO,
}


@dataclass(frozen=True)
class Plan:
    """A subscription tier and everything it unlocks."""

    name: str
    emoji: str
    #: 0 means "unlimited".
    daily_messages: int
    monthly_messages: int
    all_models: bool
    images: bool
    api_access: bool
    byok: bool
    #: community | priority | premium
    support: str
    #: Telegram Stars price (0 = free).
    price_stars: int

    @property
    def unlimited(self) -> bool:
        return self.daily_messages <= 0

    def within_daily(self, used_today: int) -> bool:
        """Is another message allowed today under this plan?"""
        return self.unlimited or used_today < self.daily_messages

    def remaining_daily(self, used_today: int) -> int | None:
        """Messages left today, or ``None`` when unlimited."""
        if self.unlimited:
            return None
        return max(0, self.daily_messages - used_today)


def tier_for(plan_name: str | None) -> str:
    """Map a licence plan name to a tier id (defaults to Free)."""
    if not plan_name:
        return FREE
    return _ALIASES.get(plan_name.strip().lower(), PLUS)


def default_plans() -> dict[str, Plan]:
    """The built-in tiers with sensible defaults."""
    return {
        FREE: Plan(
            name=FREE, emoji="🆓",
            daily_messages=10, monthly_messages=100,
            all_models=False, images=False, api_access=False, byok=True,
            support="community", price_stars=0,
        ),
        PLUS: Plan(
            name=PLUS, emoji="⭐",
            daily_messages=100, monthly_messages=2000,
            all_models=True, images=True, api_access=True, byok=True,
            support="priority", price_stars=2500,
        ),
        PRO: Plan(
            name=PRO, emoji="💎",
            daily_messages=0, monthly_messages=0,  # unlimited
            all_models=True, images=True, api_access=True, byok=True,
            support="premium", price_stars=8000,
        ),
    }


def build_plans(
    *,
    free_daily: int | None = None,
    plus_daily: int | None = None,
    pro_daily: int | None = None,
    plus_price: int | None = None,
    pro_price: int | None = None,
) -> dict[str, Plan]:
    """Built-in tiers with per-deployment overrides for limits and prices.

    Any argument left as ``None`` keeps the default for that field.
    """
    from dataclasses import replace

    plans = default_plans()
    if free_daily is not None:
        plans[FREE] = replace(plans[FREE], daily_messages=free_daily)
    if plus_daily is not None:
        plans[PLUS] = replace(plans[PLUS], daily_messages=plus_daily)
    if pro_daily is not None:
        plans[PRO] = replace(plans[PRO], daily_messages=pro_daily)
    if plus_price is not None:
        plans[PLUS] = replace(plans[PLUS], price_stars=plus_price)
    if pro_price is not None:
        plans[PRO] = replace(plans[PRO], price_stars=pro_price)
    return plans


def resolve_plan(plan_name: str | None,
                registry: dict[str, Plan] | None = None) -> Plan:
    """Resolve a licence plan name to the matching :class:`Plan`."""
    plans = registry or default_plans()
    return plans[tier_for(plan_name)]
