"""Tests for src/data/load.py"""

import numpy as np
import pandas as pd

from src.data.load import PAST_DUE_COLS, SENTINEL_VALUES, clean, load_raw


def _make_raw_csv(target_col: str = "SeriousDlqin2yrs", target_vals=None) -> str:
    """Build a minimal CSV string matching the expected raw dataset format."""
    if target_vals is None:
        target_vals = [0, 1, 0]
    rows = []
    for i, t in enumerate(target_vals):
        rows.append(f"{i},{t},0.5,30,0,0.3,5000,3,0,1,0,2")
    header = (
        f",{target_col},"
        "RevolvingUtilizationOfUnsecuredLines,age,"
        "NumberOfTime30-59DaysPastDueNotWorse,DebtRatio,"
        "MonthlyIncome,NumberOfOpenCreditLinesAndLoans,"
        "NumberOfTimes90DaysLate,NumberRealEstateLoansOrLines,"
        "NumberOfTime60-89DaysPastDueNotWorse,NumberOfDependents"
    )
    return header + "\n" + "\n".join(rows)


class TestLoadRaw:
    def test_columns_are_renamed(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(_make_raw_csv())
        df = load_raw(csv_file)
        assert "target" in df.columns
        assert "revolving_utilization" in df.columns
        assert "SeriousDlqin2yrs" not in df.columns

    def test_shape_matches_rows(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(_make_raw_csv(target_vals=[0, 1, 0, 1, 0]))
        df = load_raw(csv_file)
        assert len(df) == 5
        assert df.shape[1] == 11

    def test_openml_target_yes_no_mapped(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            _make_raw_csv(
                target_col="FinancialDistressNextTwoYears",
                target_vals=["Yes", "No", "Yes"],
            )
        )
        df = load_raw(csv_file)
        assert df["target"].dtype in (np.int64, int)
        assert set(df["target"].unique()) == {0, 1}

    def test_target_is_integer(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(_make_raw_csv())
        df = load_raw(csv_file)
        assert pd.api.types.is_integer_dtype(df["target"])


class TestClean:
    def _make_df_with_sentinels(self):
        return pd.DataFrame(
            {
                "target": [0, 1, 0],
                "revolving_utilization": [0.1, 0.5, 0.3],
                "age": [30, 40, 50],
                "past_due_30_59": [0.0, 96.0, 2.0],
                "debt_ratio": [0.2, 0.3, 0.4],
                "monthly_income": [5000.0, np.nan, 3000.0],
                "open_credit_lines": [3, 5, 2],
                "past_due_90": [0.0, 98.0, 1.0],
                "real_estate_loans": [1, 0, 2],
                "past_due_60_89": [0.0, 0.0, 0.0],
                "dependents": [2.0, 1.0, np.nan],
            }
        )

    def test_sentinel_flag_created(self):
        df = self._make_df_with_sentinels()
        result = clean(df)
        assert "had_past_due_sentinel" in result.columns
        assert result["had_past_due_sentinel"].sum() == 1  # row index 1

    def test_sentinels_replaced_with_nan(self):
        df = self._make_df_with_sentinels()
        result = clean(df)
        for col in PAST_DUE_COLS:
            vals = result[col].dropna()
            for sv in SENTINEL_VALUES:
                assert sv not in vals.values

    def test_clean_does_not_modify_original(self):
        df = self._make_df_with_sentinels()
        original_cols = set(df.columns)
        _ = clean(df)
        assert set(df.columns) == original_cols
        assert "had_past_due_sentinel" not in df.columns
