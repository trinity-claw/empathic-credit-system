# AGENTS.md — empathic-credit-system

Instructions for OpenAI Codex and other agent-based coding tools.

## Project

ML-based credit scoring system with explainable AI. Python 3.11+, FastAPI, XGBoost, SHAP.

## Package Management

- Use `uv`, never `pip`.
- Install packages: `uv add <package>`
- Run commands: `uv run <command>`

## Before Making Changes

1. Read the relevant files first. Do not guess at structure.
2. State your interpretation of the task before implementing.
3. Prefer the simplest solution. No speculative features.

## Code Rules

- Match surrounding code style. Do not reformat unrelated code.
- Pydantic models for all API I/O.
- No `print()` in `src/` — use `python-json-logger`.
- SHAP explanations required in prediction responses.

## Verification

After every change:

```bash
uv run ruff check
uv run ruff format
uv run pytest
```

All three must pass before reporting done.

## Structure

```
src/api/            — FastAPI routes and schemas
src/data/           — Data loading/preprocessing
src/evaluation/     — Evaluation utilities
src/explainability/ — SHAP logic
src/models/         — Training and serialization
tests/              — Mirrors src/ structure
models/             — Serialized artifacts
```
