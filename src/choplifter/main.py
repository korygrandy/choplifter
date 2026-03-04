
from __future__ import annotations
from .app.keyboard_events import handle_keyboard_event

from pathlib import Path
import random
import pygame

from .audio import AudioBank
from .accessibility import load_accessibility
from .controls import load_controls, matches_key, pressed
from .debug_overlay import DebugOverlay
from .game_logging import create_session_logger
from .helicopter import Facing, Helicopter, HelicopterInput, update_helicopter
from . import haptics
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
    draw_damage_flash,
    draw_flares,
    draw_helicopter_damage_fx,
    draw_impact_sparks,
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
from .physics_config import load_physics_settings
from .math2d import Vec2
from .app.cutscenes import (
    init_intro_cutscene,
    draw_intro,
    update_intro,
    skip_intro,
    start_mission_cutscene,
    draw_mission_cutscene,
    update_mission_cutscene,
    skip_mission_cutscene,
)
import src.choplifter.app.cutscene_config as cutscene_config
from .app.state import CutsceneState, IntroCutsceneState, MissionCutsceneState
from .app.input import get_active_joystick, read_gamepad
from .app.feedback import ScreenShakeState, consume_mission_feedback, rough_landing_feedback, update_screenshake_target
from .app.flares import FlareState, reset_flares, try_start_flare_salvo, update_flares
from .app.gamepads import init_connected_joysticks, handle_joy_device_added, handle_joy_device_removed
from .app.toast import ToastState
from .app.session import create_mission_and_helicopter
from .app.flow import apply_mission_preview, reset_game
from .app.menu_helpers import cycle_index, move_pause_focus
from .app.stats_snapshot import MissionStatsSnapshot, take_mission_stats_snapshot
from .app.accessibility_toggles import toggle_particles, toggle_flashes, toggle_screenshake
from .app.doors import toggle_doors_with_logging


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
    haptics.set_enabled(accessibility.rumble_enabled)
    audio = AudioBank.try_create()
    logger.info("Controls: SPACE fire | F flare | E doors (grounded) | TAB facing | R reverse | F1 debug")
    logger.info("Rescue: open compound, land near hostages, E doors to load; land at base and E to unload")
    logger.info("Gamepad: Left stick tilt | Triggers lift | A doors | X fire | Y reverse | B flare | Back facing | D-pad optional")

    # Gamepad detection (connect/disconnect notifications).
    pygame.joystick.init()
    joysticks: dict[int, pygame.joystick.Joystick] = {}

    # Cinematic feedback (screenshake + audio duck).
    screenshake = ScreenShakeState()
    toast = ToastState()

    prev_btn_a_down = False
    prev_btn_b_down = False
    prev_btn_x_down = False
    prev_btn_y_down = False
    prev_btn_start_down = False
    prev_btn_rb_down = False
    prev_btn_lb_down = False
    prev_btn_back_down = False

    def set_toast(message: str) -> None:
        toast.set(message)

    joysticks = init_connected_joysticks(logger=logger, set_toast=set_toast)

    particles_enabled = accessibility.particles_enabled
    flashes_enabled = accessibility.flashes_enabled
    screenshake_enabled = accessibility.screenshake_enabled


    flags = 0
    if window.vsync:
        # VSYNC is honored on some platforms/drivers.
        flags |= pygame.SCALED

    screen = pygame.display.set_mode((window.width, window.height), flags)
    pygame.display.set_caption(window.title)

    # Optional video intro asset (falls back to the in-engine title card if missing/unavailable).
    module_dir = Path(__file__).resolve().parent
    assets_dir = module_dir / "assets"
    cutscenes = CutsceneState(intro=IntroCutsceneState(), mission=MissionCutsceneState())
    init_intro_cutscene(cutscenes.intro, assets_dir=assets_dir, logger=logger)

    # Hostage rescue cutscene config/lookup now in app.cutscene_config

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
    mode: str = "intro"  # intro | select_mission | select_chopper | playing | paused | cutscene
    prev_menu_dir = 0
    prev_menu_vert = 0
    pause_focus: str = "choppers"  # choppers | restart_mission | restart_game | mute
    muted = False

    flares = FlareState()

    mission, helicopter = create_mission_and_helicopter(
        heli_settings=heli_settings,
        mission_id=selected_mission_id,
        chopper_asset=selected_chopper_asset,
    )

    prev_stats: MissionStatsSnapshot = take_mission_stats_snapshot(mission, boarded_count=boarded_count)

    def apply_mission_preview_wrapper() -> None:
        nonlocal helicopter, mission, accumulator, prev_stats
        mission, helicopter, accumulator, prev_stats = apply_mission_preview(
            create_mission_and_helicopter,
            heli_settings,
            selected_mission_id,
            selected_chopper_asset,
            take_mission_stats_snapshot,
            boarded_count,
            sky_smoke,
            audio,
            set_toast,
            mission,
        )

    def reset_game_wrapper() -> None:
        nonlocal helicopter, mission, accumulator, prev_stats
        nonlocal prev_btn_a_down, prev_btn_b_down, prev_btn_x_down, prev_btn_y_down, prev_btn_start_down
        nonlocal prev_btn_rb_down, prev_btn_lb_down, prev_btn_back_down
        mission, helicopter, accumulator, prev_stats = reset_game(
            create_mission_and_helicopter,
            heli_settings,
            selected_mission_id,
            selected_chopper_asset,
            take_mission_stats_snapshot,
            boarded_count,
            sky_smoke,
            audio,
            reset_flares,
            logger,
            flares,
        )
        prev_btn_a_down = False
        prev_btn_b_down = False
        prev_btn_x_down = False
        prev_btn_y_down = False
        prev_btn_start_down = False
        prev_btn_rb_down = False
        prev_btn_lb_down = False
        prev_btn_back_down = False

    def toggle_particles_wrapper() -> None:
        nonlocal particles_enabled
        particles_enabled = toggle_particles(particles_enabled, set_toast)

    def toggle_flashes_wrapper() -> None:
        nonlocal flashes_enabled
        flashes_enabled = toggle_flashes(flashes_enabled, set_toast)

    def toggle_screenshake_wrapper() -> None:
        nonlocal screenshake_enabled
        screenshake_enabled = toggle_screenshake(screenshake_enabled, set_toast)

    running = True
    accumulator = 0.0

    while running:
        frame_dt = clock.tick(120) / 1000.0
        accumulator += frame_dt

        skip_hint = (
            "Enter/Space or A/Start: Skip" if get_active_joystick(joysticks) is not None else "Enter/Space: Skip"
        )

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.JOYDEVICEADDED:
                handle_joy_device_added(event.device_index, joysticks=joysticks, logger=logger, set_toast=set_toast)
            elif event.type == pygame.JOYDEVICEREMOVED:
                handle_joy_device_removed(event.instance_id, joysticks=joysticks, logger=logger, set_toast=set_toast)
                prev_btn_a_down = False
                prev_btn_b_down = False
                prev_btn_x_down = False
                prev_btn_y_down = False
                prev_btn_back_down = False
            elif event.type == pygame.KEYDOWN:
                (
                    mode,
                    pause_focus,
                    quit_flag,
                    selected_mission_index,
                    selected_mission_id,
                    selected_chopper_index,
                    selected_chopper_asset,
                ) = handle_keyboard_event(
                    event,
                    mode=mode,
                    controls=controls,
                    mission=mission,
                    helicopter=helicopter,
                    audio=audio,
                    logger=logger,
                    chopper_choices=chopper_choices,
                    mission_choices=mission_choices,
                    pause_focus=pause_focus,
                    muted=muted,
                    set_toast=set_toast,
                    reset_game=reset_game_wrapper,
                    apply_mission_preview=apply_mission_preview_wrapper,
                    skip_intro=lambda: skip_intro(cutscenes.intro),
                    skip_mission_cutscene=lambda: skip_mission_cutscene(cutscenes.mission),
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
                    selected_mission_index=selected_mission_index,
                    selected_mission_id=selected_mission_id,
                    selected_chopper_index=selected_chopper_index,
                    selected_chopper_asset=selected_chopper_asset,
                )
                if quit_flag:
                    running = False

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

        active_js = get_active_joystick(joysticks)
        haptics.set_active_joystick(active_js)
        if active_js is not None:
            gp = read_gamepad(
                active_js,
                deadzone=float(accessibility.gamepad_deadzone),
                trigger_threshold01=float(accessibility.trigger_threshold),
            )
            gp_tilt_left = gp.tilt_left
            gp_tilt_right = gp.tilt_right
            gp_lift_up = gp.lift_up
            gp_lift_down = gp.lift_down
            menu_dir = gp.menu_dir
            menu_vert = gp.menu_vert

            a_down = gp.a_down
            b_down = gp.b_down
            x_down = gp.x_down
            y_down = gp.y_down
            start_down = gp.start_down
            rb_down = gp.rb_down
            lb_down = gp.lb_down
            back_down = gp.back_down

            # Debug overlay toggle (gamepad).
            if lb_down and not prev_btn_lb_down:
                debug = DebugSettings(show_overlay=not debug.show_overlay)
                set_toast(f"Debug overlay: {'ON' if debug.show_overlay else 'OFF'}")

            if mode == "select_chopper":
                if menu_dir != 0 and menu_dir != prev_menu_dir:
                    selected_chopper_index = cycle_index(selected_chopper_index, menu_dir, len(chopper_choices))
                    selected_chopper_asset = chopper_choices[selected_chopper_index][0]
                    audio.play_menu_select()
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
                    skip_intro(cutscenes.intro)
            elif mode == "cutscene":
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
                    mode = "playing"
                    skip_mission_cutscene(cutscenes.mission)
            elif mode == "select_mission":
                if menu_dir != 0 and menu_dir != prev_menu_dir:
                    selected_mission_index = cycle_index(selected_mission_index, menu_dir, len(mission_choices))
                    selected_mission_id = mission_choices[selected_mission_index][0]
                    audio.play_menu_select()
                    apply_mission_preview()
                if (a_down and not prev_btn_a_down) or (start_down and not prev_btn_start_down):
                    mode = "select_chopper"
                    set_toast(f"Mission selected: {mission_choices[selected_mission_index][1]}")
            elif mode == "paused":
                # Start/B resumes.
                if (start_down and not prev_btn_start_down) or (b_down and not prev_btn_b_down):
                    mode = "playing"
                    audio.play_pause_toggle()
                    audio.set_pause_menu_active(False)

                # Accessibility toggles.
                if x_down and not prev_btn_x_down:
                    toggle_particles_wrapper()
                if y_down and not prev_btn_y_down:
                    toggle_flashes_wrapper()
                if rb_down and not prev_btn_rb_down:
                    toggle_screenshake_wrapper()

                # Up/Down selects section.
                if menu_vert != 0 and menu_vert != prev_menu_vert:
                    prev_pause_focus = pause_focus
                    pause_focus = move_pause_focus(pause_focus, -1 if menu_vert < 0 else 1)
                    if pause_focus != prev_pause_focus:
                        audio.play_menu_select()

                # Left/Right changes chopper when focused.
                if pause_focus == "choppers" and menu_dir != 0 and menu_dir != prev_menu_dir:
                    selected_chopper_index = cycle_index(selected_chopper_index, menu_dir, len(chopper_choices))
                    selected_chopper_asset = chopper_choices[selected_chopper_index][0]
                    helicopter.skin_asset = selected_chopper_asset
                    audio.play_menu_select()

                # A activates current focus.
                if a_down and not prev_btn_a_down:
                    if pause_focus == "restart_mission":
                        reset_game()
                        mode = "playing"
                        audio.play_pause_toggle()
                        audio.set_pause_menu_active(False)
                    elif pause_focus == "restart_game":
                        mode = "select_mission"
                        pause_focus = "choppers"
                        set_toast("Restart Game")
                        audio.play_pause_toggle()
                        audio.set_pause_menu_active(False)
                    elif pause_focus == "mute":
                        muted = not muted
                        audio.set_muted(muted)
                    else:
                        mode = "playing"
                        audio.play_pause_toggle()
                        audio.set_pause_menu_active(False)
            else:
                # Start toggles pause while playing.
                if start_down and not prev_btn_start_down:
                    if not getattr(mission, "crash_active", False):
                        mode = "paused"
                        pause_focus = "choppers"
                        audio.play_pause_toggle()
                        audio.set_pause_menu_active(True)

                if b_down and not prev_btn_b_down:
                    try_start_flare_salvo(flares, mission=mission, helicopter=helicopter, audio=audio)

                if a_down and not prev_btn_a_down:
                    if not getattr(mission, "crash_active", False):
                        toggle_doors_with_logging(helicopter, mission, audio, logger, boarded_count)
                if y_down and not prev_btn_y_down:
                    if not getattr(mission, "crash_active", False):
                        helicopter.reverse_flip()
                if back_down and not prev_btn_back_down:
                    if not getattr(mission, "crash_active", False):
                        helicopter.cycle_facing()
                if x_down and not prev_btn_x_down:
                    if not getattr(mission, "crash_active", False):
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
            prev_btn_back_down = back_down
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
                update_flares(flares, mission=mission, helicopter=helicopter, dt=tick.dt)
                if getattr(mission, "crash_active", False):
                    # Crash animation drives the helicopter pose; stop the flight loop.
                    audio.stop_flying()
                else:
                    was_grounded = helicopter.grounded
                    # If the helicopter starts airborne, there may be no ground->air transition
                    # to kick off the flying loop. Start it as soon as the player applies lift.
                    if (helicopter_input.lift_up or helicopter_input.lift_down) and not helicopter.grounded:
                        audio.start_flying()

                    update_helicopter(
                        helicopter,
                        helicopter_input,
                        tick.dt,
                        physics,
                        heli_settings,
                        world_width=float(mission.world_width),
                        invulnerable=(mission.invuln_seconds > 0.0 or mission.ended),
                    )
                    if was_grounded and not helicopter.grounded:
                        audio.start_flying()
                    if not was_grounded and helicopter.grounded:
                        hostage_crush_check_logged(
                            mission,
                            helicopter,
                            helicopter.last_landing_vy,
                            safe_landing_vy=physics.safe_landing_vy,
                            logger=logger,
                        )

                        # Cinematic feedback on rough landings.
                        rough_landing_feedback(
                            state=screenshake,
                            landing_vy=float(helicopter.last_landing_vy),
                            safe_landing_vy=float(physics.safe_landing_vy),
                            invuln_seconds=float(mission.invuln_seconds),
                            ended=bool(mission.ended),
                            audio=audio,
                            screenshake_enabled=screenshake_enabled,
                        )
                        audio.stop_flying()
                update_mission(mission, helicopter, tick.dt, heli_settings, logger=logger)

                # Consume cinematic feedback impulses produced by mission damage events.
                consume_mission_feedback(
                    state=screenshake,
                    mission=mission,
                    audio=audio,
                    screenshake_enabled=screenshake_enabled,
                )

                helicopter.damage_flash_seconds = max(0.0, helicopter.damage_flash_seconds - tick.dt)

                saved_delta = mission.stats.saved - prev_stats.saved
                if saved_delta > 0:
                    audio.play_rescue()
                    prev_stats.saved = mission.stats.saved

                boarded_now = boarded_count(mission)
                boarded_delta = boarded_now - prev_stats.boarded
                if boarded_delta > 0:
                    audio.play_board()
                    prev_stats.boarded = boarded_now

                # One-shot hostage rescue cutscene when the first 16 hostages are onboard.
                if (
                    boarded_now >= cutscene_config.HOSTAGE_RESCUE_CUTSCENE_THRESHOLD
                    and cutscene_config.HOSTAGE_RESCUE_CUTSCENE_EVENT_ID not in mission.cutscenes_played
                ):
                    mission.cutscenes_played.add(cutscene_config.HOSTAGE_RESCUE_CUTSCENE_EVENT_ID)
                    cutscene_path = cutscene_config.get_hostage_rescue_cutscene_path(getattr(mission, "mission_id", ""))
                    if start_mission_cutscene(
                        cutscenes.mission,
                        cutscene_path=cutscene_path,
                        logger=logger,
                        event_id=cutscene_config.HOSTAGE_RESCUE_CUTSCENE_EVENT_ID,
                        mission_id=str(getattr(mission, "mission_id", "")),
                    ):
                        mode = "cutscene"
                        audio.stop_flying()

                open_compounds = sum(1 for c in mission.compounds if c.is_open)
                if open_compounds > prev_stats.open_compounds:
                    audio.play_explosion_small()
                    prev_stats.open_compounds = open_compounds

                tank_delta = mission.stats.tanks_destroyed - prev_stats.tanks_destroyed
                if tank_delta > 0:
                    audio.play_explosion_big()
                    prev_stats.tanks_destroyed = mission.stats.tanks_destroyed

                artillery_delta = mission.stats.artillery_fired - prev_stats.artillery_fired
                if artillery_delta > 0:
                    for _ in range(artillery_delta):
                        audio.play_artillery_shot()
                    prev_stats.artillery_fired = mission.stats.artillery_fired

                artillery_hit_delta = mission.stats.artillery_hits - prev_stats.artillery_hits
                if artillery_hit_delta > 0:
                    for _ in range(artillery_hit_delta):
                        audio.play_artillery_impact()
                    prev_stats.artillery_hits = mission.stats.artillery_hits

                jets_entered_delta = mission.stats.jets_entered - prev_stats.jets_entered
                if jets_entered_delta > 0:
                    audio.play_jet_flyby()
                    prev_stats.jets_entered = mission.stats.jets_entered

                mine_delta = mission.stats.mines_detonated - prev_stats.mines_detonated
                if mine_delta > 0:
                    for _ in range(mine_delta):
                        audio.play_mine_explosion()
                    prev_stats.mines_detonated = mission.stats.mines_detonated

                if mission.crashes != prev_stats.crashes:
                    if mission.ended:
                        set_toast(f"THE END: {mission.end_reason} (Enter=Retry, Esc/Start=Menu)")
                    else:
                        set_toast(f"CRASH {mission.crashes}/3 — respawn (invuln {mission.invuln_seconds:0.1f}s)")
                        audio.play_crash()
                    prev_stats.crashes = mission.crashes

                lost_delta = mission.stats.lost_in_transit - prev_stats.lost_in_transit
                if lost_delta > 0:
                    set_toast(f"Passengers lost in crash: +{lost_delta}")
                    prev_stats.lost_in_transit = mission.stats.lost_in_transit

            accumulator -= tick.dt

        toast.update(frame_dt)

        if mode == "intro":
            if update_intro(cutscenes.intro, frame_dt):
                mode = "select_mission"

        if mode == "cutscene":
            if update_mission_cutscene(cutscenes.mission, frame_dt):
                mode = "playing"

        # Visual-only sky particles.
        if particles_enabled and mode not in ("intro", "cutscene"):
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

        # Update audio (ducking is applied via bus volumes).
        audio.update(frame_dt)

        # Screenshake offsets (render-time only; affects the whole frame).
        target, shake_x, shake_y = update_screenshake_target(
            state=screenshake,
            frame_dt=frame_dt,
            enabled=screenshake_enabled,
            mode=mode,
            screen=screen,
        )

        # Render.
        if mode == "intro":
            draw_intro(cutscenes.intro, target, skip_hint=skip_hint)
        elif mode == "cutscene":
            draw_mission_cutscene(cutscenes.mission, target, skip_hint=skip_hint)
        else:
            # Background above the horizon.
            draw_sky(
                target,
                heli_settings.ground_y,
                bg_asset=getattr(mission, "bg_asset", "mission1-bg.jpg"),
                dt=frame_dt,
                enable_fade=(mode == "select_mission"),
            )
            if particles_enabled:
                sky_smoke.draw(target, horizon_y=int(heli_settings.ground_y))
            draw_ground(target, heli_settings.ground_y)
            draw_mission(target, mission, camera_x=camera_x, enable_particles=particles_enabled)
            draw_flares(target, mission, camera_x=camera_x, enable_particles=particles_enabled)
            draw_helicopter_damage_fx(target, mission, camera_x=camera_x, enable_particles=particles_enabled)
            draw_helicopter(target, helicopter, camera_x=camera_x, boarded=boarded_count(mission))
            draw_impact_sparks(target, mission, camera_x=camera_x, enable_particles=particles_enabled)
            if mode == "playing":
                draw_hud(target, mission, helicopter)
            elif mode == "select_mission":
                draw_mission_select_overlay(target, mission_choices, selected_mission_index)
            elif mode == "select_chopper":
                draw_chopper_select_overlay(target, chopper_choices, selected_chopper_index)
            else:
                draw_chopper_select_overlay(
                    target,
                    chopper_choices,
                    selected_chopper_index,
                    title="Paused",
                    hint="Up/Down choose section • Left/Right chopper • Start/B resume • A select • X particles • Y flashes • RB shake",
                    show_mute=True,
                    mute_selected=(pause_focus == "mute"),
                    muted=muted,
                    show_restart=True,
                    restart_selected=(pause_focus == "restart_mission"),
                    show_restart_game=True,
                    restart_game_selected=(pause_focus == "restart_game"),
                )
            if toast.message:
                draw_toast(target, toast.message)

            if mode == "playing" and flashes_enabled:
                draw_damage_flash(target, helicopter)

        if debug.show_overlay and mode == "playing":
            overlay.draw(target, helicopter, mission, clock.get_fps())

        if target is not screen:
            screen.fill((0, 0, 0))
            screen.blit(target, (shake_x, shake_y))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    run()
