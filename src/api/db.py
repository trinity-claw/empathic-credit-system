"""SQLAlchemy + SQLite database layer."""

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from src.api.settings import get_settings


def _get_engine():
    settings = get_settings()
    return create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    external_id: Mapped[str | None] = mapped_column(
        String(128), index=True, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    current_credit_limit: Mapped[float] = mapped_column(Float, default=0.0)
    credit_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_score: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    amount: Mapped[float] = mapped_column(Float)
    transaction_type: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="completed")
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class EmotionalEvent(Base):
    __tablename__ = "emotional_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), index=True, nullable=True
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    stress_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    impulsivity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    emotional_stability: Mapped[float | None] = mapped_column(Float, nullable=True)
    financial_stress_events_7d: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class CreditOffer(Base):
    __tablename__ = "credit_offers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), index=True, nullable=True
    )
    evaluation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("credit_evaluations.id"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    credit_limit: Mapped[float] = mapped_column(Float)
    interest_rate: Mapped[float] = mapped_column(Float)
    credit_type: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="pending")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), index=True, nullable=True
    )
    offer_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    notification_type: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="sent")


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
    __tablename__ = "credit_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(36), index=True)
    event_type: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)


def init_db() -> None:
    engine = _get_engine()
    Base.metadata.create_all(engine)


def get_session() -> Session:
    engine = _get_engine()
    return Session(engine)


def log_event(request_id: str, event_type: str, detail: dict | None = None) -> None:
    record = CreditEvent(request_id=request_id, event_type=event_type, detail=detail)
    with get_session() as session:
        session.add(record)
        session.commit()


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


def save_emotional_event(
    *,
    event_id: str,
    user_id: str | None,
    payload: dict,
) -> None:
    record = EmotionalEvent(
        id=event_id,
        user_id=user_id,
        stress_level=payload.get("stress_level"),
        impulsivity_score=payload.get("impulsivity_score"),
        emotional_stability=payload.get("emotional_stability"),
        financial_stress_events_7d=payload.get("financial_stress_events_7d"),
        raw_payload=payload,
    )
    with get_session() as session:
        session.add(record)
        session.commit()


def save_credit_offer(
    *,
    offer_id: str,
    evaluation_id: str,
    user_id: str | None,
    credit_limit: float,
    interest_rate: float,
    credit_type: str,
) -> None:
    record = CreditOffer(
        id=offer_id,
        user_id=user_id,
        evaluation_id=evaluation_id,
        credit_limit=credit_limit,
        interest_rate=interest_rate,
        credit_type=credit_type,
        status="pending",
    )
    with get_session() as session:
        session.add(record)
        session.commit()


def accept_credit_offer(offer_id: str) -> CreditOffer | None:
    with get_session() as session:
        offer = session.get(CreditOffer, offer_id)
        if offer is None or offer.status != "pending":
            return None
        offer.status = "accepted"
        session.commit()
        session.refresh(offer)
        return offer


def save_notification(
    *,
    notification_id: str,
    user_id: str | None,
    offer_id: str | None,
    notification_type: str,
    payload: dict | None = None,
) -> None:
    record = Notification(
        id=notification_id,
        user_id=user_id,
        offer_id=offer_id,
        notification_type=notification_type,
        payload=payload,
        status="sent",
    )
    with get_session() as session:
        session.add(record)
        session.commit()
