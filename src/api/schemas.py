"""Pydantic schemas for the Empathic Credit System API."""

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CreditRequest(BaseModel):
    """Input for a credit evaluation request.

    Financial fields are required. Emotional fields are optional — if omitted,
    the financial-only model is used; if provided, the emotional model is used.
    """

    # Financial features (required)
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

    # Emotional features (optional — triggers emotional model when provided)
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

    @property
    def has_emotional_features(self) -> bool:
        return all(
            f is not None
            for f in [
                self.stress_level,
                self.impulsivity_score,
                self.emotional_stability,
                self.financial_stress_events_7d,
            ]
        )


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
    model_used: str
    shap_explanation: dict[str, Any]
    top_factors: list[ShapFactor]


class AsyncJobResponse(BaseModel):
    job_id: str
    status: str  # "queued" | "started" | "finished" | "failed"
    result: CreditResponse | None = None


class HealthResponse(BaseModel):
    status: str = "ok"
    model_loaded: bool
    model_version: str
