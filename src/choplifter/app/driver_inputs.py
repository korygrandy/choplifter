from __future__ import annotations

from dataclasses import dataclass

from ..bus_ai import BusDriverInput
from ..helicopter import HelicopterInput
from ..vehicle_assets import TruckDriverInput


@dataclass
class DriverInputBuildResult:
    helicopter_input: HelicopterInput
    truck_driver_input: TruckDriverInput
    bus_driver_input: BusDriverInput


def build_driver_inputs(
    *,
    mode: str,
    helicopter_input: HelicopterInput,
    kb_tilt_left: bool,
    kb_tilt_right: bool,
    gp_tilt_left: bool,
    gp_tilt_right: bool,
    meal_truck_driver_mode: bool,
    meal_truck_lift_command_extended: bool,
    bus_driver_mode: bool,
) -> DriverInputBuildResult:
    """Build vehicle driver inputs and gate helicopter controls while driving vehicles."""
    truck_driver_input = TruckDriverInput(
        move_left=(kb_tilt_left or gp_tilt_left) if mode == "playing" and meal_truck_driver_mode else False,
        move_right=(kb_tilt_right or gp_tilt_right) if mode == "playing" and meal_truck_driver_mode else False,
        extend_lift=meal_truck_lift_command_extended if mode == "playing" and meal_truck_driver_mode else False,
    )

    bus_driver_input = BusDriverInput(
        move_left=(kb_tilt_left or gp_tilt_left) if mode == "playing" and bus_driver_mode else False,
        move_right=(kb_tilt_right or gp_tilt_right) if mode == "playing" and bus_driver_mode else False,
    )

    if meal_truck_driver_mode or bus_driver_mode:
        helicopter_input = HelicopterInput(
            tilt_left=False,
            tilt_right=False,
            lift_up=False,
            lift_down=False,
            brake=False,
        )

    return DriverInputBuildResult(
        helicopter_input=helicopter_input,
        truck_driver_input=truck_driver_input,
        bus_driver_input=bus_driver_input,
    )
