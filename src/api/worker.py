"""rq worker for async credit evaluation and credit deployment jobs."""

import json
import logging
import uuid

from redis import Redis
from rq import Queue
from rq.job import Job

from src.api import model_store
from src.api.db import accept_credit_offer, save_notification
from src.api.schemas import has_emotional_data
from src.api.settings import get_settings

logger = logging.getLogger(__name__)

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


def _deploy_credit_offer(offer_id: str, user_id: str | None) -> dict:
    offer = accept_credit_offer(offer_id)
    if offer is None:
        logger.warning("Offer not found or already processed: %s", offer_id)
        return {"status": "not_found", "offer_id": offer_id}

    notification_id = str(uuid.uuid4())
    save_notification(
        notification_id=notification_id,
        user_id=user_id,
        offer_id=offer_id,
        notification_type="credit_deployed",
        payload={
            "credit_limit": offer.credit_limit,
            "interest_rate": offer.interest_rate,
            "credit_type": offer.credit_type,
        },
    )
    logger.info(
        "Credit offer deployed",
        extra={"offer_id": offer_id, "notification_id": notification_id},
    )
    return {
        "status": "deployed",
        "offer_id": offer_id,
        "notification_id": notification_id,
    }


def enqueue_deployment(offer_id: str, user_id: str | None) -> str:
    q = _get_queue()
    job = q.enqueue(_deploy_credit_offer, offer_id, user_id)
    return job.id


_EMOTION_CHANNEL = "ecs:emotion_stream"


def publish_emotional_event(event_id: str, payload: dict) -> None:
    settings = get_settings()
    redis_conn = Redis.from_url(settings.redis_url)
    message = json.dumps({"event_id": event_id, **payload})
    redis_conn.publish(_EMOTION_CHANNEL, message)
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
