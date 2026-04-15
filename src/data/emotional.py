"""Synthetic emotional feature injection for the Empathic Credit System.

Design rationale
----------------
The ECS case asks for emotional/behavioral signals alongside financial ones.
Since no real emotional data exists for the GMSC dataset, we generate synthetic
proxies that are *correlated with financial features* (not with the target directly).
This reflects how such data would behave in the real world: a person with many
late payments is likely to be under financial stress, but the causal direction
is uncertain and the relationship is noisy.

Key constraint: noise must dominate the signal pre-sigmoid so that emotional
features carry *partial* but not *redundant* information relative to financials.
R² of each emotional feature regressed on the financial features should be < 0.3.
If it exceeds that, the noise scale is too small.

Feature definitions
-------------------
- stress_level         [0, 1]: financial stress proxy.
- impulsivity_score    [0, 1]: impulsive spending proxy.
- emotional_stability  [0, 1]: inverse of combined stress + impulsivity.
- financial_stress_events_7d [int, 0-20]: count of stress events in last 7 days.
"""

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

_NOISE_SCALE = 1.2  # N(0, _NOISE_SCALE) before sigmoid — keeps R² < 0.3


def _zscore(series: pd.Series) -> pd.Series:
    """Standardize to zero mean, unit variance; fills NaN with 0."""
    s = series.fillna(series.median())
    std = s.std()
    return (s - s.mean()) / std if std > 0 else s * 0.0


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def inject_emotional_features(
    df: pd.DataFrame,
    random_state: int = 42,
) -> pd.DataFrame:
    """Add 4 synthetic emotional features to df. Returns a copy.

    Args:
        df: DataFrame with financial features (after clean()).
        random_state: RNG seed for reproducibility.

    Returns:
        Copy of df with 4 additional columns.
    """
    rng = np.random.default_rng(random_state)
    df = df.copy()
    n = len(df)

    z_util = _zscore(df["revolving_utilization"]).values
    z_pd30 = _zscore(df["past_due_30_59"]).values
    z_pd90 = _zscore(df["past_due_90"]).values
    z_credit = _zscore(df["open_credit_lines"]).values
    z_debt = _zscore(df["debt_ratio"]).values

    # stress_level: signal from utilization + recent delinquency + heavy noise
    stress_logit = 0.4 * z_util + 0.3 * z_pd30 + rng.normal(0, _NOISE_SCALE, n)
    df["stress_level"] = _sigmoid(stress_logit).astype("float32")

    # impulsivity_score: signal from number of credit lines + debt ratio + noise
    impuls_logit = 0.3 * z_credit + 0.3 * z_debt + rng.normal(0, _NOISE_SCALE, n)
    df["impulsivity_score"] = _sigmoid(impuls_logit).astype("float32")

    # emotional_stability: inverse composite of stress + impulsivity + noise
    stab_logit = -(0.2 * stress_logit + 0.2 * impuls_logit) + rng.normal(
        0, _NOISE_SCALE, n
    )
    df["emotional_stability"] = _sigmoid(stab_logit).astype("float32")

    # financial_stress_events_7d: Poisson count driven by delinquency + noise
    # Signal coefficient halved and noise tripled vs initial design to keep R² < 0.30
    lam = np.clip(3.0 + 0.8 * z_pd90 + rng.normal(0, 1.8, n), 0.01, 20.0)
    df["financial_stress_events_7d"] = rng.poisson(lam).clip(0, 20).astype("int32")

    logger.info(
        "Injected emotional features: %s",
        {f: f"{df[f].mean():.3f}" for f in EMOTIONAL_FEATURES},
    )
    return df
