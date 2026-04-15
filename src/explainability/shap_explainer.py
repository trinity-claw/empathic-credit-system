"""SHAP-based explainability for the Empathic Credit System.

This module is used by the API to generate per-request explanations.
The CreditExplainer wraps shap.TreeExplainer (fast, exact for XGBoost).

Usage
-----
    explainer = CreditExplainer.from_model(xgb_model, feature_names)
    result = explainer.explain(X_single_row)
    # result["shap_values"] — dict feature -> float contribution
    # result["base_value"]  — expected model output (log-odds)
    # result["top_factors"] — top N factors with sign
"""

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
import shap

logger = logging.getLogger(__name__)


@dataclass
class ExplanationResult:
    """SHAP explanation for a single prediction."""

    feature_names: list[str]
    shap_values: list[float]
    base_value: float
    prediction: float

    def to_dict(self) -> dict[str, Any]:
        contributions = {
            f: round(float(v), 6) for f, v in zip(self.feature_names, self.shap_values)
        }
        top = sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True)
        return {
            "base_value": round(self.base_value, 6),
            "prediction": round(self.prediction, 6),
            "contributions": contributions,
            "top_factors": [
                {
                    "feature": k,
                    "contribution": v,
                    "direction": "increases_risk" if v > 0 else "decreases_risk",
                }
                for k, v in top[:5]
            ],
        }


class CreditExplainer:
    """Wraps shap.TreeExplainer for per-request explanations in the API.

    Loaded once at API startup (not per request). Thread-safe for reads.
    """

    def __init__(self, explainer: shap.TreeExplainer, feature_names: list[str]) -> None:
        self._explainer = explainer
        self.feature_names = feature_names

    @classmethod
    def from_model(cls, model: Any, feature_names: list[str]) -> "CreditExplainer":
        """Build a CreditExplainer from a fitted XGBoost model."""
        explainer = shap.TreeExplainer(model)
        logger.info("CreditExplainer initialized for %d features.", len(feature_names))
        return cls(explainer, feature_names)

    def explain(self, X: pd.DataFrame | np.ndarray) -> list[ExplanationResult]:
        """Compute SHAP values for one or more rows.

        Args:
            X: DataFrame or ndarray with shape (n_samples, n_features).

        Returns:
            List of ExplanationResult, one per row.
        """
        if isinstance(X, pd.DataFrame):
            X_arr = X[self.feature_names].astype("float64").values
        else:
            X_arr = np.asarray(X, dtype="float64")

        shap_vals = self._explainer.shap_values(X_arr)
        base_val = float(self._explainer.expected_value)
        # Approximate output = base + sum(shap) for each row (in log-odds space)
        row_sums = base_val + shap_vals.sum(axis=1)

        results = []
        for i in range(len(X_arr)):
            results.append(
                ExplanationResult(
                    feature_names=self.feature_names,
                    shap_values=shap_vals[i].tolist(),
                    base_value=base_val,
                    prediction=float(row_sums[i]),
                )
            )
        return results

    def explain_one(self, X: pd.DataFrame | np.ndarray) -> ExplanationResult:
        """Convenience wrapper for a single row."""
        return self.explain(X)[0]
