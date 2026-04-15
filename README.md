# Empathic Credit System

ML-based credit scoring with SHAP explainability. Trained on [Give Me Some Credit](https://www.kaggle.com/c/GiveMeSomeCredit) (150k borrowers), served via FastAPI with async job support.

## Results

| Model | AUC | KS | Brier |
|---|---|---|---|
| Logistic Regression (baseline) | 0.8216 | 0.5012 | 0.1545 |
| **XGBoost Financial (calibrated)** | **0.8676** | **0.5764** | **0.0488** |
| XGBoost Emotional (calibrated) | 0.8668 | 0.5761 | 0.0490 |

Emotional features provide no meaningful lift (+0% AUC). See [`docs/model_card.md`](docs/model_card.md) for the full ethical analysis.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client                               │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP Basic Auth
         ┌──────────────▼──────────────┐
         │        FastAPI (api)         │
         │  POST /credit/evaluate       │  ← synchronous
         │  POST /credit/evaluate/async │  ← enqueues rq job
         │  GET  /credit/evaluate/{id}  │  ← poll result
         │  GET  /health                │
         └──────┬──────────┬────────────┘
                │          │
         ┌──────▼──┐  ┌────▼──────┐
         │ SQLite  │  │   Redis   │
         │  (DB)   │  │  (queue)  │
         └─────────┘  └────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  rq worker  │
                    │  (scoring)  │
                    └─────────────┘
```

**Model pipeline per request**:
1. HTTP Basic auth
2. XGBoost prediction (loaded at startup, not per-request)
3. IsotonicRegression calibration → true probability
4. SHAP TreeExplainer → per-feature contributions
5. Persist to SQLite, return `CreditResponse`

## Quickstart

### Local

```bash
# 1. Install dependencies
uv sync

# 2. Set environment variables
cp .env.example .env

# 3. Download dataset (required for training notebooks only)
uv run python -c "
from sklearn.datasets import fetch_openml
df = fetch_openml(data_id=46929, as_frame=True).frame
df.to_csv('data/raw/cs-training.csv')
"

# 4. Prepare data and train models (run notebooks 01-05 in order)
uv run jupyter lab

# 5. Start the API
uv run uvicorn src.api.main:app --reload
```

### Docker

```bash
docker compose up --build
```

API available at `http://localhost:8000`. Default credentials: `admin` / `changeme`.

## API Usage

### Synchronous evaluation

```bash
curl -X POST http://localhost:8000/credit/evaluate \
  -u admin:changeme \
  -H "Content-Type: application/json" \
  -d '{
    "revolving_utilization": 0.3,
    "age": 45,
    "debt_ratio": 0.2,
    "monthly_income": 5000,
    "open_credit_lines": 4,
    "past_due_30_59": 0,
    "past_due_60_89": 0,
    "past_due_90": 0,
    "real_estate_loans": 1,
    "dependents": 2,
    "had_past_due_sentinel": 0
  }'
```

**Response:**

```json
{
  "request_id": "...",
  "decision": "APPROVED",
  "probability_of_default": 0.026,
  "score": 973,
  "model_used": "xgboost_financial_calibrated",
  "shap_explanation": { ... },
  "top_factors": [
    {"feature": "past_due_90", "contribution": -0.02, "direction": "decreases_risk"},
    ...
  ]
}
```

### Async evaluation

```bash
# Enqueue
curl -X POST http://localhost:8000/credit/evaluate/async \
  -u admin:changeme -H "Content-Type: application/json" -d '{...}'
# → {"job_id": "abc123", "status": "queued"}

# Poll
curl http://localhost:8000/credit/evaluate/abc123 -u admin:changeme
```

## Project Structure

```
src/
  data/
    load.py          # Data loading, column mapping, missing/sentinel treatment
    split.py         # Stratified 70/15/15 train/val/test split
    emotional.py     # Synthetic emotional feature injection
  evaluation/
    metrics.py       # AUC, KS, Brier, precision@base_rate, plots
  explainability/
    shap_explainer.py  # CreditExplainer wrapping shap.TreeExplainer
  api/
    main.py          # FastAPI app (lifespan, routes)
    schemas.py       # Pydantic CreditRequest / CreditResponse
    auth.py          # HTTP Basic authentication
    db.py            # SQLAlchemy + SQLite
    model_store.py   # Singleton model/explainer loaded at startup
    worker.py        # rq queue integration
    settings.py      # Pydantic Settings from .env
notebooks/
  01_eda.ipynb                 # Exploratory data analysis
  02_baseline_logreg.ipynb     # Logistic regression baseline
  03_xgboost.ipynb             # XGBoost financial model + calibration
  04_emotional_features.ipynb  # Emotional features experiment
  05_shap_analysis.ipynb       # SHAP + ethical conclusion
docs/
  model_card.md      # Full model card with fairness and ethics analysis
tests/
  test_metrics.py    # Unit tests for evaluation metrics
  test_emotional.py  # Unit tests for emotional feature injection
  test_api.py        # Integration tests for FastAPI endpoints
```

## Development

```bash
# Run tests
uv run pytest

# Lint + format
uv run ruff check && uv run ruff format
```

## Design Decisions

**SQLite over Postgres**: The case permits "database of your choice". SQLite provides ACID transactions with zero ops overhead — appropriate for a case study. In production at InfinitePay scale: Postgres with read replicas.

**rq over Celery**: Single-variable config (`REDIS_URL`) vs Celery's 4+ variables with silent failure modes. Same queue semantics, far lower integration risk. In production: Pub/Sub or Kafka depending on volume.

**Financial-only model for production**: Emotional features showed -0.0008 AUC delta (slightly worse). The regulatory and privacy costs outweigh any marginal benefit. See [`docs/model_card.md`](docs/model_card.md).
