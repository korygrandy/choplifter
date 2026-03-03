from __future__ import annotations

from dataclasses import asdict
import json
import logging
from pathlib import Path

from .settings import PhysicsSettings


def _clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def _coerce_float(value: object, default: float, *, lo: float, hi: float) -> float:
    try:
        if isinstance(value, (int, float)):
            return _clamp(float(value), lo, hi)
        if isinstance(value, str):
            return _clamp(float(value.strip()), lo, hi)
    except Exception:
        return default
    return default


def load_physics_settings(*, logger: logging.Logger | None = None) -> PhysicsSettings:
    """Loads optional flight tuning from `physics.json` at the repo root.

    If the file doesn't exist or can't be parsed, defaults are used.

    Use `physics.example.json` as a template.
    """

    defaults = PhysicsSettings()

    module_dir = Path(__file__).resolve().parent
    repo_root = module_dir.parents[1]
    path = repo_root / "physics.json"
    if not path.exists():
        return defaults

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        if logger is not None:
            logger.info("PHYSICS: failed to load physics.json; using defaults")
        return defaults

    if not isinstance(data, dict):
        if logger is not None:
            logger.info("PHYSICS: physics.json must be an object; using defaults")
        return defaults

    # Start with defaults, then override.
    merged = dict(asdict(defaults))

    def set_float(key: str, *, lo: float, hi: float) -> None:
        if key not in data:
            return
        merged[key] = _coerce_float(data.get(key), float(merged[key]), lo=lo, hi=hi)

    set_float("gravity", lo=0.0, hi=120.0)
    set_float("engine_power", lo=0.0, hi=200.0)
    set_float("descend_power_factor", lo=0.0, hi=1.0)
    set_float("friction", lo=0.90, hi=0.9999)
    set_float("max_speed_x", lo=0.0, hi=250.0)
    set_float("max_speed_y", lo=0.0, hi=250.0)

    set_float("position_scale", lo=1.0, hi=50.0)

    set_float("max_tilt_deg", lo=0.0, hi=89.0)
    set_float("tilt_rate_deg_per_s", lo=0.0, hi=720.0)
    set_float("tilt_return_rate_deg_per_s", lo=0.0, hi=720.0)

    set_float("brake_damping", lo=0.50, hi=1.0)
    set_float("ground_damping", lo=0.0, hi=1.0)
    set_float("ground_stop_speed", lo=0.0, hi=5.0)

    set_float("safe_landing_vy", lo=0.0, hi=50.0)

    try:
        return PhysicsSettings(**merged)
    except Exception:
        if logger is not None:
            logger.info("PHYSICS: invalid physics.json values; using defaults")
        return defaults
