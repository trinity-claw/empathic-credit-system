# Deep Study Guide — Empathic Credit System

Preparation material for the presentation and technical Q&A with Pablo.

---

## 1. XGBoost Internals

### What it is

XGBoost (eXtreme Gradient Boosting) is an ensemble of decision trees trained sequentially. Each new tree corrects the errors (residuals) of the previous ensemble. Formally, at iteration t the model minimizes:

```
L(t) = Σ l(yi, ŷi(t-1) + ft(xi)) + Ω(ft)
```

where `l` is the loss function (log-loss for binary classification), `ft` is the new tree, and `Ω` is a regularization term on tree complexity (number of leaves + L2 on leaf weights).

### Key hyperparameters in our model

- **n_estimators**: number of boosting rounds (trees). More = more capacity but risk of overfitting.
- **max_depth**: maximum tree depth. Controls complexity. Our model uses default (6).
- **learning_rate (eta)**: shrinkage factor applied to each tree. Lower = more trees needed but better generalization.
- **subsample / colsample_bytree**: fraction of data/features used per tree. Acts as regularization via random subsampling.

### Why XGBoost over alternatives

- **vs Random Forest**: XGBoost is sequential (each tree learns from errors) while RF is parallel (bagging). For tabular data with moderate size, gradient boosting consistently outperforms bagging.
- **vs Neural Networks**: For 150k rows with 11 features, a neural network would overfit without heavy regularization and wouldn't be more interpretable. SHAP TreeExplainer gives exact Shapley values for trees but only approximate ones for neural nets.
- **vs LightGBM/CatBoost**: Functionally similar. XGBoost was chosen for SHAP compatibility (TreeExplainer is natively supported) and widespread adoption in credit risk.

### If asked "Why not a neural network?"

Say: "For 150k rows and 11 features, a neural network offers no advantage over gradient boosted trees. The data is tabular, not sequential or spatial. Trees handle missing values natively, require less preprocessing, and SHAP TreeExplainer gives exact (not approximate) Shapley values — important for regulatory compliance. In credit risk, interpretability isn't optional."

Do NOT say: "I don't know how to use neural networks" or "Neural networks are always better."

---

## 2. AUC-ROC

### What it means

AUC-ROC (Area Under the Receiver Operating Characteristic curve) measures ranking quality: the probability that a randomly chosen positive example ranks higher than a randomly chosen negative example.

- **0.5** = random guessing (no discrimination)
- **0.8** = good discrimination
- **0.87** = strong discrimination (what our model achieves)
- **1.0** = perfect discrimination

### Geometric interpretation

The ROC curve plots True Positive Rate (sensitivity) vs False Positive Rate (1 - specificity) at every threshold. AUC is the area under this curve. A model that perfectly separates classes has a curve that goes up-left to (0,1) then right to (1,1) — area = 1.0.

### Limitations

AUC doesn't tell you about calibration. A model with AUC 0.90 might predict P(default) = 0.8 for everyone who actually defaults at P = 0.3. That's great ranking, terrible calibration. That's why we also measure Brier score and use IsotonicRegression calibration.

### If asked "Is AUC 0.87 good enough for production?"

Say: "For credit risk with this dataset, AUC 0.87 is strong — the original Kaggle competition winners achieved 0.86-0.87. But AUC alone isn't sufficient for deployment. We need calibration (Brier 0.049), fairness checks (4/5ths rule passes), and SHAP for explainability. All three are implemented."

---

## 3. KS (Kolmogorov-Smirnov)

### What it means

KS = maximum vertical distance between the cumulative distribution functions (CDFs) of scores for the positive class (defaults) and negative class (non-defaults). It measures how well the model separates the two populations.

- **KS > 0.30**: acceptable for credit scoring
- **KS > 0.40**: good
- **Our model**: KS = 0.58 — excellent

### Why it matters in Brazilian credit

KS is the standard metric in the Brazilian credit market (used by BACEN, Serasa, SPC). Banks and fintechs report KS to regulators. It's more intuitive than AUC for business stakeholders: "at the optimal cutoff, 58% of the bad population has been separated from the good population."

### Implementation

Our `compute_ks()` in `metrics.py` sorts predictions, computes cumulative sums for each class, and finds the max absolute difference. Manual implementation for transparency; equivalent to `scipy.stats.ks_2samp`.

---

## 4. Brier Score and Calibration

### What Brier score measures

Brier score = mean squared error between predicted probabilities and actual outcomes:

```
Brier = (1/N) Σ (pi - yi)²
```

where `pi` is the predicted probability and `yi` ∈ {0, 1}. Lower is better. A model that always predicts the base rate (0.0668) gets Brier ≈ 0.0624. Our calibrated model achieves 0.049 — better than the naive baseline.

### Calibration vs discrimination

