import json
import logging
import uuid

from redis import Redis
from rq import Queue, Retry
from rq.job import Job

from src.api import model_store
from src.api.db import (
    accept_credit_offer,
    apply_credit_to_user,
    get_credit_offer,
    notification_exists_for_offer,
    save_notification,
)
from src.api.notifications import deliver_notification
from src.api.schemas import has_emotional_data
from src.api.settings import get_settings

logger = logging.getLogger(__name__)

_NOTIFICATION_TYPE = "credit_deployed"
_CREDIT_EVENT_CHANNEL = "ecs:credit_events"
_EMOTION_CHANNEL = "ecs:emotion_stream"

_queue: Queue | None = None


def _get_queue() -> Queue:
    global _queue
    if _queue is None:
        settings = get_settings()
        redis_conn = Redis.from_url(settings.redis_url)
        _queue = Queue("credit_eval", connection=redis_conn)
    return _queue


def _run_evaluation(request_data: dict) -> dict:
    if not model_store.is_loaded():
        model_store.load_models()
    return model_store.predict(
        request_data, use_emotional=has_emotional_data(request_data)
    )


def enqueue_evaluation(request_data: dict) -> str:
    q = _get_queue()
    job = q.enqueue(_run_evaluation, request_data)
    return job.id


def _publish_credit_event(event_type: str, payload: dict) -> None:
    try:
        settings = get_settings()
        redis_conn = Redis.from_url(settings.redis_url)
        redis_conn.publish(
            _CREDIT_EVENT_CHANNEL,
            json.dumps({"event_type": event_type, **payload}),
        )
        logger.info(
            "credit.published",
            extra={"event_type": event_type, "channel": _CREDIT_EVENT_CHANNEL},
        )
    except Exception as exc:
        logger.warning(
            "credit.publish_failed", extra={"event_type": event_type, "error": str(exc)}
        )


def _deploy_credit_offer(offer_id: str, user_id: str | None) -> dict:
    offer = accept_credit_offer(offer_id)
    was_newly_accepted = offer is not None

    if offer is None:
        offer = get_credit_offer(offer_id)
        if offer is None:
            logger.warning("Offer not found: %s", offer_id)
            return {"status": "not_found", "offer_id": offer_id}
        if offer.status != "accepted":
            logger.warning(
                "Offer in unexpected state: %s (status=%s)", offer_id, offer.status
            )
            return {"status": "invalid_state", "offer_id": offer_id}

    if not was_newly_accepted and notification_exists_for_offer(
        offer_id, _NOTIFICATION_TYPE
    ):
        logger.info("Offer already deployed; skipping", extra={"offer_id": offer_id})
        return {"status": "already_processed", "offer_id": offer_id}

    effective_user_id = user_id or offer.user_id
    if effective_user_id is not None:
        apply_credit_to_user(
            user_id=effective_user_id,
            credit_limit=offer.credit_limit,
            interest_rate=offer.interest_rate,
            credit_type=offer.credit_type,
        )

    notification_id = str(uuid.uuid4())
    payload = {
        "credit_limit": offer.credit_limit,
        "interest_rate": offer.interest_rate,
        "credit_type": offer.credit_type,
    }
    save_notification(
        notification_id=notification_id,
        user_id=effective_user_id,
        offer_id=offer_id,
        notification_type=_NOTIFICATION_TYPE,
        payload=payload,
    )
    deliver_notification(
        notification_id=notification_id,
        user_id=effective_user_id,
        offer_id=offer_id,
        notification_type=_NOTIFICATION_TYPE,
        payload=payload,
    )

    logger.info(
        "Credit offer deployed",
        extra={
            "offer_id": offer_id,
            "notification_id": notification_id,
            "user_id": effective_user_id,
        },
    )

    _publish_credit_event(
        "credit.accepted",
        {
            "offer_id": offer_id,
            "user_id": effective_user_id,
            "credit_limit": offer.credit_limit,
            "interest_rate": offer.interest_rate,
            "credit_type": offer.credit_type,
        },
    )

    return {
        "status": "deployed",
        "offer_id": offer_id,
        "notification_id": notification_id,
    }


def enqueue_deployment(offer_id: str, user_id: str | None) -> str:
    q = _get_queue()
    job = q.enqueue(
        _deploy_credit_offer,
        offer_id,
        user_id,
        retry=Retry(max=3, interval=[10, 30, 60]),
    )
    return job.id


def publish_emotional_event(event_id: str, payload: dict) -> None:
    settings = get_settings()
    redis_conn = Redis.from_url(settings.redis_url)
    redis_conn.publish(_EMOTION_CHANNEL, json.dumps({"event_id": event_id, **payload}))
    logger.info(
        "Emotional event published",
        extra={"event_id": event_id, "channel": _EMOTION_CHANNEL},
    )


def get_job_result(job_id: str) -> tuple[str, dict | None]:
    settings = get_settings()
    redis_conn = Redis.from_url(settings.redis_url)
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        logger.warning("Job not found: %s", job_id)
        return "not_found", None
    status = job.get_status().value
    result = job.result if status == "finished" else None
    return status, result
