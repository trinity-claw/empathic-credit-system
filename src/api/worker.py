"""rq worker for async credit evaluation and credit deployment jobs.

The model and explainer are loaded at module level — once per worker process,
not per job. This keeps latency low on repeated jobs.
"""

import json
import logging
import uuid

from redis import Redis
from rq import Queue
from rq.job import Job

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


# ---------------------------------------------------------------------------
# Scoring job
# ---------------------------------------------------------------------------


def _run_evaluation(request_data: dict) -> dict:
    """Executed inside the rq worker process."""
    # Lazy import: model_store triggers heavy ML model loading; deferred to
    # avoid circular import when this module is imported by the API process.
    from src.api import model_store

    if not model_store.is_loaded():
        model_store.load_models()

    return model_store.predict(
        request_data, use_emotional=has_emotional_data(request_data)
    )


def enqueue_evaluation(request_data: dict) -> str:
    """Enqueue an evaluation job. Returns the job ID."""
    q = _get_queue()
    job = q.enqueue(_run_evaluation, request_data)
    return job.id


# ---------------------------------------------------------------------------
# Credit deployment job (offer accepted → update profile → notify)
# ---------------------------------------------------------------------------


def _deploy_credit_offer(offer_id: str, user_id: str | None) -> dict:
    """Executed inside the rq worker process.

    Flow: accept offer in DB → update user credit limit → send notification.
    Reflects CloudWalk's event-driven micro-service architecture where credit
    deployment is decoupled from scoring for fairness and traceability.
    """
    from src.api.db import accept_credit_offer, save_notification

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
    """Enqueue a credit deployment job. Returns the job ID."""
    q = _get_queue()
    job = q.enqueue(_deploy_credit_offer, offer_id, user_id)
    return job.id


# ---------------------------------------------------------------------------
# Real-time emotion stream (Redis Pub/Sub publisher)
# ---------------------------------------------------------------------------

_EMOTION_CHANNEL = "ecs:emotion_stream"


def publish_emotional_event(event_id: str, payload: dict) -> None:
    """Publish an emotional event to the Redis Pub/Sub channel.

    Any number of downstream consumers (analytics, risk aggregators) can
    subscribe to this channel without coupling to the API. In production,
    this would be replaced by Kafka for durability and replay semantics.
    """
    settings = get_settings()
    redis_conn = Redis.from_url(settings.redis_url)
    message = json.dumps({"event_id": event_id, **payload})
    redis_conn.publish(_EMOTION_CHANNEL, message)
    logger.info(
        "Emotional event published",
        extra={"event_id": event_id, "channel": _EMOTION_CHANNEL},
    )


# ---------------------------------------------------------------------------
# Job status polling (shared)
# ---------------------------------------------------------------------------


def get_job_result(job_id: str) -> tuple[str, dict | None]:
    """Fetch job status and result. Returns (status, result_dict | None)."""
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
