"""Tests for src/evaluation/metrics.py"""

import numpy as np

from src.evaluation.metrics import compute_ks, evaluate, precision_at_threshold


def _perfect_scores(n: int = 100, pos_rate: float = 0.1):
    y = np.array([1] * int(n * pos_rate) + [0] * int(n * (1 - pos_rate)))
    scores = y.astype(float)
    return y, scores


def _random_scores(n: int = 200, seed: int = 0):
    rng = np.random.default_rng(seed)
    y = rng.integers(0, 2, size=n)
    scores = rng.random(size=n)
    return y, scores


class TestComputeKS:
    def test_perfect_separation_is_one(self):
        y, scores = _perfect_scores()
        ks = compute_ks(y, scores)
        assert abs(ks - 1.0) < 1e-6

    def test_random_scores_between_zero_and_one(self):
        y, scores = _random_scores()
        ks = compute_ks(y, scores)
        assert 0.0 <= ks <= 1.0

    def test_all_same_class_returns_zero(self):
        y = np.zeros(50, dtype=int)
        scores = np.random.random(50)
        ks = compute_ks(y, scores)
        assert ks == 0.0

    def test_reversed_scores_same_magnitude(self):
        y, scores = _perfect_scores()
        ks_fwd = compute_ks(y, scores)
        ks_rev = compute_ks(y, 1 - scores)
        assert abs(ks_fwd - ks_rev) < 1e-6


class TestPrecisionAtThreshold:
    def test_threshold_zero_equals_base_rate(self):
        y = np.array([1, 0, 0, 0, 1])
        scores = np.array([0.8, 0.6, 0.4, 0.2, 0.9])
        p = precision_at_threshold(y, scores, threshold=0.0)
        assert abs(p - 2 / 5) < 1e-6

    def test_threshold_above_max_returns_zero(self):
        y = np.array([1, 0, 1])
        scores = np.array([0.5, 0.3, 0.7])
        p = precision_at_threshold(y, scores, threshold=1.1)
        assert p == 0.0

    def test_perfect_precision(self):
        y = np.array([1, 0, 0])
        scores = np.array([1.0, 0.0, 0.0])
        p = precision_at_threshold(y, scores, threshold=0.9)
        assert p == 1.0


class TestEvaluate:
    def test_returns_eval_result_fields(self):
        y, scores = _random_scores()
        result = evaluate(y, scores, "TestModel", "val")
        assert result.model_name == "TestModel"
        assert result.split == "val"
        assert 0.0 <= result.auc <= 1.0
        assert 0.0 <= result.ks <= 1.0
        assert result.brier >= 0.0
        assert result.n == len(y)

    def test_to_row_serializes_correctly(self):
        y, scores = _random_scores()
        result = evaluate(y, scores, "M", "train")
        row = result.to_row()
        assert row["model"] == "M"
        assert row["split"] == "train"
        assert "AUC" in row
        assert "KS" in row
