from __future__ import annotations

POST_RESPAWN_ESCORT_RISK_SECONDS = 3.0
POST_RESPAWN_ESCORT_DAMAGE_MULTIPLIER = 1.35


def _is_airport_mission(mission: object | None) -> bool:
    mission_id = str(getattr(mission, "mission_id", "")).lower()
    return mission_id in ("airport", "airport_special_ops", "mission2", "m2")


def activate_post_respawn_escort_risk(mission: object | None) -> None:
    if mission is None or not _is_airport_mission(mission):
        return
    setattr(mission, "post_respawn_escort_risk_seconds", float(POST_RESPAWN_ESCORT_RISK_SECONDS))


def tick_post_respawn_escort_risk(mission: object | None, dt: float) -> None:
    if mission is None:
        return
    remaining = max(0.0, float(getattr(mission, "post_respawn_escort_risk_seconds", 0.0)))
    if remaining <= 0.0:
        return
    remaining = max(0.0, remaining - max(0.0, float(dt)))
    setattr(mission, "post_respawn_escort_risk_seconds", remaining)


def airport_escort_damage_multiplier(mission: object | None) -> float:
    if mission is None or not _is_airport_mission(mission):
        return 1.0

    remaining = max(0.0, float(getattr(mission, "post_respawn_escort_risk_seconds", 0.0)))
    if remaining <= 0.0:
        return 1.0

    hostage_state = getattr(mission, "airport_hostage_state", None)
    hostage_state_name = str(getattr(hostage_state, "state", ""))
    if hostage_state_name != "boarded":
        return 1.0

    first_route = str(getattr(mission, "airport_first_rescue_route", "")).strip().lower()
    if first_route == "lower":
        return float(POST_RESPAWN_ESCORT_DAMAGE_MULTIPLIER * 0.92)
    if first_route == "elevated":
        return float(POST_RESPAWN_ESCORT_DAMAGE_MULTIPLIER * 1.06)

    return float(POST_RESPAWN_ESCORT_DAMAGE_MULTIPLIER)
