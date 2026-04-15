"""rq worker for async credit evaluation jobs.

The model and explainer are loaded at module level — once per worker process,
not per job. This keeps latency low on repeated jobs.
"""

import logging

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
