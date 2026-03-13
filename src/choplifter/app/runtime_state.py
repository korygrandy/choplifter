from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field


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
    debug_mode: bool = False
    debug_weather_index: int = 0
    weather_mode: str = "clear"
    weather_timer: float = 0.0
    weather_duration: float = 0.0
    hud_disabled_timer: float = 0.0
    prev_loop_mode: str = "intro"
    city_satellite_sfx_pending: bool = False
    vip_kia_overlay_timer: float = 0.0
    vip_kia_overlay_shown: bool = False
    tech_kia_overlay_timer: float = 0.0
    tech_kia_overlay_shown: bool = False
    city_objective_overlay_timer: float = 0.0
    perf_frame_prep_ms: float = 0.0
    perf_render_present_ms: float = 0.0
    perf_overlay: dict[str, float] = field(default_factory=dict)
