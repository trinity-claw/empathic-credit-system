"""Evaluation metrics for credit risk models.

Metrics used:
- AUC-ROC: ranking capability (good vs bad). 0.5=random, 1.0=perfect.
  In credit scoring, 0.75+ is decent, 0.80+ is good.
- KS (Kolmogorov-Smirnov): max distance between CDFs of good and bad scores.
  Classic metric in the Brazilian credit market. KS>30 acceptable, >40 good.
- Brier score: MSE between predicted probability and realized outcome.
  Measures CALIBRATION. Lower is better. Models that rank well but are
  uncalibrated have high Brier.
- Precision@base_rate: in credit operations you fix an approval rate (or a
  minimum recall of bads). Precision at that operating point often matters
  more than any global metric.
"""

from dataclasses import dataclass, field
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    brier_score_loss,
    confusion_matrix,
    roc_auc_score,
    roc_curve,
)


@dataclass
class EvalResult:
    """Structured evaluation result. Enables easy side-by-side model comparison."""

    model_name: str
    split: str  # "train", "val", "test"
    auc: float
    ks: float
    brier: float
    precision_at_default_rate: float
    default_rate: float
    n: int
    extras: dict[str, Any] = field(default_factory=dict)

    def to_row(self) -> dict[str, Any]:
        return {
            "model": self.model_name,
            "split": self.split,
            "AUC": round(self.auc, 4),
            "KS": round(self.ks, 4),
            "Brier": round(self.brier, 4),
            "Prec@base_rate": round(self.precision_at_default_rate, 4),
            "n": self.n,
        }


def compute_ks(y_true: np.ndarray, y_proba: np.ndarray) -> float:
    """KS statistic = max distance between CDFs of class 0 and class 1 scores.

    Manual implementation for transparency. Equivalent to scipy.stats.ks_2samp
    applied to scores separated by class.
    """
    y_true = np.asarray(y_true)
    y_proba = np.asarray(y_proba)
    order = np.argsort(y_proba)
    y_sorted = y_true[order]
    n_pos = int(y_sorted.sum())
    n_neg = len(y_sorted) - n_pos
    if n_pos == 0 or n_neg == 0:
        return 0.0
    cum_pos = np.cumsum(y_sorted) / n_pos
    cum_neg = np.cumsum(1 - y_sorted) / n_neg
    return float(np.max(np.abs(cum_pos - cum_neg)))


def precision_at_threshold(
    y_true: np.ndarray, y_proba: np.ndarray, threshold: float
) -> float:
    """Precision when predictions with score >= threshold are flagged as positive."""
    y_true = np.asarray(y_true)
    y_proba = np.asarray(y_proba)
    y_pred = (y_proba >= threshold).astype(int)
    tp = int(((y_pred == 1) & (y_true == 1)).sum())
    fp = int(((y_pred == 1) & (y_true == 0)).sum())
    return float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0


def evaluate(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    model_name: str,
    split: str,
) -> EvalResult:
    """Compute all metrics at once. Returns EvalResult."""
    y_true = np.asarray(y_true)
    y_proba = np.asarray(y_proba)
    base_rate = float(y_true.mean())
    # threshold = base rate: "flag the top X% riskiest as bad"
    threshold = float(np.quantile(y_proba, 1 - base_rate))
    return EvalResult(
        model_name=model_name,
        split=split,
        auc=float(roc_auc_score(y_true, y_proba)),
        ks=compute_ks(y_true, y_proba),
        brier=float(brier_score_loss(y_true, y_proba)),
        precision_at_default_rate=precision_at_threshold(y_true, y_proba, threshold),
        default_rate=base_rate,
        n=len(y_true),
    )


