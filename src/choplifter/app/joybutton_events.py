from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .mission_pause_transitions import apply_pause_transition, handle_mission_end_gamepad_navigation
from .playing_gamepad_inputs import handle_playing_gamepad_button


@dataclass
class JoyButtonEventResult:
    mode: str
    pause_focus: str
    meal_truck_driver_mode: bool
    meal_truck_lift_command_extended: bool
    bus_driver_mode: bool


def handle_joybuttondown_event(
    *,
    button: int,
    mode: str,
    pause_focus: str,
    set_toast: Callable[[str], None],
    audio: object,
    selected_mission_id: str,
    mission: object,
    helicopter: object,
    logger: object,
    flares: object,
    meal_truck_driver_mode: bool,
    meal_truck_lift_command_extended: bool,
    bus_driver_mode: bool,
    airport_meal_truck_state: object,
    airport_bus_state: object,
    airport_tech_state: object,
    heli_ground_y: float,
    spawn_projectile_from_helicopter_logged: Callable[..., None],
    try_start_flare_salvo: Callable[..., None],
    toggle_doors_with_logging: Callable[..., None],
    boarded_count: Callable[..., int],
    chopper_weapons_locked: Callable[..., bool],
    Facing: object,
) -> JoyButtonEventResult:
    """Handle one JOYBUTTONDOWN event and return updated runtime state."""
    next_mode = mode
    next_pause_focus = pause_focus
    next_meal_truck_driver_mode = meal_truck_driver_mode
    next_meal_truck_lift_command_extended = meal_truck_lift_command_extended
    next_bus_driver_mode = bus_driver_mode

    handled_mission_end, mission_end_mode = handle_mission_end_gamepad_navigation(
        button=button,
        mode=mode,
        set_toast=set_toast,
    )
    if handled_mission_end:
        pause_transition = apply_pause_transition(
            prev_mode=mode,
            next_mode=mission_end_mode,
            pause_focus=pause_focus,
            audio=audio,
        )
        return JoyButtonEventResult(
            mode=mission_end_mode,
            pause_focus=pause_transition.pause_focus,
            meal_truck_driver_mode=next_meal_truck_driver_mode,
            meal_truck_lift_command_extended=next_meal_truck_lift_command_extended,
            bus_driver_mode=next_bus_driver_mode,
        )

    if mode == "playing":
        playing_gamepad = handle_playing_gamepad_button(
            button=button,
            selected_mission_id=selected_mission_id,
            mission=mission,
            helicopter=helicopter,
            audio=audio,
            logger=logger,
            flares=flares,
            meal_truck_driver_mode=meal_truck_driver_mode,
            meal_truck_lift_command_extended=meal_truck_lift_command_extended,
            bus_driver_mode=bus_driver_mode,
            airport_meal_truck_state=airport_meal_truck_state,
            airport_bus_state=airport_bus_state,
            airport_tech_state=airport_tech_state,
            heli_ground_y=heli_ground_y,
            spawn_projectile_from_helicopter_logged=spawn_projectile_from_helicopter_logged,
            try_start_flare_salvo=try_start_flare_salvo,
            toggle_doors_with_logging=toggle_doors_with_logging,
            boarded_count=boarded_count,
            set_toast=set_toast,
            chopper_weapons_locked=chopper_weapons_locked,
            Facing=Facing,
        )
        next_meal_truck_driver_mode = playing_gamepad.meal_truck_driver_mode
        next_meal_truck_lift_command_extended = playing_gamepad.meal_truck_lift_command_extended
        next_bus_driver_mode = playing_gamepad.bus_driver_mode

    return JoyButtonEventResult(
        mode=next_mode,
        pause_focus=next_pause_focus,
        meal_truck_driver_mode=next_meal_truck_driver_mode,
        meal_truck_lift_command_extended=next_meal_truck_lift_command_extended,
        bus_driver_mode=next_bus_driver_mode,
    )
