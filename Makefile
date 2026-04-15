.PHONY: train test lint format serve docker clean

train:
	uv run python -m src.data.split

test:
	uv run pytest

lint:
	uv run ruff check src/ tests/
	uv run ruff format --check src/ tests/

format:
	uv run ruff check src/ tests/ --fix
	uv run ruff format src/ tests/

serve:
	uv run uvicorn src.api.main:app --reload

docker:
	docker compose up --build

clean:
	rm -rf data/processed/*.parquet data/ecs.db .pytest_cache __pycache__
