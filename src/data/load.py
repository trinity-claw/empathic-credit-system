"""Data loading and basic cleaning for Give Me Some Credit."""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

RAW_PATH = Path("data/raw/cs-training.csv")

# mapeamento das colunas originais → snake_case
# Handles both Kaggle name (SeriousDlqin2yrs) and OpenML name
# (FinancialDistressNextTwoYears) for the target column.
COLUMN_RENAME = {
    "SeriousDlqin2yrs": "target",
    "FinancialDistressNextTwoYears": "target",
    "RevolvingUtilizationOfUnsecuredLines": "revolving_utilization",
    "age": "age",
    "NumberOfTime30-59DaysPastDueNotWorse": "past_due_30_59",
    "DebtRatio": "debt_ratio",
    "MonthlyIncome": "monthly_income",
    "NumberOfOpenCreditLinesAndLoans": "open_credit_lines",
    "NumberOfTimes90DaysLate": "past_due_90",
    "NumberRealEstateLoansOrLines": "real_estate_loans",
    "NumberOfTime60-89DaysPastDueNotWorse": "past_due_60_89",
    "NumberOfDependents": "dependents",
}

# sentinel values conhecidos nas colunas de past_due (96, 98)
# representam casos especiais, não "96 atrasos de verdade"
PAST_DUE_COLS = ["past_due_30_59", "past_due_60_89", "past_due_90"]
SENTINEL_VALUES = {96, 98}


def load_raw(path: Path = RAW_PATH) -> pd.DataFrame:
    """Carrega o CSV bruto e renomeia colunas. Não faz tratamento ainda."""
    df = pd.read_csv(
        path,
        index_col=0,  # primeira col é índice sem nome
        na_values="?",  # OpenML usa '?' para missing values
    )
    df = df.rename(columns=COLUMN_RENAME)
    # OpenML encodes target as 'Yes'/'No' strings — map to 1/0
    if not pd.api.types.is_integer_dtype(df["target"]):
        yes_no_map = {"Yes": 1, "No": 0, "1": 1, "0": 0}
        df["target"] = df["target"].astype(str).map(yes_no_map).astype(int)
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica tratamentos básicos: sentinels + winsorização leve."""
    df = df.copy()

    # flag de sentinel antes de tratar (feature extra de informação)
    df["had_past_due_sentinel"] = (
        df[PAST_DUE_COLS].isin(SENTINEL_VALUES).any(axis=1).astype(int)
    )

    # substituir sentinels por NaN (deixa XGBoost decidir, imputa no logistic)
    for col in PAST_DUE_COLS:
        df.loc[df[col].isin(SENTINEL_VALUES), col] = pd.NA
        df[col] = df[col].astype("Float64")

    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    df = load_raw()
    logger.info("Raw shape: %s", df.shape)
    logger.info("Target rate: %.4f", df["target"].mean())
    logger.info("Missing:\n%s", df.isna().sum()[df.isna().sum() > 0])

    df_clean = clean(df)
    logger.info("\nApós clean:")
    logger.info(
        "  had_past_due_sentinel: %d linhas", df_clean["had_past_due_sentinel"].sum()
    )
    logger.info("  Missing em past_due após tratar sentinel:")
    logger.info("%s", df_clean[PAST_DUE_COLS].isna().sum())
