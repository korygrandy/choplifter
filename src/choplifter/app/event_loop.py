

from __future__ import annotations
import pygame
from dataclasses import dataclass
from typing import Any, Callable, Sequence

from ..controls import matches_key
from .keyboard_events import handle_keyboard_event
from .vehicle_driver_modes import handle_airport_driver_mode_doors

def handle_mission_end_keyboard_navigation(*, key: int, mode: str, mission_ended: bool, set_toast: callable) -> tuple[bool, str]:
    """Handle key navigation while the mission-end screen is active."""
    if not (mode == "mission_end" or mission_ended):
        return False, mode

    if key in (pygame.K_ESCAPE, pygame.K_PAUSE):
        set_toast("Mission ended: pause menu opened")
        return True, "paused"

    if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        set_toast("Mission ended: returning to Mission Select")
        return True, "select_mission"

    # Consume all other keys while in mission-end state.
    return True, mode

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
    apply_paused_menu_decision: callable,
    apply_paused_gameplay_shortcuts: callable,
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
    # Navigation and menu decision logic
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
    paused_applied = apply_paused_menu_decision(
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
    # Shortcuts
    apply_paused_gameplay_shortcuts(
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


def handle_mission_end_gamepad_navigation(*, button: int, mode: str, set_toast: Callable[[str], None]) -> tuple[bool, str]:
    """Handle gamepad navigation while the mission-end screen is active."""
    if mode != "mission_end":
        return False, mode

    if button == 7:  # Start button
        set_toast("Mission ended: pause menu opened")
        return True, "paused"

    return True, mode


@dataclass
class PlayingGamepadButtonResult:
    meal_truck_driver_mode: bool
    meal_truck_lift_command_extended: bool
    bus_driver_mode: bool


@dataclass
class PlayingKeyboardResult:
    handled: bool
    meal_truck_driver_mode: bool
    meal_truck_lift_command_extended: bool
    bus_driver_mode: bool


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


@dataclass
class PauseTransitionResult:
    pause_focus: str
    entered_pause: bool
    resumed_playing: bool


@dataclass
class KeydownPreflightResult:
    handled: bool
    running: bool
    mode: str
    pause_focus: str
    quit_confirm: bool
    debug_mode: bool
    debug_weather_index: int
    debug_toast: str | None
    selected_weather_mode: str | None


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


@dataclass
class JoyButtonEventResult:
    mode: str
    pause_focus: str
    meal_truck_driver_mode: bool
    meal_truck_lift_command_extended: bool
    bus_driver_mode: bool


@dataclass
class GamepadPauseFlowResult:
    running: bool
    mode: str
    pause_focus: str
    just_paused_with_start: bool
    quit_confirm: bool


@dataclass
class NonPausedGamepadModeResult:
    mode: str
    selected_mission_index: int
    selected_mission_id: str
    selected_chopper_index: int
    selected_chopper_asset: str


def handle_playing_keyboard_special_cases(
    *,
    selected_mission_id: str,
    doors_key_pressed: bool,
    fire_key_pressed: bool,
    meal_truck_driver_mode: bool,
    meal_truck_lift_command_extended: bool,
    bus_driver_mode: bool,
    airport_meal_truck_state: object,
    airport_bus_state: object,
    airport_tech_state: object,
    helicopter: object,
    heli_ground_y: float,
) -> PlayingKeyboardResult:
    """Handle playing-mode keyboard overrides before general key handling."""
    if doors_key_pressed and selected_mission_id == "airport":
        airport_driver_mode = handle_airport_driver_mode_doors(
            meal_truck_driver_mode=meal_truck_driver_mode,
            meal_truck_lift_command_extended=meal_truck_lift_command_extended,
            bus_driver_mode=bus_driver_mode,
            meal_truck_state=airport_meal_truck_state,
            bus_state=airport_bus_state,
            tech_state=airport_tech_state,
            helicopter=helicopter,
            heli_ground_y=heli_ground_y,
        )
        return PlayingKeyboardResult(
            handled=airport_driver_mode.handled,
            meal_truck_driver_mode=airport_driver_mode.meal_truck_driver_mode,
            meal_truck_lift_command_extended=airport_driver_mode.meal_truck_lift_command_extended,
            bus_driver_mode=airport_driver_mode.bus_driver_mode,
        )

    if fire_key_pressed and selected_mission_id == "airport" and meal_truck_driver_mode:
        return PlayingKeyboardResult(
            handled=True,
            meal_truck_driver_mode=meal_truck_driver_mode,
            meal_truck_lift_command_extended=not meal_truck_lift_command_extended,
            bus_driver_mode=bus_driver_mode,
        )

    return PlayingKeyboardResult(
        handled=False,
        meal_truck_driver_mode=meal_truck_driver_mode,
        meal_truck_lift_command_extended=meal_truck_lift_command_extended,
        bus_driver_mode=bus_driver_mode,
    )


def apply_pause_transition(
    *,
    prev_mode: str,
    next_mode: str,
    pause_focus: str,
    audio: object,
) -> PauseTransitionResult:
    """Apply pause-menu audio/focus side effects for a mode transition."""
    entered_pause = prev_mode != next_mode and next_mode == "paused"
    resumed_playing = prev_mode == "paused" and next_mode == "playing"
    next_pause_focus = pause_focus

    if entered_pause:
        audio.play_pause_toggle()
        audio.set_pause_menu_active(True)
        next_pause_focus = "choppers"
    elif resumed_playing:
        audio.set_pause_menu_active(False)
        audio.play_pause_toggle()

    return PauseTransitionResult(
        pause_focus=next_pause_focus,
        entered_pause=entered_pause,
        resumed_playing=resumed_playing,
    )


def handle_keydown_preflight(
    *,
    key: int,
    mode: str,
    mission_ended: bool,
    pause_focus: str,
    quit_confirm: bool,
    debug_mode: bool,
    debug_weather_index: int,
    debug_weather_modes: Sequence[str],
    set_toast: Callable[[str], None],
    audio: object,
    logger: object,
) -> KeydownPreflightResult:
    """Handle KEYDOWN cases that can short-circuit before the main keyboard handler."""
    handled_mission_end, next_mode = handle_mission_end_keyboard_navigation(
        key=key,
        mode=mode,
        mission_ended=mission_ended,
        set_toast=set_toast,
    )
    if handled_mission_end:
        pause_transition = apply_pause_transition(
            prev_mode=mode,
            next_mode=next_mode,
            pause_focus=pause_focus,
            audio=audio,
        )
        return KeydownPreflightResult(
            handled=True,
            running=True,
            mode=next_mode,
            pause_focus=pause_transition.pause_focus,
            quit_confirm=quit_confirm,
            debug_mode=debug_mode,
            debug_weather_index=debug_weather_index,
            debug_toast=None,
            selected_weather_mode=None,
        )

    handled_quit_confirm, keep_running, next_quit_confirm = handle_pause_quit_confirm_keydown(
        mode=mode,
        quit_confirm=quit_confirm,
        key=key,
    )
    if handled_quit_confirm:
        if logger is not None:
            if not keep_running:
                logger.info("PAUSE MENU: Keyboard confirm quit (Enter/Space) on quit_confirm, exiting game")
            else:
                logger.info("PAUSE MENU: Keyboard cancel quit (Escape) on quit_confirm, returning to pause menu")
        return KeydownPreflightResult(
            handled=True,
            running=keep_running,
            mode=mode,
            pause_focus=pause_focus,
            quit_confirm=next_quit_confirm,
            debug_mode=debug_mode,
            debug_weather_index=debug_weather_index,
            debug_toast=None,
            selected_weather_mode=None,
        )

    handled_debug_key, next_debug_mode, next_debug_weather_index, debug_toast, selected_weather_mode = handle_debug_weather_keydown(
        key=key,
        debug_mode=debug_mode,
        debug_weather_index=debug_weather_index,
        debug_weather_modes=debug_weather_modes,
    )
    if handled_debug_key:
        return KeydownPreflightResult(
            handled=True,
            running=True,
            mode=mode,
            pause_focus=pause_focus,
            quit_confirm=quit_confirm,
            debug_mode=next_debug_mode,
            debug_weather_index=next_debug_weather_index,
            debug_toast=debug_toast,
            selected_weather_mode=selected_weather_mode,
        )

    return KeydownPreflightResult(
        handled=False,
        running=True,
        mode=mode,
        pause_focus=pause_focus,
        quit_confirm=quit_confirm,
        debug_mode=debug_mode,
        debug_weather_index=debug_weather_index,
        debug_toast=None,
        selected_weather_mode=None,
    )


def handle_keydown_event(
    event: pygame.event.Event,
    *,
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
    )
    next_mode = keydown_preflight.mode
    next_pause_focus = keydown_preflight.pause_focus
    next_quit_confirm = keydown_preflight.quit_confirm
    next_debug_mode = keydown_preflight.debug_mode
    next_debug_weather_index = keydown_preflight.debug_weather_index
    if keydown_preflight.handled:
        running = keydown_preflight.running
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


def handle_joybuttondown_event(
    *,
    button: int,
    mode: str,
    pause_focus: str,
    set_toast: Callable[[str], None],
    audio: object,
    selected_mission_id: str,
    mission: object,
    helicopter: object,
    logger: object,
    flares: object,
    meal_truck_driver_mode: bool,
    meal_truck_lift_command_extended: bool,
    bus_driver_mode: bool,
    airport_meal_truck_state: object,
    airport_bus_state: object,
    airport_tech_state: object,
    heli_ground_y: float,
    spawn_projectile_from_helicopter_logged: Callable[..., None],
    try_start_flare_salvo: Callable[..., None],
    toggle_doors_with_logging: Callable[..., None],
    boarded_count: Callable[..., int],
    chopper_weapons_locked: Callable[..., bool],
    Facing: object,
) -> JoyButtonEventResult:
    """Handle one JOYBUTTONDOWN event and return updated runtime state."""
    next_mode = mode
    next_pause_focus = pause_focus
    next_meal_truck_driver_mode = meal_truck_driver_mode
    next_meal_truck_lift_command_extended = meal_truck_lift_command_extended
    next_bus_driver_mode = bus_driver_mode

    handled_mission_end, mission_end_mode = handle_mission_end_gamepad_navigation(
        button=button,
        mode=mode,
        set_toast=set_toast,
    )
    if handled_mission_end:
        pause_transition = apply_pause_transition(
            prev_mode=mode,
            next_mode=mission_end_mode,
            pause_focus=pause_focus,
            audio=audio,
        )
        return JoyButtonEventResult(
            mode=mission_end_mode,
            pause_focus=pause_transition.pause_focus,
            meal_truck_driver_mode=next_meal_truck_driver_mode,
            meal_truck_lift_command_extended=next_meal_truck_lift_command_extended,
            bus_driver_mode=next_bus_driver_mode,
        )

    if mode == "playing":
        playing_gamepad = handle_playing_gamepad_button(
            button=button,
            selected_mission_id=selected_mission_id,
            mission=mission,
            helicopter=helicopter,
            audio=audio,
            logger=logger,
            flares=flares,
            meal_truck_driver_mode=meal_truck_driver_mode,
            meal_truck_lift_command_extended=meal_truck_lift_command_extended,
            bus_driver_mode=bus_driver_mode,
            airport_meal_truck_state=airport_meal_truck_state,
            airport_bus_state=airport_bus_state,
            airport_tech_state=airport_tech_state,
            heli_ground_y=heli_ground_y,
            spawn_projectile_from_helicopter_logged=spawn_projectile_from_helicopter_logged,
            try_start_flare_salvo=try_start_flare_salvo,
            toggle_doors_with_logging=toggle_doors_with_logging,
            boarded_count=boarded_count,
            set_toast=set_toast,
            chopper_weapons_locked=chopper_weapons_locked,
            Facing=Facing,
        )
        next_meal_truck_driver_mode = playing_gamepad.meal_truck_driver_mode
        next_meal_truck_lift_command_extended = playing_gamepad.meal_truck_lift_command_extended
        next_bus_driver_mode = playing_gamepad.bus_driver_mode

    return JoyButtonEventResult(
        mode=next_mode,
        pause_focus=next_pause_focus,
        meal_truck_driver_mode=next_meal_truck_driver_mode,
        meal_truck_lift_command_extended=next_meal_truck_lift_command_extended,
        bus_driver_mode=next_bus_driver_mode,
    )


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
        if next_selected_mission_id == "city":
            play_satellite_reallocating()
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


def handle_playing_gamepad_button(
    *,
    button: int,
    selected_mission_id: str,
    mission: object,
    helicopter: object,
    audio: object,
    logger: object,
    flares: object,
    meal_truck_driver_mode: bool,
    meal_truck_lift_command_extended: bool,
    bus_driver_mode: bool,
    airport_meal_truck_state: object,
    airport_bus_state: object,
    airport_tech_state: object,
    heli_ground_y: float,
    spawn_projectile_from_helicopter_logged: Callable[[object, object, object], None],
    try_start_flare_salvo: Callable[..., None],
    toggle_doors_with_logging: Callable[..., None],
    boarded_count: Callable[[object], int],
    set_toast: Callable[[str], None],
    chopper_weapons_locked: Callable[..., bool],
    Facing: object,
) -> PlayingGamepadButtonResult:
    """Handle a JOYBUTTONDOWN event while in playing mode."""
    crash_active = bool(getattr(mission, "crash_active", False))
    engineer_remote_control_active = bool(getattr(mission, "engineer_remote_control_active", False))
    weapons_locked = chopper_weapons_locked(
        meal_truck_driver_mode=bool(meal_truck_driver_mode),
        bus_driver_mode=bool(bus_driver_mode),
        engineer_remote_control_active=engineer_remote_control_active,
    )

    if button == 2:  # X button: fire (or lift toggle in driver mode)
        if logger:
            logger.debug("Fire button pressed (button=2) in playing mode")
        if meal_truck_driver_mode and selected_mission_id == "airport":
            meal_truck_lift_command_extended = not meal_truck_lift_command_extended
        elif not crash_active and not weapons_locked:
            spawn_projectile_from_helicopter_logged(mission, helicopter, logger)
            if helicopter.facing is Facing.FORWARD:
                audio.play_bomb()
            else:
                audio.play_shoot()

    elif button == 1:  # B button: flare
        if logger:
            logger.debug("Flare button pressed (button=1) in playing mode")
        if not weapons_locked:
            try_start_flare_salvo(flares, mission=mission, helicopter=helicopter, audio=audio)

    elif button == 0:  # A button: doors
        if not crash_active:
            if selected_mission_id == "airport":
                airport_driver_mode = handle_airport_driver_mode_doors(
                    meal_truck_driver_mode=meal_truck_driver_mode,
                    meal_truck_lift_command_extended=meal_truck_lift_command_extended,
                    bus_driver_mode=bus_driver_mode,
                    meal_truck_state=airport_meal_truck_state,
                    bus_state=airport_bus_state,
                    tech_state=airport_tech_state,
                    helicopter=helicopter,
                    heli_ground_y=heli_ground_y,
                )
                meal_truck_driver_mode = airport_driver_mode.meal_truck_driver_mode
                meal_truck_lift_command_extended = airport_driver_mode.meal_truck_lift_command_extended
                bus_driver_mode = airport_driver_mode.bus_driver_mode
                if not airport_driver_mode.handled:
                    toggle_doors_with_logging(helicopter, mission, audio, logger, boarded_count, set_toast)
            else:
                toggle_doors_with_logging(helicopter, mission, audio, logger, boarded_count, set_toast)

    elif button == 3:  # Y button: reverse
        if not crash_active:
            helicopter.reverse_flip()

    elif button == 6:  # Back button: facing
        if not crash_active:
            helicopter.cycle_facing()

    return PlayingGamepadButtonResult(
        meal_truck_driver_mode=meal_truck_driver_mode,
        meal_truck_lift_command_extended=meal_truck_lift_command_extended,
        bus_driver_mode=bus_driver_mode,
    )


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


@dataclass
class PausedMenuApplyResult:
    mode: str
    running: bool
    selected_chopper_index: int
    selected_chopper_asset: str
    muted: bool
    quit_confirm: bool


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


def apply_paused_menu_decision(
    *,
    paused: PausedMenuDecision,
    mode: str,
    running: bool,
    selected_chopper_index: int,
    selected_chopper_asset: str,
    muted: bool,
    selected_mission_id: str,
    chopper_choices: Sequence[tuple[str, str]],
    helicopter: object,
    audio: object,
    logger: object,
    play_satellite_reallocating: Callable[[], None],
    reset_game: Callable[[], None],
    set_toast: Callable[[str], None],
    toggle_particles: Callable[[], None],
    toggle_flashes: Callable[[], None],
    toggle_screenshake: Callable[[], None],
) -> PausedMenuApplyResult:
    next_mode = mode
    next_running = running
    next_selected_chopper_index = selected_chopper_index
    next_selected_chopper_asset = selected_chopper_asset
    next_muted = muted
    next_quit_confirm = paused.quit_confirm

    if paused.selected_chopper_index != selected_chopper_index:
        next_selected_chopper_index = paused.selected_chopper_index
        next_selected_chopper_asset = chopper_choices[next_selected_chopper_index][0]
        helicopter.skin_asset = next_selected_chopper_asset

    if paused.play_menu_select:
        audio.play_menu_select()

    if paused.toggle_particles:
        toggle_particles()
    if paused.toggle_flashes:
        toggle_flashes()
    if paused.toggle_screenshake:
        toggle_screenshake()

    if paused.action != "none":
        if paused.action == "restart_mission":
            logger.info(f"PAUSE MENU: A pressed on restart_mission")
            if selected_mission_id == "city":
                play_satellite_reallocating()
            reset_game()
            next_mode = "playing"
            audio.set_pause_menu_active(False)
            audio.play_pause_toggle()
            next_quit_confirm = False
        elif paused.action == "restart_game":
            logger.info(f"PAUSE MENU: A pressed on restart_game")
            next_mode = "select_mission"
            set_toast("Restart Game")
            audio.set_pause_menu_active(False)
            audio.play_pause_toggle()
            next_quit_confirm = False
        elif paused.action == "toggle_mute":
            logger.info(f"PAUSE MENU: A pressed on mute (muted={not next_muted})")
            next_muted = not next_muted
            audio.set_muted(next_muted)
            next_quit_confirm = False
        elif paused.action == "quit_prompt":
            logger.info(f"PAUSE MENU: A pressed on quit, showing confirmation dialog")
        elif paused.action == "quit_exit":
            logger.info(f"PAUSE MENU: A pressed on quit_confirm, exiting game (gamepad A)")
            next_running = False

    if paused.cancel_quit_confirm:
        logger.info(f"PAUSE MENU: B pressed on quit_confirm, canceling quit and returning to pause menu")
        next_quit_confirm = False

    return PausedMenuApplyResult(
        mode=next_mode,
        running=next_running,
        selected_chopper_index=next_selected_chopper_index,
        selected_chopper_asset=next_selected_chopper_asset,
        muted=next_muted,
        quit_confirm=next_quit_confirm,
    )


def apply_paused_gameplay_shortcuts(
    *,
    paused: PausedMenuDecision,
    meal_truck_driver_mode: bool,
    bus_driver_mode: bool,
    mission: object,
    helicopter: object,
    audio: object,
    logger: object,
    flares: object,
    try_start_flare_salvo: Callable[..., None],
    toggle_doors_with_logging: Callable[..., None],
    boarded_count: Callable[[object], int],
    set_toast: Callable[[str], None],
    spawn_projectile_from_helicopter_logged: Callable[[object, object, object], None],
    chopper_weapons_locked: Callable[..., bool],
    Facing: object,
) -> None:
    engineer_remote_control_active = bool(getattr(mission, "engineer_remote_control_active", False))
    weapons_locked = chopper_weapons_locked(
        meal_truck_driver_mode=bool(meal_truck_driver_mode),
        bus_driver_mode=bool(bus_driver_mode),
        engineer_remote_control_active=engineer_remote_control_active,
    )

    if paused.trigger_flare and not weapons_locked:
        try_start_flare_salvo(flares, mission=mission, helicopter=helicopter, audio=audio)

    if paused.toggle_doors:
        toggle_doors_with_logging(helicopter, mission, audio, logger, boarded_count, set_toast)
    if paused.reverse_flip:
        helicopter.reverse_flip()
    if paused.cycle_facing:
        helicopter.cycle_facing()
    if paused.fire_weapon and not weapons_locked and not bool(getattr(mission, "crash_active", False)):
        spawn_projectile_from_helicopter_logged(mission, helicopter, logger)
        if helicopter.facing is Facing.FORWARD:
            audio.play_bomb()
        else:
            audio.play_shoot()
