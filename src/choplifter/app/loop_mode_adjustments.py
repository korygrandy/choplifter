from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


CITY_STYLE_BRIEF_MISSION_IDS = (
    "city",
    "city_center",
    "citycenter",
    "mission1",
    "m1",
    "worship",
    "worship_center",
    "worshipcenter",
    "mission3",
    "m3",
)


@dataclass
class LoopModeAdjustmentResult:
    mode: str


def apply_post_input_mode_adjustments(
    *,
    mode: str,
    selected_mission_id: str,
    runtime: object,
    cutscene_video: object,
    start_mission_intro_or_playing_fn: Callable[[str], str],
    play_satellite_reallocating_fn: Callable[[], None],
    play_airport_ai_mission_brief_fn: Callable[[], None],
) -> LoopModeAdjustmentResult:
    """Apply mode and deferred audio adjustments after keyboard/gamepad input handling."""
    next_mode = mode

    # Keyboard route can enter cutscene without creating mission video; route through intro helper.
    if runtime.prev_loop_mode == "select_chopper" and next_mode == "cutscene" and cutscene_video is None:
        next_mode = start_mission_intro_or_playing_fn(selected_mission_id)

    # Defer city satellite SFX until gameplay begins.
    if runtime.prev_loop_mode == "select_chopper" and next_mode in ("cutscene", "playing") and selected_mission_id in CITY_STYLE_BRIEF_MISSION_IDS:
        runtime.city_satellite_sfx_pending = True

    # Defer airport mission brief VO until gameplay begins (after cutscene/skip).
    if runtime.prev_loop_mode == "select_chopper" and next_mode in ("cutscene", "playing") and selected_mission_id in ("airport", "airport_special_ops"):
        runtime.airport_ai_mission_brief_pending = True

    if runtime.city_satellite_sfx_pending and next_mode == "playing":
        play_satellite_reallocating_fn()
        runtime.city_satellite_sfx_pending = False

    if runtime.airport_ai_mission_brief_pending and next_mode == "playing":
        play_airport_ai_mission_brief_fn()
        runtime.airport_ai_mission_brief_pending = False

    runtime.prev_loop_mode = next_mode
    return LoopModeAdjustmentResult(mode=next_mode)