def plot_evaluation(
    y_true: np.ndarray,
    y_proba: np.ndarray,
    model_name: str,
    figsize: tuple[int, int] = (14, 4),
) -> plt.Figure:
    """4-panel evaluation plot: ROC, KS, calibration, confusion matrix."""
    y_true = np.asarray(y_true)
    y_proba = np.asarray(y_proba)
    fig, axes = plt.subplots(1, 4, figsize=figsize)

    # 1. ROC curve
    fpr, tpr, _ = roc_curve(y_true, y_proba)
    auc = roc_auc_score(y_true, y_proba)
    axes[0].plot(fpr, tpr, color="#C44E52", lw=2, label=f"AUC = {auc:.3f}")
    axes[0].plot([0, 1], [0, 1], "k--", lw=1, alpha=0.5)
    axes[0].set_xlabel("False Positive Rate")
    axes[0].set_ylabel("True Positive Rate")
    axes[0].set_title("ROC Curve")
    axes[0].legend(loc="lower right")
    axes[0].grid(alpha=0.3)

    # 2. KS plot (separate CDFs)
    order = np.argsort(y_proba)
    y_sorted = y_true[order]
    proba_sorted = y_proba[order]
    n_pos = int(y_sorted.sum())
    n_neg = len(y_sorted) - n_pos
    cum_pos = np.cumsum(y_sorted) / n_pos
    cum_neg = np.cumsum(1 - y_sorted) / n_neg
    ks = float(np.max(np.abs(cum_pos - cum_neg)))
    ks_idx = int(np.argmax(np.abs(cum_pos - cum_neg)))
    axes[1].plot(proba_sorted, cum_neg, color="#4C72B0", label="CDF good")
    axes[1].plot(proba_sorted, cum_pos, color="#C44E52", label="CDF bad")
    axes[1].axvline(
        proba_sorted[ks_idx], color="black", ls="--", alpha=0.5, label=f"KS = {ks:.3f}"
    )
    axes[1].set_xlabel("Score")
    axes[1].set_ylabel("Cumulative")
    axes[1].set_title("KS Plot")
    axes[1].legend()
    axes[1].grid(alpha=0.3)

    # 3. Calibration curve
    prob_true, prob_pred = calibration_curve(
        y_true, y_proba, n_bins=10, strategy="quantile"
    )
    axes[2].plot([0, 1], [0, 1], "k--", lw=1, alpha=0.5, label="Perfect")
    axes[2].plot(prob_pred, prob_true, "o-", color="#55A868", label="Model")
    axes[2].set_xlabel("Predicted probability")
    axes[2].set_ylabel("Observed frequency")
    brier = brier_score_loss(y_true, y_proba)
    axes[2].set_title(f"Calibration (Brier={brier:.4f})")
    axes[2].legend()
    axes[2].grid(alpha=0.3)

    # 4. Confusion matrix @ threshold = base_rate
    base_rate = float(y_true.mean())
    threshold = float(np.quantile(y_proba, 1 - base_rate))
    y_pred = (y_proba >= threshold).astype(int)
    cm = confusion_matrix(y_true, y_pred)
    axes[3].imshow(cm, cmap="Blues")
    axes[3].set_xticks([0, 1])
    axes[3].set_yticks([0, 1])
    axes[3].set_xticklabels(["Good", "Bad"])
    axes[3].set_yticklabels(["Good", "Bad"])
    axes[3].set_xlabel("Predicted")
    axes[3].set_ylabel("Actual")
    axes[3].set_title(f"Confusion @ thr={threshold:.3f}")
    for i in range(2):
        for j in range(2):
            axes[3].text(
                j,
                i,
                f"{cm[i, j]:,}",
                ha="center",
                va="center",
                color="white" if cm[i, j] > cm.max() / 2 else "black",
                fontsize=11,
            )

    fig.suptitle(f"{model_name}", fontweight="bold", y=1.02)
    fig.tight_layout()
    return fig


def comparison_table(results: list[EvalResult]) -> pd.DataFrame:
    """Build a comparison table of multiple models' metrics."""
    return pd.DataFrame([r.to_row() for r in results])
