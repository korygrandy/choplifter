from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GameRuntimeState:
    """Mutable UI/runtime flags currently owned by main loop state."""

    pause_focus: str = "choppers"  # choppers | restart_mission | restart_game | mute | quit
    quit_confirm: bool = False
    muted: bool = False
    mission_end_return_seconds: float = 0.0
    just_paused_with_start: bool = False
    prev_menu_dir: int = 0
    prev_menu_vert: int = 0
    meal_truck_driver_mode: bool = False
    meal_truck_lift_command_extended: bool = False
    bus_driver_mode: bool = False
    doors_open_before_cutscene: bool = False
    camera_x_smoothed: float | None = None
