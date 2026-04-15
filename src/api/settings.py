"""Application settings loaded from environment / .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_username: str = "admin"
    api_password: str = "changeme"

    model_path: str = "models/xgboost_financial.pkl"
    calibrator_path: str = "models/xgboost_financial_calibrator.pkl"
    emotional_model_path: str = "models/xgboost_emotional.pkl"
    emotional_calibrator_path: str = "models/xgboost_emotional_calibrator.pkl"
    model_version: str = "v1.0.0"

    database_url: str = "sqlite:///./data/ecs.db"
    redis_url: str = "redis://redis:6379/0"

    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
