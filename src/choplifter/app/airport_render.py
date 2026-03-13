from __future__ import annotations

from ..bus_ai import draw_airport_bus
from ..cutscene_manager import draw_airport_cutscene_markers
from ..enemy_spawns import draw_airport_enemies
from ..hostage_logic import draw_airport_hostages
from ..mission_tech import draw_airport_mission_tech
from ..objective_manager import draw_airport_objectives
from ..vehicle_assets import draw_airport_meal_truck


def draw_airport_world_overlays(
    *,
    target: object,
    camera_x: float,
    helicopter: object,
    mission: object,
    heli_ground_y: float,
    airport_bus_state: object,
    airport_hostage_state: object,
    airport_enemy_state: object,
    airport_tech_state: object,
    airport_objective_state: object,
    airport_meal_truck_state: object,
    airport_cutscene_state: object,
) -> None:
    """Draw airport-specific world entities on top of the shared mission layer."""
    airport_boarded_on_bus = (
        int(getattr(airport_hostage_state, "boarded_hostages", 0))
        if airport_hostage_state is not None
        else 0
    )
    airport_tech_on_bus = (
        bool(getattr(airport_tech_state, "on_bus", False))
        if airport_tech_state is not None
        else False
    )
    airport_hostage_pickup_x = (
        float(getattr(airport_hostage_state, "pickup_x", 1500.0))
        if airport_hostage_state is not None
        else 1500.0
    )
    mission_elapsed_seconds = float(getattr(mission, "elapsed_seconds", 0.0))

    if airport_bus_state is not None:
        draw_airport_bus(
            target,
            airport_bus_state,
            camera_x,
            boarded_count=airport_boarded_on_bus,
            tech_on_bus=airport_tech_on_bus,
        )
    draw_airport_hostages(
        target,
        airport_hostage_state,
        camera_x=camera_x,
        meal_truck_state=airport_meal_truck_state,
        ground_y=heli_ground_y,
        bus_state=airport_bus_state,
        mission_time=mission_elapsed_seconds,
    )
    draw_airport_enemies(target, airport_enemy_state, camera_x=camera_x)
    draw_airport_mission_tech(target, airport_tech_state, camera_x=camera_x, helicopter=helicopter)
    draw_airport_meal_truck(target, airport_meal_truck_state, camera_x=camera_x)
    draw_airport_objectives(
        target,
        airport_objective_state,
        camera_x=camera_x,
        ground_y=heli_ground_y,
        bus_state=airport_bus_state,
    )
    draw_airport_cutscene_markers(
        target,
        airport_cutscene_state,
        camera_x=camera_x,
        ground_y=heli_ground_y,
        pickup_x=airport_hostage_pickup_x,
    )
