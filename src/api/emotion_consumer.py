import json
import logging
import os
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from pythonjsonlogger.json import JsonFormatter
from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from src.api.settings import get_settings

EMOTION_CHANNEL = "ecs:emotion_stream"
DLQ_CHANNEL = "ecs:emotion_stream:dlq"
MAX_PROCESS_ATTEMPTS = 3
BACKOFF_BASE_SECONDS = 1
BACKOFF_CAP_SECONDS = 30

logger = logging.getLogger("emotion_consumer")
_shutdown = threading.Event()


def _configure_logging() -> None:
    settings = get_settings()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))


def process_emotional_event(payload: dict) -> dict:
    stress = payload.get("stress_level") or 0.0
    impulsivity = payload.get("impulsivity_score") or 0.0
    signals = {
        "event_id": payload.get("event_id"),
        "user_id": payload.get("user_id"),
        "stress_level": stress,
        "impulsivity_score": impulsivity,
        "high_risk": stress >= 0.75 or impulsivity >= 0.8,
    }
    logger.info("emotion.consumed", extra=signals)
    return signals


def _send_to_dlq(redis_conn: Redis, raw: str, error: str) -> None:
    try:
        redis_conn.publish(DLQ_CHANNEL, json.dumps({"original": raw, "error": error}))
        logger.warning("emotion.dlq", extra={"channel": DLQ_CHANNEL, "error": error})
    except Exception as exc:
        logger.error("emotion.dlq_publish_failed", extra={"error": str(exc)})


def _handle_message(raw: str, redis_conn: Redis) -> None:
    last_error: str | None = None
    for attempt in range(1, MAX_PROCESS_ATTEMPTS + 1):
        try:
            payload = json.loads(raw)
            process_emotional_event(payload)
            return
        except Exception as exc:
            last_error = str(exc)
            logger.warning(
                "emotion.process_failed",
                extra={"attempt": attempt, "error": last_error},
            )
            time.sleep(min(BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)), 5))
    _send_to_dlq(redis_conn, raw, last_error or "unknown")


def _subscribe(redis_conn: Redis) -> Any:
    pubsub = redis_conn.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(EMOTION_CHANNEL)
    return pubsub


def run(
    *,
    concurrency: int | None = None,
    redis_conn: Redis | None = None,
    shutdown_event: threading.Event | None = None,
) -> None:
    shutdown = shutdown_event or _shutdown
    if concurrency is None:
        concurrency = int(os.environ.get("EMOTION_CONSUMER_CONCURRENCY", "4"))
    settings = get_settings()
    conn = redis_conn or Redis.from_url(settings.redis_url, decode_responses=True)

    logger.info(
        "emotion.consumer_starting",
        extra={"channel": EMOTION_CHANNEL, "concurrency": concurrency},
    )

    executor = ThreadPoolExecutor(max_workers=concurrency)
    backoff = BACKOFF_BASE_SECONDS
    pubsub: Any = None

    try:
        while not shutdown.is_set():
            try:
                if pubsub is None:
                    pubsub = _subscribe(conn)
                    backoff = BACKOFF_BASE_SECONDS
                    logger.info("emotion.consumer_subscribed")

                message = pubsub.get_message(timeout=1.0)
                if message is None:
                    continue
                data = message.get("data")
                if not isinstance(data, str):
                    continue
                executor.submit(_handle_message, data, conn)

            except (RedisConnectionError, RedisTimeoutError) as exc:
                logger.warning(
                    "emotion.consumer_reconnecting",
                    extra={"error": str(exc), "backoff_s": backoff},
                )
                try:
                    if pubsub is not None:
                        pubsub.close()
                except Exception:
                    pass
                pubsub = None
                time.sleep(backoff)
                backoff = min(backoff * 2, BACKOFF_CAP_SECONDS)
            except Exception as exc:
                logger.error(
                    "emotion.consumer_unexpected_error", extra={"error": str(exc)}
                )
                time.sleep(1)
    finally:
        logger.info("emotion.consumer_shutting_down")
        executor.shutdown(wait=True)
        try:
            if pubsub is not None:
                pubsub.close()
        except Exception:
            pass


def _install_signal_handlers() -> None:
    def _handle(signum, _frame):
        logger.info("emotion.consumer_signal", extra={"signal": signum})
        _shutdown.set()

    signal.signal(signal.SIGTERM, _handle)
    signal.signal(signal.SIGINT, _handle)


def main() -> None:
    _configure_logging()
    _install_signal_handlers()
    run()


if __name__ == "__main__":
    main()
