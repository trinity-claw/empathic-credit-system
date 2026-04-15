"""FastAPI application entry point for the Empathic Credit System."""

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from pythonjsonlogger.json import JsonFormatter

from src.api import model_store
from src.api.auth import require_auth
from src.api.db import init_db, save_evaluation
from src.api.schemas import (
    AsyncJobResponse,
    CreditRequest,
    CreditResponse,
    HealthResponse,
    ShapFactor,
)
from src.api.settings import get_settings
from src.api.worker import enqueue_evaluation, get_job_result

# Structured JSON logging
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler])
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


def _build_response(
    request_id: str, result: dict, request: CreditRequest
) -> CreditResponse:
    top_factors = [ShapFactor(**f) for f in result["top_factors"]]
    resp = CreditResponse(
        request_id=uuid.UUID(request_id),
        decision=result["decision"],
        probability_of_default=result["probability_of_default"],
        score=result["score"],
        model_used=result["model_used"],
        shap_explanation=result["shap_explanation"],
        top_factors=top_factors,
    )
    save_evaluation(
        request_id=request_id,
        decision=result["decision"],
        probability=result["probability_of_default"],
        score=result["score"],
        model_used=result["model_used"],
        request_payload=request.model_dump(),
        shap_explanation=result["shap_explanation"],
    )
    return resp


@app.post("/credit/evaluate", response_model=CreditResponse, tags=["credit"])
def evaluate_credit(
    request: CreditRequest,
    _user: str = Depends(require_auth),
) -> CreditResponse:
    """Synchronous credit evaluation with SHAP explanation."""
    request_id = str(uuid.uuid4())
    logger.info("Synchronous evaluation", extra={"request_id": request_id})

    result = model_store.predict(
        request.model_dump(),
        use_emotional=request.has_emotional_features,
    )
    return _build_response(request_id, result, request)


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
        top_factors = [ShapFactor(**f) for f in result["top_factors"]]
        credit_resp = CreditResponse(
            request_id=uuid.uuid4(),
            **{k: v for k, v in result.items() if k not in ("top_factors",)},
            top_factors=top_factors,
        )
        return AsyncJobResponse(job_id=job_id, status=status, result=credit_resp)
    return AsyncJobResponse(job_id=job_id, status=status)
