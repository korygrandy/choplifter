from __future__ import annotations

from dataclasses import dataclass

from .airport_session import AirportRuntimeState
from .airport_tick import update_airport_mission_tick


@dataclass
class AirportPlayingTickUpdateResult:
    meal_truck_driver_mode: bool
    meal_truck_lift_command_extended: bool


@dataclass
class AirportRuntimeContext:
    airport_runtime: AirportRuntimeState
    bus_driver_input: object
    bus_driver_mode: bool
    truck_driver_input: object
    meal_truck_driver_mode: bool
    meal_truck_lift_command_extended: bool


def apply_airport_playing_tick_update(
    *,
    context: AirportRuntimeContext,
    tick_dt: float,
    audio: object,
    helicopter: object,
    mission: object,
    heli_settings: object,
    set_toast: object,
    logger: object,
) -> AirportPlayingTickUpdateResult:
    """Apply one airport fixed-step tick and sync runtime state updates."""
    airport_runtime = context.airport_runtime

    airport_tick = update_airport_mission_tick(
        bus_state=airport_runtime.bus_state,
        hostage_state=airport_runtime.hostage_state,
        tech_state=airport_runtime.tech_state,
        meal_truck_state=airport_runtime.meal_truck_state,
        enemy_state=airport_runtime.enemy_state,
        objective_state=airport_runtime.objective_state,
        cutscene_state=airport_runtime.cutscene_state,
        dt=tick_dt,
        audio=audio,
        helicopter=helicopter,
        mission=mission,
        heli_settings=heli_settings,
        bus_driver_input=context.bus_driver_input,
        bus_driver_mode=context.bus_driver_mode,
        truck_driver_input=context.truck_driver_input,
        meal_truck_driver_mode=context.meal_truck_driver_mode,
        meal_truck_lift_command_extended=context.meal_truck_lift_command_extended,
        set_toast=set_toast,
        logger=logger,
        airport_total_rescue_target=airport_runtime.total_rescue_target,
    )

    airport_runtime.bus_state = airport_tick.bus_state
    airport_runtime.hostage_state = airport_tick.hostage_state
    airport_runtime.tech_state = airport_tick.tech_state
    airport_runtime.meal_truck_state = airport_tick.meal_truck_state
    airport_runtime.enemy_state = airport_tick.enemy_state
    airport_runtime.objective_state = airport_tick.objective_state
    airport_runtime.cutscene_state = airport_tick.cutscene_state

    return AirportPlayingTickUpdateResult(
        meal_truck_driver_mode=airport_tick.meal_truck_driver_mode,
        meal_truck_lift_command_extended=airport_tick.meal_truck_lift_command_extended,
    )