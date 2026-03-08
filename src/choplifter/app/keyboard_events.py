from __future__ import annotations

import pygame
from typing import Any, Callable
from src.choplifter.controls import matches_key, pressed
from src.choplifter.app.menu_helpers import cycle_index, move_pause_focus


def handle_keyboard_event(event: pygame.event.Event, *, mode: str, controls: Any, mission: Any, helicopter: Any, audio: Any, logger: Any, chopper_choices: list, mission_choices: list, pause_focus: str, muted: bool, set_toast: Callable, reset_game: Callable, apply_mission_preview: Callable, skip_intro: Callable, skip_mission_cutscene: Callable, toggle_particles_wrapper: Callable, toggle_flashes_wrapper: Callable, toggle_screenshake_wrapper: Callable, spawn_projectile_from_helicopter_logged: Callable, try_start_flare_salvo: Callable, toggle_doors_with_logging: Callable, Facing: Any, DebugSettings: Any, boarded_count: Any, flares: Any, selected_mission_index: int, selected_mission_id: str, selected_chopper_index: int, selected_chopper_asset: str, debug: Any, quit_confirm: bool) -> tuple[str, str, bool, int, str, int, str, Any, bool]:
    """
    Handles keyboard events and returns updated (mode, pause_focus, muted).
    """
    if mode == "playing" and event.key == pygame.K_ESCAPE:
        if logger:
            logger.debug("Pause requested (ESCAPE) in playing mode")
        mode = "paused"
        pause_focus = "choppers"
        audio.play_pause_toggle()
        audio.set_pause_menu_active(True)
    elif mode == "paused" and event.key == pygame.K_ESCAPE:
        mode = "playing"
        audio.set_pause_menu_active(False)
        audio.play_pause_toggle()
    elif matches_key(event.key, controls.quit):
        # Always return a 9-tuple, using current values for unchanged fields
        return (
            mode, pause_focus, True, selected_mission_index, selected_mission_id,
            selected_chopper_index, selected_chopper_asset, debug, quit_confirm
        )
    elif mode == "cutscene":
        mode = "playing"
        skip_mission_cutscene()
    elif mode == "intro":
        mode = "select_mission"
        skip_intro()
    elif mode == "select_chopper":
        if event.key in (pygame.K_LEFT, pygame.K_a) or matches_key(event.key, controls.tilt_left):
            selected_chopper_index = cycle_index(selected_chopper_index, -1, len(chopper_choices))
            selected_chopper_asset = chopper_choices[selected_chopper_index][0]
            audio.play_menu_select()
        elif event.key in (pygame.K_RIGHT, pygame.K_d) or matches_key(event.key, controls.tilt_right):
            selected_chopper_index = cycle_index(selected_chopper_index, 1, len(chopper_choices))
            selected_chopper_asset = chopper_choices[selected_chopper_index][0]
            audio.play_menu_select()
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            mode = "playing"
            set_toast(f"Chopper selected: {chopper_choices[selected_chopper_index][1]}")
            reset_game()
        elif event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            mode = "select_mission"
            set_toast("Back to Mission Select")
    elif mode == "select_mission":
        if event.key in (pygame.K_LEFT, pygame.K_a):
            selected_mission_index = cycle_index(selected_mission_index, -1, len(mission_choices))
            selected_mission_id = mission_choices[selected_mission_index][0]
            audio.play_menu_select()
            apply_mission_preview()
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            selected_mission_index = cycle_index(selected_mission_index, 1, len(mission_choices))
            selected_mission_id = mission_choices[selected_mission_index][0]
            audio.play_menu_select()
            apply_mission_preview()
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            mode = "select_chopper"
            set_toast(f"Mission selected: {mission_choices[selected_mission_index][1]}")
    elif mode == "paused":
        if event.key == pygame.K_F2:
            toggle_particles_wrapper()
        elif event.key == pygame.K_F3:
            toggle_flashes_wrapper()
        elif event.key == pygame.K_F4:
            toggle_screenshake_wrapper()
        if event.key in (pygame.K_UP, pygame.K_w):
            prev_pause_focus = pause_focus
            pause_focus = move_pause_focus(pause_focus, -1)
            if pause_focus != prev_pause_focus:
                audio.play_menu_select()
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            prev_pause_focus = pause_focus
            pause_focus = move_pause_focus(pause_focus, 1)
            if pause_focus != prev_pause_focus:
                audio.play_menu_select()
        elif event.key in (pygame.K_LEFT, pygame.K_a) and pause_focus == "choppers":
            selected_chopper_index = cycle_index(selected_chopper_index, -1, len(chopper_choices))
            selected_chopper_asset = chopper_choices[selected_chopper_index][0]
            helicopter.skin_asset = selected_chopper_asset
            audio.play_menu_select()
        elif event.key in (pygame.K_RIGHT, pygame.K_d) and pause_focus == "choppers":
            selected_chopper_index = cycle_index(selected_chopper_index, 1, len(chopper_choices))
            selected_chopper_asset = chopper_choices[selected_chopper_index][0]
            helicopter.skin_asset = selected_chopper_asset
            audio.play_menu_select()
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            if pause_focus == "restart_mission":
                reset_game()
                mode = "playing"
                audio.set_pause_menu_active(False)
                audio.play_pause_toggle()
            elif pause_focus == "restart_game":
                mode = "select_mission"
                pause_focus = "choppers"
                set_toast("Restart Game")
                audio.set_pause_menu_active(False)
                audio.play_pause_toggle()
            elif pause_focus == "mute":
                muted = not muted
                audio.set_muted(muted)
            elif pause_focus == "quit":
                # Open quit confirmation dialog when Enter/Space pressed on Quit
                if not quit_confirm:
                    quit_confirm = True
                    if logger:
                        logger.info(f"PAUSE MENU: Keyboard pressed on quit, showing confirmation dialog")
            else:
                mode = "playing"
                audio.set_pause_menu_active(False)
                audio.play_pause_toggle()
    elif matches_key(event.key, controls.restart) and mission.ended:
        reset_game()
    elif matches_key(event.key, controls.toggle_debug):
        debug = DebugSettings(show_overlay=not debug.show_overlay)
        set_toast(f"Debug overlay: {'ON' if debug.show_overlay else 'OFF'}")
    elif mode == "playing" and matches_key(event.key, controls.cycle_facing):
        if not getattr(mission, "crash_active", False):
            helicopter.cycle_facing()
    elif mode == "playing" and matches_key(event.key, controls.reverse_flip):
        if not getattr(mission, "crash_active", False):
            helicopter.reverse_flip()
    elif mode == "playing" and matches_key(event.key, controls.doors):
        if not getattr(mission, "crash_active", False):
            toggle_doors_with_logging(helicopter, mission, audio, logger, boarded_count, set_toast)
    elif mode == "playing" and matches_key(event.key, controls.flare):
        if logger:
            logger.debug("Flare key pressed (key=%s) in playing mode", event.key)
        try_start_flare_salvo(flares, mission=mission, helicopter=helicopter, audio=audio)
    elif mode == "playing" and matches_key(event.key, controls.fire):
        if logger:
            logger.debug("Fire key pressed (key=%s) in playing mode", event.key)
        if not getattr(mission, "crash_active", False):
            spawn_projectile_from_helicopter_logged(mission, helicopter, logger)
            if helicopter.facing is Facing.FORWARD:
                audio.play_bomb()
            else:
                audio.play_shoot()
    # Return quit_confirm as part of the tuple so main.py can update it
    return mode, pause_focus, muted, selected_mission_index, selected_mission_id, selected_chopper_index, selected_chopper_asset, debug, quit_confirm
