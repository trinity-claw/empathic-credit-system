"""FastAPI application entry point for the Empathic Credit System."""

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, Response
from pythonjsonlogger.json import JsonFormatter

from src.api import model_store
from src.api.auth import require_auth
from src.api.db import (
    init_db,
    log_event,
    save_credit_offer,
    save_evaluation,
    save_emotional_event,
)
from src.api.schemas import (
    AsyncJobResponse,
    CreditRequest,
    CreditResponse,
    EmotionStreamRequest,
    EmotionStreamResponse,
    HealthResponse,
    OfferAcceptResponse,
    ShapFactor,
)
from src.api.settings import get_settings
from src.api.worker import (
    enqueue_deployment,
    enqueue_evaluation,
    get_job_result,
    publish_emotional_event,
)

# Structured JSON logging — level driven by Settings.log_level
_settings = get_settings()
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.basicConfig(
    level=getattr(logging, _settings.log_level.upper(), logging.INFO),
    handlers=[handler],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("Starting up ECS API", extra={"model_version": settings.model_version})
    init_db()
    model_store.load_models()
    yield
    logger.info("Shutting down ECS API")


app = FastAPI(
    title="Empathic Credit System",
    description="ML-based credit scoring with SHAP explanations and real-time emotion processing.",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Middleware: X-Request-ID correlation header on every request/response
# ---------------------------------------------------------------------------


@app.middleware("http")
async def request_id_middleware(request: Request, call_next) -> Response:
    """Attach a correlation ID to every request for end-to-end tracing.

    Reads X-Request-ID from incoming headers if present (e.g. from API gateway),
    otherwise generates a new UUID. Logs method, path, status, and duration so
    every request can be correlated across distributed log queries — same pattern
    used in automatic-pix-api's InputOutputMiddleware.
    """
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = int((time.monotonic() - start) * 1000)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse, tags=["ops"])
def health():
    """Healthcheck endpoint — no auth required."""
    return HealthResponse(
        status="ok",
        model_loaded=model_store.is_loaded(),
        model_version=model_store.model_version(),
    )


# ---------------------------------------------------------------------------
# Credit evaluation
# ---------------------------------------------------------------------------


def _build_response(
    request_id: str, result: dict, offer_id: str | None = None
) -> CreditResponse:
    """Pure transformation: model output dict -> CreditResponse. No side effects."""
    top_factors = [ShapFactor(**f) for f in result["top_factors"]]
    return CreditResponse(
        request_id=uuid.UUID(request_id),
        decision=result["decision"],
        probability_of_default=result["probability_of_default"],
        score=result["score"],
        credit_limit=result["credit_limit"],
        interest_rate=result["interest_rate"],
        credit_type=result["credit_type"],
        offer_id=offer_id,
        model_used=result["model_used"],
        shap_explanation=result["shap_explanation"],
        top_factors=top_factors,
    )


@app.post("/credit/evaluate", response_model=CreditResponse, tags=["credit"])
def evaluate_credit(
    request: CreditRequest,
    _user: str = Depends(require_auth),
) -> CreditResponse:
    """Synchronous credit evaluation with SHAP explanation.

    Returns credit decision, calibrated probability, score (0-1000),
    credit limit, interest rate, credit type, and per-feature SHAP values.
    If approved, an offer_id is returned — send it to POST /credit/offers/{id}/accept
    to deploy the credit and trigger a mobile notification.
    """
    request_id = str(uuid.uuid4())
    logger.info("Synchronous evaluation", extra={"request_id": request_id})
    log_event(request_id, "request_received")

    result = model_store.predict(
        request.model_dump(),
        use_emotional=request.has_emotional_features,
    )
    log_event(request_id, "model_scored", {"model": result["model_used"]})

    # Create a pending credit offer if approved
    offer_id: str | None = None
    if result["decision"] == "APPROVED":
        offer_id = str(uuid.uuid4())
        save_credit_offer(
            offer_id=offer_id,
            evaluation_id=request_id,
            user_id=None,
            credit_limit=result["credit_limit"],
            interest_rate=result["interest_rate"],
            credit_type=result["credit_type"],
        )

    response = _build_response(request_id, result, offer_id=offer_id)
    save_evaluation(
        request_id=request_id,
        decision=result["decision"],
        probability=result["probability_of_default"],
        score=result["score"],
        model_used=result["model_used"],
        request_payload=request.model_dump(),
        shap_explanation=result["shap_explanation"],
    )
    log_event(request_id, "decision_made", {"decision": result["decision"]})
    return response


@app.post("/credit/evaluate/async", response_model=AsyncJobResponse, tags=["credit"])
def evaluate_credit_async(
    request: CreditRequest,
    _user: str = Depends(require_auth),
) -> AsyncJobResponse:
    """Enqueue a credit evaluation job via rq and return the job ID."""
    job_id = enqueue_evaluation(request.model_dump())
    logger.info("Async evaluation queued", extra={"job_id": job_id})
    return AsyncJobResponse(job_id=job_id, status="queued")


@app.get("/credit/evaluate/{job_id}", response_model=AsyncJobResponse, tags=["credit"])
def get_evaluation_result(
    job_id: str,
    _user: str = Depends(require_auth),
) -> AsyncJobResponse:
    """Poll the result of an async credit evaluation."""
    status, result = get_job_result(job_id)
    if status == "finished" and result is not None:
        credit_resp = _build_response(str(uuid.uuid4()), result)
        return AsyncJobResponse(job_id=job_id, status=status, result=credit_resp)
    return AsyncJobResponse(job_id=job_id, status=status)


# ---------------------------------------------------------------------------
# Credit offer acceptance (async deployment + notification)
# ---------------------------------------------------------------------------


@app.post(
    "/credit/offers/{offer_id}/accept",
    response_model=OfferAcceptResponse,
    tags=["credit"],
)
def accept_offer(
    offer_id: str,
    _user: str = Depends(require_auth),
) -> OfferAcceptResponse:
    """Accept an approved credit offer.

    Enqueues an rq background job that:
    1. Marks the offer as accepted in the database
    2. Updates the user profile with the new credit limit
    3. Creates a notification record (simulating mobile push delivery)

    This reflects CloudWalk's event-driven architecture — credit deployment
    is decoupled from scoring for fairness, auditability, and retryability.
    """
    job_id = enqueue_deployment(offer_id, user_id=None)
    logger.info(
        "Credit offer acceptance queued",
        extra={"offer_id": offer_id, "job_id": job_id},
    )
    return OfferAcceptResponse(offer_id=offer_id, job_id=job_id, status="queued")


# ---------------------------------------------------------------------------
# Real-time emotion stream ingestion
# ---------------------------------------------------------------------------


@app.post("/emotions/stream", response_model=EmotionStreamResponse, tags=["emotions"])
def ingest_emotion_event(
    event: EmotionStreamRequest,
    _user: str = Depends(require_auth),
) -> EmotionStreamResponse:
    """Ingest a real-time emotional event from the mobile app.

    Persists the event to the emotional_events table and publishes it to
    Redis Pub/Sub channel `ecs:emotion_stream`. Downstream consumers
    (risk aggregators, analytics services) can subscribe independently.

    Design note: Redis Pub/Sub was chosen for simplicity in this case study.
    In production at InfinitePay scale, this would be backed by Kafka for
    message durability, replay semantics, and consumer group management.
    """
    event_id = str(uuid.uuid4())
    payload = event.model_dump(exclude_none=True)

    save_emotional_event(event_id=event_id, user_id=event.user_id, payload=payload)

    try:
        publish_emotional_event(event_id, payload)
    except Exception:
        # Pub/Sub failure is non-fatal — event is already persisted in DB
        logger.warning("Redis Pub/Sub publish failed for event %s", event_id)

    logger.info("Emotional event ingested", extra={"event_id": event_id})
    return EmotionStreamResponse(event_id=event_id, status="received")
