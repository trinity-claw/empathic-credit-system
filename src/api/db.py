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


class CreditEvent(Base):
    """Audit trail: lifecycle events for each evaluation request."""

    __tablename__ = "credit_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(36), index=True)
    event_type: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)


def log_event(request_id: str, event_type: str, detail: dict | None = None) -> None:
    """Record an audit event for a credit evaluation."""
    record = CreditEvent(request_id=request_id, event_type=event_type, detail=detail)
    with get_session() as session:
        session.add(record)
        session.commit()


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
