"""Tests for src/data/emotional.py"""

import numpy as np
import pandas as pd

from src.data.emotional import EMOTIONAL_FEATURES, inject_emotional_features


def _make_dummy_df(n: int = 200, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "revolving_utilization": rng.uniform(0, 1, n),
            "age": rng.integers(18, 80, n),
            "past_due_30_59": rng.integers(0, 5, n).astype(float),
            "debt_ratio": rng.uniform(0, 1, n),
            "monthly_income": rng.uniform(1000, 10000, n),
            "open_credit_lines": rng.integers(0, 20, n),
            "past_due_90": rng.integers(0, 3, n).astype(float),
            "real_estate_loans": rng.integers(0, 3, n),
            "past_due_60_89": rng.integers(0, 3, n).astype(float),
            "dependents": rng.integers(0, 5, n).astype(float),
            "had_past_due_sentinel": rng.integers(0, 2, n),
            "target": rng.integers(0, 2, n),
        }
    )


class TestInjectEmotionalFeatures:
    def test_returns_copy_not_inplace(self):
        df = _make_dummy_df()
        original_cols = set(df.columns)
        result = inject_emotional_features(df)
        assert set(df.columns) == original_cols  # original unchanged
        assert set(EMOTIONAL_FEATURES).issubset(set(result.columns))

    def test_shape_is_extended(self):
        df = _make_dummy_df(n=50)
        result = inject_emotional_features(df)
        assert result.shape == (50, df.shape[1] + len(EMOTIONAL_FEATURES))

    def test_bounded_0_to_1(self):
        df = _make_dummy_df()
        result = inject_emotional_features(df)
        for feat in ["stress_level", "impulsivity_score", "emotional_stability"]:
            assert result[feat].min() >= 0.0, f"{feat} below 0"
            assert result[feat].max() <= 1.0, f"{feat} above 1"

    def test_financial_stress_events_bounded(self):
        df = _make_dummy_df()
        result = inject_emotional_features(df)
        assert result["financial_stress_events_7d"].min() >= 0
        assert result["financial_stress_events_7d"].max() <= 20

    def test_reproducible_with_same_seed(self):
        df = _make_dummy_df()
        r1 = inject_emotional_features(df, random_state=99)
        r2 = inject_emotional_features(df, random_state=99)
        for feat in EMOTIONAL_FEATURES:
            assert (r1[feat] == r2[feat]).all(), f"{feat} not reproducible"

    def test_different_seeds_produce_different_results(self):
        df = _make_dummy_df()
        r1 = inject_emotional_features(df, random_state=1)
        r2 = inject_emotional_features(df, random_state=2)
        assert not (r1["stress_level"] == r2["stress_level"]).all()

    def test_r2_below_threshold(self):
        """Emotional features must not be too redundant with financial ones."""
        from sklearn.impute import SimpleImputer
        from sklearn.linear_model import Ridge
        from sklearn.pipeline import Pipeline

        df = _make_dummy_df(n=500)
        result = inject_emotional_features(df)
        fin_features = [c for c in df.columns if c != "target"]
        X_fin = result[fin_features].astype("float64")

        pipe = Pipeline([("imp", SimpleImputer(strategy="median")), ("reg", Ridge())])
        for feat in EMOTIONAL_FEATURES:
            y = result[feat].astype("float64")
            pipe.fit(X_fin, y)
            r2 = pipe.score(X_fin, y)
            assert r2 < 0.30, f"{feat} R² = {r2:.4f} exceeds 0.30 threshold"
