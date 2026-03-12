from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence
import pygame

from .vehicle_driver_modes import handle_airport_driver_mode_doors


def handle_mission_end_keyboard_navigation(*, key: int, mode: str, mission_ended: bool, set_toast: Callable[[str], None]) -> tuple[bool, str]:
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
