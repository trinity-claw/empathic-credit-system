import logging

import httpx

from src.api.db import update_notification_status
from src.api.settings import get_settings

logger = logging.getLogger(__name__)


def deliver_notification(
    *,
    notification_id: str,
    user_id: str | None,
    offer_id: str,
    notification_type: str,
    payload: dict,
) -> bool:
    webhook_url = get_settings().notification_webhook_url
    body = {
        "notification_id": notification_id,
        "user_id": user_id,
        "offer_id": offer_id,
        "type": notification_type,
        "payload": payload,
    }

    delivered = False
    try:
        if webhook_url:
            with httpx.Client(timeout=3.0) as client:
                resp = client.post(webhook_url, json=body)
                resp.raise_for_status()
        else:
            logger.info(
                "notification.delivered",
                extra={
                    "event": "notification.delivered",
                    "channel": "mock_mobile_push",
                    "notification_id": notification_id,
                    "user_id": user_id,
                    "offer_id": offer_id,
                    "type": notification_type,
                },
            )
        delivered = True
    except Exception as exc:
        logger.warning(
            "notification.delivery_failed",
            extra={
                "notification_id": notification_id,
                "offer_id": offer_id,
                "error": str(exc),
            },
        )

    update_notification_status(notification_id, "delivered" if delivered else "failed")
    return delivered
