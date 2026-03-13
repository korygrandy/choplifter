from __future__ import annotations


def apply_keydown_result(
    *,
    running: bool,
    mode: str,
    runtime: object,
    selected_mission_index: int,
    selected_mission_id: str,
    selected_chopper_index: int,
    selected_chopper_asset: str,
    debug: object,
    keydown_result: object,
) -> tuple[bool, str, int, str, int, str, object]:
    running = bool(keydown_result.running and running)
    mode = keydown_result.mode
    runtime.pause_focus = keydown_result.pause_focus
    runtime.muted = keydown_result.muted
    selected_mission_index = keydown_result.selected_mission_index
    selected_mission_id = keydown_result.selected_mission_id
    selected_chopper_index = keydown_result.selected_chopper_index
    selected_chopper_asset = keydown_result.selected_chopper_asset
    debug = keydown_result.debug
    runtime.quit_confirm = keydown_result.quit_confirm
    runtime.meal_truck_driver_mode = keydown_result.meal_truck_driver_mode
    runtime.meal_truck_lift_command_extended = keydown_result.meal_truck_lift_command_extended
    runtime.bus_driver_mode = keydown_result.bus_driver_mode

    return (
        running,
        mode,
        selected_mission_index,
        selected_mission_id,
        selected_chopper_index,
        selected_chopper_asset,
        debug,
    )


def apply_joybutton_result(
    *,
    mode: str,
    runtime: object,
    joybutton_result: object,
) -> str:
    mode = joybutton_result.mode
    runtime.pause_focus = joybutton_result.pause_focus
    runtime.meal_truck_driver_mode = joybutton_result.meal_truck_driver_mode
    runtime.meal_truck_lift_command_extended = joybutton_result.meal_truck_lift_command_extended
    runtime.bus_driver_mode = joybutton_result.bus_driver_mode
    return mode


def apply_nonpaused_gamepad_result(
    *,
    mode: str,
    selected_chopper_index: int,
    selected_mission_index: int,
    selected_mission_id: str,
    selected_chopper_asset: str,
    nonpaused_result: object,
) -> tuple[str, int, int, str, str]:
    mode = nonpaused_result.mode
    selected_chopper_index = nonpaused_result.selected_chopper_index
    selected_mission_index = nonpaused_result.selected_mission_index
    selected_mission_id = nonpaused_result.selected_mission_id
    selected_chopper_asset = nonpaused_result.selected_chopper_asset
    return (
        mode,
        selected_chopper_index,
        selected_mission_index,
        selected_mission_id,
        selected_chopper_asset,
    )
