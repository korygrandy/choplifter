from __future__ import annotations

import pygame

from .debug_overlay import DebugOverlay
from .helicopter import Helicopter, HelicopterInput, update_helicopter
from .mission import MissionState, hostage_crush_check, spawn_projectile_from_helicopter, update_mission
from .rendering import draw_ground, draw_helicopter, draw_mission
from .settings import DebugSettings, FixedTickSettings, HelicopterSettings, PhysicsSettings, WindowSettings


def run() -> None:
    window = WindowSettings()
    tick = FixedTickSettings()
    physics = PhysicsSettings()
    heli_settings = HelicopterSettings()
    debug = DebugSettings()

    pygame.init()

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
                    helicopter.toggle_doors()
                elif event.key == pygame.K_SPACE:
                    spawn_projectile_from_helicopter(mission, helicopter)

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
                hostage_crush_check(mission, helicopter, helicopter.last_landing_vy)
            update_mission(mission, helicopter, tick.dt, heli_settings)
            accumulator -= tick.dt

        # Render.
        screen.fill((135, 190, 235))
        draw_ground(screen, heli_settings.ground_y)
        draw_mission(screen, mission)
        draw_helicopter(screen, helicopter)

        if debug.show_overlay:
            overlay.draw(screen, helicopter, mission, clock.get_fps())

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    run()
