"""
Subscription schemas — plan catalog, status, and RevenueCat webhook payload.

PlanConfig                 — static plan definition (GET /subscriptions/plans)
PlansResponse              — wrapper list
SubscriptionStatusResponse — current user subscription state
RevenueCatWebhookEvent     — single event sent by RevenueCat
RevenueCatWebhookPayload   — top-level webhook envelope
"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class PlanConfig(BaseModel):
    id: str                         # "free" | "monthly" | "annual"
    name: str
    price_brl: float                # 0.0 for free
    billing_period: Optional[str]   # "month" | "year" | None
    features: list[str]
    is_popular: bool = False


class PlansResponse(BaseModel):
    plans: list[PlanConfig]


class SubscriptionStatusResponse(BaseModel):
    model_config = {"from_attributes": True}

    status: str                              # "trialing" | "active" | "past_due" | "canceled" | "none"
    provider: Optional[str] = None           # "revenue_cat" | None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    is_active: bool
    days_remaining: Optional[int] = None


# ── RevenueCat webhook ────────────────────────────────────────────────────────

class RevenueCatWebhookEvent(BaseModel):
    """Single RevenueCat event (the payload's `event` field).

    `extra='allow'` keeps any forward-compatible fields RevenueCat introduces
    (e.g. transaction_id, original_transaction_id, environment, country_code).
    """
    model_config = ConfigDict(extra="allow")

    type: str
    app_user_id: Optional[str] = None
    aliases: list[str] = Field(default_factory=list)
    original_app_user_id: Optional[str] = None
    product_id: Optional[str] = None
    entitlement_id: Optional[str] = None
    entitlement_ids: Optional[list[str]] = None
    period_type: Optional[str] = None
    purchased_at_ms: Optional[int] = None
    expiration_at_ms: Optional[int] = None
    event_timestamp_ms: Optional[int] = None
    currency: Optional[str] = None
    price: Optional[float] = None
    store: Optional[str] = None


class RevenueCatWebhookPayload(BaseModel):
    """Top-level RevenueCat webhook body."""
    model_config = ConfigDict(extra="allow")

    event: RevenueCatWebhookEvent
    api_version: Optional[str] = None

    def to_event_dict(self) -> dict[str, Any]:
        """Serialize the inner event for the service layer."""
        return self.event.model_dump()
