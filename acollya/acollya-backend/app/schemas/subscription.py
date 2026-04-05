"""
Subscription & payment schemas.

PlanConfig            — static plan definition (returned by GET /subscriptions/plans)
PlansResponse         — wrapper list
SubscriptionStatusResponse — current user subscription state
CheckoutRequest       — body for POST /subscriptions/checkout
CheckoutResponse      — Stripe Checkout Session url + id
PortalResponse        — Stripe Customer Portal url
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Static plan catalog ────────────────────────────────────────────────────────

class PlanConfig(BaseModel):
    id: str                         # "free" | "monthly" | "annual"
    name: str
    price_brl: float                # 0.0 for free
    stripe_price_id: Optional[str]  # None for free plan
    billing_period: Optional[str]   # "month" | "year" | None
    features: list[str]
    is_popular: bool = False


class PlansResponse(BaseModel):
    plans: list[PlanConfig]


# ── User subscription state ────────────────────────────────────────────────────

class SubscriptionStatusResponse(BaseModel):
    model_config = {"from_attributes": True}

    status: str                              # "trialing" | "active" | "past_due" | "canceled" | "none"
    provider: Optional[str] = None           # "stripe" | "revenue_cat" | None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    is_active: bool                          # True if trialing or active
    days_remaining: Optional[int] = None     # for trial: days left; for paid: days until renewal
    stripe_customer_id: Optional[str] = None


# ── Checkout ───────────────────────────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    price_id: str = Field(..., description="Stripe Price ID (e.g. price_xxx)")
    success_url: str = Field(..., description="Redirect URL on successful payment")
    cancel_url: str = Field(..., description="Redirect URL if user cancels checkout")


class CheckoutResponse(BaseModel):
    session_id: str
    url: str


# ── Portal ─────────────────────────────────────────────────────────────────────

class PortalRequest(BaseModel):
    return_url: str = Field(..., description="URL to redirect after leaving the portal")


class PortalResponse(BaseModel):
    url: str
