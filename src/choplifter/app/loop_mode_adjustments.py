from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


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
) -> LoopModeAdjustmentResult:
    """Apply mode and deferred audio adjustments after keyboard/gamepad input handling."""
    next_mode = mode

    # Keyboard route can enter cutscene without creating mission video; route through intro helper.
    if runtime.prev_loop_mode == "select_chopper" and next_mode == "cutscene" and cutscene_video is None:
        next_mode = start_mission_intro_or_playing_fn(selected_mission_id)

    # Defer city satellite SFX until gameplay begins.
    if runtime.prev_loop_mode == "select_chopper" and next_mode in ("cutscene", "playing") and selected_mission_id == "city":
        runtime.city_satellite_sfx_pending = True

    if runtime.city_satellite_sfx_pending and next_mode == "playing":
        play_satellite_reallocating_fn()
        runtime.city_satellite_sfx_pending = False

    runtime.prev_loop_mode = next_mode
    return LoopModeAdjustmentResult(mode=next_mode)
