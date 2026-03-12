from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pygame


def handle_mission_end_keyboard_navigation(*, key: int, mode: str, mission_ended: bool, set_toast: callable) -> tuple[bool, str]:
    """Handle key navigation while the mission-end screen is active."""
    if not (mode == "mission_end" or mission_ended):
        return False, mode

    if key in (pygame.K_ESCAPE, pygame.K_PAUSE):
        set_toast("Mission ended: pause menu opened")
        return True, "paused"

    if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        set_toast("Mission ended: returning to Mission Select")
        return True, "select_mission"

    return True, mode


def handle_mission_end_gamepad_navigation(*, button: int, mode: str, set_toast: Callable[[str], None]) -> tuple[bool, str]:
    """Handle gamepad navigation while the mission-end screen is active."""
    if mode != "mission_end":
        return False, mode

    if button == 7:  # Start button
        set_toast("Mission ended: pause menu opened")
        return True, "paused"

    return True, mode


@dataclass
class PauseTransitionResult:
    pause_focus: str
    entered_pause: bool
    resumed_playing: bool


def apply_pause_transition(
    *,
    prev_mode: str,
    next_mode: str,
    pause_focus: str,
    audio: object,
) -> PauseTransitionResult:
    """Apply pause-menu audio/focus side effects for a mode transition."""
    entered_pause = prev_mode != next_mode and next_mode == "paused"
    resumed_playing = prev_mode == "paused" and next_mode == "playing"
    next_pause_focus = pause_focus

    if entered_pause:
        audio.play_pause_toggle()
        audio.set_pause_menu_active(True)
        next_pause_focus = "choppers"
    elif resumed_playing:
        audio.set_pause_menu_active(False)
        audio.play_pause_toggle()

    return PauseTransitionResult(
        pause_focus=next_pause_focus,
        entered_pause=entered_pause,
        resumed_playing=resumed_playing,
    )