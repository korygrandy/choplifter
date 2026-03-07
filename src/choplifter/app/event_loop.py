from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence
import pygame


def handle_mission_end_keyboard_navigation(*, key: int, mode: str, mission_ended: bool, set_toast: Callable[[str], None]) -> tuple[bool, str]:
    """Handle key navigation while the mission-end screen is active."""
    if not (mode == "mission_end" or mission_ended):
        return False, mode

    if key in (pygame.K_ESCAPE, pygame.K_PAUSE, pygame.K_RETURN, pygame.K_KP_ENTER):
        set_toast("Mission ended: returning to Mission Select")
        return True, "select_mission"

    # Consume all other keys while in mission-end state.
    return True, mode


def handle_mission_end_gamepad_navigation(*, button: int, mode: str, set_toast: Callable[[str], None]) -> tuple[bool, str]:
    """Handle gamepad navigation while the mission-end screen is active."""
    if mode != "mission_end":
        return False, mode

    if button == 7:  # Start button
        set_toast("Mission ended: returning to Mission Select")
        return True, "select_mission"

    return True, mode


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

    if mode == "paused":
        if (start_edge and not just_paused_with_start) or b_edge:
            return "playing", False, True, True
        if (not start_down) and prev_btn_start_down and just_paused_with_start:
            return mode, False, False, False

    return mode, just_paused_with_start, False, False


def should_skip_on_gamepad_buttons(
    *,
    a_down: bool,
    prev_btn_a_down: bool,
    b_down: bool,
    prev_btn_b_down: bool,
    x_down: bool,
    prev_btn_x_down: bool,
    y_down: bool,
    prev_btn_y_down: bool,
    start_down: bool,
    prev_btn_start_down: bool,
    rb_down: bool,
    prev_btn_rb_down: bool,
    lb_down: bool,
    prev_btn_lb_down: bool,
) -> bool:
    """Return True when any skip-eligible gamepad button is newly pressed."""
    return bool(
        (a_down and not prev_btn_a_down)
        or (b_down and not prev_btn_b_down)
        or (x_down and not prev_btn_x_down)
        or (y_down and not prev_btn_y_down)
        or (start_down and not prev_btn_start_down)
        or (rb_down and not prev_btn_rb_down)
        or (lb_down and not prev_btn_lb_down)
    )


def handle_select_chopper_gamepad(
    *,
    menu_dir: int,
    prev_menu_dir: int,
    a_down: bool,
    prev_btn_a_down: bool,
    start_down: bool,
    prev_btn_start_down: bool,
    b_down: bool,
    prev_btn_b_down: bool,
    back_down: bool,
    prev_btn_back_down: bool,
    selected_chopper_index: int,
    chopper_count: int,
) -> tuple[str, int, bool, bool]:
    """Handle select_chopper gamepad transitions.

    Returns: (next_mode, next_selected_chopper_index, did_change_selection, did_confirm)
    """
    next_mode = "select_chopper"
    next_index = int(selected_chopper_index)
    did_change_selection = False
    did_confirm = False

    if menu_dir != 0 and menu_dir != prev_menu_dir:
        next_index = (next_index + menu_dir) % max(1, int(chopper_count))
        did_change_selection = True

    if (a_down and not prev_btn_a_down) or (start_down and not prev_btn_start_down):
        next_mode = "playing"
        did_confirm = True
    elif (b_down and not prev_btn_b_down) or (back_down and not prev_btn_back_down):
        next_mode = "select_mission"

    return next_mode, next_index, did_change_selection, did_confirm


def handle_select_mission_gamepad(
    *,
    menu_dir: int,
    prev_menu_dir: int,
    a_down: bool,
    prev_btn_a_down: bool,
    start_down: bool,
    prev_btn_start_down: bool,
    selected_mission_index: int,
    mission_count: int,
) -> tuple[str, int, bool]:
    """Handle select_mission gamepad transitions.

    Returns: (next_mode, next_selected_mission_index, did_change_selection)
    """
    next_mode = "select_mission"
    next_index = int(selected_mission_index)
    did_change_selection = False

    if menu_dir != 0 and menu_dir != prev_menu_dir:
        next_index = (next_index + menu_dir) % max(1, int(mission_count))
        did_change_selection = True

    if (a_down and not prev_btn_a_down) or (start_down and not prev_btn_start_down):
        next_mode = "select_chopper"

    return next_mode, next_index, did_change_selection


