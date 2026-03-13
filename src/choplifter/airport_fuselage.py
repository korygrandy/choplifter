from __future__ import annotations

from typing import Any


FUSELAGE_DAMAGE_STAGE_INTACT = 0
FUSELAGE_DAMAGE_STAGE_HALF = 1
FUSELAGE_DAMAGE_STAGE_TOTAL = 2
FUSELAGE_DAMAGE_THRESHOLD_HALF = 200.0
FUSELAGE_DAMAGE_THRESHOLD_TOTAL = 400.0


def _is_airport_mission(mission: Any | None) -> bool:
    mission_id = str(getattr(mission, "mission_id", "")).strip().lower()
    return mission_id in ("airport", "airport_special_ops", "airportspecialops", "mission2", "m2")


def _get_airport_fuselage_compound(mission: Any | None) -> Any | None:
    if mission is None or not _is_airport_mission(mission):
        return None
    compounds = list(getattr(mission, "compounds", []) or [])
    if not compounds:
        return None

    elevated_y = min(float(getattr(getattr(c, "pos", None), "y", 0.0)) for c in compounds)
    elevated = [
        c for c in compounds if abs(float(getattr(getattr(c, "pos", None), "y", 0.0)) - elevated_y) <= 1.0
    ]
    if not elevated:
        return None

    return min(elevated, key=lambda c: float(getattr(getattr(c, "pos", None), "x", 0.0)))


def get_airport_fuselage_damage_stage(mission: Any | None) -> int:
    """Return monotonic fuselage damage stage: 0 intact, 1 half, 2 total.

    Stage thresholds use absolute damage on the fuselage compound:
    - stage 1 at >= 200 damage taken
    - stage 2 at >= 400 total damage taken
    """
    if mission is None or not _is_airport_mission(mission):
        return FUSELAGE_DAMAGE_STAGE_TOTAL

    cached_stage = int(getattr(mission, "airport_fuselage_damage_stage", FUSELAGE_DAMAGE_STAGE_INTACT))
    fuselage_compound = _get_airport_fuselage_compound(mission)
    if fuselage_compound is None:
        setattr(mission, "airport_fuselage_damage_stage", FUSELAGE_DAMAGE_STAGE_TOTAL)
        return FUSELAGE_DAMAGE_STAGE_TOTAL

    max_health = float(getattr(mission, "airport_fuselage_max_health", 0.0))
    current_health = max(0.0, float(getattr(fuselage_compound, "health", 0.0)))
    if max_health <= 0.0:
        compound_healths = [
            max(0.0, float(getattr(c, "health", 0.0)))
            for c in (getattr(mission, "compounds", []) or [])
        ]
        observed_peak = max(compound_healths) if compound_healths else current_health
        max_health = max(1.0, current_health, observed_peak)
    else:
        max_health = max(max_health, current_health)
    setattr(mission, "airport_fuselage_max_health", max_health)

    damage_taken = max(0.0, max_health - current_health)
    stage_now = FUSELAGE_DAMAGE_STAGE_INTACT
    if damage_taken >= float(FUSELAGE_DAMAGE_THRESHOLD_HALF):
        stage_now = FUSELAGE_DAMAGE_STAGE_HALF
    if (
        damage_taken >= float(FUSELAGE_DAMAGE_THRESHOLD_TOTAL)
        or bool(getattr(fuselage_compound, "is_open", False))
    ):
        stage_now = FUSELAGE_DAMAGE_STAGE_TOTAL

    stage = max(cached_stage, stage_now)
    setattr(mission, "airport_fuselage_damage_stage", stage)
    return int(stage)


def is_airport_fuselage_boarding_unlocked(mission: Any | None) -> bool:
    """Airport boarding unlocks only after fuselage reaches total-damage stage."""
    if mission is None:
        return True
    if not _is_airport_mission(mission):
        return True
    return get_airport_fuselage_damage_stage(mission) >= FUSELAGE_DAMAGE_STAGE_TOTAL


def get_airport_fuselage_damage_progress(mission: Any | None) -> tuple[float, float]:
    """Return (damage_taken, total_required_damage) for airport fuselage progression."""
    if mission is None or not _is_airport_mission(mission):
        return (0.0, float(FUSELAGE_DAMAGE_THRESHOLD_TOTAL))

    fuselage_compound = _get_airport_fuselage_compound(mission)
    if fuselage_compound is None:
        return (float(FUSELAGE_DAMAGE_THRESHOLD_TOTAL), float(FUSELAGE_DAMAGE_THRESHOLD_TOTAL))

    max_health = float(getattr(mission, "airport_fuselage_max_health", 0.0))
    current_health = max(0.0, float(getattr(fuselage_compound, "health", 0.0)))
    if max_health <= 0.0:
        get_airport_fuselage_damage_stage(mission)
        max_health = float(getattr(mission, "airport_fuselage_max_health", current_health))

    damage_taken = max(0.0, max_health - current_health)
    total_required = float(FUSELAGE_DAMAGE_THRESHOLD_TOTAL)
    return (min(damage_taken, total_required), total_required)
