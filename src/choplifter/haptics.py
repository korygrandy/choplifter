from __future__ import annotations

import logging
from typing import Any


_enabled: bool = True
_active_joystick: Any | None = None

# Tuned profile constants for airport mission feedback.
_BUS_SHIFT_LOW_BASE = 0.06
_BUS_SHIFT_LOW_SCALE = 0.10
_BUS_SHIFT_HIGH_BASE = 0.12
_BUS_SHIFT_HIGH_SCALE = 0.12
_BUS_SHIFT_MS_BASE = 42
_BUS_SHIFT_MS_SCALE = 28

_AIRPORT_EVENT_PROFILES: dict[str, tuple[float, float, int, str]] = {
    "tech_deploy": (0.22, 0.40, 92, "airport_tech_deploy"),
    "lift_extended": (0.60, 0.18, 150, "airport_lift"),
    "load_start": (0.14, 0.22, 64, "airport_load_start"),
    "load_complete": (0.28, 0.44, 104, "airport_load_complete"),
    "transfer_start": (0.46, 0.28, 128, "airport_transfer_start"),
    "rescue_complete": (0.34, 0.52, 118, "airport_rescue_complete"),
    "tech_waiting_lz": (0.22, 0.30, 82, "airport_tech_waiting"),
    "tech_kia": (0.74, 0.40, 320, "airport_failure"),
}


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


def rumble_chopper_crash(*, logger: logging.Logger | None = None) -> None:
    # Heavy, sustained crash profile to emphasize catastrophic helicopter impact.
    _rumble(low=1.00, high=0.82, duration_ms=680, profile="chopper_crash", logger=logger)


def rumble_bus_shift(*, severity: float = 1.0, logger: logging.Logger | None = None) -> None:
    # Subtle mechanical nudge for bus gear/phase shifts.
    s = _clamp01(float(severity))
    low = _BUS_SHIFT_LOW_BASE + _BUS_SHIFT_LOW_SCALE * s
    high = _BUS_SHIFT_HIGH_BASE + _BUS_SHIFT_HIGH_SCALE * s
    duration_ms = int(_BUS_SHIFT_MS_BASE + _BUS_SHIFT_MS_SCALE * s)
    _rumble(low=low, high=high, duration_ms=duration_ms, profile="bus_shift", logger=logger)


def rumble_airport_event(*, event: str, logger: logging.Logger | None = None) -> None:
    event_name = str(event).strip().lower()
    profile = _AIRPORT_EVENT_PROFILES.get(event_name)
    if profile is None:
        return
    low, high, duration_ms, profile_name = profile
    _rumble(low=low, high=high, duration_ms=duration_ms, profile=profile_name, logger=logger)
