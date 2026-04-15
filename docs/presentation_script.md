# Presentation Script — Empathic Credit System

**Duration**: 30 minutes
**Format**: Screen share + live demo
**Audience**: Pablo (CEO), Leonardo, engineering team

---

## 1. Opening (2 min)

### What to say

"I built a complete credit scoring system that:
- Trains an XGBoost model achieving **AUC 0.87** and **KS 0.58** on held-out test data
- Experimentally proved that emotional features add **zero predictive value** (AUC delta = -0.0008) and recommended against deployment
- Implements disparate impact analysis using the **4/5ths rule** — a regulatory requirement for automated credit decisions
- Serves predictions via FastAPI with **SHAP explanations on every response**, end-to-end audit trail, and async credit deployment"

### Show

- README.md Results table (3 models side-by-side)
- One-liner: "Every single decision this system makes is explainable and auditable."

---

## 2. System Architecture (5 min)

### What to say

"The architecture starts where the challenge says: at the customer's brain. The mobile app captures emotional sensor readings — stress, impulsivity, stability — and streams them to our API via `POST /emotions/stream`. These events are persisted to the database and published to Redis Pub/Sub for downstream consumers.

When a credit evaluation is requested, the API runs the XGBoost model, calibrates the probability, maps it to a credit product (limit, rate, type), generates SHAP explanations, and returns everything in one response. If approved, a credit offer is created. The user can accept it, which triggers an async rq job that updates their profile and sends a notification.

Every request gets a correlation ID via X-Request-ID middleware. Every lifecycle event is logged to the credit_events audit table."

### Show

- README architecture diagram (full ASCII from brain to notification)
- `docker-compose.yml` — 4 services: api, worker, redis, dashboard
- Quick scroll through `src/api/main.py` — the endpoints

### Numbers to cite

- 7 API endpoints
- 7 database tables
- X-Request-ID on every request/response with duration_ms

---

## 3. ML Pipeline (8 min)

### 3a. Dataset and EDA (2 min)

"The dataset is Give Me Some Credit from Kaggle/OpenML — 150,000 borrowers with a 6.68% default rate. Strong class imbalance. Key findings from EDA:
- `monthly_income` has ~20% missing values
- `dependents` has ~2.6% missing
- Sentinel values 96/98 in past_due columns (269 rows) — I flagged these with a binary `had_past_due_sentinel` feature
- `revolving_utilization` has extreme outliers (max > 50,000) due to data quality issues"

### Show

- `notebooks/01_eda.ipynb` — distribution plots, missing value table

### 3b. Baseline (2 min)

"Started with Logistic Regression as baseline — Pipeline with SimpleImputer(median) + StandardScaler + LogReg(class_weight=balanced). Got **AUC 0.82** on validation. The coefficients make intuitive sense: past_due variables increase risk, age and income decrease it. This confirmed the data is clean and the target is well-defined."

### Show

- `notebooks/02_baseline_logreg.ipynb` — coefficient bar chart
- Point out: "These coefficients match credit risk intuition — if they didn't, we'd have a data problem."

### 3c. XGBoost + Calibration (2 min)

"XGBoost pushed AUC to **0.87** on validation. But raw XGBoost probabilities are poorly calibrated — Brier score 0.055 raw vs **0.049 after IsotonicRegression calibration**. The calibration curve went from an S-curve to nearly diagonal.

I used isotonic regression rather than Platt scaling because the relationship between raw probabilities and true frequencies is non-linear for tree ensembles. The calibrator was fitted on validation data and the final evaluation was done on a held-out test set to confirm no overfitting."

### Numbers to cite

| Metric | Baseline LogReg | XGBoost Raw | XGBoost Calibrated |
|--------|----------------|-------------|-------------------|
| AUC    | 0.8216         | 0.8676      | 0.8676            |
| KS     | 0.5012         | 0.5764      | 0.5764            |
| Brier  | 0.1545         | 0.0550      | 0.0488            |

### Show

- `notebooks/03_xgboost.ipynb` — 4-panel evaluation plot (ROC, KS, calibration, confusion)
- Test set results at the bottom

### 3d. SHAP (2 min)

"Every prediction comes with SHAP values computed by TreeExplainer — exact Shapley values in O(TLD) time where T is trees, L is leaves, D is depth. This isn't an approximation.

The top 5 risk factors are returned per request. The base value + sum of all SHAP values = model prediction in log-odds space. This gives us legally defensible explanations — LGPD Article 20 requires the right to explanation for automated decisions."

### Show

- `notebooks/05_shap_analysis.ipynb` — summary plot (global) + waterfall (individual)
- API response JSON showing `shap_explanation` and `top_factors`

---

## 4. Ethical Analysis (5 min)

### 4a. Emotional Features Experiment (3 min)

"The challenge asks us to use emotional data. I took this seriously — I generated synthetic emotional features that are correlated with financial behavior (stress correlates with delinquency, impulsivity with credit utilization) but noisy enough that R-squared < 0.30 against financials.

Result: the emotional model achieved AUC **0.8668** vs financial-only AUC **0.8676**. That's a delta of **-0.0008** — the emotional features actually hurt slightly. SHAP confirms: the emotional features have near-zero SHAP values compared to past_due_90, revolving_utilization, and age.