- **Discrimination** (AUC, KS): can the model rank borrowers by risk?
- **Calibration** (Brier, calibration curve): when the model says "10% default probability," do 10% of those borrowers actually default?

Both matter. A model with great AUC but poor calibration will rank correctly but assign wrong probabilities — leading to wrong credit limits and interest rates.

### IsotonicRegression calibration

XGBoost outputs are poorly calibrated because the trees optimize log-loss at each split, not global probability alignment. IsotonicRegression fits a monotonic piecewise-constant function mapping raw probabilities to calibrated ones. We fit it on the validation set and evaluate on a held-out test set to avoid overfitting the calibrator.

### If asked "Why not Platt scaling?"

Say: "Platt scaling fits a logistic function (sigmoid) to the raw probabilities. This assumes the calibration error is logistic-shaped. For tree ensembles, the error is typically more complex — an S-curve. IsotonicRegression makes no parametric assumption, it just forces monotonicity. The Brier score improvement confirms this: 0.055 raw → 0.049 calibrated."

---

## 5. SHAP (SHapley Additive exPlanations)

### Foundation: Shapley values from game theory

Shapley values come from cooperative game theory (Lloyd Shapley, 1953). Given a "game" (model prediction) with "players" (features), the Shapley value of a feature is its average marginal contribution across all possible coalitions (subsets of features).

```
φi = Σ [|S|! (n-|S|-1)! / n!] × [f(S ∪ {i}) - f(S)]
```

This is the only attribution method that satisfies four axioms: efficiency (values sum to prediction - baseline), symmetry, dummy (zero contribution for unused features), and linearity.

### TreeExplainer: exact computation

For tree ensembles, SHAP provides TreeExplainer which computes exact Shapley values in O(TLD²) time where T = number of trees, L = max leaves per tree, D = max depth. This is polynomial, not exponential — it exploits the tree structure to enumerate coalitions efficiently.

Key property: `base_value + Σ shap_values = model prediction` (in log-odds space for binary classification).

### In our system

- `CreditExplainer` wraps `shap.TreeExplainer`
- `explain_one()` returns `ExplanationResult` with base_value, prediction, contributions dict, and top 5 factors
- Every API response includes the full SHAP explanation
- The `direction` field ("increases_risk" / "decreases_risk") is derived from the sign of the SHAP value

### Global vs local explanations

- **Global** (summary plot): which features are most important across all predictions? → `past_due_90`, `revolving_utilization`, `age` dominate
- **Local** (waterfall): why was THIS specific borrower approved/denied? → "Your past_due_90 = 0 decreased your risk by 0.52 log-odds"

### If asked "How do you know SHAP is correct?"

Say: "TreeExplainer computes exact Shapley values — not approximations. We verify by checking that base_value + sum(shap_values) = model prediction for every request. This is tested in `test_shap_explainer.py::test_prediction_equals_base_plus_shap_sum`."

---

## 6. Credit Risk Fundamentals

### PD / LGD / EAD framework

- **PD (Probability of Default)**: What we model. Our XGBoost predicts P(default within 2 years).
- **LGD (Loss Given Default)**: How much is lost if the borrower defaults. Typically 40-60% for unsecured credit. Not modeled here — would require recovery data.
- **EAD (Exposure at Default)**: The outstanding balance at time of default.
- **Expected Loss = PD × LGD × EAD**

Our model focuses on PD because it's the component that benefits most from ML (behavioral data, feature interactions). LGD and EAD are typically simpler models or fixed assumptions.

### Basel / BACEN requirements

