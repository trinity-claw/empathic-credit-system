"""Synthetic emotional feature injection for comparative analysis."""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

EMOTIONAL_FEATURES = [
    "stress_level",
    "impulsivity_score",
    "emotional_stability",
    "financial_stress_events_7d",
]

_NOISE_SCALE = 1.2


def _zscore(series: pd.Series) -> pd.Series:
    s = series.fillna(series.median())
    std = s.std()
    return (s - s.mean()) / std if std > 0 else s * 0.0


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def inject_emotional_features(
    df: pd.DataFrame,
    random_state: int = 42,
) -> pd.DataFrame:
    """Add 4 synthetic emotional features to df. Returns a copy."""
    rng = np.random.default_rng(random_state)
    df = df.copy()
    n = len(df)

    z_util = _zscore(df["revolving_utilization"]).values
    z_pd30 = _zscore(df["past_due_30_59"]).values
    z_pd90 = _zscore(df["past_due_90"]).values
    z_credit = _zscore(df["open_credit_lines"]).values
    z_debt = _zscore(df["debt_ratio"]).values

    stress_logit = 0.4 * z_util + 0.3 * z_pd30 + rng.normal(0, _NOISE_SCALE, n)
    df["stress_level"] = _sigmoid(stress_logit).astype("float32")

    impuls_logit = 0.3 * z_credit + 0.3 * z_debt + rng.normal(0, _NOISE_SCALE, n)
    df["impulsivity_score"] = _sigmoid(impuls_logit).astype("float32")

    stab_logit = -(0.2 * stress_logit + 0.2 * impuls_logit) + rng.normal(
        0, _NOISE_SCALE, n
    )
    df["emotional_stability"] = _sigmoid(stab_logit).astype("float32")

    lam = np.clip(3.0 + 0.8 * z_pd90 + rng.normal(0, 1.8, n), 0.01, 20.0)
    df["financial_stress_events_7d"] = rng.poisson(lam).clip(0, 20).astype("int32")

    logger.info(
        "Injected emotional features: %s",
        {f: f"{df[f].mean():.3f}" for f in EMOTIONAL_FEATURES},
    )
    return df
