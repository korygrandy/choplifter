from __future__ import annotations

import pygame

from .debug_overlay import DebugOverlay
from .game_logging import create_session_logger
from .helicopter import Helicopter, HelicopterInput, update_helicopter
from .mission import (
    MissionState,
    hostage_crush_check_logged,
    boarded_count,
    spawn_projectile_from_helicopter_logged,
    update_mission,
)
from .rendering import draw_ground, draw_helicopter, draw_hud, draw_mission, draw_toast
from .settings import DebugSettings, FixedTickSettings, HelicopterSettings, PhysicsSettings, WindowSettings


def run() -> None:
    window = WindowSettings()
    tick = FixedTickSettings()
    physics = PhysicsSettings()
    heli_settings = HelicopterSettings()
    debug = DebugSettings()

    pygame.init()

    logger = create_session_logger()
    logger.info("Controls: SPACE fire | E doors (grounded) | TAB facing | R reverse | F1 debug")
    logger.info("Rescue: open compound, land near hostages, E doors to load; land at base and E to unload")

    # Gamepad detection (connect/disconnect notifications).
    pygame.joystick.init()
    joysticks: dict[int, pygame.joystick.Joystick] = {}
    toast_message = ""
    toast_seconds = 0.0

    def set_toast(message: str) -> None:
        nonlocal toast_message, toast_seconds
        toast_message = message
        toast_seconds = 3.0

    for i in range(pygame.joystick.get_count()):
        js = pygame.joystick.Joystick(i)
        js.init()
        joysticks[js.get_instance_id()] = js
        name = js.get_name() or "Gamepad"
        logger.info("GAMEPAD_CONNECTED: %s", name)
        set_toast(f"Gamepad connected: {name}")

    flags = 0
    if window.vsync:
        # VSYNC is honored on some platforms/drivers.
        flags |= pygame.SCALED

    screen = pygame.display.set_mode((window.width, window.height), flags)
    pygame.display.set_caption(window.title)

    clock = pygame.time.Clock()
    overlay = DebugOverlay()

    helicopter = Helicopter.spawn(heli_settings)
    mission = MissionState.create_default(heli_settings)

    running = True
    accumulator = 0.0

    while running:
        frame_dt = clock.tick(120) / 1000.0
        accumulator += frame_dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.JOYDEVICEADDED:
                js = pygame.joystick.Joystick(event.device_index)
                js.init()
                joysticks[js.get_instance_id()] = js
                name = js.get_name() or "Gamepad"
                logger.info("GAMEPAD_CONNECTED: %s", name)
                set_toast(f"Gamepad connected: {name}")
            elif event.type == pygame.JOYDEVICEREMOVED:
                removed = joysticks.pop(event.instance_id, None)
                name = removed.get_name() if removed is not None else "Gamepad"
                logger.info("GAMEPAD_DISCONNECTED: %s", name)
                set_toast(f"Gamepad disconnected: {name}")
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_F1:
                    debug = DebugSettings(show_overlay=not debug.show_overlay)
                elif event.key == pygame.K_TAB:
                    helicopter.cycle_facing()
                elif event.key == pygame.K_r:
                    helicopter.reverse_flip()
                elif event.key == pygame.K_e:
                    at_base = mission.base.contains_point(helicopter.pos)
                    if not helicopter.grounded:
                        logger.info("DOORS: toggle blocked (not grounded)")
                    else:
                        before = helicopter.doors_open
                        helicopter.toggle_doors()
                        after = helicopter.doors_open
                        if before != after:
                            logger.info(
                                "DOORS: %s at_base=%s boarded=%d",
                                "OPEN" if after else "closed",
                                at_base,
                                boarded_count(mission),
                            )
                        if after and not at_base and boarded_count(mission) > 0:
                            logger.info("UNLOAD_BLOCKED: doors open but not in base zone")
                        if after and at_base and boarded_count(mission) == 0:
                            logger.info("UNLOAD: no boarded passengers")
                elif event.key == pygame.K_SPACE:
                    spawn_projectile_from_helicopter_logged(mission, helicopter, logger)

        keys = pygame.key.get_pressed()
        helicopter_input = HelicopterInput(
            tilt_left=keys[pygame.K_LEFT] or keys[pygame.K_a],
            tilt_right=keys[pygame.K_RIGHT] or keys[pygame.K_d],
            lift_up=keys[pygame.K_UP] or keys[pygame.K_w],
            lift_down=keys[pygame.K_DOWN] or keys[pygame.K_s],
            brake=keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT],
        )

        # Fixed-timestep update.
        # Clamp accumulator to avoid spiral of death if the window stalls.
        if accumulator > 0.25:
            accumulator = 0.25

        while accumulator >= tick.dt:
            was_grounded = helicopter.grounded
            update_helicopter(helicopter, helicopter_input, tick.dt, physics, heli_settings, world_width=float(window.width))
            if not was_grounded and helicopter.grounded:
                hostage_crush_check_logged(mission, helicopter, helicopter.last_landing_vy, logger)
            update_mission(mission, helicopter, tick.dt, heli_settings, logger=logger)
            accumulator -= tick.dt

        if toast_seconds > 0.0:
            toast_seconds -= frame_dt
            if toast_seconds <= 0.0:
                toast_message = ""

        # Render.
        screen.fill((135, 190, 235))
        draw_ground(screen, heli_settings.ground_y)
        draw_mission(screen, mission)
        draw_helicopter(screen, helicopter)
        draw_hud(screen, mission, helicopter)
        if toast_message:
            draw_toast(screen, toast_message)

        if debug.show_overlay:
            overlay.draw(screen, helicopter, mission, clock.get_fps())

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    run()
