"""Tests for src/api/model_store.py"""

from unittest.mock import MagicMock

import numpy as np
import pytest

from src.api.model_store import (
    DEFAULT_THRESHOLD,
    FINANCIAL_FEATURES,
    SCORE_MAX,
    _compute_credit_product,
    predict,
)


def _setup_store(proba: float = 0.05, cal_proba: float = 0.05):
    """Inject mock models into the global _store."""
    mock_model = MagicMock()
    mock_model.predict_proba.return_value = np.array([[1 - proba, proba]])

    mock_calibrator = MagicMock()
    mock_calibrator.transform.return_value = np.array([cal_proba])

    mock_explainer = MagicMock()
    mock_explanation = MagicMock()
    mock_explanation.to_dict.return_value = {
        "base_value": -2.0,
        "prediction": -1.9,
        "contributions": {"age": -0.1},
        "top_factors": [
            {"feature": "age", "contribution": -0.1, "direction": "decreases_risk"}
        ],
    }
    mock_explainer.explain_one.return_value = mock_explanation

    from src.api import model_store

    model_store._store = {
        "fin_model": mock_model,
        "fin_calibrator": mock_calibrator,
        "emo_model": mock_model,
        "emo_calibrator": mock_calibrator,
        "fin_explainer": mock_explainer,
        "emo_explainer": mock_explainer,
    }


@pytest.fixture(autouse=True)
def _reset_store():
    from src.api import model_store

    original = model_store._store.copy()
    yield
    model_store._store = original


def _make_request_data():
    return {f: 0.0 for f in FINANCIAL_FEATURES}


class TestPredict:
    def test_returns_required_keys(self):
        _setup_store()
        result = predict(_make_request_data(), use_emotional=False)
        assert "decision" in result
        assert "probability_of_default" in result
        assert "score" in result
        assert "credit_limit" in result
        assert "interest_rate" in result
        assert "credit_type" in result
        assert "model_used" in result
        assert "shap_explanation" in result
        assert "top_factors" in result

    def test_approved_below_threshold(self):
        _setup_store(cal_proba=DEFAULT_THRESHOLD - 0.01)
        result = predict(_make_request_data(), use_emotional=False)
        assert result["decision"] == "APPROVED"

    def test_denied_at_or_above_threshold(self):
        _setup_store(cal_proba=DEFAULT_THRESHOLD)
        result = predict(_make_request_data(), use_emotional=False)
        assert result["decision"] == "DENIED"

    def test_score_range(self):
        _setup_store(cal_proba=0.5)
        result = predict(_make_request_data(), use_emotional=False)
        assert 0 <= result["score"] <= SCORE_MAX

    def test_score_low_risk_near_max(self):
        _setup_store(cal_proba=0.01)
        result = predict(_make_request_data(), use_emotional=False)
        assert result["score"] >= 900

    def test_score_high_risk_near_zero(self):
        _setup_store(cal_proba=0.99)
        result = predict(_make_request_data(), use_emotional=False)
        assert result["score"] <= 100

    def test_emotional_model_name(self):
        _setup_store()
        result = predict(_make_request_data(), use_emotional=True)
        assert "emotional" in result["model_used"]

    def test_financial_model_name(self):
        _setup_store()
        result = predict(_make_request_data(), use_emotional=False)
        assert "financial" in result["model_used"]


class TestCreditProduct:
    def test_denied_has_zero_limit(self):
        product = _compute_credit_product(score=400, decision="DENIED")
        assert product["credit_limit"] == 0.0
        assert product["interest_rate"] is None
        assert product["credit_type"] == "denied"

    def test_high_score_long_term(self):
        product = _compute_credit_product(score=900, decision="APPROVED")
        assert product["credit_type"] == "long_term"
        assert product["credit_limit"] > 0
        assert product["interest_rate"] is not None

    def test_low_score_short_term(self):
        product = _compute_credit_product(score=300, decision="APPROVED")
        assert product["credit_type"] == "short_term"

    def test_interest_rate_decreases_with_score(self):
        high = _compute_credit_product(score=900, decision="APPROVED")
        low = _compute_credit_product(score=300, decision="APPROVED")
        assert high["interest_rate"] < low["interest_rate"]

    def test_credit_limit_increases_with_score(self):
        high = _compute_credit_product(score=900, decision="APPROVED")
        low = _compute_credit_product(score=300, decision="APPROVED")
        assert high["credit_limit"] > low["credit_limit"]
