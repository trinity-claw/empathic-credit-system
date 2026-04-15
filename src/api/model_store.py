"""Singleton model + explainer store loaded once at API startup."""

import logging
from typing import Any

import joblib
import pandas as pd

from src.api.settings import get_settings
from src.data.emotional import EMOTIONAL_FEATURES
from src.explainability.shap_explainer import CreditExplainer

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLD = 0.15
SCORE_MAX = 1000

_CREDIT_TIERS = [
    (850, 50_000.0, 0.015, "long_term"),
    (700, 20_000.0, 0.025, "long_term"),
    (550, 8_000.0, 0.040, "short_term"),
    (0, 2_000.0, 0.060, "short_term"),
]

FINANCIAL_FEATURES = [
    "revolving_utilization",
    "age",
    "past_due_30_59",
    "debt_ratio",
    "monthly_income",
    "open_credit_lines",
    "past_due_90",
    "real_estate_loans",
    "past_due_60_89",
    "dependents",
    "had_past_due_sentinel",
]

_store: dict[str, Any] = {}


def load_models() -> None:
    settings = get_settings()

    fin_model = joblib.load(settings.model_path)
    fin_cal = joblib.load(settings.calibrator_path)
    emo_model = joblib.load(settings.emotional_model_path)
    emo_cal = joblib.load(settings.emotional_calibrator_path)

    _store["fin_model"] = fin_model
    _store["fin_calibrator"] = fin_cal
    _store["emo_model"] = emo_model
    _store["emo_calibrator"] = emo_cal
    _store["fin_explainer"] = CreditExplainer.from_model(fin_model, FINANCIAL_FEATURES)
    _store["emo_explainer"] = CreditExplainer.from_model(
        emo_model, FINANCIAL_FEATURES + EMOTIONAL_FEATURES
    )

    logger.info(
        "Models loaded: financial + emotional (with calibrators + SHAP explainers)."
    )


def predict(request_data: dict, use_emotional: bool = False) -> dict:
    if use_emotional:
        features = FINANCIAL_FEATURES + EMOTIONAL_FEATURES
        model = _store["emo_model"]
        calibrator = _store["emo_calibrator"]
        explainer = _store["emo_explainer"]
        model_name = "xgboost_emotional_calibrated"
    else:
        features = FINANCIAL_FEATURES
        model = _store["fin_model"]
        calibrator = _store["fin_calibrator"]
        explainer = _store["fin_explainer"]
        model_name = "xgboost_financial_calibrated"

    X = pd.DataFrame([{f: request_data.get(f) for f in features}]).astype("float64")

    raw_proba = float(model.predict_proba(X)[:, 1][0])
    cal_proba = float(calibrator.transform([raw_proba])[0])
    score = max(0, min(SCORE_MAX, int((1 - cal_proba) * SCORE_MAX)))
    decision = "DENIED" if cal_proba >= DEFAULT_THRESHOLD else "APPROVED"

    explanation = explainer.explain_one(X).to_dict()
    credit_product = _compute_credit_product(score, decision)

    return {
        "decision": decision,
        "probability_of_default": round(cal_proba, 6),
        "score": score,
        "model_used": model_name,
        "shap_explanation": explanation,
        "top_factors": explanation["top_factors"],
        **credit_product,
    }


def _compute_credit_product(score: int, decision: str) -> dict:
    if decision == "DENIED":
        return {"credit_limit": 0.0, "interest_rate": None, "credit_type": "denied"}
    for min_score, limit, rate, credit_type in _CREDIT_TIERS:
        if score >= min_score:
            return {
                "credit_limit": limit,
                "interest_rate": rate,
                "credit_type": credit_type,
            }
    return {"credit_limit": 0.0, "interest_rate": None, "credit_type": "denied"}


def is_loaded() -> bool:
    return bool(_store)


def model_version() -> str:
    return get_settings().model_version
