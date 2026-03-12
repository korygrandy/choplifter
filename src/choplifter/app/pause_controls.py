from __future__ import annotations

import pygame


def handle_pause_quit_confirm_keydown(*, mode: str, quit_confirm: bool, key: int) -> tuple[bool, bool, bool]:
    """Handle paused quit-confirm keyboard flow.

    Returns: (handled, running, quit_confirm)
    """
    if not (mode == "paused" and quit_confirm):
        return False, True, quit_confirm

    if key in (pygame.K_RETURN, pygame.K_SPACE):
        return True, False, quit_confirm

    if key == pygame.K_ESCAPE:
        return True, True, False

    return False, True, quit_confirm


def handle_pause_quit_confirm_gamepad(
    *,
    quit_confirm: bool,
    a_down: bool,
    prev_btn_a_down: bool,
    b_down: bool,
    prev_btn_b_down: bool,
) -> tuple[bool, bool, bool]:
    """Handle quit-confirm flow while paused using gamepad buttons.

    Returns: (handled, running, quit_confirm)
    """
    if not quit_confirm:
        return False, True, quit_confirm

    if a_down and not prev_btn_a_down:
        return True, False, quit_confirm

    if b_down and not prev_btn_b_down:
        return True, True, False

    return False, True, quit_confirm


def handle_gamepad_pause_button(
    *,
    mode: str,
    start_down: bool,
    prev_btn_start_down: bool,
    b_down: bool,
    prev_btn_b_down: bool,
    just_paused_with_start: bool,
) -> tuple[str, bool, bool, bool]:
    """Handle Start/B pause toggling.

    Returns: (next_mode, next_just_paused_with_start, toggled_pause_state, clear_quit_confirm)
    """
    start_edge = bool(start_down and not prev_btn_start_down)
    b_edge = bool(b_down and not prev_btn_b_down)

    if mode == "playing" and start_edge:
        return "paused", True, True, False

    if mode == "mission_end" and start_edge:
        return "paused", True, True, False

    if mode == "paused":
        if (start_edge and not just_paused_with_start) or b_edge:
            return "playing", False, True, True
        if (not start_down) and prev_btn_start_down and just_paused_with_start:
            return mode, False, False, False

    return mode, just_paused_with_start, False, False