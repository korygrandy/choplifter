from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .vehicle_driver_modes import handle_airport_driver_mode_doors


@dataclass
class PlayingGamepadButtonResult:
    meal_truck_driver_mode: bool
    meal_truck_lift_command_extended: bool
    bus_driver_mode: bool


def handle_playing_gamepad_button(
    *,
    button: int,
    selected_mission_id: str,
    mission: object,
    helicopter: object,
    audio: object,
    logger: object,
    flares: object,
    meal_truck_driver_mode: bool,
    meal_truck_lift_command_extended: bool,
    bus_driver_mode: bool,
    airport_meal_truck_state: object,
    airport_bus_state: object,
    airport_tech_state: object,
    heli_ground_y: float,
    spawn_projectile_from_helicopter_logged: Callable[[object, object, object], None],
    try_start_flare_salvo: Callable[..., None],
    toggle_doors_with_logging: Callable[..., None],
    boarded_count: Callable[[object], int],
    set_toast: Callable[[str], None],
    chopper_weapons_locked: Callable[..., bool],
    Facing: object,
) -> PlayingGamepadButtonResult:
    """Handle a JOYBUTTONDOWN event while in playing mode."""
    crash_active = bool(getattr(mission, "crash_active", False))
    engineer_remote_control_active = bool(getattr(mission, "engineer_remote_control_active", False))
    weapons_locked = chopper_weapons_locked(
        meal_truck_driver_mode=bool(meal_truck_driver_mode),
        bus_driver_mode=bool(bus_driver_mode),
        engineer_remote_control_active=engineer_remote_control_active,
    )

    if button == 2:  # X button: fire (or lift toggle in driver mode)
        if logger:
            logger.debug("Fire button pressed (button=2) in playing mode")
        if meal_truck_driver_mode and selected_mission_id == "airport":
            meal_truck_lift_command_extended = not meal_truck_lift_command_extended
        elif not crash_active and not weapons_locked:
            spawn_projectile_from_helicopter_logged(mission, helicopter, logger)
            if helicopter.facing is Facing.FORWARD:
                audio.play_bomb()
            else:
                audio.play_shoot()

    elif button == 1:  # B button: flare
        if logger:
            logger.debug("Flare button pressed (button=1) in playing mode")
        if not weapons_locked:
            try_start_flare_salvo(flares, mission=mission, helicopter=helicopter, audio=audio)

    elif button == 0:  # A button: doors
        if not crash_active:
            if selected_mission_id == "airport":
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
                meal_truck_driver_mode = airport_driver_mode.meal_truck_driver_mode
                meal_truck_lift_command_extended = airport_driver_mode.meal_truck_lift_command_extended
                bus_driver_mode = airport_driver_mode.bus_driver_mode
                if not airport_driver_mode.handled:
                    toggle_doors_with_logging(helicopter, mission, audio, logger, boarded_count, set_toast)
            else:
                toggle_doors_with_logging(helicopter, mission, audio, logger, boarded_count, set_toast)

    elif button == 3:  # Y button: reverse
        if not crash_active:
            helicopter.reverse_flip()

    elif button == 6:  # Back button: facing
        if not crash_active:
            helicopter.cycle_facing()

    return PlayingGamepadButtonResult(
        meal_truck_driver_mode=meal_truck_driver_mode,
        meal_truck_lift_command_extended=meal_truck_lift_command_extended,
        bus_driver_mode=bus_driver_mode,
    )