Basel II/III require banks to estimate PD, LGD, EAD for IRB (Internal Ratings-Based) approach. BACEN (Brazil's central bank) adopts Basel standards. Key requirements:
- Models must be validated on out-of-time data
- Discrimination (AUC/KS) and calibration must be monitored
- Explanations must be available for adverse action (customer denied credit)

### Credit scoring vs credit risk

- **Scoring**: ranking borrowers by risk (what we do)
- **Risk management**: setting limits, pricing, reserves (partially addressed via score-to-product mapping in `_compute_credit_product`)

### If asked "How would you set credit limits in production?"

Say: "In our system, credit limits are mapped from score tiers — a simplified version. In production, you'd use an optimization model that maximizes expected revenue subject to risk constraints. Inputs: PD from our model, LGD estimate, target loss rate, customer lifetime value. The limit is where marginal expected revenue = marginal expected loss."

---

## 7. Fairness and the 4/5ths Rule

### The 4/5ths rule

From US EEOC (Equal Employment Opportunity Commission) Uniform Guidelines: if the selection rate for any protected group is less than 80% (4/5ths) of the selection rate for the group with the highest rate, there is prima facie evidence of adverse impact.

Example: if men are approved at 90% and women at 65%, the ratio is 65/90 = 72% < 80% → disparate impact.

### Our implementation

- Tested across **age cohorts** (18-29, 30-39, 40-49, 50-59, 60+) and **income quartiles** (Q1-Q4)
- Age: all cohorts pass the 4/5ths rule
- Income: Q1 is borderline at ~82% of Q4's rate — passes but warrants monitoring
- Subgroup calibration: checked that probabilities are well-calibrated within each cohort

### LGPD relevance

LGPD Article 20: the data subject has the right to request review of decisions made solely by automated processing. SHAP provides this. Article 11: sensitive data (which emotional data qualifies as) requires explicit consent and higher protection.

### If asked "Is the 4/5ths rule legally binding in Brazil?"

Say: "No, it's a US standard. Brazil's LGPD and BACEN regulations don't specify a numeric threshold. But the 4/5ths rule is the most widely recognized quantitative test for disparate impact, and applying it proactively shows the model was evaluated for fairness before deployment — which LGPD Article 6 (non-discrimination principle) requires."

---

## 8. System Design

### Event-driven architecture

Our credit deployment flow is event-driven: evaluation → offer created → user accepts → rq job enqueued → worker processes → notification created. Each step is decoupled, auditable, and retryable.

Benefits:
- **Fairness**: scoring and deployment are separate — you can add human-in-the-loop review between them
- **Traceability**: every state transition is logged in `credit_events`
- **Resilience**: if the worker fails, the job stays in Redis and is retried

### Redis Pub/Sub vs Kafka

| Aspect | Redis Pub/Sub | Kafka |
|--------|--------------|-------|
| Durability | Fire-and-forget — if no subscriber, message is lost | Persistent log — messages retained for configurable period |
| Replay | Not possible | Consumers can rewind to any offset |
| Consumer groups | Not supported | Built-in — multiple consumers can share load |
| Throughput | ~100k msg/s per node | ~1M msg/s per partition |
| Complexity | Single Redis dependency | Broker + Zookeeper + schema registry |

We use Redis Pub/Sub because: (1) the DB is our source of truth (emotion events are persisted before publishing), (2) adding Kafka would be a fourth infrastructure component with no architectural benefit for a case study.

### If asked "What happens if Redis goes down?"

Say: "Three scenarios: (1) Emotion publishing fails — the event is already persisted in SQLite, so it's non-fatal. The `try/except` in `ingest_emotion_event` handles this. (2) rq jobs in the queue — they're serialized in Redis. If Redis restarts with persistence (RDB/AOF), jobs survive. Without persistence, jobs are lost and must be re-enqueued. (3) The API itself doesn't depend on Redis for sync evaluations — only for async jobs and Pub/Sub."

### If asked "How would you scale this to 10M users?"

Say: "Four changes: (1) Replace SQLite with Postgres — read replicas for scoring queries, write primary for evaluations. (2) Replace Redis Pub/Sub with Kafka — durability, consumer groups, and partitioned throughput. (3) Horizontal scaling of FastAPI workers behind a load balancer — the model is loaded once per process, so memory is O(workers × model_size). (4) Add model serving with batching — group multiple scoring requests into batch predictions for GPU utilization if using a heavier model."

---

## 9. Data Privacy (LGPD)

### Key articles

- **Article 7**: Legal bases for processing. Financial data: legitimate interest (Art 7-IX). Emotional data: explicit consent (Art 11-I).
- **Article 11**: Sensitive data (racial, health, biometric, AND data that can serve as proxy). Emotional data qualifies. Requires consent or one of few exceptions.
- **Article 18**: Data subject rights: access, correction, deletion, portability, information about sharing.
- **Article 20**: Right to review of automated decisions. Our SHAP explanations directly enable this.

### Pseudonymisation vs anonymisation

- **Pseudonymisation**: replace direct identifiers with pseudonyms (UUIDs, hashes). Data can still be re-identified with the mapping key. Our approach: `external_id` is SHA-256 of real user ID.
- **Anonymisation**: irreversible removal of identifying information. Data is no longer personal data under LGPD. Harder to achieve — aggregate statistics may still be identifying (k-anonymity, l-diversity).

### Encryption

- **In transit**: TLS 1.3 enforced at load balancer / API gateway
- **At rest**: disk-level encryption (LUKS) or database-level (SQLCipher for SQLite, TDE for Postgres)
- **Redis**: TLS-enabled connections (Redis 7+), AUTH password

### If asked "How do you handle the right to erasure?"

Say: "Our data model uses pseudonymised IDs. To erase a user: (1) delete the external_id mapping in the source system — this makes the pseudonymised records unlinkable, (2) optionally purge emotional_events older than 90 days as per retention policy, (3) credit evaluations are retained for 5 years per BACEN regulation but the PII link is broken."

---

## 10. Python / FastAPI Specifics

### Pydantic v2

Pydantic v2 is a complete rewrite using Rust (pydantic-core) for validation. 5-50x faster than v1. Key features we use:
- `model_dump()` for serialization
- `Field(..., ge=0, le=1)` for numeric constraints
- `model_config` with `json_schema_extra` for OpenAPI examples
- Union types: `float | None` for nullable fields

### Sync vs async in FastAPI

Our endpoints are sync (`def`, not `async def`). FastAPI runs sync endpoints in a threadpool. This is correct for our use case because:
- XGBoost `predict_proba()` is CPU-bound (releases GIL via C extension)
- SQLAlchemy operations are I/O-bound but short-lived
- Using `async def` with synchronous DB calls would block the event loop

### Middleware chain

Request flow: `request_id_middleware` (adds X-Request-ID, measures duration) → route handler → response. The middleware wraps `call_next` which invokes the rest of the stack.

### Dependency injection

`Depends(require_auth)` injects the authenticated username into every protected endpoint. FastAPI resolves the dependency tree at request time. If auth fails, the 401 is raised before the route handler executes.

---

## 11. Docker

### Our setup

- **Dockerfile**: single-stage build from `python:3.11-slim`, installs `uv`, syncs dependencies, copies source
- **docker-compose.yml**: 4 services (api, worker, redis, dashboard)
- **Healthchecks**: API uses Python `urllib.request.urlopen` (no curl in slim images), Redis uses `redis-cli ping`
- **Volumes**: `./data` and `./models` mounted for persistence

### If asked about multi-stage builds

Say: "For a Python application, multi-stage builds have limited benefit because the main image size comes from Python itself and pip packages, not from build artifacts. The benefit is larger for compiled languages (Go, Rust, C++) where you can compile in a builder stage and copy only the binary to a minimal runtime image."

---

## 12. Trap Questions and How to Handle Them

### "Why didn't you use a more complex model?"

"Complexity must be justified by performance. XGBoost achieved AUC 0.87 with 11 features. A neural network on this dataset would achieve roughly the same AUC (the data is small and tabular) but would lose exact SHAP explanations, require more hyperparameter tuning, and be harder to validate for regulators. I chose the simplest model that met the performance bar."

### "How would you handle model drift?"

"Monitor calibration and discrimination over time using the same metrics (AUC, KS, Brier) on a rolling window of production data. If calibration degrades (Brier increases by more than 10% relative), trigger recalibration with recent data. If discrimination degrades (AUC drops more than 0.02), retrain the model. This monitoring can be implemented with periodic batch scoring and comparison against the baseline metrics stored in `models/metrics_log.json`."

### "What if the emotional data was real and actually helped?"

"If emotional features genuinely improved AUC by a meaningful margin (say, +0.03), I'd recommend a phased approach: (1) Deploy financial-only model as primary, (2) Run emotional model in shadow mode — score but don't use for decisions, (3) After 3 months of shadow testing with real data, evaluate lift and fairness impact, (4) Only deploy if the lift justifies the LGPD consent burden and privacy infrastructure cost."

### "Your error handling seems basic — what about circuit breakers?"

"The challenge mentions circuit breakers as optional. The pattern applies when you have an external service call that can fail (e.g., calling an ML model microservice over HTTP). In our architecture, the model is loaded in-process — there's no network call to break. If we moved to a model-serving architecture (TensorFlow Serving, Triton), a circuit breaker on the gRPC/HTTP client would be appropriate: open after N consecutive failures, half-open after timeout, close after successful probe."

### "Why SQLite? That's not production-ready."

"The challenge says 'database of your choice.' SQLite provides ACID transactions, zero ops, and lets me focus on the ML and architecture instead of database administration. In production, I'd use Postgres with connection pooling (PgBouncer), read replicas for scoring queries, and row-level security for multi-tenant isolation. The SQLAlchemy ORM layer means the migration is a one-line config change (`DATABASE_URL`)."

### "What's your testing strategy?"

"78 tests across 8 files. Unit tests for: evaluation metrics (KS computation, precision@threshold), emotional feature injection (shape, R-squared non-circularity), SHAP explanations (structure, sorting, additivity), model store (decision logic, credit product mapping), database (all 7 tables, save/accept/notify flows), data loading (column mapping, sentinel handling), splits (proportions, stratification). Integration tests for: all API endpoints including auth, async evaluation, offer acceptance, emotion streaming, and X-Request-ID middleware."

### "How do you ensure the model doesn't discriminate based on age?"

"Two mechanisms: (1) The 4/5ths rule analysis in notebook 06 checks approval rates across age cohorts — all pass. (2) SHAP values reveal exactly how much `age` contributes to each decision. If age had an outsized negative SHAP value for young borrowers, we'd flag it. Currently, age is the 3rd most important feature with a protective effect (older = lower risk), which is consistent with credit risk literature and not discriminatory per se — it reflects the actuarial reality that payment history improves with age."
