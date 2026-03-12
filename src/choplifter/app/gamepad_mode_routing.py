from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GamepadModeRoutingResult:
    mode: str
    selected_chopper_index: int
    selected_mission_index: int
    chopper_selection_changed: bool
    chopper_confirmed: bool
    mission_selection_changed: bool
    selected_mission_backtracked: bool
    skip_intro_requested: bool
    skip_cutscene_requested: bool


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
        next_mode = "cutscene"
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


def route_gamepad_mode_inputs(
    *,
    mode: str,
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
    start_down: bool,
    prev_btn_start_down: bool,
    rb_down: bool,
    prev_btn_rb_down: bool,
    lb_down: bool,
    prev_btn_lb_down: bool,
    back_down: bool,
    prev_btn_back_down: bool,
    selected_chopper_index: int,
    chopper_count: int,
    selected_mission_index: int,
    mission_count: int,
) -> GamepadModeRoutingResult:
    """Resolve non-paused gamepad mode routing and return side-effect-free flags."""
    next_mode = mode
    next_chopper_index = int(selected_chopper_index)
    next_mission_index = int(selected_mission_index)
    chopper_selection_changed = False
    chopper_confirmed = False
    mission_selection_changed = False
    selected_mission_backtracked = False
    skip_intro_requested = False
    skip_cutscene_requested = False

    if mode == "select_chopper":
        previous_mode = next_mode
        (
            next_mode,
            next_chopper_index,
            chopper_selection_changed,
            chopper_confirmed,
        ) = handle_select_chopper_gamepad(
            menu_dir=menu_dir,
            prev_menu_dir=prev_menu_dir,
            a_down=a_down,
            prev_btn_a_down=prev_btn_a_down,
            start_down=start_down,
            prev_btn_start_down=prev_btn_start_down,
            b_down=b_down,
            prev_btn_b_down=prev_btn_b_down,
            back_down=back_down,
            prev_btn_back_down=prev_btn_back_down,
            selected_chopper_index=next_chopper_index,
            chopper_count=chopper_count,
        )
        selected_mission_backtracked = previous_mode == "select_chopper" and next_mode == "select_mission"

    elif mode == "intro":
        skip_intro_requested = should_skip_on_gamepad_buttons(
            a_down=a_down,
            prev_btn_a_down=prev_btn_a_down,
            b_down=b_down,
            prev_btn_b_down=prev_btn_b_down,
            x_down=x_down,
            prev_btn_x_down=prev_btn_x_down,
            y_down=y_down,
            prev_btn_y_down=prev_btn_y_down,
            start_down=start_down,
            prev_btn_start_down=prev_btn_start_down,
            rb_down=rb_down,
            prev_btn_rb_down=prev_btn_rb_down,
            lb_down=lb_down,
            prev_btn_lb_down=prev_btn_lb_down,
        )
        if skip_intro_requested:
            next_mode = "select_mission"

    elif mode == "cutscene":
        skip_cutscene_requested = should_skip_on_gamepad_buttons(
            a_down=a_down,
            prev_btn_a_down=prev_btn_a_down,
            b_down=b_down,
            prev_btn_b_down=prev_btn_b_down,
            x_down=x_down,
            prev_btn_x_down=prev_btn_x_down,
            y_down=y_down,
            prev_btn_y_down=prev_btn_y_down,
            start_down=start_down,
            prev_btn_start_down=prev_btn_start_down,
            rb_down=rb_down,
            prev_btn_rb_down=prev_btn_rb_down,
            lb_down=lb_down,
            prev_btn_lb_down=prev_btn_lb_down,
        )
        if skip_cutscene_requested:
            next_mode = "playing"

    elif mode == "select_mission":
        previous_mode = next_mode
        next_mode, next_mission_index, mission_selection_changed = handle_select_mission_gamepad(
            menu_dir=menu_dir,
            prev_menu_dir=prev_menu_dir,
            a_down=a_down,
            prev_btn_a_down=prev_btn_a_down,
            start_down=start_down,
            prev_btn_start_down=prev_btn_start_down,
            selected_mission_index=next_mission_index,
            mission_count=mission_count,
        )
        selected_mission_backtracked = previous_mode == "select_mission" and next_mode == "select_chopper"

    return GamepadModeRoutingResult(
        mode=next_mode,
        selected_chopper_index=next_chopper_index,
        selected_mission_index=next_mission_index,
        chopper_selection_changed=chopper_selection_changed,
        chopper_confirmed=chopper_confirmed,
        mission_selection_changed=mission_selection_changed,
        selected_mission_backtracked=selected_mission_backtracked,
        skip_intro_requested=skip_intro_requested,
        skip_cutscene_requested=skip_cutscene_requested,
    )