from __future__ import annotations

import pygame
from dataclasses import dataclass
from typing import Any, Callable, Sequence

from ..controls import matches_key
from .gamepad_pause_flow import handle_gamepad_pause_flow
from .gamepads import handle_joy_device_added, handle_joy_device_removed
from .joybutton_events import handle_joybuttondown_event
from .keydown_preflight import KeydownPreflightResult, handle_keydown_preflight
from .keyboard_events import handle_keyboard_event
from .mission_pause_transitions import PauseTransitionResult, apply_pause_transition, handle_mission_end_gamepad_navigation, handle_mission_end_keyboard_navigation
from .nonpaused_gamepad_mode_flow import handle_nonpaused_gamepad_mode_flow
from .pause_controls import handle_gamepad_pause_button, handle_pause_quit_confirm_gamepad
from .pause_menu_effects import apply_paused_gameplay_shortcuts, apply_paused_menu_decision
from .pause_menu_inputs import resolve_paused_mode_inputs
from .paused_gamepad_mode_flow import handle_paused_gamepad_mode_flow
from .playing_keyboard_inputs import handle_playing_keyboard_special_cases
from .loop_state_updates import apply_keydown_result, apply_joybutton_result


def handle_global_debug_keydown(
    *,
    key: int,
    mission: object,
    set_toast: callable,
    toggle_thermal_mode: callable,
    enemy_kind_barak_mrad: object,
    barak_state_deploy: str,
) -> bool:
    """Handle global debug and utility key presses before mode-specific routing."""
    if key == pygame.K_t:
        toggle_thermal_mode()
        set_toast("Thermal mode toggled (T)")
        return True

    if key == pygame.K_F9:
        for enemy in getattr(mission, "enemies", []):
            if getattr(enemy, "kind", None) == enemy_kind_barak_mrad and getattr(enemy, "alive", False):
                enemy.vel.x = 0.0
                enemy.mrad_state = barak_state_deploy
                enemy.mrad_state_seconds = 0.0
                enemy.mrad_reload_seconds = 0.0
                enemy.launcher_angle = 0.0
                enemy.launcher_ext_progress = 0.0
                enemy.missile_fired = False
                mission_audio = getattr(mission, "audio", None)
                if mission_audio is not None and hasattr(mission_audio, "play_barak_mrad_deploy"):
                    mission_audio.play_barak_mrad_deploy()
                set_toast("DEBUG: BARAK missile launch sequence triggered (F9)")
                return True

    return False


@dataclass
class KeydownEventResult:
    running: bool
    mode: str
    pause_focus: str
    muted: bool
    selected_mission_index: int
    selected_mission_id: str
    selected_chopper_index: int
    selected_chopper_asset: str
    debug: object
    quit_confirm: bool
    meal_truck_driver_mode: bool
    meal_truck_lift_command_extended: bool
    bus_driver_mode: bool