def handle_paused_focus_navigation(*, menu_vert: int, prev_menu_vert: int, pause_focus: str) -> tuple[str, bool]:
    """Move pause focus when vertical menu input edges occur."""
    if menu_vert == 0 or menu_vert == prev_menu_vert:
        return pause_focus, False

    order = ["choppers", "restart_mission", "restart_game", "mute", "quit"]
    try:
        idx = order.index(pause_focus)
    except ValueError:
        idx = 0
    step = -1 if menu_vert < 0 else 1
    next_focus = order[(idx + step) % len(order)]
    return next_focus, next_focus != pause_focus


def handle_paused_chopper_cycle(
    *,
    pause_focus: str,
    menu_dir: int,
    prev_menu_dir: int,
    selected_chopper_index: int,
    chopper_count: int,
) -> tuple[int, bool]:
    """Cycle chopper selection while pause focus is on choppers."""
    if pause_focus != "choppers" or menu_dir == 0 or menu_dir == prev_menu_dir:
        return selected_chopper_index, False
    next_index = (int(selected_chopper_index) + int(menu_dir)) % max(1, int(chopper_count))
    return next_index, next_index != selected_chopper_index


def resolve_paused_a_action(
    *,
    a_down: bool,
    prev_btn_a_down: bool,
    pause_focus: str,
    quit_confirm: bool,
) -> tuple[str, bool, str]:
    """Resolve paused-menu A-button behavior.

    Returns: (action, next_quit_confirm, next_pause_focus)
    """
    if not (a_down and not prev_btn_a_down):
        return "none", quit_confirm, pause_focus

    if pause_focus == "restart_mission":
        return "restart_mission", False, pause_focus
    if pause_focus == "restart_game":
        return "restart_game", False, "choppers"
    if pause_focus == "mute":
        return "toggle_mute", False, pause_focus
    if pause_focus == "quit":
        if quit_confirm:
            return "quit_exit", True, pause_focus
        return "quit_prompt", True, pause_focus

    return "none", quit_confirm, pause_focus


def resolve_paused_gameplay_shortcuts(
    *,
    b_down: bool,
    prev_btn_b_down: bool,
    a_down: bool,
    prev_btn_a_down: bool,
    y_down: bool,
    prev_btn_y_down: bool,
    back_down: bool,
    prev_btn_back_down: bool,
    x_down: bool,
    prev_btn_x_down: bool,
    crash_active: bool,
    quit_confirm: bool,
) -> tuple[bool, bool, bool, bool, bool, bool]:
    """Resolve paused-mode gameplay shortcut flags.

    Returns:
    (cancel_quit_confirm, trigger_flare, toggle_doors, reverse_flip, cycle_facing, fire_weapon)
    """
    b_edge = bool(b_down and not prev_btn_b_down)
    a_edge = bool(a_down and not prev_btn_a_down)
    y_edge = bool(y_down and not prev_btn_y_down)
    back_edge = bool(back_down and not prev_btn_back_down)
    x_edge = bool(x_down and not prev_btn_x_down)

    cancel_quit_confirm = bool(b_edge and quit_confirm)
    trigger_flare = b_edge

    if crash_active:
        return cancel_quit_confirm, trigger_flare, False, False, False, False

    return cancel_quit_confirm, trigger_flare, a_edge, y_edge, back_edge, x_edge


def handle_debug_weather_keydown(
    *,
    key: int,
    debug_mode: bool,
    debug_weather_index: int,
    debug_weather_modes: Sequence[str],
) -> tuple[bool, bool, int, str | None, str | None]:
    """Handle F3/F5/F6 debug-weather key events.

    Returns: (handled, next_debug_mode, next_weather_index, toast_message, selected_weather_mode)
    """
    if key == pygame.K_F3:
        next_debug_mode = not debug_mode
        return True, next_debug_mode, debug_weather_index, f"Debug mode: {'ON' if next_debug_mode else 'OFF'} (F3)", None

    if debug_mode and key == pygame.K_F5:
        next_index = (debug_weather_index + 1) % max(1, len(debug_weather_modes))
        selected_mode = debug_weather_modes[next_index]
        return True, debug_mode, next_index, f"Weather: {selected_mode}", selected_mode

    if debug_mode and key == pygame.K_F6:
        next_index = (debug_weather_index - 1) % max(1, len(debug_weather_modes))
        selected_mode = debug_weather_modes[next_index]
        return True, debug_mode, next_index, f"Weather: {selected_mode}", selected_mode

    return False, debug_mode, debug_weather_index, None, None


