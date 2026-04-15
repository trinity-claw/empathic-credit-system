# CLAUDE.md — empathic-credit-system

Project-level instructions. See also the global `~/.claude/CLAUDE.md` for behavioral guidelines.

## Project Overview

ML-based credit scoring system with empathic/explainable AI focus.

- **Language:** Python 3.11+
- **Package manager:** `uv` (use `uv run` / `uv add`, never `pip` directly)
- **API:** FastAPI + Uvicorn
- **ML stack:** scikit-learn, XGBoost, SHAP
- **Linting/formatting:** Ruff (`uv run ruff check`, `uv run ruff format`)
- **Tests:** pytest (`uv run pytest`)

## Structure

```
src/
  api/           # FastAPI routes and schemas
  data/          # Data loading and preprocessing
  evaluation/    # Model evaluation utilities
  explainability/ # SHAP and explainability logic
  models/        # Model training and persistence
tests/
notebooks/
data/
models/          # Serialized model artifacts
```

## Conventions

- Follow existing code style — match surrounding patterns before inventing new ones.
- Pydantic models for all API inputs/outputs.
- SHAP explanations must accompany every prediction endpoint response.
- No raw `print()` in src/ — use `python-json-logger`.
- Tests live in `tests/`, mirror `src/` structure.
