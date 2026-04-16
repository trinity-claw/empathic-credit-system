# Empathic Credit System

ML-based credit scoring with SHAP explainability. Trained on [Give Me Some Credit](https://www.kaggle.com/c/GiveMeSomeCredit) (150k borrowers), served via FastAPI with real-time emotion ingestion, async job support, and full audit trail.

## Results

| Model | AUC | KS | Brier |
|---|---|---|---|
| Logistic Regression (baseline) | 0.8216 | 0.5012 | 0.1545 |
| **XGBoost Financial (calibrated)** | **0.8676** | **0.5764** | **0.0488** |
| XGBoost Emotional (calibrated) | 0.8668 | 0.5761 | 0.0490 |

Emotional features provide no meaningful lift (+0% AUC). See [`docs/model_card.md`](docs/model_card.md) for the full ethical analysis.

---

## Architecture

The system starts at the customer's brain and ends at a credit decision with a traceable audit trail.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Customer Brain / Mobile App (InfinitePay)                                   │
│  Emotion sensor captures: stress, impulsivity, stability, stress_events      │
└──────────────┬──────────────────────────────┬───────────────────────────────┘
               │ Emotion Stream               │ Credit Evaluation Request
               │ POST /emotions/stream        │ POST /credit/evaluate
               ▼                              ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                      FastAPI (api service)                                   │
│                                                                              │
│  X-Request-ID middleware (correlation header on every request)               │
│  HTTP Basic Auth on protected endpoints                                      │
│                                                                              │
│  POST /emotions/stream          → persist event + publish to Redis Pub/Sub   │
│  POST /credit/evaluate          → sync: XGBoost + SHAP → decision + limit   │
│  POST /credit/evaluate/async    → enqueue rq job → return job_id             │
│  GET  /credit/evaluate/{job_id} → poll async result                          │
│  POST /credit/offers/{id}/accept → enqueue deployment job                   │
│  GET  /credit/evaluations       → paginated evaluation history               │
│  GET  /credit/evaluations/stats → aggregate KPIs (approval rate, avg score)  │
│  GET  /credit/offers            → paginated offer history                    │
│  GET  /health, /healthz         → healthcheck (no auth)                      │
└──────┬───────────────────────────────┬──────────────────────────────────────┘
       │                               │
       ▼                               ▼
┌──────────────┐              ┌────────────────────┐
│   SQLite     │              │   Redis             │
│              │              │                     │
│  users       │              │  Queue: credit_eval  │  ← scoring jobs
│  emotional   │              │  Queue: credit_eval  │  ← deployment jobs
│   _events    │              │  Pub/Sub: emotion    │  ← stream consumers
│              │              │   _stream            │
│  credit_     │              └──────────┬───────────┘
│   offers     │                         │
│  notifications│                        │
│  credit_     │              ┌──────────▼───────────┐
│   evaluations│              │   rq worker           │
│  credit_     │              │                       │
│   events     │              │  _run_evaluation:     │
└──────────────┘              │    score+SHAP only    │
                              │    (no SQLite write)  │
                              │                       │
                              │  _deploy_credit_offer:│
                              │    accept offer        │
                              │    save notification   │
                              └───────────────────────┘
```

Sync `POST /credit/evaluate` writes `credit_evaluations`, `credit_events`, and `credit_offers` (when approved) from the API. `POST /credit/evaluate/async` runs scoring in the worker for polling only and does **not** insert evaluation rows; offer acceptance still uses the worker to update offers and notifications.

**ML pipeline per credit evaluation request**:
1. HTTP Basic auth + X-Request-ID correlation
2. XGBoost prediction (loaded at startup, not per-request — ~1ms latency)
3. IsotonicRegression calibration → true probability of default
4. Score mapping: `score = (1 - P(default)) × 1000`
5. Credit product assignment: limit + interest rate + type (based on score tier)
6. SHAP TreeExplainer → per-feature contributions (exact, O(TLD))
7. **Sync path only:** persist to SQLite (`credit_evaluations` + `credit_events` audit trail)
8. If approved: create `credit_offer` record, return `offer_id` in response

**Emotion stream pipeline**:
1. Mobile app posts emotional sensor reading to `POST /emotions/stream`
2. Event persisted to `emotional_events` table
3. Published to Redis Pub/Sub `ecs:emotion_stream` channel
4. Downstream consumers (analytics, risk aggregators) subscribe independently

**Credit deployment pipeline** (event-driven, decoupled from scoring):
1. User calls `POST /credit/offers/{id}/accept`
2. rq job enqueued: `_deploy_credit_offer`
3. Worker marks offer as accepted, saves `Notification` record

---

## Database Schema

The physical schema is created by SQLAlchemy in [`src/api/db.py`](src/api/db.py) (`Base.metadata.create_all` → SQLite by default). There are **6 tables**; foreign keys and indexes match the `ForeignKey` / `index=True` definitions in code.

**Diagram (DBML)** — copy the block below and paste it into [dbdiagram.io](https://dbdiagram.io/d) (or a `.dbml` file per the [DBML](https://dbml.dbdiagram.io/docs/) spec) to view the interactive ER diagram with relationships and notes.

```dbml
// Empathic Credit System — SQLite (see DATABASE_URL)
// Source of truth: src/api/db.py

Project ecs_api {
  Note: '''
    Runtime: SQLite file (DATABASE_URL), not a hosted server type in DBML.
    credit_events.request_id correlates with credit_evaluations.id / X-Request-ID (audit);
    there is no ORM ForeignKey on that column.
    notifications.offer_id points to credit_offers.id by convention only (no DB FK).
  '''
}

Table users {
  id varchar(36) [pk, note: 'UUID string']
  external_id varchar(128) [null, note: 'optional upstream id']
  created_at datetime [not null, note: 'UTC']
  current_credit_limit float [not null, default: 0, note: 'BRL']
  credit_type varchar(32) [null]
  last_score int [null, note: 'last ECS score 0–1000']

  Indexes {
    external_id [name: 'ix_users_external_id']
  }
}

Table credit_evaluations {
  id varchar(36) [pk, note: 'sync POST /credit/evaluate: equals X-Request-ID']
  created_at datetime [not null, note: 'UTC']
  decision varchar(10) [not null, note: 'APPROVED | DENIED']
  probability_of_default float [not null, note: 'calibrated P(default)']
  score int [not null, note: '0 = high risk, 1000 = low risk']
  model_used varchar(64) [not null, note: 'e.g. xgboost_financial_calibrated']
  request_payload json [not null, note: 'borrower features as submitted']
  shap_explanation json [not null, note: 'SHAP dict + top_factors']
}

Table credit_offers {
  id varchar(36) [pk, note: 'returned as offer_id when APPROVED']
  user_id varchar(36) [null, note: 'FK → users.id']
  evaluation_id varchar(36) [not null, note: 'FK → credit_evaluations.id']
  created_at datetime [not null, note: 'UTC']
  credit_limit float [not null, note: 'BRL']
  interest_rate float [not null, note: 'monthly rate']
  credit_type varchar(32) [not null, note: 'short_term | long_term | denied']
  status varchar(16) [not null, default: 'pending', note: 'pending | accepted']

  Indexes {
    evaluation_id [name: 'ix_credit_offers_evaluation_id']
    user_id [name: 'ix_credit_offers_user_id']
  }
}

Table credit_events {
  id integer [pk, increment, note: 'SQLite autoincrement']
  request_id varchar(36) [not null, note: 'same id space as credit_evaluations.id']
  event_type varchar(32) [not null, note: 'request_received | model_scored | …']
  created_at datetime [not null, note: 'UTC']
  detail json [null]

  Indexes {
    request_id [name: 'ix_credit_events_request_id']
  }
}

Table emotional_events {
  id varchar(36) [pk]
  user_id varchar(36) [null, note: 'FK → users.id']
  captured_at datetime [not null, note: 'UTC']
  stress_level float [null, note: '0–1']
  impulsivity_score float [null, note: '0–1']
  emotional_stability float [null, note: '0–1']
  financial_stress_events_7d int [null, note: '0–20']
  raw_payload json [null, note: 'full POST /emotions/stream body']

  Indexes {
    user_id [name: 'ix_emotional_events_user_id']
  }
}

Table notifications {
  id varchar(36) [pk]
  user_id varchar(36) [null, note: 'FK → users.id']
  offer_id varchar(36) [null, note: 'logical → credit_offers.id (no FK in ORM)']
  created_at datetime [not null, note: 'UTC']
  notification_type varchar(32) [not null]
  payload json [null]
  status varchar(16) [not null, default: 'sent']

  Indexes {
    user_id [name: 'ix_notifications_user_id']
  }
}

// --- Foreign keys (SQLAlchemy) ----------------------------------------------

Ref: credit_offers.user_id > users.id
Ref: credit_offers.evaluation_id > credit_evaluations.id
Ref: emotional_events.user_id > users.id
Ref: notifications.user_id > users.id
```

### Local database (DBeaver)

- Default file DB: `data/ecs.db` (see `DATABASE_URL` in [`.env.example`](.env.example)). The file is created on first API startup; tables start **empty** until you call the API.
- Connect in DBeaver as **SQLite**, path to `data/ecs.db` from the project root (same path the running API uses, or you will see different data).

### Example SQL queries (reproducible)

Run the **prerequisite** curls first so each query returns rows. Use the same credentials as the API (`admin` / `changeme` by default).

**Prerequisite A — one emotional event (for query 1):**

```bash
curl -sS -X POST http://localhost:8000/emotions/stream \
  -u admin:changeme \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "stress_level": 0.72,
    "impulsivity_score": 0.45,
    "emotional_stability": 0.38,
    "financial_stress_events_7d": 3
  }'
