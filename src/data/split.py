"""Stratified train/val/test split with parquet persistence.

Why stratified: with 6.68% positive class, random splits can produce folds
with significantly different proportions, especially in the smaller val/test
sets. Stratification preserves ~6.68% in each split.

Why not temporal: the Give Me Some Credit dataset has no time column.
In a production scenario with CloudWalk data, splits would be by observation
date to simulate real usage (train on past, test on future). This limitation
is documented in the model card.
"""

import logging
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from src.data.load import clean, load_raw

logger = logging.getLogger(__name__)

PROCESSED_DIR = Path("data/processed")
RANDOM_STATE = 42
TARGET = "target"


def make_splits(
    df: pd.DataFrame,
    test_size: float = 0.15,
    val_size: float = 0.15,
    random_state: int = RANDOM_STATE,
) -> dict[str, pd.DataFrame]:
    """Stratified 70/15/15 split preserving target class ratio.

    Strategy: first separate test (15%), then divide remainder into train/val
    adjusting val_size to be the correct fraction of the remaining train_val.
    """
    train_val, test = train_test_split(
        df,
        test_size=test_size,
        random_state=random_state,
        stratify=df[TARGET],
    )

    val_relative = val_size / (1 - test_size)
    train, val = train_test_split(
        train_val,
        test_size=val_relative,
        random_state=random_state,
        stratify=train_val[TARGET],
    )

    return {"train": train, "val": val, "test": test}


def save_splits(splits: dict[str, pd.DataFrame], out_dir: Path = PROCESSED_DIR) -> None:
    """Persist each split as parquet (preserves dtypes, fast to read)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, df in splits.items():
        path = out_dir / f"{name}.parquet"
        df.to_parquet(path, index=False)
        logger.info(
            "  %s: %d rows, %.4f positive rate -> %s",
            name,
            len(df),
            df[TARGET].mean(),
            path,
        )


def load_splits(processed_dir: Path = PROCESSED_DIR) -> dict[str, pd.DataFrame]:
    """Load persisted splits. Used by notebooks and the API."""
    return {
        name: pd.read_parquet(processed_dir / f"{name}.parquet")
        for name in ("train", "val", "test")
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    logger.info("Loading and cleaning raw data...")
    df = clean(load_raw())
    logger.info("  Shape: %s, positive rate: %.4f", df.shape, df[TARGET].mean())

    logger.info("Creating stratified splits...")
    splits = make_splits(df)
    save_splits(splits)

    logger.info("Sanity check (all should be ~0.0668):")
    for name, part in splits.items():
        logger.info("  %s: %.4f", name, part[TARGET].mean())
