from __future__ import annotations

from dataclasses import dataclass

from ..vehicle_assets import should_activate_truck_driver_mode


@dataclass
class AirportDriverModeDoorResult:
    handled: bool
    meal_truck_driver_mode: bool
    meal_truck_lift_command_extended: bool
    bus_driver_mode: bool


def _set_engineer_boarding_animation(
    tech_state,
    *,
    animation_state: str,
    start_x: float,
    end_x: float,
    ground_y: float,
) -> None:
    if tech_state is None:
        return

    tech_state.boarding_animation_state = animation_state
    tech_state.boarding_animation_timer = 0.0
    tech_state.boarding_start_x = start_x
    tech_state.boarding_start_y = ground_y
    tech_state.boarding_end_x = end_x
    tech_state.boarding_end_y = ground_y


def can_enter_bus_driver_mode(*, bus_state=None, tech_state=None, helicopter=None) -> bool:
    """Tech must be on the bus and the helicopter must be near it to re-board."""
    if bus_state is None or tech_state is None or helicopter is None:
        return False
    if not bool(getattr(tech_state, "on_bus", False)):
        return False
    heli_x = float(getattr(helicopter.pos, "x", 0.0))
    bus_x = float(getattr(bus_state, "x", 0.0))
    return abs(heli_x - bus_x) <= 200.0


def handle_airport_driver_mode_doors(
    *,
    meal_truck_driver_mode: bool,
    meal_truck_lift_command_extended: bool,
    bus_driver_mode: bool,
    meal_truck_state=None,
    bus_state=None,
    tech_state=None,
    helicopter=None,
    heli_ground_y: float,
) -> AirportDriverModeDoorResult:
    """Handle airport-specific door presses for truck and bus driver modes."""
    engineer_ground_y = float(heli_ground_y) - 18.0

    if meal_truck_driver_mode and meal_truck_state is not None:
        meal_truck_driver_mode = False
        meal_truck_state.driver_mode_active = False
        meal_truck_state.driver_mode_exit_timer = 0.2
        _set_engineer_boarding_animation(
            tech_state,
            animation_state="returning",
            start_x=float(getattr(meal_truck_state, "x", 0.0)),
            end_x=float(getattr(getattr(helicopter, "pos", None), "x", 0.0)),
            ground_y=engineer_ground_y,
        )
        return AirportDriverModeDoorResult(
            handled=True,
            meal_truck_driver_mode=meal_truck_driver_mode,
            meal_truck_lift_command_extended=meal_truck_lift_command_extended,
            bus_driver_mode=bus_driver_mode,
        )

    if should_activate_truck_driver_mode(
        meal_truck_state=meal_truck_state,
        doors_button_pressed=True,
    ):
        meal_truck_driver_mode = True
        if meal_truck_state is not None:
            meal_truck_state.driver_mode_active = True
            meal_truck_lift_command_extended = bool(
                float(getattr(meal_truck_state, "extension_progress", 0.0)) >= 0.5
            )
            _set_engineer_boarding_animation(
                tech_state,
                animation_state="deploying",
                start_x=float(getattr(getattr(helicopter, "pos", None), "x", 0.0)),
                end_x=float(getattr(meal_truck_state, "x", 0.0)),
                ground_y=engineer_ground_y,
            )
        return AirportDriverModeDoorResult(
            handled=True,
            meal_truck_driver_mode=meal_truck_driver_mode,
            meal_truck_lift_command_extended=meal_truck_lift_command_extended,
            bus_driver_mode=bus_driver_mode,
        )

    if bus_driver_mode and bus_state is not None:
        bus_driver_mode = False
        bus_state.driver_mode_active = False
        return AirportDriverModeDoorResult(
            handled=True,
            meal_truck_driver_mode=meal_truck_driver_mode,
            meal_truck_lift_command_extended=meal_truck_lift_command_extended,
            bus_driver_mode=bus_driver_mode,
        )

    if can_enter_bus_driver_mode(bus_state=bus_state, tech_state=tech_state, helicopter=helicopter):
        bus_driver_mode = True
        if bus_state is not None:
            bus_state.driver_mode_active = True
        return AirportDriverModeDoorResult(
            handled=True,
            meal_truck_driver_mode=meal_truck_driver_mode,
            meal_truck_lift_command_extended=meal_truck_lift_command_extended,
            bus_driver_mode=bus_driver_mode,
        )

    return AirportDriverModeDoorResult(
        handled=False,
        meal_truck_driver_mode=meal_truck_driver_mode,
        meal_truck_lift_command_extended=meal_truck_lift_command_extended,
        bus_driver_mode=bus_driver_mode,
    )