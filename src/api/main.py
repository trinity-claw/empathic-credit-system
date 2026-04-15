"""FastAPI application entry point for the Empathic Credit System."""

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pythonjsonlogger.json import JsonFormatter

from src.api import model_store
from src.api.auth import require_auth
from src.api.db import (
    get_evaluation_stats,
    init_db,
    list_evaluations,
    list_offers,
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
    EvaluationListResponse,
    EvaluationStats,
    EvaluationSummary,
    HealthResponse,
    OfferAcceptResponse,
    OfferListResponse,
    OfferSummary,
    ShapFactor,
)
from src.api.settings import get_settings
from src.api.worker import (
    enqueue_deployment,
    enqueue_evaluation,
    get_job_result,
    publish_emotional_event,
)

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next) -> Response:
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


def _health_response() -> HealthResponse:
    return HealthResponse(
        status="ok",
        model_loaded=model_store.is_loaded(),
        model_version=model_store.model_version(),
    )


@app.get("/health", response_model=HealthResponse, tags=["ops"])
def health():
    return _health_response()


@app.get("/healthz", response_model=HealthResponse, tags=["ops"])
def healthz():
    """Alias for probe compatibility (challenge mentions /healthz)."""
    return _health_response()


def _build_response(
    request_id: str, result: dict, offer_id: str | None = None
) -> CreditResponse:
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
    request_id = str(uuid.uuid4())
    logger.info("Synchronous evaluation", extra={"request_id": request_id})
    log_event(request_id, "request_received")

    result = model_store.predict(
        request.model_dump(),
        use_emotional=request.has_emotional_features,
    )
    log_event(request_id, "model_scored", {"model": result["model_used"]})

    save_evaluation(
        request_id=request_id,
        decision=result["decision"],
        probability=result["probability_of_default"],
        score=result["score"],
        model_used=result["model_used"],
        request_payload=request.model_dump(),
        shap_explanation=result["shap_explanation"],
    )

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
    log_event(request_id, "decision_made", {"decision": result["decision"]})
    return response


@app.post("/credit/evaluate/async", response_model=AsyncJobResponse, tags=["credit"])
def evaluate_credit_async(
    request: CreditRequest,
    _user: str = Depends(require_auth),
) -> AsyncJobResponse:
    job_id = enqueue_evaluation(request.model_dump())
    logger.info("Async evaluation queued", extra={"job_id": job_id})
    return AsyncJobResponse(job_id=job_id, status="queued")


@app.get("/credit/evaluate/{job_id}", response_model=AsyncJobResponse, tags=["credit"])
def get_evaluation_result(
    job_id: str,
    _user: str = Depends(require_auth),
) -> AsyncJobResponse:
    status, result = get_job_result(job_id)
    if status == "finished" and result is not None:
        credit_resp = _build_response(str(uuid.uuid4()), result)
        return AsyncJobResponse(job_id=job_id, status=status, result=credit_resp)
    return AsyncJobResponse(job_id=job_id, status=status)


@app.post(
    "/credit/offers/{offer_id}/accept",
    response_model=OfferAcceptResponse,
    tags=["credit"],
)
def accept_offer(
    offer_id: str,
    _user: str = Depends(require_auth),
) -> OfferAcceptResponse:
    """Accept an approved credit offer and enqueue async deployment."""
    job_id = enqueue_deployment(offer_id, user_id=None)
    logger.info(
        "Credit offer acceptance queued",
        extra={"offer_id": offer_id, "job_id": job_id},
    )
    return OfferAcceptResponse(offer_id=offer_id, job_id=job_id, status="queued")


@app.get("/credit/evaluations/stats", response_model=EvaluationStats, tags=["credit"])
def evaluation_stats(_user: str = Depends(require_auth)) -> EvaluationStats:
    return EvaluationStats(**get_evaluation_stats())


@app.get("/credit/evaluations", response_model=EvaluationListResponse, tags=["credit"])
def list_credit_evaluations(
    limit: int = 20,
    offset: int = 0,
    _user: str = Depends(require_auth),
) -> EvaluationListResponse:
    items, total = list_evaluations(limit=limit, offset=offset)
    summaries = [EvaluationSummary(**item) for item in items]
    return EvaluationListResponse(items=summaries, total=total)


@app.get("/credit/offers", response_model=OfferListResponse, tags=["credit"])
def list_credit_offers(
    limit: int = 20,
    offset: int = 0,
    _user: str = Depends(require_auth),
) -> OfferListResponse:
    items, total = list_offers(limit=limit, offset=offset)
    summaries = [OfferSummary(**item) for item in items]
    return OfferListResponse(items=summaries, total=total)


@app.post("/emotions/stream", response_model=EmotionStreamResponse, tags=["emotions"])
def ingest_emotion_event(
    event: EmotionStreamRequest,
    _user: str = Depends(require_auth),
) -> EmotionStreamResponse:
    """Ingest a real-time emotional event. Persists to DB and publishes to Redis Pub/Sub."""
    event_id = str(uuid.uuid4())
    payload = event.model_dump(exclude_none=True)

    save_emotional_event(event_id=event_id, user_id=event.user_id, payload=payload)

    try:
        publish_emotional_event(event_id, payload)
    except Exception:
        logger.warning("Redis Pub/Sub publish failed for event %s", event_id)

    logger.info("Emotional event ingested", extra={"event_id": event_id})
    return EmotionStreamResponse(event_id=event_id, status="received")
