"""rq worker for async credit evaluation jobs.

The model and explainer are loaded at module level — once per worker process,
not per job. This keeps latency low on repeated jobs.
"""

import logging

from redis import Redis
from rq import Queue

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
    from src.api import model_store

    if not model_store.is_loaded():
        model_store.load_models()

    use_emotional = all(
        request_data.get(f) is not None
        for f in [
            "stress_level",
            "impulsivity_score",
            "emotional_stability",
            "financial_stress_events_7d",
        ]
    )
    return model_store.predict(request_data, use_emotional=use_emotional)


def enqueue_evaluation(request_data: dict) -> str:
    """Enqueue an evaluation job. Returns the job ID."""
    q = _get_queue()
    job = q.enqueue(_run_evaluation, request_data)
    return job.id


def get_job_result(job_id: str) -> tuple[str, dict | None]:
    """Fetch job status and result. Returns (status, result_dict | None)."""
    from rq.job import Job

    settings = get_settings()
    redis_conn = Redis.from_url(settings.redis_url)
    try:
        job = Job.fetch(job_id, connection=redis_conn)
        status = job.get_status().value
        result = job.result if status == "finished" else None
        return status, result
    except Exception:
        return "not_found", None
