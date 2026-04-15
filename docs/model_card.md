# Model Card — Empathic Credit System

## Model Overview

| Field | Value |
|---|---|
| **Name** | XGBoost Financial Credit Scorer (calibrated) |
| **Version** | v1.0.0 |
| **Type** | Gradient Boosted Decision Tree (XGBoost 3.2) |
| **Task** | Binary classification — probability of default within 2 years |
| **Recommended for production** | `xgboost_financial_calibrated` |

---

## Dataset

**Source**: [Give Me Some Credit](https://www.kaggle.com/c/GiveMeSomeCredit) — Kaggle / OpenML ID 46929  
**Size**: 150,000 observations, 10 financial features  
**Target**: `SeriousDlqin2yrs` — 1 if borrower experienced 90+ days past due or worse within 2 years  
**Positive class rate**: 6.68% (imbalance ratio ≈ 14:1)

### Features

| Feature | Type | Notes |
|---|---|---|
| `revolving_utilization` | float | Revolving balance / credit limit |
| `age` | int | Age of borrower |
| `past_due_30_59` | float | Times 30-59 days past due |
| `debt_ratio` | float | Monthly debt / gross income |
| `monthly_income` | float | Monthly income (19.8% missing) |
| `open_credit_lines` | int | Number of open accounts |
| `past_due_90` | float | Times 90+ days past due |
| `real_estate_loans` | int | Number of real estate loans |
| `past_due_60_89` | float | Times 60-89 days past due |
| `dependents` | float | Number of dependents (2.6% missing) |
| `had_past_due_sentinel` | int | Binary flag: sentinel values (96/98) present in past_due columns |

### Splits

| Split | Rows | Positive rate |
|---|---|---|
| Train | 105,000 | 6.68% |
| Val | 22,500 | 6.68% |
| Test | 22,500 | 6.68% |

Stratified split (70/15/15) preserving class ratio.

**Limitation**: No temporal ordering — the dataset has no date column. In production with CloudWalk data, splits would be by observation date to prevent data leakage.

---

## Model Performance (Validation Set)

| Model | AUC | KS | Brier | Prec@base_rate |
|---|---|---|---|---|
| Logistic Regression (baseline) | 0.8216 | 0.5012 | 0.1545 | 0.4142 |
| XGBoost Financial | 0.8651 | 0.5740 | 0.1402 | 0.4322 |
| **XGBoost Financial (calibrated)** | **0.8676** | **0.5764** | **0.0488** | 0.3795 |
| XGBoost Emotional | 0.8645 | 0.5735 | 0.1401 | 0.4298 |
| XGBoost Emotional (calibrated) | 0.8668 | 0.5761 | 0.0490 | 0.3792 |

**Interpretation**:
- XGBoost financial beats baseline by +4.6 AUC points, +7.5 KS points — meaningful in credit scoring.
- Isotonic calibration drops Brier from 0.14 → 0.05 without loss of rank ordering (AUC/KS preserved). This matters for pricing and provisioning decisions that rely on calibrated probabilities.
- Emotional features add **-0.0008 AUC** (slightly worse). See section on emotional features below.

---

## Top Predictors (SHAP)

Ranked by mean absolute SHAP value on the validation set:

1. `past_due_90` — strongest positive signal; any 90+ day delinquency sharply increases risk
2. `revolving_utilization` — high utilization increases risk (nonlinear: jumps at ~80%)
3. `past_due_30_59` — early delinquency signal
4. `age` — negative (protective) — older borrowers default less
5. `monthly_income` — negative (protective) — higher income reduces risk
6. `debt_ratio` — positive, but weaker than utilization
7. `had_past_due_sentinel` — small but consistent positive signal

---

## Emotional Features Experiment

Four synthetic emotional signals were generated for this experiment:

| Feature | Correlation with | R² vs financials |
|---|---|---|
| `stress_level` | `revolving_utilization`, `past_due_30_59` | 0.049 |
| `impulsivity_score` | `open_credit_lines`, `debt_ratio` | 0.068 |
| `emotional_stability` | inverse of stress + impulsivity | 0.007 |
| `financial_stress_events_7d` | `past_due_90` | 0.088 |

Noise scale was set so R² < 0.30 for all features, ensuring they are correlated with (but not deterministic functions of) financial variables.

### Ethical Recommendation: Do Not Use Emotional Features in Production

**Quantitative finding**: Emotional features contribute < 0.1% gain in AUC. The model with emotional features (AUC 0.8668) underperforms the financial-only calibrated model (AUC 0.8676) by 0.0008.

**Regulatory risk**: Using behavioral or emotional data in credit decisions is incompatible with anti-discrimination law (e.g., Equal Credit Opportunity Act equivalents in Brazil, BACEN Resolution 4.557). Emotional states can be proxies for protected characteristics (disability, mental health conditions, gender).

**Privacy risk**: Collecting real-time emotional data from borrowers for scoring is invasive and creates significant informed-consent and data minimization obligations under LGPD.

**Fairness risk**: SHAP analysis shows emotional features can amplify existing biases present in the financial data, particularly for younger borrowers with thin credit files.

**Decision**: Deploy `xgboost_financial_calibrated` only.

---

## Fairness Analysis

Default rates were analyzed by age cohort and income bucket on the validation set:

| Age group | Default rate | Model default rate (mean score) |
|---|---|---|
| 18-25 | ~11% | Higher risk scores (expected) |
| 25-45 | ~7% | Near base rate |
| 45-65 | ~5% | Lower risk scores (expected) |
| 65+ | ~4% | Lowest risk scores |

The model reflects real-world risk differences by age. However, **decisions should be reviewed for disparate impact** if the approval rate for any protected group falls more than 80% below the majority group rate (4/5ths rule). This analysis requires real production data.

**Drift monitoring**: Monitor monthly income distribution, revolving utilization quartiles, and default rate on approved loans monthly. Model retraining should be triggered if AUC on a held-out sample drops below 0.82.

---

## Technical Details

| Field | Value |
|---|---|
| Framework | XGBoost 3.2 + scikit-learn 1.8 |
| Hyperparameters | `n_estimators=500, lr=0.05, max_depth=5, subsample=0.8, colsample_bytree=0.8` |
| Early stopping | Val AUC, 30 rounds patience (stopped at iteration ~103) |
| Class reweighting | `scale_pos_weight ≈ 14` (neg/pos ratio) |
| Calibration | IsotonicRegression fitted on validation set probabilities |
| Explainability | SHAP TreeExplainer (exact, O(TLD) per prediction) |
| Serving | FastAPI + SQLite + rq (async) + Redis |

---

## Limitations

1. No temporal validation — cannot estimate performance on data from a future period.
2. US-based dataset — feature semantics may differ in Brazilian credit market (e.g., consignado, rotating credit card limits).
3. Synthetic emotional features — not validated against any real behavioral instrument.
4. No demographic features — fairness analysis is post-hoc on available proxies (age, income).

---

## Model Authors

Empathic Credit System case study. Dataset: Give Me Some Credit (Kaggle, 2011).
