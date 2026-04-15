"""Singleton model + explainer store loaded once at API startup."""

import logging
from typing import Any

import joblib
import pandas as pd

from src.api.settings import get_settings
from src.data.emotional import EMOTIONAL_FEATURES
from src.explainability.shap_explainer import CreditExplainer

logger = logging.getLogger(__name__)

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
    """Load all models into the global store. Called once at startup."""
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
    """Run inference + SHAP for a single request.

    Returns a dict with decision, probability, score, model_used, shap.
    """
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
    score = max(0, min(1000, int((1 - cal_proba) * 1000)))
    decision = "DENIED" if cal_proba >= 0.15 else "APPROVED"

    explanation = explainer.explain_one(X).to_dict()

    return {
        "decision": decision,
        "probability_of_default": round(cal_proba, 6),
        "score": score,
        "model_used": model_name,
        "shap_explanation": explanation,
        "top_factors": explanation["top_factors"],
    }


def is_loaded() -> bool:
    return bool(_store)


def model_version() -> str:
    return get_settings().model_version
