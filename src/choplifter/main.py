from __future__ import annotations

import pygame

from .audio import AudioBank
from .debug_overlay import DebugOverlay
from .game_logging import create_session_logger
from .helicopter import Facing, Helicopter, HelicopterInput, update_helicopter
from .mission import (
    MissionState,
    hostage_crush_check_logged,
    boarded_count,
    spawn_projectile_from_helicopter_logged,
    update_mission,
)
from .rendering import draw_ground, draw_helicopter, draw_hud, draw_mission, draw_sky, draw_toast
from .settings import DebugSettings, FixedTickSettings, HelicopterSettings, PhysicsSettings, WindowSettings
from .sky_smoke import SkySmokeSystem


def run() -> None:
    window = WindowSettings()
    tick = FixedTickSettings()
    physics = PhysicsSettings()
    heli_settings = HelicopterSettings()
    debug = DebugSettings()

    pygame.init()
    audio = AudioBank.try_create()

    logger = create_session_logger()
    logger.info("Controls: SPACE fire | E doors (grounded) | TAB facing | R reverse | F1 debug")
    logger.info("Rescue: open compound, land near hostages, E doors to load; land at base and E to unload")
    logger.info("Gamepad: Left stick tilt | Triggers lift | A doors | X fire | Y facing | B reverse | D-pad optional")

    # Gamepad detection (connect/disconnect notifications).
    pygame.joystick.init()
    joysticks: dict[int, pygame.joystick.Joystick] = {}
    toast_message = ""
    toast_seconds = 0.0

    prev_btn_a_down = False
    prev_btn_b_down = False
    prev_btn_x_down = False
    prev_btn_y_down = False
    prev_btn_start_down = False

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
        logger.info("GAMEPAD_INFO: axes=%d buttons=%d hats=%d", js.get_numaxes(), js.get_numbuttons(), js.get_numhats())
        set_toast(f"Gamepad connected: {name}")

    def get_active_joystick() -> pygame.joystick.Joystick | None:
        if not joysticks:
            return None
        # Prefer a stable order to avoid flipping between devices.
        instance_id = sorted(joysticks.keys())[0]
        return joysticks.get(instance_id)

    def axis_value(js: pygame.joystick.Joystick, axis_index: int) -> float:
        if axis_index < 0 or axis_index >= js.get_numaxes():
            return 0.0
        return float(js.get_axis(axis_index))

    def trigger_pressed(raw: float, threshold01: float = 0.55) -> bool:
        # Triggers are inconsistent across drivers:
        # - Some report in [-1..1] (rest=-1, pressed=1)
        # - Some report in [0..1] (rest=0, pressed=1)
        if raw < -0.1:
            value01 = (raw + 1.0) * 0.5
        else:
            value01 = raw
        return value01 >= threshold01

    def toggle_doors_with_logging() -> None:
        at_base = mission.base.contains_point(helicopter.pos)
        if not helicopter.grounded:
            logger.info("DOORS: toggle blocked (not grounded)")
            return

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

    flags = 0
    if window.vsync:
        # VSYNC is honored on some platforms/drivers.
        flags |= pygame.SCALED

    screen = pygame.display.set_mode((window.width, window.height), flags)
    pygame.display.set_caption(window.title)

    clock = pygame.time.Clock()
    overlay = DebugOverlay()

    sky_smoke = SkySmokeSystem()

    mission = MissionState.create_default(heli_settings)
    helicopter = Helicopter.spawn(heli_settings, start_x=mission.base.pos.x + mission.base.width * 0.5)
    helicopter.facing = Facing.LEFT

    prev_crashes = mission.crashes
    prev_lost_in_transit = mission.stats.lost_in_transit
    prev_saved = mission.stats.saved
    prev_open_compounds = sum(1 for c in mission.compounds if c.is_open)

    def reset_game() -> None:
        nonlocal helicopter, mission, accumulator
        nonlocal prev_btn_a_down, prev_btn_b_down, prev_btn_x_down, prev_btn_y_down, prev_btn_start_down
        nonlocal prev_crashes, prev_lost_in_transit, prev_saved, prev_open_compounds

        mission = MissionState.create_default(heli_settings)
        helicopter = Helicopter.spawn(heli_settings, start_x=mission.base.pos.x + mission.base.width * 0.5)
        helicopter.facing = Facing.LEFT
        accumulator = 0.0
        sky_smoke.reset()
        prev_crashes = mission.crashes
        prev_lost_in_transit = mission.stats.lost_in_transit
        prev_saved = mission.stats.saved
        prev_open_compounds = sum(1 for c in mission.compounds if c.is_open)
        prev_btn_a_down = False
        prev_btn_b_down = False
        prev_btn_x_down = False
        prev_btn_y_down = False
        prev_btn_start_down = False
        logger.info("RESET: mission restarted")

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
                logger.info("GAMEPAD_INFO: axes=%d buttons=%d hats=%d", js.get_numaxes(), js.get_numbuttons(), js.get_numhats())
                set_toast(f"Gamepad connected: {name}")
            elif event.type == pygame.JOYDEVICEREMOVED:
                removed = joysticks.pop(event.instance_id, None)
                name = removed.get_name() if removed is not None else "Gamepad"
                logger.info("GAMEPAD_DISCONNECTED: %s", name)
                set_toast(f"Gamepad disconnected: {name}")
                prev_btn_a_down = False
                prev_btn_b_down = False
                prev_btn_x_down = False
                prev_btn_y_down = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_RETURN and mission.ended:
                    reset_game()
                elif event.key == pygame.K_F1:
                    debug = DebugSettings(show_overlay=not debug.show_overlay)
                elif event.key == pygame.K_TAB:
                    helicopter.cycle_facing()
                elif event.key == pygame.K_r:
                    helicopter.reverse_flip()
                elif event.key == pygame.K_e:
                    toggle_doors_with_logging()
                elif event.key == pygame.K_SPACE:
                    spawn_projectile_from_helicopter_logged(mission, helicopter, logger)
                    if helicopter.facing is Facing.FORWARD:
                        audio.play_bomb()
                    else:
                        audio.play_shoot()

        keys = pygame.key.get_pressed()
        kb_tilt_left = keys[pygame.K_LEFT] or keys[pygame.K_a]
        kb_tilt_right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        kb_lift_up = keys[pygame.K_UP] or keys[pygame.K_w]
        kb_lift_down = keys[pygame.K_DOWN] or keys[pygame.K_s]
        kb_brake = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]

        gp_tilt_left = False
        gp_tilt_right = False
        gp_lift_up = False
        gp_lift_down = False

        active_js = get_active_joystick()
        if active_js is not None:
            x_axis = axis_value(active_js, 0)
            deadzone = 0.35
            gp_tilt_left = x_axis <= -deadzone
            gp_tilt_right = x_axis >= deadzone

            if active_js.get_numhats() > 0:
                hat_x, hat_y = active_js.get_hat(0)
                gp_tilt_left = gp_tilt_left or hat_x <= -1
                gp_tilt_right = gp_tilt_right or hat_x >= 1
                gp_lift_up = gp_lift_up or hat_y >= 1
                gp_lift_down = gp_lift_down or hat_y <= -1

            axes = active_js.get_numaxes()
            if axes >= 6:
                gp_lift_down = trigger_pressed(axis_value(active_js, 4))
                gp_lift_up = trigger_pressed(axis_value(active_js, 5))
            elif axes >= 3:
                # Common fallback: a combined trigger axis.
                trig = axis_value(active_js, 2)
                gp_lift_down = trig <= -0.35
                gp_lift_up = trig >= 0.35

            # Edge-triggered actions.
            a_down = bool(active_js.get_numbuttons() > 0 and active_js.get_button(0))
            b_down = bool(active_js.get_numbuttons() > 1 and active_js.get_button(1))
            x_down = bool(active_js.get_numbuttons() > 2 and active_js.get_button(2))
            y_down = bool(active_js.get_numbuttons() > 3 and active_js.get_button(3))
            start_down = bool(active_js.get_numbuttons() > 7 and active_js.get_button(7))

            if start_down and not prev_btn_start_down and mission.ended:
                reset_game()

            if a_down and not prev_btn_a_down:
                toggle_doors_with_logging()
            if b_down and not prev_btn_b_down:
                helicopter.reverse_flip()
            if y_down and not prev_btn_y_down:
                helicopter.cycle_facing()
            if x_down and not prev_btn_x_down:
                spawn_projectile_from_helicopter_logged(mission, helicopter, logger)
                if helicopter.facing is Facing.FORWARD:
                    audio.play_bomb()
                else:
                    audio.play_shoot()

            prev_btn_a_down = a_down
            prev_btn_b_down = b_down
            prev_btn_x_down = x_down
            prev_btn_y_down = y_down
            prev_btn_start_down = start_down

        helicopter_input = HelicopterInput(
            tilt_left=kb_tilt_left or gp_tilt_left,
            tilt_right=kb_tilt_right or gp_tilt_right,
            lift_up=kb_lift_up or gp_lift_up,
            lift_down=kb_lift_down or gp_lift_down,
            brake=kb_brake,
        )

        # Fixed-timestep update.
        # Clamp accumulator to avoid spiral of death if the window stalls.
        if accumulator > 0.25:
            accumulator = 0.25

        while accumulator >= tick.dt:
            was_grounded = helicopter.grounded
            update_helicopter(helicopter, helicopter_input, tick.dt, physics, heli_settings, world_width=float(mission.world_width))
            if not was_grounded and helicopter.grounded:
                hostage_crush_check_logged(mission, helicopter, helicopter.last_landing_vy, logger)
            update_mission(mission, helicopter, tick.dt, heli_settings, logger=logger)

            saved_delta = mission.stats.saved - prev_saved
            if saved_delta > 0:
                audio.play_rescue()
                prev_saved = mission.stats.saved

            open_compounds = sum(1 for c in mission.compounds if c.is_open)
            if open_compounds > prev_open_compounds:
                audio.play_explosion()
                prev_open_compounds = open_compounds

            if mission.crashes != prev_crashes:
                if mission.ended:
                    set_toast(f"THE END: {mission.end_reason} (Enter/Start)")
                else:
                    set_toast(f"CRASH {mission.crashes}/3 — respawn (invuln {mission.invuln_seconds:0.1f}s)")
                    audio.play_crash()
                prev_crashes = mission.crashes

            lost_delta = mission.stats.lost_in_transit - prev_lost_in_transit
            if lost_delta > 0:
                set_toast(f"Passengers lost in crash: +{lost_delta}")
                prev_lost_in_transit = mission.stats.lost_in_transit

            accumulator -= tick.dt

        if toast_seconds > 0.0:
            toast_seconds -= frame_dt
            if toast_seconds <= 0.0:
                toast_message = ""

        # Visual-only sky particles.
        sky_smoke.update(frame_dt, width=screen.get_width(), horizon_y=int(heli_settings.ground_y))

        # Side-scrolling camera (world x -> screen x).
        world_w = float(mission.world_width)
        view_w = float(screen.get_width())
        max_cam_x = max(0.0, world_w - view_w)
        camera_x = helicopter.pos.x - view_w * 0.5
        if camera_x < 0.0:
            camera_x = 0.0
        elif camera_x > max_cam_x:
            camera_x = max_cam_x

        # Render.
        # Background above the horizon.
        draw_sky(screen, heli_settings.ground_y)
        sky_smoke.draw(screen, horizon_y=int(heli_settings.ground_y))
        draw_ground(screen, heli_settings.ground_y)
        draw_mission(screen, mission, camera_x=camera_x)
        draw_helicopter(screen, helicopter, camera_x=camera_x)
        draw_hud(screen, mission, helicopter)
        if toast_message:
            draw_toast(screen, toast_message)

        if debug.show_overlay:
            overlay.draw(screen, helicopter, mission, clock.get_fps())

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    run()