def handle_keydown_event(
    event: pygame.event.Event,
    *,
    runtime: object,
    mode: str,
    mission: object,
    controls: Any,
    pause_focus: str,
    quit_confirm: bool,
    debug_mode: bool,
    debug_weather_index: int,
    debug_weather_modes: Sequence[str],
    selected_mission_id: str,
    meal_truck_driver_mode: bool,
    meal_truck_lift_command_extended: bool,
    bus_driver_mode: bool,
    airport_meal_truck_state: object,
    airport_bus_state: object,
    airport_tech_state: object,
    helicopter: object,
    heli_ground_y: float,
    audio: object,
    logger: object,
    set_toast: Callable[[str], None],
    set_console_log_debug: Callable[[bool], None],
    set_debug_weather_mode: Callable[[str], None],
    chopper_choices: list,
    mission_choices: list,
    muted: bool,
    reset_game: Callable[[], None],
    apply_mission_preview: Callable[[], None],
    skip_intro: Callable[[], None],
    skip_mission_cutscene: Callable[[], None],
    toggle_particles_wrapper: Callable[[], None],
    toggle_flashes_wrapper: Callable[[], None],
    toggle_screenshake_wrapper: Callable[[], None],
    spawn_projectile_from_helicopter_logged: Callable[..., None],
    try_start_flare_salvo: Callable[..., None],
    toggle_doors_with_logging: Callable[..., None],
    Facing: object,
    DebugSettings: Any,
    boarded_count: Callable[..., int],
    flares: object,
    selected_mission_index: int,
    selected_chopper_index: int,
    selected_chopper_asset: str,
    debug: object,
    helicopter_weapon_locked: bool,
) -> KeydownEventResult:
    """Handle one KEYDOWN event end-to-end and return the updated runtime state."""
    next_mode = mode
    next_pause_focus = pause_focus
    next_muted = muted
    next_selected_mission_index = selected_mission_index
    next_selected_mission_id = selected_mission_id
    next_selected_chopper_index = selected_chopper_index
    next_selected_chopper_asset = selected_chopper_asset
    next_debug = debug
    next_quit_confirm = quit_confirm
    next_meal_truck_driver_mode = meal_truck_driver_mode
    next_meal_truck_lift_command_extended = meal_truck_lift_command_extended
    next_bus_driver_mode = bus_driver_mode
    running = True

    keydown_preflight = handle_keydown_preflight(
        key=event.key,
        mode=mode,
        mission_ended=bool(getattr(mission, "ended", False)),
        pause_focus=pause_focus,
        quit_confirm=quit_confirm,
        debug_mode=debug_mode,
        debug_weather_index=debug_weather_index,
        debug_weather_modes=debug_weather_modes,
        set_toast=set_toast,
        audio=audio,
        logger=logger,
        handle_mission_end_keyboard_navigation_fn=handle_mission_end_keyboard_navigation,
        apply_pause_transition_fn=apply_pause_transition,
    )
    next_mode = keydown_preflight.mode
    next_pause_focus = keydown_preflight.pause_focus
    next_quit_confirm = keydown_preflight.quit_confirm
    next_debug_mode = keydown_preflight.debug_mode
    next_debug_weather_index = keydown_preflight.debug_weather_index
    if keydown_preflight.handled:
        running = keydown_preflight.running
        runtime.debug_mode = bool(next_debug_mode)
        runtime.debug_weather_index = int(next_debug_weather_index)
        set_console_log_debug(next_debug_mode)
        if keydown_preflight.selected_weather_mode is not None:
            set_debug_weather_mode(keydown_preflight.selected_weather_mode)
        if keydown_preflight.debug_toast:
            set_toast(keydown_preflight.debug_toast)
        return KeydownEventResult(
            running=running,
            mode=next_mode,
            pause_focus=next_pause_focus,
            muted=next_muted,
            selected_mission_index=next_selected_mission_index,
            selected_mission_id=next_selected_mission_id,
            selected_chopper_index=next_selected_chopper_index,
            selected_chopper_asset=next_selected_chopper_asset,
            debug=next_debug,
            quit_confirm=next_quit_confirm,
            meal_truck_driver_mode=next_meal_truck_driver_mode,
            meal_truck_lift_command_extended=next_meal_truck_lift_command_extended,
            bus_driver_mode=next_bus_driver_mode,
        )

    doors_key_pressed = next_mode == "playing" and matches_key(event.key, controls.doors) and not getattr(mission, "crash_active", False)
    fire_key_pressed = next_mode == "playing" and matches_key(event.key, controls.fire) and not getattr(mission, "crash_active", False)
    playing_keyboard = handle_playing_keyboard_special_cases(
        selected_mission_id=selected_mission_id,
        doors_key_pressed=doors_key_pressed,
        fire_key_pressed=fire_key_pressed,
        meal_truck_driver_mode=meal_truck_driver_mode,
        meal_truck_lift_command_extended=meal_truck_lift_command_extended,
        bus_driver_mode=bus_driver_mode,
        airport_meal_truck_state=airport_meal_truck_state,
        airport_bus_state=airport_bus_state,
        airport_tech_state=airport_tech_state,
        helicopter=helicopter,
        heli_ground_y=heli_ground_y,
    )
    next_meal_truck_driver_mode = playing_keyboard.meal_truck_driver_mode
    next_meal_truck_lift_command_extended = playing_keyboard.meal_truck_lift_command_extended
    next_bus_driver_mode = playing_keyboard.bus_driver_mode
    if not playing_keyboard.handled:
        (
            next_mode,
            next_pause_focus,
            next_muted,
            next_selected_mission_index,
            next_selected_mission_id,
            next_selected_chopper_index,
            next_selected_chopper_asset,
            next_debug,
            next_quit_confirm,
        ) = handle_keyboard_event(
            event,
            mode=next_mode,
            controls=controls,
            mission=mission,
            helicopter=helicopter,
            audio=audio,
            logger=logger,
            chopper_choices=chopper_choices,
            mission_choices=mission_choices,
            pause_focus=next_pause_focus,
            muted=next_muted,
            set_toast=set_toast,
            reset_game=reset_game,
            apply_mission_preview=apply_mission_preview,
            skip_intro=skip_intro,
            skip_mission_cutscene=skip_mission_cutscene,
            toggle_particles_wrapper=toggle_particles_wrapper,
            toggle_flashes_wrapper=toggle_flashes_wrapper,
            toggle_screenshake_wrapper=toggle_screenshake_wrapper,
            spawn_projectile_from_helicopter_logged=spawn_projectile_from_helicopter_logged,
            try_start_flare_salvo=try_start_flare_salvo,
            toggle_doors_with_logging=toggle_doors_with_logging,
            Facing=Facing,
            DebugSettings=DebugSettings,
            boarded_count=boarded_count,
            flares=flares,
            selected_mission_index=next_selected_mission_index,
            selected_mission_id=next_selected_mission_id,
            selected_chopper_index=next_selected_chopper_index,
            selected_chopper_asset=next_selected_chopper_asset,
            debug=next_debug,
            quit_confirm=next_quit_confirm,
            helicopter_weapon_locked=helicopter_weapon_locked,
        )

    return KeydownEventResult(
        running=running,
        mode=next_mode,
        pause_focus=next_pause_focus,
        muted=next_muted,
        selected_mission_index=next_selected_mission_index,
        selected_mission_id=next_selected_mission_id,
        selected_chopper_index=next_selected_chopper_index,
        selected_chopper_asset=next_selected_chopper_asset,
        debug=next_debug,
        quit_confirm=next_quit_confirm,
        meal_truck_driver_mode=next_meal_truck_driver_mode,
        meal_truck_lift_command_extended=next_meal_truck_lift_command_extended,
        bus_driver_mode=next_bus_driver_mode,
    )


