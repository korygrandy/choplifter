from __future__ import annotations

from dataclasses import dataclass

from .vehicle_driver_modes import handle_airport_driver_mode_doors


@dataclass
class PlayingKeyboardResult:
    handled: bool
    meal_truck_driver_mode: bool
    meal_truck_lift_command_extended: bool
    bus_driver_mode: bool


def handle_playing_keyboard_special_cases(
    *,
    selected_mission_id: str,
    doors_key_pressed: bool,
    fire_key_pressed: bool,
    meal_truck_driver_mode: bool,
    meal_truck_lift_command_extended: bool,
    bus_driver_mode: bool,
    airport_meal_truck_state: object,
    airport_bus_state: object,
    airport_tech_state: object,
    helicopter: object,
    heli_ground_y: float,
) -> PlayingKeyboardResult:
    """Handle playing-mode keyboard overrides before general key handling."""
    if doors_key_pressed and selected_mission_id == "airport":
        airport_driver_mode = handle_airport_driver_mode_doors(
            meal_truck_driver_mode=meal_truck_driver_mode,
            meal_truck_lift_command_extended=meal_truck_lift_command_extended,
            bus_driver_mode=bus_driver_mode,
            meal_truck_state=airport_meal_truck_state,
            bus_state=airport_bus_state,
            tech_state=airport_tech_state,
            helicopter=helicopter,
            heli_ground_y=heli_ground_y,
        )
        return PlayingKeyboardResult(
            handled=airport_driver_mode.handled,
            meal_truck_driver_mode=airport_driver_mode.meal_truck_driver_mode,
            meal_truck_lift_command_extended=airport_driver_mode.meal_truck_lift_command_extended,
            bus_driver_mode=airport_driver_mode.bus_driver_mode,
        )

    if fire_key_pressed and selected_mission_id == "airport" and meal_truck_driver_mode:
        return PlayingKeyboardResult(
            handled=True,
            meal_truck_driver_mode=meal_truck_driver_mode,
            meal_truck_lift_command_extended=not meal_truck_lift_command_extended,
            bus_driver_mode=bus_driver_mode,
        )

    return PlayingKeyboardResult(
        handled=False,
        meal_truck_driver_mode=meal_truck_driver_mode,
        meal_truck_lift_command_extended=meal_truck_lift_command_extended,
        bus_driver_mode=bus_driver_mode,
    )