My recommendation: **do not deploy emotional features**. The privacy and regulatory cost is high (LGPD Article 11 — sensitive data), the technical cost is non-trivial (real-time sensor stream, consent management), and the predictive benefit is zero."

### Show

- `notebooks/04_emotional_features.ipynb` — side-by-side comparison table
- SHAP summary plot showing emotional features at the bottom
- `docs/model_card.md` — ethical analysis section

### 4b. Fairness (2 min)

"I implemented disparate impact analysis using the 4/5ths rule: the approval rate for any subgroup must be at least 80% of the highest group's rate. I tested across age cohorts and income quartiles.

Age: all cohorts pass. Income: Q1 is borderline at ~82% of Q4's rate — something to monitor in production with real data. I also checked subgroup calibration: the model is well-calibrated across all cohorts.

This isn't just a checkbox — InfinitePay operates under BACEN regulation, and the LGPD requires demonstrable fairness for automated financial decisions."

### Show

- `notebooks/06_fairness_analysis.ipynb` — 4/5ths rule bar charts
- Streamlit dashboard Fairness page

---

## 5. Backend Deep Dive (5 min)

### 5a. API Design (2 min)

"Seven endpoints, all protected by HTTP Basic Auth with constant-time comparison (`secrets.compare_digest`). Pydantic v2 for all input/output validation — the OpenAPI docs are auto-generated at `/docs`.

The credit evaluation endpoint does: predict → calibrate → map to credit product → generate SHAP → create offer → persist to DB → log audit events → respond. All synchronous, ~50ms per request with models pre-loaded at startup.

Async evaluation available via rq for batch workloads. Offer acceptance triggers a separate deployment job."

### Show

- `http://localhost:8000/docs` — Swagger UI
- `src/api/schemas.py` — CreditRequest, CreditResponse models

### 5b. Database (1 min)

"Seven tables: users, transactions, emotional_events, credit_offers, notifications, credit_evaluations, credit_events. Foreign keys and indexes. The evaluation audit trail captures every lifecycle event with timestamps."

### Show

- README Database Schema section with example SQL queries

### 5c. Observability (1 min)

"Structured JSON logging via python-json-logger. X-Request-ID middleware on every request with method, path, status_code, duration_ms. The log_level is configurable via environment variable."

### 5d. Docker (1 min)

"Four services in docker-compose: API, rq worker, Redis, Streamlit dashboard. Healthcheck on API and Redis. Multi-stage Dockerfile."

---

## 6. Live Demo (3 min)

### Steps

1. **Start**: `docker compose up --build` (or show already running)
2. **Health check**: `curl http://localhost:8000/health`
3. **Credit evaluation**:
```bash
curl -X POST http://localhost:8000/credit/evaluate \
  -u admin:changeme \
  -H "Content-Type: application/json" \
  -d '{"revolving_utilization":0.3,"age":45,"debt_ratio":0.2,"monthly_income":5000,"open_credit_lines":4,"past_due_30_59":0,"past_due_60_89":0,"past_due_90":0,"real_estate_loans":1,"dependents":2,"had_past_due_sentinel":0}'
```
4. **Show response**: point out decision, score, credit_limit, interest_rate, offer_id, shap_explanation, top_factors
5. **Accept offer**: `curl -X POST http://localhost:8000/credit/offers/{offer_id}/accept -u admin:changeme`
6. **Emotion stream**: `curl -X POST http://localhost:8000/emotions/stream -u admin:changeme -H "Content-Type: application/json" -d '{"stress_level":0.7,"impulsivity_score":0.4}'`
7. **Dashboard**: open `http://localhost:8501` — show Score Distribution and SHAP Explorer pages

---

## 7. Design Decisions (2 min)

### What to say

"Three key trade-offs:

1. **SQLite over Postgres**: The challenge says 'database of your choice'. SQLite gives us ACID transactions with zero ops. In production: Postgres with read replicas and row-level security.

2. **rq over Celery**: Single config variable (REDIS_URL) vs Celery's 4+ with silent failure modes. Same semantics, dramatically lower integration risk. In production at scale: Kafka for event sourcing.

3. **Redis Pub/Sub over Kafka for emotion stream**: Kafka provides durability and replay that Pub/Sub doesn't. But adding a fourth infrastructure component to a case study adds risk without demonstrating anything new architecturally. The code is identical — swap one function in worker.py.

The meta-decision: I optimized for **reliability of delivery** over **impressiveness of stack**. Every component works end-to-end. Nothing is half-implemented."

---

## Closing

"This system scores 150,000 borrowers with AUC 0.87, explains every decision with SHAP, experimentally proves emotional features don't help, implements regulatory fairness checks, and runs in Docker with a single command. Questions?"

---

## Timing Summary

| Section | Duration | Cumulative |
|---------|----------|------------|
| Opening | 2 min | 2 min |
| Architecture | 5 min | 7 min |
| ML Pipeline | 8 min | 15 min |
| Ethical Analysis | 5 min | 20 min |
| Backend | 5 min | 25 min |
| Live Demo | 3 min | 28 min |
| Design Decisions | 2 min | 30 min |
