import json
import threading
import time
from unittest.mock import MagicMock

from redis.exceptions import ConnectionError as RedisConnectionError

from src.api import emotion_consumer


class _FakePubSub:
    def __init__(self, messages):
        self._messages = list(messages)
        self.closed = False

    def subscribe(self, *_args, **_kwargs):
        return None

    def get_message(self, **_kwargs):
        if self._messages:
            m = self._messages.pop(0)
            if isinstance(m, Exception):
                raise m
            return {"type": "message", "data": m}
        time.sleep(0.01)
        return None

    def close(self):
        self.closed = True


def _make_conn(pubsubs):
    conn = MagicMock()
    iterator = iter(pubsubs)
    conn.pubsub.side_effect = lambda **kwargs: next(iterator)
    conn.publish = MagicMock()
    return conn


def _run_in_thread(conn, shutdown, concurrency=4):
    t = threading.Thread(
        target=emotion_consumer.run,
        kwargs={
            "redis_conn": conn,
            "shutdown_event": shutdown,
            "concurrency": concurrency,
        },
        daemon=True,
    )
    t.start()
    return t


class TestConsumer:
    def test_processes_concurrent_messages(self):
        messages = [
            json.dumps({"event_id": f"e{i}", "user_id": "u1", "stress_level": 0.1})
            for i in range(20)
        ]
        pubsub = _FakePubSub(messages)
        conn = _make_conn([pubsub])

        processed = []
        lock = threading.Lock()
        real_process = emotion_consumer.process_emotional_event

        def spy(payload):
            with lock:
                processed.append(payload.get("event_id"))
            return real_process(payload)

        shutdown = threading.Event()
        emotion_consumer.process_emotional_event = spy
        try:
            t = _run_in_thread(conn, shutdown, concurrency=4)
            deadline = time.time() + 3
            while time.time() < deadline and len(processed) < 20:
                time.sleep(0.05)
            shutdown.set()
            t.join(timeout=3)
        finally:
            emotion_consumer.process_emotional_event = real_process

        assert len(processed) == 20
        assert set(processed) == {f"e{i}" for i in range(20)}

    def test_process_event_derives_high_risk_signal(self):
        payload = {
            "event_id": "ev-1",
            "user_id": "u1",
            "stress_level": 0.9,
            "impulsivity_score": 0.3,
        }
        result = emotion_consumer.process_emotional_event(payload)

        assert result["event_id"] == "ev-1"
        assert result["stress_level"] == 0.9
        assert result["high_risk"] is True

    def test_process_event_low_risk(self):
        payload = {
            "event_id": "ev-2",
            "user_id": "u2",
            "stress_level": 0.2,
            "impulsivity_score": 0.1,
        }
        result = emotion_consumer.process_emotional_event(payload)

        assert result["high_risk"] is False

    def test_reconnects_on_connection_error(self):
        failing = _FakePubSub([RedisConnectionError("boom")])
        recovered = _FakePubSub(
            [json.dumps({"event_id": "after-reconnect", "stress_level": 0.2})]
        )
        conn = _make_conn([failing, recovered])

        processed = []
        real_process = emotion_consumer.process_emotional_event
        emotion_consumer.process_emotional_event = lambda p: processed.append(
            p.get("event_id")
        )

        orig_backoff = emotion_consumer.BACKOFF_BASE_SECONDS
        emotion_consumer.BACKOFF_BASE_SECONDS = 0

        shutdown = threading.Event()
        try:
            t = _run_in_thread(conn, shutdown)
            deadline = time.time() + 3
            while time.time() < deadline and not processed:
                time.sleep(0.05)
            shutdown.set()
            t.join(timeout=3)
        finally:
            emotion_consumer.process_emotional_event = real_process
            emotion_consumer.BACKOFF_BASE_SECONDS = orig_backoff

        assert processed == ["after-reconnect"]
        assert failing.closed is True

    def test_poisoned_message_goes_to_dlq_with_correct_payload(self):
        raw_bad = "{not json"
        pubsub = _FakePubSub([raw_bad])
        conn = _make_conn([pubsub])

        orig_backoff = emotion_consumer.BACKOFF_BASE_SECONDS
        emotion_consumer.BACKOFF_BASE_SECONDS = 0

        shutdown = threading.Event()
        try:
            t = _run_in_thread(conn, shutdown, concurrency=1)
            deadline = time.time() + 3
            while time.time() < deadline and not conn.publish.called:
                time.sleep(0.05)
            shutdown.set()
            t.join(timeout=3)
        finally:
            emotion_consumer.BACKOFF_BASE_SECONDS = orig_backoff

        conn.publish.assert_called_once()
        channel, raw_payload = conn.publish.call_args[0]
        assert channel == emotion_consumer.DLQ_CHANNEL
        body = json.loads(raw_payload)
        assert body["original"] == raw_bad
        assert "error" in body
