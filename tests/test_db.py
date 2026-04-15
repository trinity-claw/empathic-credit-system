"""Tests for src/api/db.py"""

from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from src.api.db import (
    Base,
    CreditEvaluation,
    CreditEvent,
    CreditOffer,
    EmotionalEvent,
    Notification,
    accept_credit_offer,
    log_event,
    save_credit_offer,
    save_emotional_event,
    save_evaluation,
    save_notification,
)

_EVALUATION_ID = "eval-000"


@pytest.fixture()
def _use_memory_db():
    """Override the engine to use an in-memory SQLite database."""
    engine = create_engine("sqlite:///:memory:")

    with patch("src.api.db._get_engine", return_value=engine):
        Base.metadata.create_all(engine)
        yield engine


class TestInitDb:
    def test_creates_all_tables(self, _use_memory_db):
        engine = _use_memory_db
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            tables = [row[0] for row in result]
        for expected in (
            "users",
            "transactions",
            "emotional_events",
            "credit_offers",
            "notifications",
            "credit_evaluations",
            "credit_events",
        ):
            assert expected in tables, f"Table '{expected}' not found"


class TestSaveEvaluation:
    def test_persists_and_reads_back(self, _use_memory_db):
        engine = _use_memory_db
        save_evaluation(
            request_id=_EVALUATION_ID,
            decision="APPROVED",
            probability=0.05,
            score=950,
            model_used="xgboost_financial_calibrated",
            request_payload={"age": 30, "debt_ratio": 0.2},
            shap_explanation={"base_value": -2.0, "contributions": {"age": -0.1}},
        )
        with Session(engine) as session:
            record = session.get(CreditEvaluation, _EVALUATION_ID)

        assert record is not None
        assert record.decision == "APPROVED"
        assert record.probability_of_default == 0.05
        assert record.score == 950
        assert record.model_used == "xgboost_financial_calibrated"

    def test_payload_stored_as_dict(self, _use_memory_db):
        engine = _use_memory_db
        payload = {"age": 45, "monthly_income": 5000.0}
        save_evaluation(
            request_id="test-456",
            decision="DENIED",
            probability=0.30,
            score=700,
            model_used="xgboost_emotional_calibrated",
            request_payload=payload,
            shap_explanation={},
        )
        with Session(engine) as session:
            record = session.get(CreditEvaluation, "test-456")

        assert isinstance(record.request_payload, dict)
        assert record.request_payload["age"] == 45


class TestCreditEvent:
    def test_creates_events_table(self, _use_memory_db):
        engine = _use_memory_db
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            tables = [row[0] for row in result]
        assert "credit_events" in tables

    def test_log_event_persists(self, _use_memory_db):
        engine = _use_memory_db
        log_event("req-001", "request_received")
        log_event("req-001", "model_scored", {"model": "xgboost_financial"})

        with Session(engine) as session:
            events = (
                session.query(CreditEvent)
                .filter_by(request_id="req-001")
                .order_by(CreditEvent.id)
                .all()
            )

        assert len(events) == 2
        assert events[0].event_type == "request_received"
        assert events[1].event_type == "model_scored"
        assert events[1].detail["model"] == "xgboost_financial"


class TestEmotionalEvent:
    def test_save_emotional_event(self, _use_memory_db):
        engine = _use_memory_db
        payload = {
            "stress_level": 0.7,
            "impulsivity_score": 0.4,
            "emotional_stability": 0.6,
            "financial_stress_events_7d": 2,
        }
        save_emotional_event(event_id="ev-001", user_id=None, payload=payload)

        with Session(engine) as session:
            record = session.get(EmotionalEvent, "ev-001")

        assert record is not None
        assert record.stress_level == 0.7
        assert record.impulsivity_score == 0.4

    def test_raw_payload_stored(self, _use_memory_db):
        payload = {"stress_level": 0.5, "custom_field": "vendor_data"}
        save_emotional_event(event_id="ev-002", user_id=None, payload=payload)

        with Session(_use_memory_db) as session:
            record = session.get(EmotionalEvent, "ev-002")

        assert isinstance(record.raw_payload, dict)
        assert record.raw_payload["custom_field"] == "vendor_data"


class TestCreditOffer:
    def _create_eval(self, engine):
        save_evaluation(
            request_id=_EVALUATION_ID,
            decision="APPROVED",
            probability=0.05,
            score=950,
            model_used="xgboost_financial_calibrated",
            request_payload={},
            shap_explanation={},
        )

    def test_save_and_accept_offer(self, _use_memory_db):
        engine = _use_memory_db
        self._create_eval(engine)

        save_credit_offer(
            offer_id="offer-001",
            evaluation_id=_EVALUATION_ID,
            user_id=None,
            credit_limit=50000.0,
            interest_rate=0.015,
            credit_type="long_term",
        )

        with Session(engine) as session:
            offer = session.get(CreditOffer, "offer-001")

        assert offer is not None
        assert offer.status == "pending"
        assert offer.credit_limit == 50000.0

    def test_accept_offer_changes_status(self, _use_memory_db):
        engine = _use_memory_db
        self._create_eval(engine)

        save_credit_offer(
            offer_id="offer-002",
            evaluation_id=_EVALUATION_ID,
            user_id=None,
            credit_limit=20000.0,
            interest_rate=0.025,
            credit_type="long_term",
        )

        result = accept_credit_offer("offer-002")
        assert result is not None
        assert result.status == "accepted"

    def test_accept_nonexistent_offer_returns_none(self, _use_memory_db):
        result = accept_credit_offer("does-not-exist")
        assert result is None

    def test_accept_already_accepted_offer_returns_none(self, _use_memory_db):
        engine = _use_memory_db
        self._create_eval(engine)

        save_credit_offer(
            offer_id="offer-003",
            evaluation_id=_EVALUATION_ID,
            user_id=None,
            credit_limit=8000.0,
            interest_rate=0.040,
            credit_type="short_term",
        )
        accept_credit_offer("offer-003")
        result = accept_credit_offer("offer-003")
        assert result is None


class TestNotification:
    def test_save_notification(self, _use_memory_db):
        save_notification(
            notification_id="notif-001",
            user_id=None,
            offer_id="offer-001",
            notification_type="credit_deployed",
            payload={"credit_limit": 50000.0},
        )

        with Session(_use_memory_db) as session:
            record = session.get(Notification, "notif-001")

        assert record is not None
        assert record.notification_type == "credit_deployed"
        assert record.status == "sent"
        assert record.payload["credit_limit"] == 50000.0
