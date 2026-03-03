from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from pathlib import Path


def _clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def _coerce_bool(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    return default


def _coerce_float(value: object, default: float, *, lo: float, hi: float) -> float:
    try:
        if isinstance(value, (int, float)):
            return _clamp(float(value), lo, hi)
        if isinstance(value, str):
            return _clamp(float(value.strip()), lo, hi)
    except Exception:
        return default
    return default


@dataclass(frozen=True)
class AccessibilitySettings:
    # Visual comfort.
    particles_enabled: bool = True
    flashes_enabled: bool = True
    screenshake_enabled: bool = True

    # Haptics.
    rumble_enabled: bool = True

    # Input comfort.
    gamepad_deadzone: float = 0.35
    trigger_threshold: float = 0.55

    @staticmethod
    def defaults() -> "AccessibilitySettings":
        return AccessibilitySettings()


def load_accessibility(*, logger: logging.Logger | None = None) -> AccessibilitySettings:
    """Loads optional accessibility tuning from `accessibility.json` at the repo root.

    If the file doesn't exist or can't be parsed, defaults are used.

    Format example:
    {
      "particles_enabled": true,
      "flashes_enabled": true,
      "screenshake_enabled": true,
            "rumble_enabled": true,
      "gamepad_deadzone": 0.35,
      "trigger_threshold": 0.55
    }
    """

    settings = AccessibilitySettings.defaults()

    module_dir = Path(__file__).resolve().parent
    repo_root = module_dir.parents[1]
    path = repo_root / "accessibility.json"
    if not path.exists():
        return settings

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        if logger is not None:
            logger.info("ACCESSIBILITY: failed to load accessibility.json; using defaults")
        return settings

    if not isinstance(data, dict):
        if logger is not None:
            logger.info("ACCESSIBILITY: accessibility.json must be an object; using defaults")
        return settings

    return AccessibilitySettings(
        particles_enabled=_coerce_bool(data.get("particles_enabled"), settings.particles_enabled),
        flashes_enabled=_coerce_bool(data.get("flashes_enabled"), settings.flashes_enabled),
        screenshake_enabled=_coerce_bool(data.get("screenshake_enabled"), settings.screenshake_enabled),
        rumble_enabled=_coerce_bool(data.get("rumble_enabled"), settings.rumble_enabled),
        gamepad_deadzone=_coerce_float(data.get("gamepad_deadzone"), settings.gamepad_deadzone, lo=0.0, hi=0.95),
        trigger_threshold=_coerce_float(data.get("trigger_threshold"), settings.trigger_threshold, lo=0.05, hi=0.95),
    )
