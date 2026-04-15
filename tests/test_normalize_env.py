"""Tests for scripts/normalize_env.py (imported by file path)."""

import importlib.util
from pathlib import Path


def _load_normalize_module():
    path = Path(__file__).resolve().parent.parent / "scripts" / "normalize_env.py"
    spec = importlib.util.spec_from_file_location("normalize_env", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_patch_env_rewrites_missing_model_path(tmp_path):
    mod = _load_normalize_module()
    (tmp_path / "models").mkdir(parents=True)
    (tmp_path / "models" / "xgboost_financial.pkl").write_bytes(b"0")
    env = tmp_path / ".env"
    env.write_text("MODEL_PATH=models/xgboost_credit.pkl\n", encoding="utf-8")

    assert mod.patch_env_file(tmp_path, env) is True
    assert "MODEL_PATH=models/xgboost_financial.pkl" in env.read_text(encoding="utf-8")


def test_patch_env_noop_when_path_exists(tmp_path):
    mod = _load_normalize_module()
    (tmp_path / "models").mkdir(parents=True)
    target = tmp_path / "models" / "custom.pkl"
    target.write_bytes(b"0")
    env = tmp_path / ".env"
    env.write_text("MODEL_PATH=models/custom.pkl\n", encoding="utf-8")

    assert mod.patch_env_file(tmp_path, env) is False


def test_drops_calibration_path_when_financial_calibrator_exists(tmp_path):
    """Legacy calibration_path steals pydantic calibrator_path if left in .env."""
    mod = _load_normalize_module()
    (tmp_path / "models").mkdir(parents=True)
    (tmp_path / "models" / "xgboost_financial_calibrator.pkl").write_bytes(b"0")
    (tmp_path / "models" / "xgboost_financial.pkl").write_bytes(b"0")
    env = tmp_path / ".env"
    env.write_text(
        "CALIBRATOR_PATH=models/xgboost_financial_calibrator.pkl\n"
        "calibration_path=models/calibrator.pkl\n",
        encoding="utf-8",
    )

    assert mod.patch_env_file(tmp_path, env) is True
    text = env.read_text(encoding="utf-8")
    assert "calibration_path" not in text
    assert "models/calibrator.pkl" not in text
    assert "CALIBRATOR_PATH=models/xgboost_financial_calibrator.pkl" in text


def test_appends_calibrator_when_only_legacy_calibration_path(tmp_path):
    mod = _load_normalize_module()
    (tmp_path / "models").mkdir(parents=True)
    (tmp_path / "models" / "xgboost_financial_calibrator.pkl").write_bytes(b"0")
    env = tmp_path / ".env"
    env.write_text("calibration_path=models/calibrator.pkl\n", encoding="utf-8")

    assert mod.patch_env_file(tmp_path, env) is True
    text = env.read_text(encoding="utf-8")
    assert "calibration_path" not in text
    assert "CALIBRATOR_PATH=models/xgboost_financial_calibrator.pkl" in text
