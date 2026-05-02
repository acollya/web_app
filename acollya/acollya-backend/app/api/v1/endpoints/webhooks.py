"""
Webhook endpoints (no Bearer auth — providers authenticate with shared secrets).

POST /webhooks/revenuecat — receives IAP purchase / renewal / cancellation
events from RevenueCat and syncs subscription state.
"""
import hmac
import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, Request, Response, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.dependencies import get_db
from app.schemas.subscription import RevenueCatWebhookPayload
from app.services import subscription_service

logger = logging.getLogger(__name__)

router = APIRouter()


def _verify_revenuecat_secret(authorization: Optional[str]) -> bool:
    """Constant-time comparison of the shared secret RevenueCat sends.

    RevenueCat sets the raw secret as the `Authorization` header value (no
    "Bearer " prefix), but we tolerate either form.
    """
    expected = settings.revenue_cat_webhook_secret
    if not expected or not authorization:
        return False
    received = authorization.strip()
    if received.lower().startswith("bearer "):
        received = received[7:].strip()
    return hmac.compare_digest(received, expected)


@router.post(
    "/revenuecat",
    summary="RevenueCat webhook receiver (IAP events)",
    include_in_schema=False,
)
async def revenuecat_webhook(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    authorization: Annotated[Optional[str], Header(alias="Authorization")] = None,
) -> Response:
    if not _verify_revenuecat_secret(authorization):
        logger.warning("revenuecat_webhook_unauthorized")
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)

    # Parse defensively — RevenueCat retries on non-2xx, so malformed payloads
    # are acknowledged (logged) rather than rejected.
    try:
        body = await request.json()
    except Exception as exc:  # noqa: BLE001 - payload is fully untrusted
        logger.warning("revenuecat_webhook_invalid_json", extra={"error": str(exc)})
        return Response(status_code=status.HTTP_200_OK)

    try:
        payload = RevenueCatWebhookPayload.model_validate(body)
    except Exception as exc:  # noqa: BLE001 - tolerate schema drift
        logger.warning(
            "revenuecat_webhook_invalid_payload",
            extra={"error": str(exc)},
        )
        return Response(status_code=status.HTTP_200_OK)

    try:
        await subscription_service.handle_revenuecat_event(db, payload.to_event_dict())
    except SQLAlchemyError:
        # Transient DB error — return 503 so RevenueCat retries the event.
        logger.exception(
            "revenuecat_webhook_db_error",
            extra={"event_type": payload.event.type},
        )
        return Response(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
    except Exception:  # noqa: BLE001 - unexpected app bug — accept and alarm
        logger.exception(
            "revenuecat_webhook_processing_failed",
            extra={"event_type": payload.event.type},
        )
        return Response(status_code=status.HTTP_200_OK)

    return Response(status_code=status.HTTP_200_OK)
