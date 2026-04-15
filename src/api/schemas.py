"""Pydantic schemas for the Empathic Credit System API."""

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

EMOTIONAL_FIELD_NAMES = (
    "stress_level",
    "impulsivity_score",
    "emotional_stability",
    "financial_stress_events_7d",
)


def has_emotional_data(data: dict) -> bool:
    return all(data.get(f) is not None for f in EMOTIONAL_FIELD_NAMES)


class CreditRequest(BaseModel):
    """Input for a credit evaluation request.

    Financial fields are required. Emotional fields are optional — when all
    four are provided, the emotional model variant is used instead.
    """

    revolving_utilization: float = Field(
        ..., ge=0, description="Revolving utilization of unsecured lines"
    )
    age: int = Field(..., ge=18, le=120, description="Age of the borrower")
    past_due_30_59: float = Field(
        default=0.0, ge=0, description="Times 30-59 days past due"
    )
    debt_ratio: float = Field(
        ..., ge=0, description="Monthly debt payments / monthly gross income"
    )
    monthly_income: float | None = Field(
        default=None, ge=0, description="Monthly income (nullable)"
    )
    open_credit_lines: int = Field(
        default=0, ge=0, description="Number of open credit lines and loans"
    )
    past_due_90: float = Field(default=0.0, ge=0, description="Times 90+ days late")
    real_estate_loans: int = Field(
        default=0, ge=0, description="Number of real estate loans"
    )
    past_due_60_89: float = Field(
        default=0.0, ge=0, description="Times 60-89 days past due"
    )
    dependents: float | None = Field(
        default=None, ge=0, description="Number of dependents (nullable)"
    )
    had_past_due_sentinel: int = Field(
        default=0, ge=0, le=1, description="Flag: sentinel value in past due fields"
    )

    stress_level: float | None = Field(
        default=None, ge=0, le=1, description="Stress level [0,1]"
    )
    impulsivity_score: float | None = Field(
        default=None, ge=0, le=1, description="Impulsivity score [0,1]"
    )
    emotional_stability: float | None = Field(
        default=None, ge=0, le=1, description="Emotional stability [0,1]"
    )
    financial_stress_events_7d: int | None = Field(
        default=None, ge=0, le=20, description="Stress events last 7 days"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "revolving_utilization": 0.30,
                    "age": 45,
                    "past_due_30_59": 0.0,
                    "debt_ratio": 0.20,
                    "monthly_income": 5000.0,
                    "open_credit_lines": 4,
                    "past_due_90": 0.0,
                    "real_estate_loans": 1,
                    "past_due_60_89": 0.0,
                    "dependents": 2.0,
                    "had_past_due_sentinel": 0,
                }
            ]
        }
    }

    @property
    def has_emotional_features(self) -> bool:
        return has_emotional_data(self.model_dump())


class ShapFactor(BaseModel):
    feature: str
    contribution: float
    direction: str  # "increases_risk" | "decreases_risk"


class CreditResponse(BaseModel):
    """Output of a credit evaluation."""

    request_id: UUID = Field(default_factory=uuid4)
    decision: str  # "APPROVED" | "DENIED"
    probability_of_default: float = Field(..., ge=0, le=1)
    score: int = Field(..., ge=0, le=1000, description="Score (1000 = lowest risk)")
    credit_limit: float = Field(
        ..., ge=0, description="Approved credit limit in BRL (0 if denied)"
    )
    interest_rate: float | None = Field(
        None, ge=0, description="Monthly interest rate (None if denied)"
    )
    credit_type: str | None = Field(None, description="short_term | long_term | denied")
    offer_id: str | None = Field(
        None, description="Offer ID — send to /credit/offers/{id}/accept"
    )
    model_used: str
    shap_explanation: dict[str, Any]
    top_factors: list[ShapFactor]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                    "decision": "APPROVED",
                    "probability_of_default": 0.042,
                    "score": 958,
                    "credit_limit": 50000.0,
                    "interest_rate": 0.015,
                    "credit_type": "long_term",
                    "offer_id": "f1e2d3c4-b5a6-7890-abcd-123456789abc",
                    "model_used": "xgboost_financial_calibrated",
                    "shap_explanation": {
                        "base_value": -2.63,
                        "prediction": -3.13,
                        "contributions": {"age": -0.28, "past_due_90": 0.01},
                    },
                    "top_factors": [
                        {
                            "feature": "age",
                            "contribution": -0.28,
                            "direction": "decreases_risk",
                        }
                    ],
                }
            ]
        }
    }


class AsyncJobResponse(BaseModel):
    job_id: str
    status: str  # "queued" | "started" | "finished" | "failed"
    result: CreditResponse | None = None


class HealthResponse(BaseModel):
    status: str = "ok"
    model_loaded: bool
    model_version: str


class EmotionStreamRequest(BaseModel):
    """Emotional event payload from the mobile app sensor. All fields optional."""

    user_id: str | None = Field(None, description="Pseudonymised user UUID")
    stress_level: float | None = Field(None, ge=0, le=1)
    impulsivity_score: float | None = Field(None, ge=0, le=1)
    emotional_stability: float | None = Field(None, ge=0, le=1)
    financial_stress_events_7d: int | None = Field(None, ge=0, le=20)
    captured_at: str | None = Field(None, description="ISO 8601 timestamp from device")
    raw_sensor_data: dict | None = Field(
        None, description="Vendor-specific raw sensor payload"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "user_id": "550e8400-e29b-41d4-a716-446655440000",
                    "stress_level": 0.72,
                    "impulsivity_score": 0.45,
                    "emotional_stability": 0.38,
                    "financial_stress_events_7d": 3,
                    "captured_at": "2026-04-15T10:30:00Z",
                }
            ]
        }
    }


class EmotionStreamResponse(BaseModel):
    event_id: str
    status: str = "received"


class OfferAcceptResponse(BaseModel):
    offer_id: str
    job_id: str
    status: str = "queued"


class EvaluationSummary(BaseModel):
    request_id: str
    decision: str
    score: int
    probability_of_default: float
    model_used: str
    created_at: str
    request_payload: dict[str, Any]
    shap_explanation: dict[str, Any]


class EvaluationListResponse(BaseModel):
    items: list[EvaluationSummary]
    total: int


class EvaluationStats(BaseModel):
    total_evaluations: int
    approval_rate: float
    avg_score: float
    pending_offers: int
    tier_distribution: dict[str, int]


class OfferSummary(BaseModel):
    offer_id: str
    evaluation_id: str
    credit_limit: float
    interest_rate: float
    credit_type: str
    status: str
    created_at: str


class OfferListResponse(BaseModel):
    items: list[OfferSummary]
    total: int
