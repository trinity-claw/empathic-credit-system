"""Tests for src/api/db.py"""

from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from src.api.db import Base, CreditEvaluation, save_evaluation


@pytest.fixture()
def _use_memory_db():
    """Override the engine to use an in-memory SQLite database."""
    engine = create_engine("sqlite:///:memory:")

    with patch("src.api.db._get_engine", return_value=engine):
        Base.metadata.create_all(engine)
        yield engine


class TestInitDb:
    def test_creates_table(self, _use_memory_db):
        engine = _use_memory_db
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            tables = [row[0] for row in result]
        assert "credit_evaluations" in tables


class TestSaveEvaluation:
    def test_persists_and_reads_back(self, _use_memory_db):
        engine = _use_memory_db
        save_evaluation(
            request_id="test-123",
            decision="APPROVED",
            probability=0.05,
            score=950,
            model_used="xgboost_financial_calibrated",
            request_payload={"age": 30, "debt_ratio": 0.2},
            shap_explanation={"base_value": -2.0, "contributions": {"age": -0.1}},
        )
        with Session(engine) as session:
            record = session.get(CreditEvaluation, "test-123")

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