@dataclass
class PygameEventDispatchResult:
    running: bool
    mode: str
    selected_mission_index: int
    selected_mission_id: str
    selected_chopper_index: int
    selected_chopper_asset: str
    debug: object


def process_pygame_events(
    *,
    running: bool,
    mode: str,
    runtime: object,
    mission: object,
    controls: object,
    debug_weather_modes: Sequence[str],
    selected_mission_index: int,
    selected_mission_id: str,
    selected_chopper_index: int,
    selected_chopper_asset: str,
    debug: object,
    airport_runtime: object,
    helicopter: object,
    heli_ground_y: float,
    chopper_choices: list,
    mission_choices: list,
    audio: object,
    logger: object,
    set_toast: Callable[[str], None],
    set_console_log_debug: Callable[[bool], None],
    set_debug_weather_mode: Callable[[str], None],
    reset_game: Callable[[], None],
    apply_mission_preview: Callable[[], None],
    skip_intro: Callable[[], None],
    skip_mission_cutscene: Callable[[], None],
    toggle_particles_wrapper: Callable[[], None],
    toggle_flashes_wrapper: Callable[[], None],
    toggle_screenshake_wrapper: Callable[[], None],
    spawn_projectile_from_helicopter_logged: Callable[..., None],
    try_start_flare_salvo: Callable[..., None],
    toggle_doors_with_logging: Callable[..., None],
    facing_enum: object,
    debug_settings: object,
    boarded_count: Callable[..., int],
    flares: object,
    chopper_weapons_locked_fn: Callable[..., bool],
    toggle_thermal_mode: Callable[[], None],
    enemy_kind_barak_mrad: object,
    barak_state_deploy: str,
    joysticks: dict[int, pygame.joystick.Joystick],
    gamepad_buttons: object,
) -> PygameEventDispatchResult:
    """Process pygame events for one frame and return updated loop state."""
    next_running = bool(running)
    next_mode = mode
    next_selected_mission_index = selected_mission_index
    next_selected_mission_id = selected_mission_id
    next_selected_chopper_index = selected_chopper_index
    next_selected_chopper_asset = selected_chopper_asset
    next_debug = debug

    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN and handle_global_debug_keydown(
            key=event.key,
            mission=mission,
            set_toast=set_toast,
            toggle_thermal_mode=toggle_thermal_mode,
            enemy_kind_barak_mrad=enemy_kind_barak_mrad,
            barak_state_deploy=barak_state_deploy,
        ):
            continue
        if event.type == pygame.QUIT:
            next_running = False
            continue
        if event.type == pygame.JOYDEVICEADDED:
            handle_joy_device_added(event.device_index, joysticks=joysticks, logger=logger, set_toast=set_toast)
            continue
        if event.type == pygame.JOYDEVICEREMOVED:
            handle_joy_device_removed(event.instance_id, joysticks=joysticks, logger=logger, set_toast=set_toast)
            gamepad_buttons.clear_on_disconnect()
            continue
        if event.type == pygame.KEYDOWN:
            keydown_result = handle_keydown_event(
                event,
                runtime=runtime,
                mode=next_mode,
                mission=mission,
                controls=controls,
                pause_focus=runtime.pause_focus,
                quit_confirm=runtime.quit_confirm,
                debug_mode=runtime.debug_mode,
                debug_weather_index=runtime.debug_weather_index,
                debug_weather_modes=debug_weather_modes,
                selected_mission_id=next_selected_mission_id,
                meal_truck_driver_mode=runtime.meal_truck_driver_mode,
                meal_truck_lift_command_extended=runtime.meal_truck_lift_command_extended,
                bus_driver_mode=runtime.bus_driver_mode,
                airport_meal_truck_state=airport_runtime.meal_truck_state,
                airport_bus_state=airport_runtime.bus_state,
                airport_tech_state=airport_runtime.tech_state,
                helicopter=helicopter,
                heli_ground_y=heli_ground_y,
                audio=audio,
                logger=logger,
                set_toast=set_toast,
                set_console_log_debug=set_console_log_debug,
                set_debug_weather_mode=set_debug_weather_mode,
                chopper_choices=chopper_choices,
                mission_choices=mission_choices,
                muted=runtime.muted,
                reset_game=reset_game,
                apply_mission_preview=apply_mission_preview,
                skip_intro=skip_intro,
                skip_mission_cutscene=skip_mission_cutscene,
                toggle_particles_wrapper=toggle_particles_wrapper,
                toggle_flashes_wrapper=toggle_flashes_wrapper,
                toggle_screenshake_wrapper=toggle_screenshake_wrapper,
                spawn_projectile_from_helicopter_logged=spawn_projectile_from_helicopter_logged,
                try_start_flare_salvo=try_start_flare_salvo,
                toggle_doors_with_logging=toggle_doors_with_logging,
                Facing=facing_enum,
                DebugSettings=debug_settings,
                boarded_count=boarded_count,
                flares=flares,
                selected_mission_index=next_selected_mission_index,
                selected_chopper_index=next_selected_chopper_index,
                selected_chopper_asset=next_selected_chopper_asset,
                debug=next_debug,
                helicopter_weapon_locked=chopper_weapons_locked_fn(
                    meal_truck_driver_mode=bool(runtime.meal_truck_driver_mode),
                    bus_driver_mode=bool(runtime.bus_driver_mode),
                    engineer_remote_control_active=bool(getattr(mission, "engineer_remote_control_active", False)),
                ),
            )
            (
                next_running,
                next_mode,
                next_selected_mission_index,
                next_selected_mission_id,
                next_selected_chopper_index,
                next_selected_chopper_asset,
                next_debug,
            ) = apply_keydown_result(
                running=next_running,
                mode=next_mode,
                runtime=runtime,
                selected_mission_index=next_selected_mission_index,
                selected_mission_id=next_selected_mission_id,
                selected_chopper_index=next_selected_chopper_index,
                selected_chopper_asset=next_selected_chopper_asset,
                debug=next_debug,
                keydown_result=keydown_result,
            )
            if not next_running:
                continue
            continue
        if event.type == pygame.JOYBUTTONDOWN:
            if logger:
                logger.debug("GAMEPAD BUTTONDOWN: button=%s", event.button)
            joybutton_result = handle_joybuttondown_event(
                button=event.button,
                mode=next_mode,
                pause_focus=runtime.pause_focus,
                set_toast=set_toast,
                audio=audio,
                selected_mission_id=next_selected_mission_id,
                mission=mission,
                helicopter=helicopter,
                logger=logger,
                flares=flares,
                meal_truck_driver_mode=runtime.meal_truck_driver_mode,
                meal_truck_lift_command_extended=runtime.meal_truck_lift_command_extended,
                bus_driver_mode=runtime.bus_driver_mode,
                airport_meal_truck_state=airport_runtime.meal_truck_state,
                airport_bus_state=airport_runtime.bus_state,
                airport_tech_state=airport_runtime.tech_state,
                heli_ground_y=heli_ground_y,
                spawn_projectile_from_helicopter_logged=spawn_projectile_from_helicopter_logged,
                try_start_flare_salvo=try_start_flare_salvo,
                toggle_doors_with_logging=toggle_doors_with_logging,
                boarded_count=boarded_count,
                chopper_weapons_locked=chopper_weapons_locked_fn,
                Facing=facing_enum,
            )
            next_mode = apply_joybutton_result(
                mode=next_mode,
                runtime=runtime,
                joybutton_result=joybutton_result,
            )

    return PygameEventDispatchResult(
        running=next_running,
        mode=next_mode,
        selected_mission_index=next_selected_mission_index,
        selected_mission_id=next_selected_mission_id,
        selected_chopper_index=next_selected_chopper_index,
        selected_chopper_asset=next_selected_chopper_asset,
        debug=next_debug,
    )