@dataclass
class PausedMenuDecision:
    pause_focus: str
    quit_confirm: bool
    selected_chopper_index: int
    play_menu_select: bool
    action: str
    toggle_particles: bool
    toggle_flashes: bool
    toggle_screenshake: bool
    cancel_quit_confirm: bool
    trigger_flare: bool
    toggle_doors: bool
    reverse_flip: bool
    cycle_facing: bool
    fire_weapon: bool


def resolve_paused_mode_inputs(
    *,
    pause_focus: str,
    quit_confirm: bool,
    selected_chopper_index: int,
    chopper_count: int,
    menu_vert: int,
    prev_menu_vert: int,
    menu_dir: int,
    prev_menu_dir: int,
    a_down: bool,
    prev_btn_a_down: bool,
    b_down: bool,
    prev_btn_b_down: bool,
    x_down: bool,
    prev_btn_x_down: bool,
    y_down: bool,
    prev_btn_y_down: bool,
    rb_down: bool,
    prev_btn_rb_down: bool,
    back_down: bool,
    prev_btn_back_down: bool,
    crash_active: bool,
) -> PausedMenuDecision:
    """Resolve all paused-mode gamepad decisions in one place."""
    toggle_particles = bool(x_down and not prev_btn_x_down)
    toggle_flashes = bool(y_down and not prev_btn_y_down)
    toggle_screenshake = bool(rb_down and not prev_btn_rb_down)

    next_pause_focus = pause_focus
    next_quit_confirm = quit_confirm
    next_chopper_index = int(selected_chopper_index)
    play_menu_select = False

    next_pause_focus, focus_changed = handle_paused_focus_navigation(
        menu_vert=menu_vert,
        prev_menu_vert=prev_menu_vert,
        pause_focus=next_pause_focus,
    )
    if focus_changed:
        play_menu_select = True
        next_quit_confirm = False

    next_chopper_index, chopper_changed = handle_paused_chopper_cycle(
        pause_focus=next_pause_focus,
        menu_dir=menu_dir,
        prev_menu_dir=prev_menu_dir,
        selected_chopper_index=next_chopper_index,
        chopper_count=chopper_count,
    )
    if chopper_changed:
        play_menu_select = True
        next_quit_confirm = False

    action, next_quit_confirm, next_pause_focus = resolve_paused_a_action(
        a_down=a_down,
        prev_btn_a_down=prev_btn_a_down,
        pause_focus=next_pause_focus,
        quit_confirm=next_quit_confirm,
    )

    (
        cancel_quit_confirm,
        trigger_flare,
        toggle_doors,
        reverse_flip,
        cycle_facing,
        fire_weapon,
    ) = resolve_paused_gameplay_shortcuts(
        b_down=b_down,
        prev_btn_b_down=prev_btn_b_down,
        a_down=a_down,
        prev_btn_a_down=prev_btn_a_down,
        y_down=y_down,
        prev_btn_y_down=prev_btn_y_down,
        back_down=back_down,
        prev_btn_back_down=prev_btn_back_down,
        x_down=x_down,
        prev_btn_x_down=prev_btn_x_down,
        crash_active=crash_active,
        quit_confirm=next_quit_confirm,
    )

    return PausedMenuDecision(
        pause_focus=next_pause_focus,
        quit_confirm=next_quit_confirm,
        selected_chopper_index=next_chopper_index,
        play_menu_select=play_menu_select,
        action=action,
        toggle_particles=toggle_particles,
        toggle_flashes=toggle_flashes,
        toggle_screenshake=toggle_screenshake,
        cancel_quit_confirm=cancel_quit_confirm,
        trigger_flare=trigger_flare,
        toggle_doors=toggle_doors,
        reverse_flip=reverse_flip,
        cycle_facing=cycle_facing,
        fire_weapon=fire_weapon,
    )