```

**Prerequisite B — one high-risk evaluation (for query 2; expect `DENIED`, score under 400):**

```bash
curl -sS -X POST http://localhost:8000/credit/evaluate \
  -u admin:changeme \
  -H "Content-Type: application/json" \
  -d '{
    "revolving_utilization": 0.92,
    "age": 28,
    "debt_ratio": 0.45,
    "monthly_income": 3000,
    "open_credit_lines": 8,
    "past_due_30_59": 2,
    "past_due_60_89": 1,
    "past_due_90": 3,
    "had_past_due_sentinel": 1
  }'
```

**Prerequisite C — any synchronous evaluation (for queries 3–5):** repeat Prerequisite B and/or run an approval example from [API Usage](#api-usage) so `credit_events` and `credit_evaluations` have rows.

**1. Emotional events for one user in the last 7 days** (needs Prerequisite A):

```sql
SELECT id, captured_at, stress_level, impulsivity_score, emotional_stability
FROM emotional_events
WHERE user_id = '550e8400-e29b-41d4-a716-446655440000'
  AND captured_at >= datetime('now', '-7 days')
ORDER BY captured_at DESC;
```

**2. High-risk evaluations with SHAP top factor** (needs Prerequisite B):

```sql
SELECT id, decision, score, probability_of_default,
       json_extract(shap_explanation, '$.top_factors[0].feature') AS top_factor,
       created_at
