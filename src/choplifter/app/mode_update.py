from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ModeTransitionResult:
    mode: str
    mission_end_return_seconds: float
    restore_doors_after_cutscene: bool
    mission_end_auto_returned: bool


def resolve_post_frame_mode_transitions(
    *,
    mode: str,
    frame_dt: float,
    mission_end_return_seconds: float,
    intro_finished: bool,
    cutscene_finished: bool,
) -> ModeTransitionResult:
    """Apply non-playing mode transitions after a frame update."""
    next_mode = mode
    next_mission_end_seconds = float(mission_end_return_seconds)
    restore_doors_after_cutscene = False
    mission_end_auto_returned = False

    if mode == "intro" and intro_finished:
        next_mode = "select_mission"

    elif mode == "cutscene" and cutscene_finished:
        next_mode = "playing"
        restore_doors_after_cutscene = True

    elif mode == "mission_end":
        next_mission_end_seconds = max(0.0, float(mission_end_return_seconds) - float(frame_dt))
        if next_mission_end_seconds <= 0.0:
            next_mode = "select_mission"
            mission_end_auto_returned = True

    return ModeTransitionResult(
        mode=next_mode,
        mission_end_return_seconds=next_mission_end_seconds,
        restore_doors_after_cutscene=restore_doors_after_cutscene,
        mission_end_auto_returned=mission_end_auto_returned,
    )
