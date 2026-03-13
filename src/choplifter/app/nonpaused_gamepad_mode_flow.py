from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .gamepad_mode_routing import route_gamepad_mode_inputs


@dataclass
class NonPausedGamepadModeResult:
    mode: str
    selected_mission_index: int
    selected_mission_id: str
    selected_chopper_index: int
    selected_chopper_asset: str


def handle_nonpaused_gamepad_mode_flow(
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
    selected_mission_index: int,
    selected_mission_id: str,
    selected_chopper_asset: str,
    chopper_choices: list,
    mission_choices: list,
    audio: object,
    set_toast: Callable[[str], None],
    play_satellite_reallocating: Callable[[], None],
    reset_game: Callable[[], None],
    start_mission_intro_or_playing_fn: Callable[[str], str],
    skip_intro: Callable[[], None],
    skip_mission_cutscene: Callable[[], None],
    apply_mission_preview: Callable[[], None],
) -> NonPausedGamepadModeResult:
    """Handle gamepad mode routing when not paused and apply side effects."""
    previous_mode = mode
    next_mode = mode
    next_selected_chopper_index = int(selected_chopper_index)
    next_selected_mission_index = int(selected_mission_index)
    next_selected_mission_id = str(selected_mission_id)
    next_selected_chopper_asset = str(selected_chopper_asset)

    gamepad_mode = route_gamepad_mode_inputs(
        mode=mode,
        menu_dir=menu_dir,
        prev_menu_dir=prev_menu_dir,
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
        back_down=back_down,
        prev_btn_back_down=prev_btn_back_down,
        selected_chopper_index=next_selected_chopper_index,
        chopper_count=len(chopper_choices),
        selected_mission_index=next_selected_mission_index,
        mission_count=len(mission_choices),
    )
    next_mode = gamepad_mode.mode
    next_selected_chopper_index = gamepad_mode.selected_chopper_index
    next_selected_mission_index = gamepad_mode.selected_mission_index

    if gamepad_mode.chopper_selection_changed:
        next_selected_chopper_asset = chopper_choices[next_selected_chopper_index][0]
        audio.play_menu_select()
    if gamepad_mode.chopper_confirmed:
        set_toast(f"Chopper selected: {chopper_choices[next_selected_chopper_index][1]}")
        reset_game()
        next_mode = start_mission_intro_or_playing_fn(next_selected_mission_id)
    elif previous_mode == "select_chopper" and gamepad_mode.selected_mission_backtracked:
        set_toast("Back to Mission Select")

    if gamepad_mode.skip_intro_requested:
        skip_intro()
    if gamepad_mode.skip_cutscene_requested:
        skip_mission_cutscene()

    if gamepad_mode.mission_selection_changed:
        next_selected_mission_id = mission_choices[next_selected_mission_index][0]
        audio.play_menu_select()
        apply_mission_preview()
    if previous_mode == "select_mission" and gamepad_mode.selected_mission_backtracked:
        set_toast(f"Mission selected: {mission_choices[next_selected_mission_index][1]}")

    return NonPausedGamepadModeResult(
        mode=next_mode,
        selected_mission_index=next_selected_mission_index,
        selected_mission_id=next_selected_mission_id,
        selected_chopper_index=next_selected_chopper_index,
        selected_chopper_asset=next_selected_chopper_asset,
    )
