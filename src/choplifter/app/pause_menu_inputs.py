from __future__ import annotations

from dataclasses import dataclass


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


def handle_paused_focus_navigation(*, menu_vert: int, prev_menu_vert: int, pause_focus: str) -> tuple[str, bool]:
    """Move pause focus when vertical menu input edges occur."""
    if menu_vert == 0 or menu_vert == prev_menu_vert:
        return pause_focus, False

    order = ["choppers", "restart_mission", "restart_game", "mute", "quit"]
    try:
        idx = order.index(pause_focus)
    except ValueError:
        return pause_focus, False
    step = -1 if menu_vert < 0 else 1
    next_idx = (idx + step) % len(order)
    return order[next_idx], True


def handle_paused_chopper_cycle(
    *,
    pause_focus: str,
    menu_dir: int,
    prev_menu_dir: int,
    selected_chopper_index: int,
    chopper_count: int,
) -> tuple[int, bool]:
    """Cycle paused-menu chopper selection on left/right input edges."""
    if pause_focus != "choppers":
        return selected_chopper_index, False

    if menu_dir == 0 or menu_dir == prev_menu_dir:
        return selected_chopper_index, False

    if chopper_count <= 0:
        return 0, False

    next_index = (int(selected_chopper_index) + int(menu_dir)) % int(chopper_count)
    return next_index, (next_index != int(selected_chopper_index))


def resolve_paused_a_action(
    *,
    a_down: bool,
    prev_btn_a_down: bool,
    pause_focus: str,
    quit_confirm: bool,
) -> tuple[str, bool, str]:
    """Resolve paused-menu A button action and quit-confirm state."""
    if not (a_down and not prev_btn_a_down):
        return "none", quit_confirm, pause_focus

    if pause_focus == "restart_mission":
        return "restart_mission", False, pause_focus
    if pause_focus == "restart_game":
        return "restart_game", False, pause_focus
    if pause_focus == "mute":
        return "toggle_mute", False, pause_focus
    if pause_focus == "quit":
        if quit_confirm:
            return "quit_exit", True, pause_focus
        return "quit_prompt", True, pause_focus

    return "none", False, pause_focus


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