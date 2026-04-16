"""Application settings loaded from environment / .env file."""

from functools import lru_cache
from typing import Any

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_username: str = "admin"
    api_password: str = "changeme"

    model_path: str = "models/xgboost_financial.pkl"
    # Accept legacy .env keys calibration_path / CALIBRATION_PATH (common typo)
    calibrator_path: str = Field(
        default="models/xgboost_financial_calibrator.pkl",
        validation_alias=AliasChoices(
            "CALIBRATOR_PATH",
            "calibrator_path",
            "CALIBRATION_PATH",
            "calibration_path",
        ),
    )
    emotional_model_path: str = "models/xgboost_emotional.pkl"
    emotional_calibrator_path: str = "models/xgboost_emotional_calibrator.pkl"
    model_version: str = "v1.0.0"

    database_url: str = "sqlite:///./data/ecs.db"
    redis_url: str = "redis://redis:6379/0"

    log_level: str = "INFO"

    notification_webhook_url: str | None = Field(
        default=None,
        description="If set, POST JSON credit notifications here (gateway or tools like webhook.site).",
    )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @model_validator(mode="before")
    @classmethod
    def _coalesce_calibrator_env(cls, data: Any) -> Any:
        """pydantic-settings leaves CALIBRATION_PATH as extra; merge legacy keys into CALIBRATOR_PATH."""
        if not isinstance(data, dict):
            return data
        primary = data.get("CALIBRATOR_PATH") or data.get("calibrator_path")
        legacy = data.pop("CALIBRATION_PATH", None) or data.pop(
            "calibration_path", None
        )
        data.pop("calibrator_path", None)
        if primary is not None:
            data["CALIBRATOR_PATH"] = primary
        elif legacy is not None:
            data["CALIBRATOR_PATH"] = legacy
        if data.get("CALIBRATOR_PATH") is not None:
            data.pop("CALIBRATION_PATH", None)
            data.pop("calibration_path", None)
        return data


@lru_cache
def get_settings() -> Settings:
    return Settings()
