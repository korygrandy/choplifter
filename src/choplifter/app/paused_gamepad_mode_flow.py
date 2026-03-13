from __future__ import annotations

from .pause_menu_effects import apply_paused_gameplay_shortcuts as _apply_paused_gameplay_shortcuts
from .pause_menu_effects import apply_paused_menu_decision as _apply_paused_menu_decision
from .pause_menu_inputs import resolve_paused_mode_inputs


def handle_paused_gamepad_mode_flow(
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
    mode: str,
    running: bool,
    selected_chopper_asset: str,
    muted: bool,
    selected_mission_id: str,
    chopper_choices: list,
    helicopter: object,
    audio: object,
    logger: object,
    play_satellite_reallocating: callable,
    reset_game: callable,
    set_toast: callable,
    toggle_particles: callable,
    toggle_flashes: callable,
    toggle_screenshake: callable,
    apply_paused_menu_decision: callable | None = None,
    apply_paused_gameplay_shortcuts: callable | None = None,
    flares: object,
    meal_truck_driver_mode: bool,
    bus_driver_mode: bool,
    mission: object,
    spawn_projectile_from_helicopter_logged: callable,
    try_start_flare_salvo: callable,
    toggle_doors_with_logging: callable,
    boarded_count: callable,
    chopper_weapons_locked: callable,
    Facing: object,
) -> tuple:
    """Handle gamepad mode routing and side effects when paused."""
    apply_menu_decision_fn = apply_paused_menu_decision or _apply_paused_menu_decision
    apply_gameplay_shortcuts_fn = apply_paused_gameplay_shortcuts or _apply_paused_gameplay_shortcuts

    paused = resolve_paused_mode_inputs(
        pause_focus=pause_focus,
        quit_confirm=quit_confirm,
        selected_chopper_index=selected_chopper_index,
        chopper_count=chopper_count,
        menu_vert=menu_vert,
        prev_menu_vert=prev_menu_vert,
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
        rb_down=rb_down,
        prev_btn_rb_down=prev_btn_rb_down,
        back_down=back_down,
        prev_btn_back_down=prev_btn_back_down,
        crash_active=crash_active,
    )
    new_pause_focus = paused.pause_focus
    paused_applied = apply_menu_decision_fn(
        paused=paused,
        mode=mode,
        running=running,
        selected_chopper_index=selected_chopper_index,
        selected_chopper_asset=selected_chopper_asset,
        muted=muted,
        selected_mission_id=selected_mission_id,
        chopper_choices=chopper_choices,
        helicopter=helicopter,
        audio=audio,
        logger=logger,
        play_satellite_reallocating=play_satellite_reallocating,
        reset_game=reset_game,
        set_toast=set_toast,
        toggle_particles=toggle_particles,
        toggle_flashes=toggle_flashes,
        toggle_screenshake=toggle_screenshake,
    )
    new_mode = paused_applied.mode
    new_running = paused_applied.running
    new_selected_chopper_index = paused_applied.selected_chopper_index
    new_selected_chopper_asset = paused_applied.selected_chopper_asset
    new_muted = paused_applied.muted
    new_quit_confirm = paused_applied.quit_confirm

    apply_gameplay_shortcuts_fn(
        paused=paused,
        meal_truck_driver_mode=meal_truck_driver_mode,
        bus_driver_mode=bus_driver_mode,
        mission=mission,
        helicopter=helicopter,
        audio=audio,
        logger=logger,
        flares=flares,
        try_start_flare_salvo=try_start_flare_salvo,
        toggle_doors_with_logging=toggle_doors_with_logging,
        boarded_count=boarded_count,
        set_toast=set_toast,
        spawn_projectile_from_helicopter_logged=spawn_projectile_from_helicopter_logged,
        chopper_weapons_locked=chopper_weapons_locked,
        Facing=Facing,
    )
    return (
        new_pause_focus,
        new_mode,
        new_running,
        new_selected_chopper_index,
        new_selected_chopper_asset,
        new_muted,
        new_quit_confirm,
    )
