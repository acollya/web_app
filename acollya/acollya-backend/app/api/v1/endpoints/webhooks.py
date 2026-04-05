"""
Stripe webhook endpoint.

POST /webhooks/stripe  — receive and process Stripe events

Security: Stripe signature verified via stripe.Webhook.construct_event before
any payload processing. Raw bytes body required — reads body via Request directly
and must NOT be parsed through Pydantic first.

IMPORTANT: This endpoint has NO auth dependency — Stripe sends unsigned HTTP POSTs.
The signature header is the only security mechanism; keep webhook_secret safe.
"""
import logging

import stripe
from fastapi import APIRouter, Depends, Header, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import get_db
from app.services import webhook_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/stripe",
    status_code=status.HTTP_200_OK,
    summary="Receive Stripe webhook events",
    include_in_schema=False,  # hide from public Swagger docs
)
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    stripe_signature: str = Header(..., alias="stripe-signature"),
) -> Response:
    raw_body: bytes = await request.body()

    webhook_secret: str = settings.stripe_config.get("webhook_secret", "")
    if not webhook_secret:
        logger.error("stripe webhook_secret not configured — rejecting event")
        return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    try:
        event: stripe.Event = stripe.Webhook.construct_event(
            payload=raw_body,
            sig_header=stripe_signature,
            secret=webhook_secret,
        )
    except stripe.error.SignatureVerificationError as exc:
        logger.warning("Stripe signature verification failed: %s", exc)
        return Response(
            content="Invalid signature",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as exc:
        logger.error("Failed to construct Stripe event: %s", exc)
        return Response(
            content="Bad request",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        await webhook_service.handle_stripe_event(db, event)
    except Exception as exc:
        # Return 200 so Stripe doesn't retry indefinitely for app-level errors.
        # All errors are logged; retryable failures should raise explicitly if needed.
        logger.exception(
            "Unhandled error processing Stripe event id=%s type=%s: %s",
            event.get("id"), event.get("type"), exc,
        )

    return Response(status_code=status.HTTP_200_OK)
