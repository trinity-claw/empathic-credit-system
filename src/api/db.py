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
    func,
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
    current_interest_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    credit_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_score: Mapped[int | None] = mapped_column(Integer, nullable=True)


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
        try:
            offer = session.get(CreditOffer, offer_id)
            if offer is None or offer.status != "pending":
                return None
            offer.status = "accepted"
            session.commit()
            session.refresh(offer)
            return offer
        except Exception:
            session.rollback()
            raise


def get_credit_offer(offer_id: str) -> CreditOffer | None:
    with get_session() as session:
        return session.get(CreditOffer, offer_id)


def notification_exists_for_offer(offer_id: str, notification_type: str) -> bool:
    with get_session() as session:
        q = session.query(func.count(Notification.id)).filter(
            Notification.offer_id == offer_id,
            Notification.notification_type == notification_type,
        )
        return (q.scalar() or 0) > 0


def apply_credit_to_user(
    *,
    user_id: str,
    credit_limit: float,
    interest_rate: float,
    credit_type: str,
) -> None:
    """Idempotently apply approved credit terms to a user profile.

    Creates the user row if it does not yet exist (offers may be issued
    for users not previously materialized in the local DB).
    """
    with get_session() as session:
        try:
            user = session.get(User, user_id)
            if user is None:
                user = User(id=user_id)
                session.add(user)
            user.current_credit_limit = credit_limit
            user.current_interest_rate = interest_rate
            user.credit_type = credit_type
            session.commit()
        except Exception:
            session.rollback()
            raise


def update_notification_status(notification_id: str, status: str) -> None:
    with get_session() as session:
        try:
            record = session.get(Notification, notification_id)
            if record is None:
                return
            record.status = status
            session.commit()
        except Exception:
            session.rollback()
            raise


def list_evaluations(*, limit: int = 20, offset: int = 0) -> tuple[list[dict], int]:
    with get_session() as session:
        total = session.query(func.count(CreditEvaluation.id)).scalar() or 0
        rows = (
            session.query(CreditEvaluation)
            .order_by(CreditEvaluation.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        items = [
            {
                "request_id": row.id,
                "decision": row.decision,
                "score": row.score,
                "probability_of_default": row.probability_of_default,
                "model_used": row.model_used,
                "created_at": row.created_at.isoformat(),
                "request_payload": row.request_payload,
                "shap_explanation": row.shap_explanation,
            }
            for row in rows
        ]
        return items, total


def get_evaluation_stats() -> dict:
    with get_session() as session:
        total = session.query(func.count(CreditEvaluation.id)).scalar() or 0
        approved = (
            session.query(func.count(CreditEvaluation.id))
            .filter(CreditEvaluation.decision == "APPROVED")
            .scalar()
            or 0
        )
        avg_score_raw = session.query(func.avg(CreditEvaluation.score)).scalar()
        avg_score = float(avg_score_raw) if avg_score_raw is not None else 0.0

        def _count_score_range(lo: int | None, hi: int | None) -> int:
            q = session.query(func.count(CreditEvaluation.id))
            if lo is not None:
                q = q.filter(CreditEvaluation.score >= lo)
            if hi is not None:
                q = q.filter(CreditEvaluation.score < hi)
            return q.scalar() or 0

        pending_offers = (
            session.query(func.count(CreditOffer.id))
            .filter(CreditOffer.status == "pending")
            .scalar()
            or 0
        )

        return {
            "total_evaluations": total,
            "approval_rate": approved / total if total > 0 else 0.0,
            "avg_score": avg_score,
            "pending_offers": pending_offers,
            "tier_distribution": {
                "850+": _count_score_range(850, None),
                "700-849": _count_score_range(700, 850),
                "550-699": _count_score_range(550, 700),
                "<550": _count_score_range(None, 550),
            },
        }


def list_offers(*, limit: int = 20, offset: int = 0) -> tuple[list[dict], int]:
    with get_session() as session:
        total = session.query(func.count(CreditOffer.id)).scalar() or 0
        rows = (
            session.query(CreditOffer)
            .order_by(CreditOffer.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        items = [
            {
                "offer_id": row.id,
                "evaluation_id": row.evaluation_id,
                "credit_limit": row.credit_limit,
                "interest_rate": row.interest_rate,
                "credit_type": row.credit_type,
                "status": row.status,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]
        return items, total


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
