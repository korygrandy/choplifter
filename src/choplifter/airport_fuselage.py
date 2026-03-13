from __future__ import annotations

from typing import Any


FUSELAGE_DAMAGE_STAGE_INTACT = 0
FUSELAGE_DAMAGE_STAGE_HALF = 1
FUSELAGE_DAMAGE_STAGE_TOTAL = 2
FUSELAGE_DAMAGE_THRESHOLD_HALF = 120.0
FUSELAGE_DAMAGE_THRESHOLD_TOTAL = 240.0
FUSELAGE_HALF_STAGE_MIN_SECONDS = 0.65


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
    - stage 1 at >= FUSELAGE_DAMAGE_THRESHOLD_HALF
    - stage 2 at >= FUSELAGE_DAMAGE_THRESHOLD_TOTAL
    """
    if mission is None or not _is_airport_mission(mission):
        return FUSELAGE_DAMAGE_STAGE_TOTAL

    cached_stage = int(getattr(mission, "airport_fuselage_damage_stage", FUSELAGE_DAMAGE_STAGE_INTACT))
    fuselage_compound = _get_airport_fuselage_compound(mission)
    if fuselage_compound is None:
        setattr(mission, "airport_fuselage_damage_stage", FUSELAGE_DAMAGE_STAGE_TOTAL)
        return FUSELAGE_DAMAGE_STAGE_TOTAL

    # Use explicit damage counter if present
    damage_taken = float(getattr(mission, "airport_fuselage_damage_taken", -1.0))
    if damage_taken < 0.0:
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
    mission_time = float(getattr(mission, "elapsed_seconds", 0.0))
    stage_now = FUSELAGE_DAMAGE_STAGE_INTACT
    if damage_taken >= float(FUSELAGE_DAMAGE_THRESHOLD_HALF):
        stage_now = FUSELAGE_DAMAGE_STAGE_HALF

    reached_total_damage = damage_taken >= float(FUSELAGE_DAMAGE_THRESHOLD_TOTAL)
    is_open = bool(getattr(fuselage_compound, "is_open", False))
    half_hold_until = float(getattr(mission, "airport_fuselage_half_stage_hold_until_s", -1.0))

    if reached_total_damage:
        stage_now = FUSELAGE_DAMAGE_STAGE_TOTAL
    elif is_open:
        # If the fuselage opens before total threshold damage, force a visible
        # half-damaged phase before allowing full-damaged stage.
        if cached_stage < FUSELAGE_DAMAGE_STAGE_HALF:
            stage_now = FUSELAGE_DAMAGE_STAGE_HALF
            setattr(
                mission,
                "airport_fuselage_half_stage_hold_until_s",
                mission_time + float(FUSELAGE_HALF_STAGE_MIN_SECONDS),
            )
        elif cached_stage == FUSELAGE_DAMAGE_STAGE_HALF and mission_time < half_hold_until:
            stage_now = FUSELAGE_DAMAGE_STAGE_HALF
        else:
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
