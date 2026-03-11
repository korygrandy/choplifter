from __future__ import annotations


def _retire_active_barak_missiles(mission: object) -> None:
    projectiles = getattr(mission, "projectiles", None)
    if not projectiles:
        return
    for projectile in projectiles:
        if bool(getattr(projectile, "alive", False)) and bool(getattr(projectile, "is_barak_missile", False)):
            projectile.alive = False


def sync_airport_runtime_flags(
    *,
    mission: object,
    selected_mission_id: str,
    airport_tech_state: object | None,
    meal_truck_driver_mode: bool,
    bus_driver_mode: bool,
) -> None:
    """Synchronize airport mission runtime flags used by combat/AI systems."""
    if selected_mission_id == "airport":
        was_driving_vehicle = bool(getattr(mission, "player_driving_vehicle", False))
        engineer_off_chopper = bool(
            airport_tech_state is not None
            and str(getattr(airport_tech_state, "state", "on_chopper")) != "on_chopper"
        )
        now_driving_vehicle = bool(meal_truck_driver_mode or bus_driver_mode)
        mission.engineer_remote_control_active = bool(meal_truck_driver_mode)
        mission.player_driving_vehicle = now_driving_vehicle
        mission.engineer_off_chopper = engineer_off_chopper
        # BARAK suppression is limited to active remote-control driving.
        mission.barak_suppressed = bool(meal_truck_driver_mode)
        if (not was_driving_vehicle) and now_driving_vehicle:
            _retire_active_barak_missiles(mission)
        return

    mission.engineer_remote_control_active = False
    mission.player_driving_vehicle = False
    mission.engineer_off_chopper = False
    mission.barak_suppressed = False
