"""Settings: legacy calibrator env keys vs pydantic-settings."""

import importlib

import pytest


@pytest.fixture
def fresh_settings():
    import src.api.settings as settings_mod

    settings_mod.get_settings.cache_clear()
    yield settings_mod
    settings_mod.get_settings.cache_clear()


def test_calibrator_prefers_calibrator_path_when_calibration_path_in_os(
    fresh_settings, monkeypatch
):
    """CALIBRATION_PATH in the process env is not a valid alias for pydantic-settings; merge in code."""
    monkeypatch.setenv("CALIBRATION_PATH", "models/wrong.pkl")
    monkeypatch.delenv("CALIBRATOR_PATH", raising=False)
    mod = importlib.reload(fresh_settings)
    s = mod.Settings()
    assert s.calibrator_path == "models/xgboost_financial_calibrator.pkl"


def test_calibrator_falls_back_to_calibration_path_env(
    fresh_settings, monkeypatch, tmp_path
):
    monkeypatch.delenv("CALIBRATION_PATH", raising=False)
    monkeypatch.delenv("CALIBRATOR_PATH", raising=False)
    monkeypatch.delenv("calibration_path", raising=False)
    monkeypatch.setenv("CALIBRATION_PATH", "models/legacy_only.pkl")
    env = tmp_path / ".env"
    env.write_text("MODEL_PATH=models/xgboost_financial.pkl\n", encoding="utf-8")
    mod = importlib.reload(fresh_settings)
    s = mod.Settings(_env_file=str(env))
    assert s.calibrator_path == "models/legacy_only.pkl"
