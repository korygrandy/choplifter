from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .gamepad_pause_flow import handle_gamepad_pause_flow
from .gamepad_state_sync import sync_gamepad_state
from .loop_state_updates import apply_nonpaused_gamepad_result
from .nonpaused_gamepad_mode_flow import handle_nonpaused_gamepad_mode_flow
from .paused_gamepad_mode_flow import handle_paused_gamepad_mode_flow


@dataclass
class ActiveGamepadFrameResult:
    running: bool
    mode: str
    selected_chopper_index: int
    selected_mission_index: int
    selected_mission_id: str
    selected_chopper_asset: str
    debug: object
    gp_tilt_left: bool
    gp_tilt_right: bool
    gp_lift_up: bool
    gp_lift_down: bool


def process_active_gamepad_frame(
    *,
    active_gamepad: object,
    running: bool,
    mode: str,
    runtime: object,
    selected_chopper_index: int,
    selected_mission_index: int,
    selected_mission_id: str,
    selected_chopper_asset: str,
    debug: object,
    debug_settings: object,
    mission: object,
    helicopter: object,
    audio: object,
    logger: object,
    set_toast: Callable[[str], None],
    play_satellite_reallocating: Callable[[], None],
    reset_game: Callable[[], None],
    start_mission_intro_or_playing_fn: Callable[[str], str],
    skip_intro: Callable[[], None],
    skip_mission_cutscene: Callable[[], None],
    apply_mission_preview: Callable[[], None],
    toggle_particles: Callable[[], None],
    toggle_flashes: Callable[[], None],
    toggle_screenshake: Callable[[], None],
    apply_paused_menu_decision: Callable[..., object],
    apply_paused_gameplay_shortcuts: Callable[..., object],
    spawn_projectile_from_helicopter_logged: Callable[..., None],
    try_start_flare_salvo: Callable[..., None],
    toggle_doors_with_logging: Callable[..., None],
    boarded_count: Callable[..., int],
    chopper_weapons_locked: Callable[..., bool],
    facing_enum: object,
    chopper_choices: list,
    mission_choices: list,
    flares: object,
    airport_runtime: object,
    gamepad_buttons: object,
) -> ActiveGamepadFrameResult:
    """Process one frame of active gamepad input and return updated loop state."""
    next_running = bool(running)
    next_mode = mode
    next_selected_chopper_index = selected_chopper_index
    next_selected_mission_index = selected_mission_index
    next_selected_mission_id = selected_mission_id
    next_selected_chopper_asset = selected_chopper_asset
    next_debug = debug

    gp = active_gamepad.readout
    gp_tilt_left = bool(gp.tilt_left)
    gp_tilt_right = bool(gp.tilt_right)
    gp_lift_up = bool(gp.lift_up)
    gp_lift_down = bool(gp.lift_down)
    menu_dir = int(gp.menu_dir)
    menu_vert = int(gp.menu_vert)

    a_down = bool(gp.a_down)
    b_down = bool(gp.b_down)
    x_down = bool(gp.x_down)
    y_down = bool(gp.y_down)
    start_down = bool(gp.start_down)
    rb_down = bool(gp.rb_down)
    lb_down = bool(gp.lb_down)
    back_down = bool(gp.back_down)

    prev_btn_a_down = bool(active_gamepad.prev_a_down)
    prev_btn_b_down = bool(active_gamepad.prev_b_down)
    prev_btn_x_down = bool(active_gamepad.prev_x_down)
    prev_btn_y_down = bool(active_gamepad.prev_y_down)
    prev_btn_start_down = bool(active_gamepad.prev_start_down)
    prev_btn_rb_down = bool(active_gamepad.prev_rb_down)
    prev_btn_lb_down = bool(active_gamepad.prev_lb_down)
    prev_btn_back_down = bool(active_gamepad.prev_back_down)

    if lb_down and not prev_btn_lb_down:
        next_debug = debug_settings(show_overlay=not bool(getattr(next_debug, "show_overlay", False)))
        set_toast(f"Debug overlay: {'ON' if next_debug.show_overlay else 'OFF'}")

    pause_flow = handle_gamepad_pause_flow(
        mode=next_mode,
        pause_focus=runtime.pause_focus,
        just_paused_with_start=runtime.just_paused_with_start,
        quit_confirm=runtime.quit_confirm,
        start_down=start_down,
        prev_btn_start_down=prev_btn_start_down,
        b_down=b_down,
        prev_btn_b_down=prev_btn_b_down,
        a_down=a_down,
        prev_btn_a_down=prev_btn_a_down,
        audio=audio,
        logger=logger,
    )
    next_mode = pause_flow.mode
    runtime.pause_focus = pause_flow.pause_focus
    runtime.just_paused_with_start = pause_flow.just_paused_with_start
    runtime.quit_confirm = pause_flow.quit_confirm
    next_running = bool(next_running and pause_flow.running)

    if next_mode != "paused":
        nonpaused_result = handle_nonpaused_gamepad_mode_flow(
            mode=next_mode,
            menu_dir=menu_dir,
            prev_menu_dir=runtime.prev_menu_dir,
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
            selected_mission_index=next_selected_mission_index,
            selected_mission_id=next_selected_mission_id,
            selected_chopper_asset=next_selected_chopper_asset,
            chopper_choices=chopper_choices,
            mission_choices=mission_choices,
            audio=audio,
            set_toast=set_toast,
            play_satellite_reallocating=play_satellite_reallocating,
            reset_game=reset_game,
            start_mission_intro_or_playing_fn=start_mission_intro_or_playing_fn,
            skip_intro=skip_intro,
            skip_mission_cutscene=skip_mission_cutscene,
            apply_mission_preview=apply_mission_preview,
        )
        (
            next_mode,
            next_selected_chopper_index,
            next_selected_mission_index,
            next_selected_mission_id,
            next_selected_chopper_asset,
        ) = apply_nonpaused_gamepad_result(
            mode=next_mode,
            selected_chopper_index=next_selected_chopper_index,
            selected_mission_index=next_selected_mission_index,
            selected_mission_id=next_selected_mission_id,
            selected_chopper_asset=next_selected_chopper_asset,
            nonpaused_result=nonpaused_result,
        )
    elif next_mode == "paused":
        (
            runtime.pause_focus,
            next_mode,
            next_running,
            next_selected_chopper_index,
            next_selected_chopper_asset,
            runtime.muted,
            runtime.quit_confirm,
        ) = handle_paused_gamepad_mode_flow(
            pause_focus=runtime.pause_focus,
            quit_confirm=runtime.quit_confirm,
            selected_chopper_index=next_selected_chopper_index,
            chopper_count=len(chopper_choices),
            menu_vert=menu_vert,
            prev_menu_vert=runtime.prev_menu_vert,
            menu_dir=menu_dir,
            prev_menu_dir=runtime.prev_menu_dir,
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
            crash_active=bool(getattr(mission, "crash_active", False)),
            mode=next_mode,
            running=next_running,
            selected_chopper_asset=next_selected_chopper_asset,
            muted=runtime.muted,
            selected_mission_id=next_selected_mission_id,
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
            apply_paused_menu_decision=apply_paused_menu_decision,
            apply_paused_gameplay_shortcuts=apply_paused_gameplay_shortcuts,
            flares=flares,
            meal_truck_driver_mode=runtime.meal_truck_driver_mode,
            bus_driver_mode=runtime.bus_driver_mode,
            mission=mission,
            spawn_projectile_from_helicopter_logged=spawn_projectile_from_helicopter_logged,
            try_start_flare_salvo=try_start_flare_salvo,
            toggle_doors_with_logging=toggle_doors_with_logging,
            boarded_count=boarded_count,
            chopper_weapons_locked=chopper_weapons_locked,
            Facing=facing_enum,
        )

    sync_gamepad_state(
        gamepad_buttons=gamepad_buttons,
        runtime=runtime,
        a_down=a_down,
        b_down=b_down,
        x_down=x_down,
        y_down=y_down,
        start_down=start_down,
        rb_down=rb_down,
        lb_down=lb_down,
        back_down=back_down,
        menu_dir=menu_dir,
        menu_vert=menu_vert,
    )

    return ActiveGamepadFrameResult(
        running=next_running,
        mode=next_mode,
        selected_chopper_index=next_selected_chopper_index,
        selected_mission_index=next_selected_mission_index,
        selected_mission_id=next_selected_mission_id,
        selected_chopper_asset=next_selected_chopper_asset,
        debug=next_debug,
        gp_tilt_left=gp_tilt_left,
        gp_tilt_right=gp_tilt_right,
        gp_lift_up=gp_lift_up,
        gp_lift_down=gp_lift_down,
    )
