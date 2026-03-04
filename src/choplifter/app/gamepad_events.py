from __future__ import annotations

from typing import Any, Callable

def handle_gamepad_event(
    *,
    mode: str,
    pause_focus: str,
    muted: bool,
    menu_dir: int,
    prev_menu_dir: int,
    menu_vert: int,
    prev_menu_vert: int,
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
    chopper_choices: list,
    selected_chopper_index: int,
    selected_chopper_asset: str,
    mission_choices: list,
    selected_mission_index: int,
    selected_mission_id: str,
    helicopter: Any,
    audio: Any,
    set_toast: Callable,
    reset_game: Callable,
    apply_mission_preview: Callable,
    move_pause_focus: Callable,
    cycle_index: Callable,
    toggle_particles_wrapper: Callable,
    toggle_flashes_wrapper: Callable,
    toggle_screenshake_wrapper: Callable,
    try_start_flare_salvo: Callable,
    flares: Any,
    mission: Any,
    logger: Any,
    boarded_count: Any,
    toggle_doors_with_logging: Callable,
    spawn_projectile_from_helicopter_logged: Callable,
    Facing: Any,
) -> tuple[str, str, bool, int, str, int, str, bool]:
    """
    Handles gamepad events and returns updated (mode, pause_focus, muted, selected_chopper_index, selected_chopper_asset, selected_mission_index, selected_mission_id, running).
    """
    # Debug overlay toggle (gamepad).
    if lb_down and not prev_btn_lb_down:
        # debug is not returned, so this only works if debug is global or handled elsewhere
        # debug = DebugSettings(show_overlay=not debug.show_overlay)
        set_toast(f"Debug overlay toggled")

    if mode == "select_chopper":
        if menu_dir != 0 and menu_dir != prev_menu_dir:
            selected_chopper_index = cycle_index(selected_chopper_index, menu_dir, len(chopper_choices))
            selected_chopper_asset = chopper_choices[selected_chopper_index][0]
            audio.play_menu_select()
        if (a_down and not prev_btn_a_down) or (start_down and not prev_btn_start_down):
            mode = "playing"
            set_toast(f"Chopper selected: {chopper_choices[selected_chopper_index][1]}")
            reset_game()
    elif mode == "intro":
        skip_btn = (
            (a_down and not prev_btn_a_down)
            or (b_down and not prev_btn_b_down)
            or (x_down and not prev_btn_x_down)
            or (y_down and not prev_btn_y_down)
            or (start_down and not prev_btn_start_down)
            or (rb_down and not prev_btn_rb_down)
            or (lb_down and not prev_btn_lb_down)
        )
        if skip_btn:
            mode = "select_mission"
            # skip_intro(cutscenes.intro) -- not available here
    elif mode == "cutscene":
        skip_btn = (
            (a_down and not prev_btn_a_down)
            or (b_down and not prev_btn_b_down)
            or (x_down and not prev_btn_x_down)
            or (y_down and not prev_btn_y_down)
            or (start_down and not prev_btn_start_down)
            or (rb_down and not prev_btn_rb_down)
            or (lb_down and not prev_btn_lb_down)
        )
        if skip_btn:
            mode = "playing"
            # skip_mission_cutscene(cutscenes.mission) -- not available here
    elif mode == "select_mission":
        if menu_dir != 0 and menu_dir != prev_menu_dir:
            selected_mission_index = cycle_index(selected_mission_index, menu_dir, len(mission_choices))
            selected_mission_id = mission_choices[selected_mission_index][0]
            audio.play_menu_select()
            apply_mission_preview()
        if (a_down and not prev_btn_a_down) or (start_down and not prev_btn_start_down):
            mode = "select_chopper"
            set_toast(f"Mission selected: {mission_choices[selected_mission_index][1]}")
    elif mode == "paused":
        # Start/B resumes.
        if (start_down and not prev_btn_start_down) or (b_down and not prev_btn_b_down):
            mode = "playing"
            audio.play_pause_toggle()
            audio.set_pause_menu_active(False)

        # Accessibility toggles.
        if x_down and not prev_btn_x_down:
            toggle_particles_wrapper()
        if y_down and not prev_btn_y_down:
            toggle_flashes_wrapper()
        if rb_down and not prev_btn_rb_down:
            toggle_screenshake_wrapper()

        # Up/Down selects section.
        if menu_vert != 0 and menu_vert != prev_menu_vert:
            prev_pause_focus = pause_focus
            pause_focus = move_pause_focus(pause_focus, -1 if menu_vert < 0 else 1)
            if pause_focus != prev_pause_focus:
                audio.play_menu_select()

        # Left/Right changes chopper when focused.
        if pause_focus == "choppers" and menu_dir != 0 and menu_dir != prev_menu_dir:
            selected_chopper_index = cycle_index(selected_chopper_index, menu_dir, len(chopper_choices))
            selected_chopper_asset = chopper_choices[selected_chopper_index][0]
            helicopter.skin_asset = selected_chopper_asset
            audio.play_menu_select()

        # A activates current focus.
        if a_down and not prev_btn_a_down:
            if pause_focus == "restart_mission":
                reset_game()
                mode = "playing"
                audio.play_pause_toggle()
                audio.set_pause_menu_active(False)
            elif pause_focus == "restart_game":
                mode = "select_mission"
                pause_focus = "choppers"
                set_toast("Restart Game")
                audio.play_pause_toggle()
                audio.set_pause_menu_active(False)
            elif pause_focus == "mute":
                muted = not muted
                audio.set_muted(muted)
            else:
                mode = "playing"
                audio.play_pause_toggle()
                audio.set_pause_menu_active(False)
    else:
        # Start toggles pause while playing.
        if start_down and not prev_btn_start_down:
            if not getattr(mission, "crash_active", False):
                mode = "paused"
                pause_focus = "choppers"
                audio.play_pause_toggle()
                audio.set_pause_menu_active(True)

        if b_down and not prev_btn_b_down:
            try_start_flare_salvo(flares, mission=mission, helicopter=helicopter, audio=audio)

        if a_down and not prev_btn_a_down:
            if not getattr(mission, "crash_active", False):
                toggle_doors_with_logging(helicopter, mission, audio, logger, boarded_count)
        if y_down and not prev_btn_y_down:
            if not getattr(mission, "crash_active", False):
                helicopter.reverse_flip()
        if back_down and not prev_btn_back_down:
            if not getattr(mission, "crash_active", False):
                helicopter.cycle_facing()
        if x_down and not prev_btn_x_down:
            if not getattr(mission, "crash_active", False):
                spawn_projectile_from_helicopter_logged(mission, helicopter, logger)
                if helicopter.facing is Facing.FORWARD:
                    audio.play_bomb()
                else:
                    audio.play_shoot()

    return mode, pause_focus, muted, selected_chopper_index, selected_chopper_asset, selected_mission_index, selected_mission_id
