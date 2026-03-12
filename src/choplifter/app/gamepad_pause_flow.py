from __future__ import annotations

from dataclasses import dataclass

from .mission_pause_transitions import apply_pause_transition
from .pause_controls import handle_gamepad_pause_button, handle_pause_quit_confirm_gamepad


@dataclass
class GamepadPauseFlowResult:
    running: bool
    mode: str
    pause_focus: str
    just_paused_with_start: bool
    quit_confirm: bool


def handle_gamepad_pause_flow(
    *,
    mode: str,
    pause_focus: str,
    just_paused_with_start: bool,
    quit_confirm: bool,
    start_down: bool,
    prev_btn_start_down: bool,
    b_down: bool,
    prev_btn_b_down: bool,
    a_down: bool,
    prev_btn_a_down: bool,
    audio: object,
    logger: object,
) -> GamepadPauseFlowResult:
    """Apply pause toggle and quit-confirm gamepad flow from snapshot button state."""
    running = True
    next_mode = mode
    next_pause_focus = pause_focus
    next_just_paused = just_paused_with_start
    next_quit_confirm = quit_confirm

    if start_down and not prev_btn_start_down and logger is not None:
        logger.info(
            "GAMEPAD: Start button pressed (start_down=%s, prev_btn_start_down=%s, mode=%s)",
            start_down,
            prev_btn_start_down,
            mode,
        )

    if mode != "playing" and (start_down and not prev_btn_start_down) and logger is not None:
        logger.info("GAMEPAD: Start button pressed but pause not triggered (mode=%s)", mode)

    prev_mode = next_mode
    next_mode, next_just_paused, toggled_pause_state, clear_quit_confirm = handle_gamepad_pause_button(
        mode=next_mode,
        start_down=start_down,
        prev_btn_start_down=prev_btn_start_down,
        b_down=b_down,
        prev_btn_b_down=prev_btn_b_down,
        just_paused_with_start=next_just_paused,
    )

    if toggled_pause_state:
        pause_transition = apply_pause_transition(
            prev_mode=prev_mode,
            next_mode=next_mode,
            pause_focus=next_pause_focus,
            audio=audio,
        )
        next_pause_focus = pause_transition.pause_focus

    if prev_mode == "playing" and next_mode == "paused" and logger is not None:
        logger.info("PAUSE: Gamepad Start pressed, entering pause menu (mode=playing)")
    if prev_mode == "paused" and next_mode == "playing" and logger is not None:
        logger.info("UNPAUSE: Gamepad Start or B pressed, resuming game (mode=paused)")

    if clear_quit_confirm:
        next_quit_confirm = False

    handled_quit_confirm_gamepad, keep_running, next_quit_confirm = handle_pause_quit_confirm_gamepad(
        quit_confirm=next_quit_confirm,
        a_down=a_down,
        prev_btn_a_down=prev_btn_a_down,
        b_down=b_down,
        prev_btn_b_down=prev_btn_b_down,
    )
    if handled_quit_confirm_gamepad and not keep_running:
        running = False

    return GamepadPauseFlowResult(
        running=running,
        mode=next_mode,
        pause_focus=next_pause_focus,
        just_paused_with_start=next_just_paused,
        quit_confirm=next_quit_confirm,
    )
