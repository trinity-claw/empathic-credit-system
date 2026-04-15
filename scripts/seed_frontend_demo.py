#!/usr/bin/env python3
"""Populate the API DB with demo evaluations (and emotion events) for the Next.js UI.

Requires a running API with models loaded (e.g. after ./start.sh).

Profiles are tuned against the shipped XGBoost + isotonic calibrator (default
threshold 0.15 on calibrated P(default)): strong approvals, strong denials,
borderline financial-only cases, and emotional-only paths including one
\"rescue\" (financial-only would deny at the same utilization band).

  uv run python scripts/seed_frontend_demo.py
  ECS_API_BASE=http://127.0.0.1:8000 API_USERNAME=admin API_PASSWORD=changeme uv run python scripts/seed_frontend_demo.py

Uses synchronous POST /credit/evaluate (persists to SQLite) and POST /emotions/stream.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from uuid import uuid4


def _auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode()).decode("ascii")
    return f"Basic {token}"


def _post_json(
    base: str, path: str, body: dict, user: str, password: str, timeout: int
) -> dict:
    url = f"{base.rstrip('/')}{path}"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": _auth_header(user, password),
            "X-Request-ID": str(uuid4()),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{e.code} {url}: {detail}") from e


def _base_financial() -> dict:
    return {
        "past_due_30_59": 0.0,
        "monthly_income": 6000.0,
        "open_credit_lines": 4,
        "past_due_90": 0.0,
        "real_estate_loans": 0,
        "past_due_60_89": 0.0,
        "dependents": 1.0,
        "had_past_due_sentinel": 0,
    }


def _credit_payloads() -> list[dict]:
    """19 profiles: 10 financial-only + 9 with emotional features (calibrated spread)."""
    b = _base_financial()

    financial_only: list[dict] = [
        # Strong approvals (very low calibrated PD)
        {
            **b,
            "revolving_utilization": 0.02,
            "age": 58,
            "debt_ratio": 0.06,
            "monthly_income": 15000.0,
            "open_credit_lines": 2,
            "real_estate_loans": 1,
        },
        {
            **b,
            "revolving_utilization": 0.06,
            "age": 56,
            "debt_ratio": 0.10,
            "monthly_income": 12000.0,
            "open_credit_lines": 3,
            "real_estate_loans": 2,
        },
        {
            **b,
            "revolving_utilization": 0.12,
            "age": 50,
            "debt_ratio": 0.16,
            "monthly_income": 9500.0,
            "open_credit_lines": 4,
        },
        # Mid-pack approval
        {
            **b,
            "revolving_utilization": 0.28,
            "age": 44,
            "debt_ratio": 0.26,
            "monthly_income": 7200.0,
            "open_credit_lines": 5,
        },
        {
            **b,
            "revolving_utilization": 0.42,
            "age": 34,
            "debt_ratio": 0.48,
            "monthly_income": 4200.0,
            "open_credit_lines": 7,
            "past_due_30_59": 1.0,
        },
        # Borderline financial (same band except utilization step → APP then DEN)
        {
            **b,
            "revolving_utilization": 0.542,
            "age": 34,
            "debt_ratio": 0.48,
            "monthly_income": 4200.0,
            "open_credit_lines": 7,
            "past_due_30_59": 1.0,
        },
        {
            **b,
            "revolving_utilization": 0.544,
            "age": 34,
            "debt_ratio": 0.48,
            "monthly_income": 4200.0,
            "open_credit_lines": 7,
            "past_due_30_59": 1.0,
        },
        # Clear denials (high PD)
        {
            **b,
            "revolving_utilization": 0.72,
            "age": 31,
            "debt_ratio": 0.58,
            "monthly_income": 3200.0,
            "open_credit_lines": 9,
            "past_due_30_59": 1.5,
        },
        {
            **b,
            "revolving_utilization": 0.85,
            "age": 24,
            "debt_ratio": 0.72,
            "monthly_income": 2500.0,
            "open_credit_lines": 12,
            "past_due_30_59": 3.0,
            "past_due_90": 2.0,
        },
        {
            **b,
            "revolving_utilization": 0.99,
            "age": 22,
            "debt_ratio": 0.95,
            "monthly_income": 1800.0,
            "open_credit_lines": 18,
            "past_due_30_59": 6.0,
            "past_due_60_89": 4.0,
            "past_due_90": 5.0,
            "had_past_due_sentinel": 1,
        },
    ]

    emotional: list[dict] = [
        # Emotional model — strong approval
        {
            **b,
            "revolving_utilization": 0.04,
            "age": 59,
            "debt_ratio": 0.07,
            "monthly_income": 14000.0,
            "open_credit_lines": 2,
            "real_estate_loans": 2,
            "stress_level": 0.08,
            "impulsivity_score": 0.10,
            "emotional_stability": 0.90,
            "financial_stress_events_7d": 0,
        },
        {
            **b,
            "revolving_utilization": 0.14,
            "age": 52,
            "debt_ratio": 0.18,
            "monthly_income": 8800.0,
            "stress_level": 0.12,
            "impulsivity_score": 0.14,
            "emotional_stability": 0.85,
            "financial_stress_events_7d": 1,
        },
        # Mid / “healthy mix” approvals
        {
            **b,
            "revolving_utilization": 0.30,
            "age": 40,
            "debt_ratio": 0.35,
            "monthly_income": 5500.0,
            "open_credit_lines": 5,
            "stress_level": 0.35,
            "impulsivity_score": 0.38,
            "emotional_stability": 0.58,
            "financial_stress_events_7d": 2,
        },
        {
            **b,
            "revolving_utilization": 0.50,
            "age": 36,
            "debt_ratio": 0.45,
            "monthly_income": 5200.0,
            "open_credit_lines": 6,
            "past_due_30_59": 0.5,
            "stress_level": 0.35,
            "impulsivity_score": 0.40,
            "emotional_stability": 0.55,
            "financial_stress_events_7d": 4,
        },
        # Almost at threshold (still approved on this artifact)
        {
            **b,
            "revolving_utilization": 0.542,
            "age": 34,
            "debt_ratio": 0.48,
            "monthly_income": 4200.0,
            "open_credit_lines": 7,
            "past_due_30_59": 1.0,
            "stress_level": 0.50,
            "impulsivity_score": 0.50,
            "emotional_stability": 0.40,
            "financial_stress_events_7d": 6,
        },
        # Same financial band as a financial-only denial, but stable emotions → approval
        {
            **b,
            "revolving_utilization": 0.544,
            "age": 34,
            "debt_ratio": 0.48,
            "monthly_income": 4200.0,
            "open_credit_lines": 7,
            "past_due_30_59": 1.0,
            "stress_level": 0.05,
            "impulsivity_score": 0.06,
            "emotional_stability": 0.92,
            "financial_stress_events_7d": 0,
        },
        # Strong denials (emotional model)
        {
            **b,
            "revolving_utilization": 0.92,
            "age": 23,
            "debt_ratio": 0.88,
            "monthly_income": 2200.0,
            "open_credit_lines": 15,
            "past_due_90": 3.0,
            "stress_level": 0.92,
            "impulsivity_score": 0.88,
            "emotional_stability": 0.12,
            "financial_stress_events_7d": 18,
        },
        {
            **b,
            "revolving_utilization": 0.78,
            "age": 25,
            "debt_ratio": 0.68,
            "monthly_income": 2800.0,
            "open_credit_lines": 11,
            "past_due_90": 2.0,
            "past_due_30_59": 2.0,
            "stress_level": 0.75,
            "impulsivity_score": 0.70,
            "emotional_stability": 0.22,
            "financial_stress_events_7d": 12,
        },
        {
            **b,
            "revolving_utilization": 0.88,
            "age": 27,
            "debt_ratio": 0.75,
            "monthly_income": 2400.0,
            "open_credit_lines": 14,
            "past_due_90": 1.0,
            "past_due_60_89": 1.5,
            "stress_level": 0.60,
            "impulsivity_score": 0.65,
            "emotional_stability": 0.30,
            "financial_stress_events_7d": 10,
        },
    ]

    return financial_only + emotional


def _emotion_events() -> list[dict]:
    def _uid() -> str:
        return str(uuid4())

    return [
        {
            "user_id": _uid(),
            "stress_level": 0.12,
            "impulsivity_score": 0.18,
            "emotional_stability": 0.82,
            "financial_stress_events_7d": 1,
        },
        {
            "user_id": _uid(),
            "stress_level": 0.72,
            "impulsivity_score": 0.68,
            "emotional_stability": 0.25,
            "financial_stress_events_7d": 9,
        },
        {
            "user_id": _uid(),
            "stress_level": 0.05,
            "impulsivity_score": 0.08,
            "emotional_stability": 0.94,
            "financial_stress_events_7d": 0,
        },
        {
            "user_id": _uid(),
            "stress_level": 0.48,
            "impulsivity_score": 0.52,
            "emotional_stability": 0.48,
            "financial_stress_events_7d": 5,
        },
        {
            "user_id": None,
            "stress_level": 0.28,
            "impulsivity_score": 0.32,
            "emotional_stability": 0.62,
            "financial_stress_events_7d": 3,
        },
        {
            "user_id": _uid(),
            "stress_level": 0.88,
            "impulsivity_score": 0.82,
            "emotional_stability": 0.15,
            "financial_stress_events_7d": 15,
        },
    ]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--base-url",
        default=os.environ.get("ECS_API_BASE", "http://127.0.0.1:8000"),
        help="API root (default: ECS_API_BASE or http://127.0.0.1:8000)",
    )
    p.add_argument(
        "--user",
        default=os.environ.get("API_USERNAME", "admin"),
    )
    p.add_argument(
        "--password",
        default=os.environ.get("API_PASSWORD", "changeme"),
    )
    p.add_argument(
        "--sleep",
        type=float,
        default=0.35,
        help="Seconds between credit requests (SHAP can be heavy)",
    )
    p.add_argument("--timeout", type=int, default=180, help="HTTP timeout per request")
    args = p.parse_args()

    payloads = _credit_payloads()
    if len(payloads) < 15:
        print("internal error: expected >=15 profiles", file=sys.stderr)
        return 1

    print(f"Seeding {len(payloads)} credit evaluations at {args.base_url} …")
    for i, body in enumerate(payloads, 1):
        try:
            r = _post_json(
                args.base_url,
                "/credit/evaluate",
                body,
                args.user,
                args.password,
                args.timeout,
            )
        except Exception as e:
            print(f"[{i}/{len(payloads)}] FAIL: {e}", file=sys.stderr)
            return 1
        print(
            f"[{i}/{len(payloads)}] {r.get('decision')} score={r.get('score')} "
            f"p={r.get('probability_of_default')} model={r.get('model_used')}"
        )
        if args.sleep > 0:
            time.sleep(args.sleep)

    print(f"Seeding {len(_emotion_events())} emotion stream events …")
    for i, body in enumerate(_emotion_events(), 1):
        try:
            r = _post_json(
                args.base_url,
                "/emotions/stream",
                body,
                args.user,
                args.password,
                min(60, args.timeout),
            )
        except Exception as e:
            print(f"emotion [{i}] FAIL: {e}", file=sys.stderr)
            return 1
        print(f"emotion [{i}] {r.get('status')} id={r.get('event_id')}")

    print(
        "Done. Open the app: History / Analytics / Dashboard should show varied decisions."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
