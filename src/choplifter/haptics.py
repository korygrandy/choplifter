from __future__ import annotations

import logging
from typing import Any


_enabled: bool = True
_active_joystick: Any | None = None


def set_enabled(enabled: bool) -> None:
    global _enabled
    _enabled = bool(enabled)


def set_active_joystick(joystick: Any | None) -> None:
    global _active_joystick
    _active_joystick = joystick


def _clamp01(v: float) -> float:
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


def _rumble(
    *,
    low: float,
    high: float,
    duration_ms: int,
    profile: str | None = None,
    logger: logging.Logger | None = None,
) -> bool:
    if not _enabled:
        return False

    js = _active_joystick
    if js is None:
        return False

    rumble_fn = getattr(js, "rumble", None)
    if rumble_fn is None:
        return False

    try:
        if logger is not None and profile is not None:
            logger.debug("HAPTICS: profile=%s low=%.2f high=%.2f ms=%d", profile, _clamp01(low), _clamp01(high), int(duration_ms))
        return bool(rumble_fn(_clamp01(low), _clamp01(high), int(duration_ms)))
    except Exception as e:
        if logger is not None:
            logger.info("HAPTICS: rumble failed (%s)", type(e).__name__)
        return False


def rumble_hit(*, amount: float, source: str | None = None, logger: logging.Logger | None = None) -> None:
    # Short, sharp pulse. Scale slightly with damage amount.
    amt = float(amount)
    scale = _clamp01(0.25 + (amt / 40.0))

    # Bias toward high-frequency motor for "impact" feel.
    low = 0.10 * scale
    high = 0.65 * scale
    duration_ms = int(85 + 90 * scale)

    # Slightly stronger for mines/jets (but still below rough-landing weight).
    if source in ("AIR_MINE", "JET"):
        high = _clamp01(high + 0.15)
        duration_ms = int(duration_ms + 35)

    profile = "mine" if source == "AIR_MINE" else None
    _rumble(low=low, high=high, duration_ms=duration_ms, profile=profile, logger=logger)


def rumble_rough_landing(*, impact_vy: float, safe_vy: float, logger: logging.Logger | None = None) -> None:
    # Only called when we already decided it's a rough landing; treat it as a heavier thump.
    vy = abs(float(impact_vy))
    safe = max(0.001, float(safe_vy))
    severity = _clamp01((vy - safe) / (safe * 1.25))

    # Heavier than mine impacts: emphasize low-frequency body thump.
    low = 0.70 + 0.24 * severity
    high = 0.32 + 0.16 * severity
    duration_ms = int(190 + 50 * severity)

    _rumble(low=low, high=high, duration_ms=duration_ms, profile="rough", logger=logger)


def rumble_tank_destroyed(*, logger: logging.Logger | None = None) -> None:
    # Longer, celebratory rumble for destroying a ground artillery cannon.
    # (One continuous rumble call; actual device behavior varies by driver.)
    _rumble(low=0.75, high=0.55, duration_ms=360, logger=logger)


def rumble_artillery_hit(*, logger: logging.Logger | None = None) -> None:
    # Extended rumble specifically for when an enemy artillery round impacts the helicopter.
    # Keep other events as short/normal pulses.
    _rumble(low=0.85, high=0.65, duration_ms=520, profile="artillery", logger=logger)


def rumble_barak_missile_hit(*, logger: logging.Logger | None = None) -> None:
    # Distinct BARAK profile: shorter, sharper, high-frequency dominant hit.
    _rumble(low=0.58, high=0.94, duration_ms=280, profile="barak", logger=logger)
