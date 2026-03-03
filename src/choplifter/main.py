from __future__ import annotations

from pathlib import Path
import pygame

from .audio import AudioBank
from .accessibility import load_accessibility
from .controls import load_controls, matches_key, pressed
from .debug_overlay import DebugOverlay
from .game_logging import create_session_logger
from .helicopter import Facing, Helicopter, HelicopterInput, update_helicopter
from .mission import (
    MissionState,
    get_mission_config_by_id,
    hostage_crush_check_logged,
    boarded_count,
    spawn_projectile_from_helicopter_logged,
    update_mission,
)
from .rendering import (
    bg_asset_exists,
    draw_chopper_select_overlay,
    draw_intro_cutscene,
    draw_skip_overlay,
    draw_ground,
    draw_helicopter,
    draw_hud,
    draw_mission,
    draw_mission_select_overlay,
    draw_sky,
    draw_toast,
)
from .settings import DebugSettings, FixedTickSettings, HelicopterSettings, PhysicsSettings, WindowSettings
from .sky_smoke import SkySmokeSystem
from .intro_video import IntroVideoPlayer
from .physics_config import load_physics_settings


def run() -> None:
    window = WindowSettings()
    tick = FixedTickSettings()
    physics = load_physics_settings()
    heli_settings = HelicopterSettings()
    debug = DebugSettings()

    pygame.init()
    logger = create_session_logger()

    # Window icon (taskbar/alt-tab). This does not change the .exe file icon.
    try:
        module_dir = Path(__file__).resolve().parent
        icon_path = module_dir / "assets" / "chopper-one.png"
        icon = pygame.image.load(str(icon_path))
        try:
            icon = pygame.transform.smoothscale(icon, (32, 32))
        except Exception:
            pass
        pygame.display.set_icon(icon)
        logger.info("WINDOW_ICON: %s", icon_path.as_posix())
    except Exception as e:
        logger.info("WINDOW_ICON: failed (%s)", type(e).__name__)

    controls = load_controls(logger=logger)
    accessibility = load_accessibility(logger=logger)
    audio = AudioBank.try_create()
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
    prev_btn_rb_down = False
    prev_btn_lb_down = False

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

    def trigger_pressed(raw: float, threshold01: float) -> bool:
        # Triggers are inconsistent across drivers:
        # - Some report in [-1..1] (rest=-1, pressed=1)
        # - Some report in [0..1] (rest=0, pressed=1)
        if raw < -0.1:
            value01 = (raw + 1.0) * 0.5
        else:
            value01 = raw
        return value01 >= threshold01

    particles_enabled = accessibility.particles_enabled
    flashes_enabled = accessibility.flashes_enabled
    screenshake_enabled = accessibility.screenshake_enabled

    def toggle_doors_with_logging() -> None:
        at_base = mission.base.contains_point(helicopter.pos)
        if not helicopter.grounded:
            logger.info("DOORS: toggle blocked (not grounded)")
            return

        before = helicopter.doors_open
        helicopter.toggle_doors()
        after = helicopter.doors_open
        if before != after:
            if after:
                audio.play_doors_open()
            else:
                audio.play_doors_close()
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

    # Optional video intro asset (falls back to the in-engine title card if missing/unavailable).
    module_dir = Path(__file__).resolve().parent
    assets_dir = module_dir / "assets"
    # Prefer the legacy MPG intro for now (simpler asset workflow).
    # MP4 remains as a fallback if the MPG is missing.
    intro_candidates = (
        assets_dir / "intro.mpg",
        assets_dir / "choplifter-intro.mp4",
        assets_dir / "choplifter-intro,mp4",
    )
    intro_video_path = next((p for p in intro_candidates if p.exists()), intro_candidates[0])
    intro_video = IntroVideoPlayer.try_create(intro_video_path)
    if intro_video is None:
        logger.info(
            "INTRO_VIDEO: disabled path=%s exists=%s reason=%s",
            intro_video_path.as_posix(),
            intro_video_path.exists(),
            IntroVideoPlayer.last_error(),
        )
    else:
        logger.info(
            "INTRO_VIDEO: enabled path=%s fps=%0.1f duration_s=%0.2f",
            intro_video_path.as_posix(),
            float(intro_video.fps),
            float(intro_video.duration_s),
        )

    clock = pygame.time.Clock()
    overlay = DebugOverlay()

    sky_smoke = SkySmokeSystem()

    # Pre-game mission selection overlay.
    mission_choices: list[tuple[str, str]] = [
        ("city", "City Center Seige"),
        ("airport", "Airport Special Ops"),
        ("worship", "Worship Center Warfare"),
    ]
    selected_mission_index = 0
    selected_mission_id = mission_choices[selected_mission_index][0]

    # Pre-game chopper selection overlay.
    chopper_choices: list[tuple[str, str]] = [
        ("chopper-one.png", "Classic"),
        ("chopper-two-orange.png", "Orange"),
        ("chopper-three-green.png", "Green"),
        ("chopper-four-blue.png", "Blue"),
        ("chopper-five-desert.png", "Desert"),
    ]
    selected_chopper_index = 0
    selected_chopper_asset = chopper_choices[selected_chopper_index][0]

    # Intro cutscene plays on every launch.
    mode: str = "intro"  # intro | select_mission | select_chopper | playing | paused
    intro_t = 0.0
    intro_seconds = float(intro_video.duration_s) if (intro_video is not None and intro_video.duration_s > 0.5) else 4.25
    prev_menu_dir = 0
    prev_menu_vert = 0
    pause_focus: str = "choppers"  # choppers | restart_mission | restart_game

    mission = MissionState.create_from_level_config(heli_settings, get_mission_config_by_id(selected_mission_id))
    helicopter = Helicopter.spawn(
        heli_settings,
        start_x=mission.base.pos.x + mission.base.width * 0.5,
        skin_asset=selected_chopper_asset,
    )
    helicopter.facing = Facing.LEFT

    prev_crashes = mission.crashes
    prev_lost_in_transit = mission.stats.lost_in_transit
    prev_saved = mission.stats.saved
    prev_boarded = boarded_count(mission)
    prev_open_compounds = sum(1 for c in mission.compounds if c.is_open)
    prev_tanks_destroyed = mission.stats.tanks_destroyed

    def apply_mission_preview() -> None:
        nonlocal helicopter, mission, accumulator
        nonlocal prev_crashes, prev_lost_in_transit, prev_saved, prev_boarded, prev_open_compounds, prev_tanks_destroyed

        mission = MissionState.create_from_level_config(heli_settings, get_mission_config_by_id(selected_mission_id))
        helicopter = Helicopter.spawn(
            heli_settings,
            start_x=mission.base.pos.x + mission.base.width * 0.5,
            skin_asset=selected_chopper_asset,
        )
        helicopter.facing = Facing.LEFT
        accumulator = 0.0
        sky_smoke.reset()
        audio.stop_flying()
        prev_crashes = mission.crashes
        prev_lost_in_transit = mission.stats.lost_in_transit
        prev_saved = mission.stats.saved
        prev_boarded = boarded_count(mission)
        prev_open_compounds = sum(1 for c in mission.compounds if c.is_open)
        prev_tanks_destroyed = mission.stats.tanks_destroyed

        bg = getattr(mission, "bg_asset", "")
        if bg and not bg_asset_exists(bg):
            set_toast(f"Missing background: {bg}")

    def reset_game() -> None:
        nonlocal helicopter, mission, accumulator
        nonlocal selected_chopper_asset
        nonlocal selected_mission_id
        nonlocal prev_btn_a_down, prev_btn_b_down, prev_btn_x_down, prev_btn_y_down, prev_btn_start_down
        nonlocal prev_crashes, prev_lost_in_transit, prev_saved, prev_boarded, prev_open_compounds, prev_tanks_destroyed

        mission = MissionState.create_from_level_config(heli_settings, get_mission_config_by_id(selected_mission_id))
        helicopter = Helicopter.spawn(
            heli_settings,
            start_x=mission.base.pos.x + mission.base.width * 0.5,
            skin_asset=selected_chopper_asset,
        )
        helicopter.facing = Facing.LEFT
        accumulator = 0.0
        sky_smoke.reset()
        audio.stop_flying()
        prev_crashes = mission.crashes
        prev_lost_in_transit = mission.stats.lost_in_transit
        prev_saved = mission.stats.saved
        prev_boarded = boarded_count(mission)
        prev_open_compounds = sum(1 for c in mission.compounds if c.is_open)
        prev_tanks_destroyed = mission.stats.tanks_destroyed
        prev_btn_a_down = False
        prev_btn_b_down = False
        prev_btn_x_down = False
        prev_btn_y_down = False
        prev_btn_start_down = False
        prev_btn_rb_down = False
        prev_btn_lb_down = False
        logger.info("RESET: mission restarted")

    def toggle_particles() -> None:
        nonlocal particles_enabled
        particles_enabled = not particles_enabled
        set_toast(f"Particles: {'ON' if particles_enabled else 'OFF'}")

    def toggle_flashes() -> None:
        nonlocal flashes_enabled
        flashes_enabled = not flashes_enabled
        set_toast(f"Flashes: {'ON' if flashes_enabled else 'OFF'}")

    def toggle_screenshake() -> None:
        nonlocal screenshake_enabled
        screenshake_enabled = not screenshake_enabled
        set_toast(f"Screenshake: {'ON' if screenshake_enabled else 'OFF'}")

    running = True
    accumulator = 0.0

    while running:
        frame_dt = clock.tick(120) / 1000.0
        accumulator += frame_dt

        skip_hint = "Enter/Space or A/Start: Skip" if get_active_joystick() is not None else "Enter/Space: Skip"

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
                if matches_key(event.key, controls.quit):
                    running = False
                elif mode == "intro":
                    # Skip intro immediately on any key press (except quit which is handled above).
                    mode = "select_mission"
                    intro_t = 0.0
                    if intro_video is not None:
                        intro_video.close(immediate=True)
                        intro_video = None
                elif mode == "playing" and event.key == pygame.K_ESCAPE:
                    mode = "paused"
                    pause_focus = "choppers"
                elif mode == "paused" and event.key == pygame.K_ESCAPE:
                    mode = "playing"
                elif mode == "select_chopper":
                    if event.key in (pygame.K_LEFT, pygame.K_a) or matches_key(event.key, controls.tilt_left):
                        selected_chopper_index = (selected_chopper_index - 1) % len(chopper_choices)
                        selected_chopper_asset = chopper_choices[selected_chopper_index][0]
                    elif event.key in (pygame.K_RIGHT, pygame.K_d) or matches_key(event.key, controls.tilt_right):
                        selected_chopper_index = (selected_chopper_index + 1) % len(chopper_choices)
                        selected_chopper_asset = chopper_choices[selected_chopper_index][0]
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        mode = "playing"
                        set_toast(f"Chopper selected: {chopper_choices[selected_chopper_index][1]}")
                        reset_game()
                elif mode == "select_mission":
                    if event.key in (pygame.K_LEFT, pygame.K_a):
                        selected_mission_index = (selected_mission_index - 1) % len(mission_choices)
                        selected_mission_id = mission_choices[selected_mission_index][0]
                        apply_mission_preview()
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        selected_mission_index = (selected_mission_index + 1) % len(mission_choices)
                        selected_mission_id = mission_choices[selected_mission_index][0]
                        apply_mission_preview()
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        mode = "select_chopper"
                        set_toast(f"Mission selected: {mission_choices[selected_mission_index][1]}")
                elif mode == "paused":
                    if event.key == pygame.K_F2:
                        toggle_particles()
                    elif event.key == pygame.K_F3:
                        toggle_flashes()
                    elif event.key == pygame.K_F4:
                        toggle_screenshake()
                    if event.key in (pygame.K_UP, pygame.K_w):
                        if pause_focus == "restart_game":
                            pause_focus = "restart_mission"
                        elif pause_focus == "restart_mission":
                            pause_focus = "choppers"
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        if pause_focus == "choppers":
                            pause_focus = "restart_mission"
                        elif pause_focus == "restart_mission":
                            pause_focus = "restart_game"
                    elif event.key in (pygame.K_LEFT, pygame.K_a) and pause_focus == "choppers":
                        selected_chopper_index = (selected_chopper_index - 1) % len(chopper_choices)
                        selected_chopper_asset = chopper_choices[selected_chopper_index][0]
                        helicopter.skin_asset = selected_chopper_asset
                    elif event.key in (pygame.K_RIGHT, pygame.K_d) and pause_focus == "choppers":
                        selected_chopper_index = (selected_chopper_index + 1) % len(chopper_choices)
                        selected_chopper_asset = chopper_choices[selected_chopper_index][0]
                        helicopter.skin_asset = selected_chopper_asset
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if pause_focus == "restart_mission":
                            reset_game()
                            mode = "playing"
                        elif pause_focus == "restart_game":
                            mode = "select_mission"
                            pause_focus = "choppers"
                            set_toast("Restart Game")
                        else:
                            mode = "playing"
                elif matches_key(event.key, controls.restart) and mission.ended:
                    reset_game()
                elif matches_key(event.key, controls.toggle_debug):
                    debug = DebugSettings(show_overlay=not debug.show_overlay)
                    set_toast(f"Debug overlay: {'ON' if debug.show_overlay else 'OFF'}")
                elif mode == "playing" and matches_key(event.key, controls.cycle_facing):
                    helicopter.cycle_facing()
                elif mode == "playing" and matches_key(event.key, controls.reverse_flip):
                    helicopter.reverse_flip()
                elif mode == "playing" and matches_key(event.key, controls.doors):
                    toggle_doors_with_logging()
                elif mode == "playing" and matches_key(event.key, controls.fire):
                    spawn_projectile_from_helicopter_logged(mission, helicopter, logger)
                    if helicopter.facing is Facing.FORWARD:
                        audio.play_bomb()
                    else:
                        audio.play_shoot()

        keys = pygame.key.get_pressed()
        kb_tilt_left = pressed(keys, controls.tilt_left)
        kb_tilt_right = pressed(keys, controls.tilt_right)
        kb_lift_up = pressed(keys, controls.lift_up)
        kb_lift_down = pressed(keys, controls.lift_down)
        kb_brake = pressed(keys, controls.brake)

        gp_tilt_left = False
        gp_tilt_right = False
        gp_lift_up = False
        gp_lift_down = False

        active_js = get_active_joystick()
        if active_js is not None:
            x_axis = axis_value(active_js, 0)
            deadzone = float(accessibility.gamepad_deadzone)
            gp_tilt_left = x_axis <= -deadzone
            gp_tilt_right = x_axis >= deadzone

            menu_dir = -1 if gp_tilt_left else (1 if gp_tilt_right else 0)
            menu_vert = 0

            if active_js.get_numhats() > 0:
                hat_x, hat_y = active_js.get_hat(0)
                gp_tilt_left = gp_tilt_left or hat_x <= -1
                gp_tilt_right = gp_tilt_right or hat_x >= 1
                gp_lift_up = gp_lift_up or hat_y >= 1
                gp_lift_down = gp_lift_down or hat_y <= -1
                if hat_x <= -1:
                    menu_dir = -1
                elif hat_x >= 1:
                    menu_dir = 1
                if hat_y >= 1:
                    menu_vert = -1
                elif hat_y <= -1:
                    menu_vert = 1
            else:
                # Fallback: use left stick Y for menu up/down.
                y_axis = axis_value(active_js, 1)
                if y_axis <= -deadzone:
                    menu_vert = -1
                elif y_axis >= deadzone:
                    menu_vert = 1

            axes = active_js.get_numaxes()
            if axes >= 6:
                gp_lift_down = trigger_pressed(axis_value(active_js, 4), threshold01=float(accessibility.trigger_threshold))
                gp_lift_up = trigger_pressed(axis_value(active_js, 5), threshold01=float(accessibility.trigger_threshold))
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
            rb_down = bool(active_js.get_numbuttons() > 5 and active_js.get_button(5))
            lb_down = bool(active_js.get_numbuttons() > 4 and active_js.get_button(4))

            # Debug overlay toggle (gamepad).
            if lb_down and not prev_btn_lb_down:
                debug = DebugSettings(show_overlay=not debug.show_overlay)
                set_toast(f"Debug overlay: {'ON' if debug.show_overlay else 'OFF'}")

            if mode == "select_chopper":
                if menu_dir != 0 and menu_dir != prev_menu_dir:
                    selected_chopper_index = (selected_chopper_index + menu_dir) % len(chopper_choices)
                    selected_chopper_asset = chopper_choices[selected_chopper_index][0]
                if (a_down and not prev_btn_a_down) or (start_down and not prev_btn_start_down):
                    mode = "playing"
                    set_toast(f"Chopper selected: {chopper_choices[selected_chopper_index][1]}")
                    reset_game()
            elif mode == "intro":
                skip_btn = (
                    (a_down and not prev_btn_a_down)
                    or (b_down and not prev_btn_b_down)
                    or (x_down and not prev_btn_x_down)
                    or (y_down and not prev_btn_y_down)
                    or (start_down and not prev_btn_start_down)
                    or (rb_down and not prev_btn_rb_down)
                    or (lb_down and not prev_btn_lb_down)
                )
                if skip_btn:
                    mode = "select_mission"
                    intro_t = 0.0
                    if intro_video is not None:
                        intro_video.close(immediate=True)
                        intro_video = None
            elif mode == "select_mission":
                if menu_dir != 0 and menu_dir != prev_menu_dir:
                    selected_mission_index = (selected_mission_index + menu_dir) % len(mission_choices)
                    selected_mission_id = mission_choices[selected_mission_index][0]
                    apply_mission_preview()
                if (a_down and not prev_btn_a_down) or (start_down and not prev_btn_start_down):
                    mode = "select_chopper"
                    set_toast(f"Mission selected: {mission_choices[selected_mission_index][1]}")
            elif mode == "paused":
                # Start/B resumes.
                if (start_down and not prev_btn_start_down) or (b_down and not prev_btn_b_down):
                    mode = "playing"

                # Accessibility toggles.
                if x_down and not prev_btn_x_down:
                    toggle_particles()
                if y_down and not prev_btn_y_down:
                    toggle_flashes()
                if rb_down and not prev_btn_rb_down:
                    toggle_screenshake()

                # Up/Down selects section.
                if menu_vert != 0 and menu_vert != prev_menu_vert:
                    if menu_vert < 0:
                        if pause_focus == "restart_game":
                            pause_focus = "restart_mission"
                        elif pause_focus == "restart_mission":
                            pause_focus = "choppers"
                    else:
                        if pause_focus == "choppers":
                            pause_focus = "restart_mission"
                        elif pause_focus == "restart_mission":
                            pause_focus = "restart_game"

                # Left/Right changes chopper when focused.
                if pause_focus == "choppers" and menu_dir != 0 and menu_dir != prev_menu_dir:
                    selected_chopper_index = (selected_chopper_index + menu_dir) % len(chopper_choices)
                    selected_chopper_asset = chopper_choices[selected_chopper_index][0]
                    helicopter.skin_asset = selected_chopper_asset

                # A activates current focus.
                if a_down and not prev_btn_a_down:
                    if pause_focus == "restart_mission":
                        reset_game()
                        mode = "playing"
                    elif pause_focus == "restart_game":
                        mode = "select_mission"
                        pause_focus = "choppers"
                        set_toast("Restart Game")
                    else:
                        mode = "playing"
            else:
                # Start toggles pause while playing.
                if start_down and not prev_btn_start_down and not mission.ended:
                    mode = "paused"
                    pause_focus = "choppers"

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
            prev_btn_rb_down = rb_down
            prev_btn_lb_down = lb_down
            prev_menu_dir = menu_dir
            prev_menu_vert = menu_vert

        helicopter_input = HelicopterInput(
            tilt_left=(kb_tilt_left or gp_tilt_left) if mode == "playing" else False,
            tilt_right=(kb_tilt_right or gp_tilt_right) if mode == "playing" else False,
            lift_up=(kb_lift_up or gp_lift_up) if mode == "playing" else False,
            lift_down=(kb_lift_down or gp_lift_down) if mode == "playing" else False,
            brake=kb_brake if mode == "playing" else False,
        )

        # Fixed-timestep update.
        # Clamp accumulator to avoid spiral of death if the window stalls.
        if accumulator > 0.25:
            accumulator = 0.25

        while accumulator >= tick.dt:
            if mode == "playing":
                was_grounded = helicopter.grounded
                update_helicopter(helicopter, helicopter_input, tick.dt, physics, heli_settings, world_width=float(mission.world_width))
                if was_grounded and not helicopter.grounded:
                    audio.start_flying()
                if not was_grounded and helicopter.grounded:
                    hostage_crush_check_logged(mission, helicopter, helicopter.last_landing_vy, logger)
                    audio.stop_flying()
                update_mission(mission, helicopter, tick.dt, heli_settings, logger=logger)

                saved_delta = mission.stats.saved - prev_saved
                if saved_delta > 0:
                    audio.play_rescue()
                    prev_saved = mission.stats.saved

                boarded_now = boarded_count(mission)
                boarded_delta = boarded_now - prev_boarded
                if boarded_delta > 0:
                    audio.play_board()
                    prev_boarded = boarded_now

                open_compounds = sum(1 for c in mission.compounds if c.is_open)
                if open_compounds > prev_open_compounds:
                    audio.play_explosion_small()
                    prev_open_compounds = open_compounds

                tank_delta = mission.stats.tanks_destroyed - prev_tanks_destroyed
                if tank_delta > 0:
                    audio.play_explosion_big()
                    prev_tanks_destroyed = mission.stats.tanks_destroyed

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

        if mode == "intro":
            intro_t += frame_dt
            if intro_video is not None:
                intro_video.update(frame_dt)
                if intro_video.done:
                    mode = "select_mission"
                    intro_t = 0.0
                    intro_video.close()
                    intro_video = None
            if intro_t >= intro_seconds:
                mode = "select_mission"
                intro_t = 0.0
                if intro_video is not None:
                    intro_video.close()
                    intro_video = None

        # Visual-only sky particles.
        if particles_enabled and mode != "intro":
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
        if mode == "intro":
            if intro_video is not None:
                intro_video.draw(screen)
                draw_skip_overlay(screen, text=skip_hint)
            else:
                draw_intro_cutscene(screen, intro_t, show_skip=True, skip_text=skip_hint)
        else:
            # Background above the horizon.
            draw_sky(
                screen,
                heli_settings.ground_y,
                bg_asset=getattr(mission, "bg_asset", "mission1-bg.jpg"),
                dt=frame_dt,
                enable_fade=(mode == "select_mission"),
            )
            if particles_enabled:
                sky_smoke.draw(screen, horizon_y=int(heli_settings.ground_y))
            draw_ground(screen, heli_settings.ground_y)
            draw_mission(screen, mission, camera_x=camera_x, enable_particles=particles_enabled)
            draw_helicopter(screen, helicopter, camera_x=camera_x)
            if mode == "playing":
                draw_hud(screen, mission, helicopter)
            elif mode == "select_mission":
                draw_mission_select_overlay(screen, mission_choices, selected_mission_index)
            elif mode == "select_chopper":
                draw_chopper_select_overlay(screen, chopper_choices, selected_chopper_index)
            else:
                draw_chopper_select_overlay(
                    screen,
                    chopper_choices,
                    selected_chopper_index,
                    title="Paused",
                    hint="Up/Down choose section • Left/Right chopper • Start/B resume • A select • X particles • Y flashes • RB shake",
                    show_restart=True,
                    restart_selected=(pause_focus == "restart_mission"),
                    show_restart_game=True,
                    restart_game_selected=(pause_focus == "restart_game"),
                )
            if toast_message:
                draw_toast(screen, toast_message)

        if debug.show_overlay and mode == "playing":
            overlay.draw(screen, helicopter, mission, clock.get_fps())

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    run()
