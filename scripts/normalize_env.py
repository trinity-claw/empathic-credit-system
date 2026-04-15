"""Align .env model paths with files under models/ (post-notebook train).

Also removes legacy keys calibration_path / CALIBRATION_PATH — they bind to the same
Pydantic field as CALIBRATOR_PATH and can override the correct path with a stale value
like models/calibrator.pkl.

Run: uv run python scripts/normalize_env.py
"""

from __future__ import annotations

import sys
from pathlib import Path

FIXUPS: tuple[tuple[str, str, str], ...] = (
    ("MODEL_PATH", "models/xgboost_financial.pkl", "models/xgboost_financial.pkl"),
    (
        "CALIBRATOR_PATH",
        "models/xgboost_financial_calibrator.pkl",
        "models/xgboost_financial_calibrator.pkl",
    ),
    (
        "EMOTIONAL_MODEL_PATH",
        "models/xgboost_emotional.pkl",
        "models/xgboost_emotional.pkl",
    ),
    (
        "EMOTIONAL_CALIBRATOR_PATH",
        "models/xgboost_emotional_calibrator.pkl",
        "models/xgboost_emotional_calibrator.pkl",
    ),
)


def _resolve(root: Path, value: str) -> Path:
    value = value.strip().strip('"').strip("'").strip("\r")
    p = Path(value)
    if p.is_absolute():
        return p
    return (root / value).resolve()


def patch_env_file(root: Path, env_path: Path) -> bool:
    """Rewrite env_path when paths are missing or legacy keys steal calibrator_path.

    Returns True if env_path was modified.
    """
    if not env_path.is_file():
        return False

    fin_cal_canon = root / "models" / "xgboost_financial_calibrator.pkl"
    raw = env_path.read_text(encoding="utf-8")
    had_trailing_nl = raw.endswith("\n")
    lines = raw.splitlines()
    key_to_default = {
        k: (default, root / canonical) for k, default, canonical in FIXUPS
    }

    new_lines: list[str] = []
    changed = False
    saw_calibrator_key = False  # CALIBRATOR_PATH (not legacy CALIBRATION_PATH)

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue
        if "=" not in stripped:
            new_lines.append(line)
            continue
        key_part, val_part = stripped.split("=", 1)
        key_upper = key_part.strip().upper()

        # pydantic Field(calibrator_path) accepts calibration_path / CALIBRATION_PATH
        # as aliases; a second .env line can override CALIBRATOR_PATH with models/calibrator.pkl
        if key_upper == "CALIBRATION_PATH" and fin_cal_canon.is_file():
            changed = True
            continue

        if key_upper == "CALIBRATOR_PATH":
            saw_calibrator_key = True

        if key_upper not in key_to_default:
            new_lines.append(line)
            continue

        default, canonical = key_to_default[key_upper]
        resolved = _resolve(root, val_part)
        if not resolved.is_file() and canonical.is_file():
            new_lines.append(f"{key_upper}={default}")
            changed = True
        else:
            new_lines.append(line)

    if fin_cal_canon.is_file() and not saw_calibrator_key:
        new_lines.append("CALIBRATOR_PATH=models/xgboost_financial_calibrator.pkl")
        changed = True

    if changed:
        body = "\n".join(new_lines)
        if had_trailing_nl or body:
            body += "\n"
        env_path.write_text(body, encoding="utf-8")

    return changed


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    env_path = root / ".env"
    if patch_env_file(root, env_path):
        print(
            f"normalize_env: updated {env_path} — model paths + legacy calibration keys",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