FROM credit_evaluations
WHERE score < 400
ORDER BY score ASC
LIMIT 100;
```

**3. Audit trail for the latest credit evaluation** (needs Prerequisite C; uses the most recent `request_id` from evaluations):

```sql
SELECT ce.id, ce.request_id, ce.event_type, ce.created_at, ce.detail
FROM credit_events ce
WHERE ce.request_id = (
  SELECT id FROM credit_evaluations ORDER BY created_at DESC LIMIT 1
)
ORDER BY ce.id ASC;
```

**4. Recent approved credit offers** (needs at least one synchronous `APPROVED` evaluation):

```sql
SELECT id, evaluation_id, credit_limit, interest_rate, credit_type, status, created_at
FROM credit_offers
ORDER BY created_at DESC
LIMIT 20;
```

**5. Decision mix across stored evaluations** (needs Prerequisite C):

```sql
SELECT decision, COUNT(*) AS n, ROUND(AVG(score), 1) AS avg_score
FROM credit_evaluations
GROUP BY decision;
```

---

## Model & data artifacts (why they are not in Git)

Binary model weights (`models/*.pkl`, `*.joblib`), generated metrics (`models/metrics_log.json`), processed splits (`data/processed/*.parquet`), and the raw CSV under `data/raw/` are **gitignored** on purpose. The **source of truth** for how they are produced is the code plus notebooks `02`–`04` (and [`src/data/split.py`](src/data/split.py)).

**Why keep artifacts out of Git?** (common ML-repo practice)

- **Size and history** — weights can be large; committing them slows clones and inflates the object database.
- **Not source code** — what you review is the training pipeline (notebooks/scripts + splits), not every binary blob from each experiment.
- **Retrains churn** — each run produces new pickles; Git diffs on `.pkl` are not meaningful for code review.
- **Risk control** — some teams avoid accidentally committing trained weights that might reflect sensitive data.

Ignoring them is fine **as long as** there is a clear way to obtain files: this repo documents **`./start-from-scratch.sh`** (full bootstrap), manual commands below, or your own CI/release bucket that restores `models/` before `docker compose build`.

**Tests:** [`tests/test_api.py`](tests/test_api.py) mocks `model_store.predict`, so `uv run pytest` can pass without any `models/*.pkl`; the **running** API (and Docker images) still need the four files below.

**What the API expects locally** (paths from [`src/api/settings.py`](src/api/settings.py)):

| File | Role |
|------|------|
| `models/xgboost_financial.pkl` | Financial XGBoost |
| `models/xgboost_financial_calibrator.pkl` | Isotonic calibrator |
| `models/xgboost_emotional.pkl` | Emotional XGBoost |
| `models/xgboost_emotional_calibrator.pkl` | Emotional calibrator |

**Docker:** the `Dockerfile` runs `COPY models/ ./models/`. Build the image only **after** those files exist on your machine (see bootstrap below).

---

## Quickstart

### Full stack from zero (new machine / fresh clone)

One script installs Python deps, creates `.env` if missing, downloads OpenML data when needed, builds `data/processed/*.parquet`, **executes notebooks 02–04 headlessly** to populate `models/`, runs `npm install` in `frontend/` if needed, then starts Redis + API + worker + Next.js (same as `start.sh`):

```bash
chmod +x start-from-scratch.sh start.sh
./start-from-scratch.sh
```

- Requires **network** for the first OpenML download.
- Notebook execution can take **several minutes** (XGBoost + SHAP). Override per-notebook timeout with `ECS_NB_TIMEOUT` (seconds, default `3600`).
- Press **Ctrl+C** to stop all services started by `start.sh`.

If you already have the four pickle files above, use **`./start.sh`** only (no retrain). It runs [`scripts/normalize_env.py`](scripts/normalize_env.py) and clears conflicting calibrator env exports before Uvicorn — details under **Demo data & environment helpers** below.

### Local (manual)

```bash
# 1. Install dependencies
uv sync

# 2. Set environment variables
cp .env.example .env
# For local Redis (not Docker hostname "redis"), set e.g. REDIS_URL=redis://localhost:6379/0

# 3. Download dataset (OpenML id 46929, same schema as Kaggle Give Me Some Credit)
uv run python -c "
from pathlib import Path
from sklearn.datasets import fetch_openml
Path('data/raw').mkdir(parents=True, exist_ok=True)
df = fetch_openml(data_id=46929, as_frame=True).frame
df.to_csv('data/raw/cs-training.csv')
"

# 4. Stratified splits → data/processed/{train,val,test}.parquet
uv run python -m src.data.split

# 5. Train models for the API — notebooks write to ../models/ when cwd is notebooks/
#    • Interactive: cd notebooks && uv run jupyter lab — run 02 → 03 → 04 in order.
#    • Headless (same sequence as start-from-scratch.sh):
cd notebooks
export MPLBACKEND=Agg
NB_TIMEOUT="${ECS_NB_TIMEOUT:-3600}"
for nb in 02_baseline_logreg 03_xgboost 04_emotional_features; do
  uv run python -m jupyter nbconvert --to notebook --execute \
    --Execute.timeout="${NB_TIMEOUT}" \
    --output "/tmp/ecs_${nb}_executed.ipynb" \
    "${nb}.ipynb"
done
cd ..

# 6. Start the API (or ./start.sh for Redis + worker + frontend)
uv run uvicorn src.api.main:app --reload
```

Exploratory notebooks (`01`, `05`, `06`, …) are optional for running the API; **`02` → `03` → `04`** are the minimum chain that writes the four pickle/calibrator files under `models/`.

### Docker

```bash
docker compose up --build
```

Ensure `models/` contains the four pickle files **before** `docker compose build`, or the API container will fail at startup when loading weights.

API available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.
Frontend dashboard at `http://localhost:3000`. Default API credentials: `admin` / `changeme`.

### Frontend (Next.js + shadcn/ui)

```bash
cd frontend
npm install
npm run dev
```

Opens at `http://localhost:3000` with 5 pages:
- **Dashboard** — live KPIs (approval rate, avg score), recent decisions, credit product tiers
- **Credit assessment** — interactive form: submit borrower data, receive score + SHAP waterfall + offer acceptance
- **History** — paginated evaluation history with expandable SHAP details per row
- **Analytics** — operational metrics (live) + ROC curve, calibration plot, model comparison (training data)
- **Fairness** — 4/5ths rule by age/income cohort, LGPD regulatory risk analysis

### Demo data & environment helpers

With the API running (`./start.sh` or `docker compose up`), you can fill **`data/ecs.db`** with many synthetic credit decisions (mix of **clear approvals**, **clear denials**, **borderline** financial-only cases, emotional-model paths including a “rescue” profile) plus emotion-stream rows for the dashboard:

```bash
uv run python scripts/seed_frontend_demo.py
```

Use `ECS_API_BASE` (default `http://127.0.0.1:8000`), `API_USERNAME`, and `API_PASSWORD` if they differ from defaults; flags `--sleep` and `--timeout` throttle SHAP-heavy requests.

**`.env` vs trained files:** `start.sh` / `start-from-scratch.sh` invoke [`scripts/normalize_env.py`](scripts/normalize_env.py) so missing paths point at the four pickles under `models/` when those files exist, and legacy **`calibration_path` / `CALIBRATION_PATH`** lines are removed from `.env` (they map to the same field as `CALIBRATOR_PATH`). `start.sh` also **`unset`s `CALIBRATION_PATH` / `calibration_path`** in the shell before Uvicorn so stray exports do not override a cleaned `.env`.

**Settings:** [`src/api/settings.py`](src/api/settings.py) coalesces legacy calibrator keys during model validation so pydantic-settings does not treat `CALIBRATION_PATH` from the process environment as an extra forbidden field when `CALIBRATOR_PATH` is also set.

---

## API Usage

### Synchronous credit evaluation

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
  "credit_limit": 50000.0,
  "interest_rate": 0.015,
  "credit_type": "long_term",
  "offer_id": "f1e2d3c4-...",
  "model_used": "xgboost_financial_calibrated",
  "shap_explanation": { ... },
  "top_factors": [
    {"feature": "past_due_90", "contribution": -0.02, "direction": "decreases_risk"},
    ...
  ]
}
```

### Accept credit offer (async deployment)

```bash
curl -X POST http://localhost:8000/credit/offers/{offer_id}/accept \
  -u admin:changeme
# → {"offer_id": "...", "job_id": "...", "status": "queued"}
```

The rq worker runs `_deploy_credit_offer`, persists a `Notification`, and calls `deliver_notification`. If `NOTIFICATION_WEBHOOK_URL` is set, the worker **POSTs JSON** to that URL; otherwise it logs a mock “mobile push” event.

#### Testing the notification webhook (webhook.site)

You can use [Webhook.site](https://webhook.site) (or any request bin) as a stand-in for an FCM/APNS gateway: it gives you a unique HTTPS URL that shows each request instantly.

1. Open Webhook.site and copy **Your unique URL** (keep this private; do not commit it).
2. In your **`.env`** (not tracked by git), set:
   ```bash
   NOTIFICATION_WEBHOOK_URL=https://webhook.site/<your-uuid>
   ```
3. **Restart the worker** so it picks up the variable (`docker compose restart worker`, or restart `./start.sh` / your local worker process).
4. Obtain an **approved** evaluation with an `offer_id` (e.g. `POST /credit/evaluate` with a low-risk payload, or use the dashboard **Credit assessment** page).
5. Call `POST /credit/offers/{offer_id}/accept` (curl or UI). When the job finishes, Webhook.site should show a **POST** with JSON like:
   ```json
   {
     "notification_id": "...",
     "user_id": null,
     "offer_id": "...",
     "type": "credit_deployed",
     "payload": {
       "credit_limit": 50000.0,
       "interest_rate": 0.015,
       "credit_type": "long_term"
     }
   }
   ```

If nothing appears, confirm Redis + worker are running and check worker logs for `notification.delivery_failed`.

### Real-time emotion stream

```bash
curl -X POST http://localhost:8000/emotions/stream \
  -u admin:changeme \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "stress_level": 0.72,
    "impulsivity_score": 0.45,
    "emotional_stability": 0.38,
    "financial_stress_events_7d": 3
  }'
# → {"event_id": "...", "status": "received"}
```

### Async evaluation

Queues scoring on the rq worker and returns the result when polled. This path demonstrates the job queue and **does not** write rows to `credit_evaluations` / `credit_events`; use synchronous `POST /credit/evaluate` for a persisted audit trail and DBeaver-friendly history.

```bash
# Enqueue (requires Redis + worker, e.g. docker compose or ./start.sh)
curl -X POST http://localhost:8000/credit/evaluate/async \
  -u admin:changeme -H "Content-Type: application/json" -d '{...}'
# → {"job_id": "abc123", "status": "queued"}

# Poll
curl http://localhost:8000/credit/evaluate/abc123 -u admin:changeme
```

---

## Project Structure

```
src/
  data/
    load.py            # Data loading, column mapping, missing/sentinel treatment
    split.py           # Stratified 70/15/15 train/val/test split
    emotional.py       # Synthetic emotional feature injection
  evaluation/
    metrics.py         # AUC, KS, Brier, precision@base_rate, plots
  explainability/
    shap_explainer.py  # CreditExplainer wrapping shap.TreeExplainer
  api/
    main.py            # FastAPI app (lifespan, middleware, routes)
    schemas.py         # Pydantic models: CreditRequest, CreditResponse, EmotionStreamRequest
    auth.py            # HTTP Basic authentication
    db.py              # SQLAlchemy + SQLite (6 tables)
    model_store.py     # Singleton model/explainer + credit product mapping
    worker.py          # rq jobs: scoring, deployment; Redis Pub/Sub publisher
    settings.py        # Pydantic Settings from .env
notebooks/
  01_eda.ipynb                  # Exploratory data analysis
  02_baseline_logreg.ipynb      # Logistic regression baseline
  03_xgboost.ipynb              # XGBoost financial model + calibration + test set eval
  04_emotional_features.ipynb   # Emotional features experiment
  05_shap_analysis.ipynb        # SHAP + ethical conclusion
  06_fairness_analysis.ipynb    # Disparate impact analysis (4/5ths rule, LGPD)
docs/
  model_card.md           # Full model card with fairness and ethics analysis
  demo_guide.md           # Detailed demo script (Portuguese)
  presentation_index.md   # 10–15 min talk index + requirement→evidence map
tests/
  test_metrics.py      # Evaluation metrics (KS, precision, AUC)
  test_emotional.py    # Emotional feature injection + R² non-circularity
  test_api.py          # API integration: all endpoints + auth + middleware
  test_db.py           # Database: all tables, save/accept/notify flows
  test_model_store.py  # predict() + credit product mapping
  test_shap_explainer.py  # CreditExplainer + ExplanationResult
  test_load.py         # Data loading + sentinel handling
  test_split.py        # Stratified splits
```

---

## Development

```bash
make test    # uv run pytest
make lint    # uv run ruff check + format check
make format  # uv run ruff check --fix + format
make check   # lint + test (full local Python gate)
make serve   # uv run uvicorn src.api.main:app --reload
make docker  # docker compose up --build
```

### Development workflow

After `uv sync` (include dev dependencies so `pre-commit` is available):

```bash
uv run pre-commit install   # once per clone: fast hooks on every commit
uv run pre-commit run --all-files   # optional: run hooks on the whole tree
```

Commit hooks run **Ruff** (lint with auto-fix where safe, plus format) and lightweight file checks (trailing whitespace, TOML/YAML, merge conflicts, etc.). They intentionally **do not** run the full test suite; use `make check` or `make test` before pushing. The Next.js app under `frontend/` has its own toolchain (`npm run lint`, `npm run build`).

---

## Data Privacy and Security

### Sensitive Data Classification

Emotional data (stress, impulsivity, stability) is **highly sensitive** — it can serve as a proxy for mental health status, disability, or protected characteristics. Under Brazil’s LGPD (Article 11), this is **sensitive personal data** (*dados pessoais sensíveis*), requiring explicit consent and the highest protection tier.

### Encryption

| Layer | Approach |
|---|---|
| In transit | TLS 1.3 (enforced at load balancer / API gateway in production) |
| At rest (SQLite) | Disk-level encryption (LUKS on Linux) or SQLCipher; in production: Postgres with Transparent Data Encryption |
| Redis | TLS-enabled Redis 7+ with AUTH; in production: Redis Enterprise with at-rest encryption |

### Pseudonymisation

- `users.external_id` stores a pseudonymised identifier — never the raw InfinitePay user ID. In production, this would be a SHA-256 hash enforced at the application layer
- `emotional_events.user_id` is a UUID that maps to the pseudonymised profile, not to PII
- Raw PII (name, CPF, address) is never stored in the ECS database — it remains in the source system of record
- SHAP explanations reference feature names (`revolving_utilization`, `age`) — not individual identities

### LGPD Compliance

| Requirement | Implementation |
|---|---|
| **Right to explanation** | Every decision includes SHAP values per feature — legally defensible explanation of automated decisions |
| **Data minimization** | Only features required for scoring are stored; raw sensor data is optional |
| **Consent** | Emotional features are opt-in; financial-only model is deployed by default |
| **Audit trail** | `credit_events` table logs every lifecycle event with timestamps |
| **Retention** | Recommended policy: emotional events purged after 90 days; evaluations retained for 5 years per BACEN |
| **Right to erasure** | Pseudonymised records can be unlinked by deleting the external_id mapping |

### Trade-offs and Assumptions

- This case study uses HTTP Basic Auth with env-variable credentials. Production would use OAuth 2.0 / JWT with short-lived tokens.
- The emotional model is **not deployed** — zero emotional data influences production credit decisions. This was a deliberate ethical choice backed by the experiment showing -0.0008 AUC delta.
- SQLite is used for case study simplicity. Production at InfinitePay scale would use Postgres with row-level security policies.

---

## Design Decisions

**SQLite over Postgres**: The case permits "database of your choice". SQLite provides ACID transactions with zero ops overhead — appropriate for a case study. In production at InfinitePay scale: Postgres with read replicas.

**rq over Celery**: Single-variable config (`REDIS_URL`) vs Celery's 4+ variables with silent failure modes. Same queue semantics, far lower integration risk. In production: Pub/Sub or Kafka depending on volume.

**Redis Pub/Sub over Kafka for emotion stream**: Kafka provides durability, replay, and consumer group semantics that Kafka needs for production. Redis Pub/Sub was chosen for this case study to avoid adding a fourth infrastructure component. The design is identical — swap the publisher in `worker.py:publish_emotional_event`.

**Financial-only model for production**: Emotional features showed -0.0008 AUC delta (slightly worse). The regulatory and privacy costs outweigh any marginal benefit. See [`docs/model_card.md`](docs/model_card.md).
