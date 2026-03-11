from __future__ import annotations


def chopper_weapons_locked(
    *,
    meal_truck_driver_mode: bool,
    bus_driver_mode: bool,
    engineer_remote_control_active: bool,
) -> bool:
    """Return True when chopper fire/flare controls must be blocked."""
    return bool(meal_truck_driver_mode or bus_driver_mode or engineer_remote_control_active)
