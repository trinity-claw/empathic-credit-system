import json
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from src.api.db import (
    Notification,
    User,
    get_credit_offer,
    save_credit_offer,
    save_evaluation,
)
from src.api.worker import _CREDIT_EVENT_CHANNEL, _deploy_credit_offer

_USER_ID = "user-worker-1"
_EVAL_ID = "eval-worker-1"
_OFFER_ID = "offer-worker-1"


@pytest.fixture(autouse=True)
def _notification_no_webhook():
    """Avoid real HTTP when NOTIFICATION_WEBHOOK_URL is set in developer .env."""
    mock_settings = MagicMock()
    mock_settings.notification_webhook_url = None
    with patch("src.api.notifications.get_settings", return_value=mock_settings):
        yield


@pytest.fixture()
def _redis_spy():
    m = MagicMock()
    with patch("src.api.worker.Redis") as MockRedis:
        MockRedis.from_url.return_value = m
        yield m


@pytest.fixture()
def mem_db(db_engine, _redis_spy):
    return db_engine


def _seed_offer(engine):
    save_evaluation(
        request_id=_EVAL_ID,
        decision="APPROVED",
        probability=0.05,
        score=900,
        model_used="xgboost_financial_calibrated",
        request_payload={},
        shap_explanation={},
    )
    save_credit_offer(
        offer_id=_OFFER_ID,
        evaluation_id=_EVAL_ID,
        user_id=_USER_ID,
        credit_limit=25000.0,
        interest_rate=0.021,
        credit_type="long_term",
    )


class TestDeployCreditOffer:
    def test_updates_user_profile_and_delivers_notification(self, mem_db, _redis_spy):
        _seed_offer(mem_db)

        result = _deploy_credit_offer(_OFFER_ID, _USER_ID)

        assert result["status"] == "deployed"
        assert result["offer_id"] == _OFFER_ID

        with Session(mem_db) as session:
            user = session.get(User, _USER_ID)
            assert user is not None
            assert user.current_credit_limit == 25000.0
            assert user.current_interest_rate == 0.021
            assert user.credit_type == "long_term"

            notifs = (
                session.query(Notification)
                .filter(Notification.offer_id == _OFFER_ID)
                .all()
            )
            assert len(notifs) == 1
            assert notifs[0].status == "delivered"
            assert notifs[0].notification_type == "credit_deployed"

        _redis_spy.publish.assert_called_once()
        channel, raw_payload = _redis_spy.publish.call_args[0]
        assert channel == _CREDIT_EVENT_CHANNEL
        event = json.loads(raw_payload)
        assert event["event_type"] == "credit.accepted"
        assert event["offer_id"] == _OFFER_ID
        assert event["credit_limit"] == 25000.0
        assert event["credit_type"] == "long_term"

    def test_is_idempotent_on_rerun(self, mem_db, _redis_spy):
        _seed_offer(mem_db)

        first = _deploy_credit_offer(_OFFER_ID, _USER_ID)
        second = _deploy_credit_offer(_OFFER_ID, _USER_ID)

        assert first["status"] == "deployed"
        assert second["status"] == "already_processed"

        with Session(mem_db) as session:
            notifs = (
                session.query(Notification)
                .filter(Notification.offer_id == _OFFER_ID)
                .all()
            )
            assert len(notifs) == 1

        assert _redis_spy.publish.call_count == 1

    def test_not_found_when_offer_missing(self, mem_db):
        result = _deploy_credit_offer("does-not-exist", _USER_ID)
        assert result["status"] == "not_found"

    def test_transient_apply_error_propagates_for_rq_retry(self, mem_db):
        _seed_offer(mem_db)

        with patch(
            "src.api.worker.apply_credit_to_user",
            side_effect=RuntimeError("transient DB error"),
        ):
            with pytest.raises(RuntimeError):
                _deploy_credit_offer(_OFFER_ID, _USER_ID)

        offer = get_credit_offer(_OFFER_ID)
        assert offer.status == "accepted"

        result = _deploy_credit_offer(_OFFER_ID, _USER_ID)
        assert result["status"] == "deployed"
        with Session(mem_db) as session:
            user = session.get(User, _USER_ID)
            assert user.current_credit_limit == 25000.0
