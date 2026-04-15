"""SQLAlchemy + SQLite database layer."""

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from src.api.settings import get_settings


def _get_engine():
    settings = get_settings()
    return create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
    )


class Base(DeclarativeBase):
    pass


class CreditEvaluation(Base):
    __tablename__ = "credit_evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    decision: Mapped[str] = mapped_column(String(10))
    probability_of_default: Mapped[float] = mapped_column(Float)
    score: Mapped[int]
    model_used: Mapped[str] = mapped_column(String(64))
    request_payload: Mapped[dict] = mapped_column(JSON)
    shap_explanation: Mapped[dict] = mapped_column(JSON)


def init_db() -> None:
    """Create tables if they don't exist."""
    engine = _get_engine()
    Base.metadata.create_all(engine)


def get_session() -> Session:
    engine = _get_engine()
    return Session(engine)


def save_evaluation(
    *,
    request_id: str,
    decision: str,
    probability: float,
    score: int,
    model_used: str,
    request_payload: dict,
    shap_explanation: dict,
) -> None:
    """Persist a credit evaluation record."""
    record = CreditEvaluation(
        id=request_id,
        decision=decision,
        probability_of_default=probability,
        score=score,
        model_used=model_used,
        request_payload=request_payload,
        shap_explanation=shap_explanation,
    )
    with get_session() as session:
        session.add(record)
        session.commit()
