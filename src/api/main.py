"""FastAPI application entry point for the Empathic Credit System."""

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from pythonjsonlogger.json import JsonFormatter

from src.api import model_store
from src.api.auth import require_auth
from src.api.db import init_db, log_event, save_evaluation
from src.api.schemas import (
    AsyncJobResponse,
    CreditRequest,
    CreditResponse,
    HealthResponse,
    ShapFactor,
)
from src.api.settings import get_settings
from src.api.worker import enqueue_evaluation, get_job_result

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
    description="ML-based credit scoring with SHAP explanations",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse, tags=["ops"])
def health():
    """Healthcheck endpoint — no auth required."""
    return HealthResponse(
        status="ok",
        model_loaded=model_store.is_loaded(),
        model_version=model_store.model_version(),
    )


def _build_response(request_id: str, result: dict) -> CreditResponse:
    """Pure transformation: model output dict -> CreditResponse. No side effects."""
    top_factors = [ShapFactor(**f) for f in result["top_factors"]]
    return CreditResponse(
        request_id=uuid.UUID(request_id),
        decision=result["decision"],
        probability_of_default=result["probability_of_default"],
        score=result["score"],
        model_used=result["model_used"],
        shap_explanation=result["shap_explanation"],
        top_factors=top_factors,
    )


@app.post("/credit/evaluate", response_model=CreditResponse, tags=["credit"])
def evaluate_credit(
    request: CreditRequest,
    _user: str = Depends(require_auth),
) -> CreditResponse:
    """Synchronous credit evaluation with SHAP explanation."""
    request_id = str(uuid.uuid4())
    logger.info("Synchronous evaluation", extra={"request_id": request_id})
    log_event(request_id, "request_received")

    result = model_store.predict(
        request.model_dump(),
        use_emotional=request.has_emotional_features,
    )
    log_event(request_id, "model_scored", {"model": result["model_used"]})

    response = _build_response(request_id, result)
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
