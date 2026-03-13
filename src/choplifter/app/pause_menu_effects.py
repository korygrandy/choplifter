from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from .pause_menu_inputs import PausedMenuDecision


@dataclass
class PausedMenuApplyResult:
    mode: str
    running: bool
    selected_chopper_index: int
    selected_chopper_asset: str
    muted: bool
    quit_confirm: bool


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