"""Tests for src/explainability/shap_explainer.py"""

from unittest.mock import MagicMock

import numpy as np
import pandas as pd

from src.explainability.shap_explainer import (
    TOP_FACTORS_COUNT,
    CreditExplainer,
    ExplanationResult,
)

FEATURES = ["feat_a", "feat_b", "feat_c"]


class TestExplanationResult:
    def test_to_dict_has_required_keys(self):
        result = ExplanationResult(
            feature_names=FEATURES,
            shap_values=[0.1, -0.05, 0.02],
            base_value=-2.0,
            prediction=-1.93,
        )
        d = result.to_dict()
        assert "base_value" in d
        assert "prediction" in d
        assert "contributions" in d
        assert "top_factors" in d

    def test_top_factors_sorted_by_abs_contribution(self):
        result = ExplanationResult(
            feature_names=FEATURES,
            shap_values=[0.01, -0.5, 0.3],
            base_value=0.0,
            prediction=0.0,
        )
        d = result.to_dict()
        factors = d["top_factors"]
        abs_vals = [abs(f["contribution"]) for f in factors]
        assert abs_vals == sorted(abs_vals, reverse=True)

    def test_direction_field_correct(self):
        result = ExplanationResult(
            feature_names=FEATURES,
            shap_values=[0.1, -0.2, 0.0],
            base_value=0.0,
            prediction=0.0,
        )
        d = result.to_dict()
        directions = {f["feature"]: f["direction"] for f in d["top_factors"]}
        assert directions["feat_a"] == "increases_risk"
        assert directions["feat_b"] == "decreases_risk"

    def test_top_factors_limited_to_constant(self):
        many_features = [f"f{i}" for i in range(20)]
        many_values = list(np.linspace(-0.5, 0.5, 20))
        result = ExplanationResult(
            feature_names=many_features,
            shap_values=many_values,
            base_value=0.0,
            prediction=0.0,
        )
        d = result.to_dict()
        assert len(d["top_factors"]) == TOP_FACTORS_COUNT


class TestCreditExplainer:
    def _make_mock_explainer(self):
        mock_tree = MagicMock()
        mock_tree.shap_values.return_value = np.array([[0.1, -0.2, 0.05]])
        mock_tree.expected_value = -1.5
        explainer = CreditExplainer(mock_tree, FEATURES)
        return explainer

    def test_explain_returns_list_of_results(self):
        explainer = self._make_mock_explainer()
        X = pd.DataFrame([[0.5, 30, 0.1]], columns=FEATURES)
        results = explainer.explain(X)
        assert isinstance(results, list)
        assert len(results) == 1
        assert isinstance(results[0], ExplanationResult)

    def test_explain_one_returns_single_result(self):
        explainer = self._make_mock_explainer()
        X = pd.DataFrame([[0.5, 30, 0.1]], columns=FEATURES)
        result = explainer.explain_one(X)
        assert isinstance(result, ExplanationResult)

    def test_prediction_equals_base_plus_shap_sum(self):
        explainer = self._make_mock_explainer()
        X = pd.DataFrame([[0.5, 30, 0.1]], columns=FEATURES)
        result = explainer.explain_one(X)
        expected = -1.5 + 0.1 + (-0.2) + 0.05
        assert abs(result.prediction - expected) < 1e-6
