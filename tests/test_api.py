"""Tests for the FastAPI application."""

import base64
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

_MOCK_RESULT = {
    "decision": "APPROVED",
    "probability_of_default": 0.05,
    "score": 950,
    "credit_limit": 50000.0,
    "interest_rate": 0.015,
    "credit_type": "long_term",
    "model_used": "xgboost_financial_calibrated",
    "shap_explanation": {
        "base_value": 0.01,
        "prediction": 0.05,
        "contributions": {"age": -0.02, "past_due_90": 0.01},
        "top_factors": [
            {"feature": "age", "contribution": -0.02, "direction": "decreases_risk"},
            {
                "feature": "past_due_90",
                "contribution": 0.01,
                "direction": "increases_risk",
            },
        ],
    },
    "top_factors": [
        {"feature": "age", "contribution": -0.02, "direction": "decreases_risk"},
        {"feature": "past_due_90", "contribution": 0.01, "direction": "increases_risk"},
    ],
}


@pytest.fixture(scope="module")
def client():
    with (
        patch("src.api.model_store.load_models"),
        patch("src.api.model_store.is_loaded", return_value=True),
        patch("src.api.model_store.predict", return_value=_MOCK_RESULT),
        patch("src.api.db.init_db"),
        patch("src.api.db.save_evaluation"),
        patch("src.api.db.save_credit_offer"),
        patch("src.api.db.save_emotional_event"),
        patch("src.api.db.log_event"),
        patch("src.api.worker.publish_emotional_event"),
    ):
        from src.api.main import app

        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


def _auth_header(username: str = "admin", password: str = "changeme") -> dict:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


class TestHealth:
    def test_health_no_auth_required(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["model_loaded"] is True

    def test_health_returns_version(self, client):
        resp = client.get("/health")
        assert "model_version" in resp.json()

    def test_health_returns_x_request_id(self, client):
        resp = client.get("/health")
        assert "x-request-id" in resp.headers


class TestAuth:
    def test_missing_auth_returns_401(self, client):
        resp = client.post("/credit/evaluate", json={})
        assert resp.status_code == 401

    def test_wrong_password_returns_401(self, client):
        headers = _auth_header(password="wrong")
        resp = client.post("/credit/evaluate", json={}, headers=headers)
        assert resp.status_code == 401


class TestEvaluate:
    _VALID_PAYLOAD = {
        "revolving_utilization": 0.3,
        "age": 45,
        "past_due_30_59": 0.0,
        "debt_ratio": 0.2,
        "monthly_income": 5000.0,
        "open_credit_lines": 4,
        "past_due_90": 0.0,
        "real_estate_loans": 1,
        "past_due_60_89": 0.0,
        "dependents": 2.0,
        "had_past_due_sentinel": 0,
    }

    def test_valid_request_returns_200(self, client):
        resp = client.post(
            "/credit/evaluate",
            json=self._VALID_PAYLOAD,
            headers=_auth_header(),
        )
        assert resp.status_code == 200

    def test_response_has_required_fields(self, client):
        resp = client.post(
            "/credit/evaluate",
            json=self._VALID_PAYLOAD,
            headers=_auth_header(),
        )
        body = resp.json()
        assert "decision" in body
        assert "probability_of_default" in body
        assert "score" in body
        assert "credit_limit" in body
        assert "interest_rate" in body
        assert "credit_type" in body
        assert "shap_explanation" in body
        assert "top_factors" in body

    def test_response_has_offer_id_when_approved(self, client):
        resp = client.post(
            "/credit/evaluate",
            json=self._VALID_PAYLOAD,
            headers=_auth_header(),
        )
        body = resp.json()
        assert body["decision"] == "APPROVED"
        assert body["offer_id"] is not None

    def test_decision_is_valid_value(self, client):
        resp = client.post(
            "/credit/evaluate",
            json=self._VALID_PAYLOAD,
            headers=_auth_header(),
        )
        assert resp.json()["decision"] in ("APPROVED", "DENIED")

    def test_missing_required_field_returns_422(self, client):
        payload = {k: v for k, v in self._VALID_PAYLOAD.items() if k != "age"}
        resp = client.post(
            "/credit/evaluate",
            json=payload,
            headers=_auth_header(),
        )
        assert resp.status_code == 422


class TestAsyncEvaluate:
    _VALID_PAYLOAD = TestEvaluate._VALID_PAYLOAD

    def test_async_returns_job_id(self, client):
        with patch("src.api.main.enqueue_evaluation", return_value="job-abc-123"):
            resp = client.post(
                "/credit/evaluate/async",
                json=self._VALID_PAYLOAD,
                headers=_auth_header(),
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["job_id"] == "job-abc-123"
        assert body["status"] == "queued"

    def test_get_finished_job(self, client):
        with patch(
            "src.api.main.get_job_result",
            return_value=("finished", _MOCK_RESULT),
        ):
            resp = client.get(
                "/credit/evaluate/some-job-id",
                headers=_auth_header(),
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "finished"
        assert body["result"] is not None
        assert body["result"]["decision"] == "APPROVED"

    def test_get_pending_job(self, client):
        with patch(
            "src.api.main.get_job_result",
            return_value=("started", None),
        ):
            resp = client.get(
                "/credit/evaluate/some-job-id",
                headers=_auth_header(),
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "started"
        assert body["result"] is None

    def test_get_not_found_job(self, client):
        with patch(
            "src.api.main.get_job_result",
            return_value=("not_found", None),
        ):
            resp = client.get(
                "/credit/evaluate/nonexistent",
                headers=_auth_header(),
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "not_found"


class TestOfferAcceptance:
    def test_accept_offer_queues_job(self, client):
        with patch("src.api.main.enqueue_deployment", return_value="deploy-job-1"):
            resp = client.post(
                "/credit/offers/offer-abc-123/accept",
                headers=_auth_header(),
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["offer_id"] == "offer-abc-123"
        assert body["job_id"] == "deploy-job-1"
        assert body["status"] == "queued"

    def test_accept_offer_requires_auth(self, client):
        resp = client.post("/credit/offers/some-id/accept")
        assert resp.status_code == 401


class TestEmotionStream:
    _VALID_EVENT = {
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "stress_level": 0.7,
        "impulsivity_score": 0.4,
        "emotional_stability": 0.5,
        "financial_stress_events_7d": 2,
    }

    def test_stream_event_returns_200(self, client):
        resp = client.post(
            "/emotions/stream",
            json=self._VALID_EVENT,
            headers=_auth_header(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "received"
        assert "event_id" in body

    def test_stream_event_requires_auth(self, client):
        resp = client.post("/emotions/stream", json=self._VALID_EVENT)
        assert resp.status_code == 401

    def test_stream_event_accepts_partial_payload(self, client):
        resp = client.post(
            "/emotions/stream",
            json={"stress_level": 0.5},
            headers=_auth_header(),
        )
        assert resp.status_code == 200
