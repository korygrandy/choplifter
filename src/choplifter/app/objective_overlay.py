from __future__ import annotations

CITY_SIEGE_MISSION_IDS = ("city", "city_center", "citycenter", "mission1", "m1")
AIRPORT_MISSION_IDS = ("airport", "airport_special_ops", "airportspecialops", "mission2", "m2")
WORSHIP_MISSION_IDS = ("worship", "worship_center", "worshipcenter", "mission3", "m3")

OBJECTIVE_OVERLAY_DURATION_S = 3.0


def is_city_siege_mission(mission_id: str) -> bool:
    return str(mission_id or "").strip().lower() in CITY_SIEGE_MISSION_IDS


def get_mission_objective_overlay(*, mission_id: str) -> tuple[str, bool]:
    normalized = str(mission_id or "").strip().lower()

    if normalized in CITY_SIEGE_MISSION_IDS:
        return "Rescue the VIP hostage", True
    if normalized in AIRPORT_MISSION_IDS:
        return "Rescue hostages and return them to base", False
    if normalized in WORSHIP_MISSION_IDS:
        return "Rescue hostages amid heavy resistance", False
    return "", False


def get_mission_objective_overlay_duration(*, mission_id: str) -> float:
    message, _ = get_mission_objective_overlay(mission_id=mission_id)
    if message:
        return OBJECTIVE_OVERLAY_DURATION_S
    return 0.0


def get_city_siege_objective_overlay_duration(*, mission_id: str) -> float:
    if not is_city_siege_mission(mission_id):
        return 0.0
    return OBJECTIVE_OVERLAY_DURATION_S


def tick_overlay_timer(*, timer_s: float, frame_dt: float) -> float:
    return max(0.0, float(timer_s) - float(frame_dt))


def overlay_alpha(*, remaining_s: float, total_s: float = 3.0, fade_s: float = 0.5) -> int:
    remaining = max(0.0, float(remaining_s))
    total = max(0.1, float(total_s))
    fade = max(0.05, float(fade_s))

    if remaining <= 0.0:
        return 0
    if remaining < fade:
        return max(0, min(255, int(255.0 * (remaining / fade))))
    if remaining > total - fade:
        return max(0, min(255, int(255.0 * ((total - remaining) / fade))))
    return 255
