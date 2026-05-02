"""
Subscription schemas — plan catalog and status.

PlanConfig            — static plan definition (GET /subscriptions/plans)
PlansResponse         — wrapper list
SubscriptionStatusResponse — current user subscription state
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


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
