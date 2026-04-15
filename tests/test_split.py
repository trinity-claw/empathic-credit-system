"""Tests for src/data/split.py"""

import numpy as np
import pandas as pd

from src.data.split import make_splits


def _make_df(n: int = 1000, target_rate: float = 0.067, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n_pos = int(n * target_rate)
    target = np.concatenate([np.ones(n_pos), np.zeros(n - n_pos)]).astype(int)
    rng.shuffle(target)
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
            "target": target,
        }
    )


class TestMakeSplits:
    def test_split_proportions(self):
        df = _make_df(n=1000)
        splits = make_splits(df, test_size=0.15, val_size=0.15)

        total = sum(len(s) for s in splits.values())
        assert total == len(df)

        assert abs(len(splits["test"]) / len(df) - 0.15) < 0.02
        assert abs(len(splits["val"]) / len(df) - 0.15) < 0.02
        assert abs(len(splits["train"]) / len(df) - 0.70) < 0.02

    def test_target_rate_preserved(self):
        df = _make_df(n=2000, target_rate=0.10)
        splits = make_splits(df)
        original_rate = df["target"].mean()

        for name, part in splits.items():
            rate = part["target"].mean()
            assert abs(rate - original_rate) < 0.02, (
                f"{name} target rate {rate:.4f} deviates from {original_rate:.4f}"
            )

    def test_no_row_overlap(self):
        df = _make_df(n=500)
        df = df.reset_index(drop=True)
        df["_idx"] = range(len(df))
        splits = make_splits(df)

        train_idx = set(splits["train"]["_idx"])
        val_idx = set(splits["val"]["_idx"])
        test_idx = set(splits["test"]["_idx"])

        assert train_idx.isdisjoint(val_idx)
        assert train_idx.isdisjoint(test_idx)
        assert val_idx.isdisjoint(test_idx)

    def test_deterministic_with_same_seed(self):
        df = _make_df(n=300)
        s1 = make_splits(df, random_state=42)
        s2 = make_splits(df, random_state=42)
        for name in ("train", "val", "test"):
            pd.testing.assert_frame_equal(s1[name], s2[name])
