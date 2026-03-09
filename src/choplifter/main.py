from .app.keyboard_events import handle_keyboard_event

from .game_types import EnemyKind
from .barak_mrad import BARAK_STATE_DEPLOY

from pathlib import Path
import random
import pygame

from .audio import AudioBank
from .audio_extra import play_satellite_reallocating
from .accessibility import load_accessibility
from .controls import load_controls, matches_key, pressed
from .debug_overlay import DebugOverlay
from .game_logging import create_session_logger
from .helicopter import Facing, Helicopter, update_helicopter
from . import haptics
from .mission import update_mission
from .mission_configs import get_mission_config_by_id
from .mission_helpers import boarded_count
from .mission_hostages import hostage_crush_check_logged
from .mission_player_fire import spawn_projectile_from_helicopter_logged
from .mission_state import MissionState
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
# --- Airport Special Ops mission modules ---
from .bus_ai import *
from .hostage_logic import *
from .enemy_spawns import *
from .mission_tech import *
from .vehicle_assets import *
from .objective_manager import *
from .cutscene_manager import *
from .settings import DebugSettings, FixedTickSettings, HelicopterSettings, PhysicsSettings, WindowSettings
from .sky_smoke import SkySmokeSystem
from .fx.rain import RainSystem
from .fx.fog import FogSystem
from .fx.dust_storm import DustStormSystem
from .fx.wind_dust_clouds import WindBlownDustCloudSystem
from .fx.lightning import LightningSystem
from .fx.storm_clouds import StormCloudSystem
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
from .app.state import CutsceneState, IntroCutsceneState, MissionCutsceneState
from .app.input import get_active_joystick, read_gamepad
from .app.feedback import ScreenShakeState, rough_landing_feedback, update_screenshake_target
from .app.flares import FlareState, reset_flares, try_start_flare_salvo, update_flares
from .app.gamepads import init_connected_joysticks, handle_joy_device_added, handle_joy_device_removed
from .app.toast import ToastState
from .app.ui_constants import MISSION_END_RETURN_DELAY_S, PAUSED_MENU_HINT
from .app.session import create_mission_and_helicopter
from .app.flow import apply_mission_preview, reset_game
from .app.stats_snapshot import MissionStatsSnapshot, take_mission_stats_snapshot
from .app.accessibility_toggles import toggle_particles, toggle_flashes, toggle_screenshake
from .app.doors import toggle_doors_with_logging
from .app.runtime_state import GameRuntimeState
from .app.objective_overlay import get_mission_objective_overlay_duration
from .app.game_update import (
    build_helicopter_input,
    run_playing_fixed_step,
)
from .app.mode_update import resolve_post_frame_mode_transitions
from .app.frame_update import update_weather_effects, compute_camera_x
from .app.frame_render import draw_mode_overlays, draw_playing_hud_and_overlays, draw_weather_particles, render_frame_post_fx
from .app.event_loop import (
    handle_debug_weather_keydown,
    handle_gamepad_pause_button,
    handle_mission_end_gamepad_navigation,
    handle_mission_end_keyboard_navigation,
    handle_pause_quit_confirm_keydown,
    resolve_paused_mode_inputs,
    handle_select_chopper_gamepad,
    handle_select_mission_gamepad,
    should_skip_on_gamepad_buttons,
)


def draw_debug_overlay(target):
    font = pygame.font.SysFont(None, 32)
    overlay = font.render("DEBUG MODE", True, (255, 0, 0))
    target.blit(overlay, (12, 12))


def run() -> None:
    vip_kia_overlay_timer = 0.0
    vip_kia_overlay_shown = False
    city_objective_overlay_timer = 0.0
    from .render.world import toggle_thermal_mode

    def set_debug_weather_mode(mode):
        nonlocal weather_mode, weather_timer, weather_duration
        weather_mode = mode
        weather_timer = 0.0
        weather_duration = 9999.0  # Prevent auto-cycling

    debug_mode = False
    debug_weather_modes = ["clear", "rain", "fog", "dust", "storm"]
    debug_weather_index = 0
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
    accessibility_mode = getattr(accessibility, 'mode', None)
    accessibility_toggles = getattr(accessibility, 'toggles', None)
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

    # --- Weather/particle systems ---
    rain = RainSystem()
    fog = FogSystem()
    dust = DustStormSystem()
    lightning = LightningSystem(area_width=window.width, area_height=window.height)
    storm_clouds = StormCloudSystem(window.width, window.height)

    weather_mode = random.choice(["clear", "rain", "fog", "dust", "storm"])
    weather_timer = 0.0
    weather_duration = random.uniform(18, 40)
    hud_disabled_timer = 0.0

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
    mode: str = "intro"  # intro | select_mission | select_chopper | playing | paused | cutscene | mission_end
    runtime = GameRuntimeState()
    just_paused_with_start = False
    prev_menu_dir = 0
    prev_menu_vert = 0

    flares = FlareState()





    # --- Mission initialization ---
    mission, helicopter = create_mission_and_helicopter(
        heli_settings=heli_settings,
        mission_id=selected_mission_id,
        chopper_asset=selected_chopper_asset,
    )
    mission.audio = audio
    campaign_sentiment = float(getattr(mission, "sentiment", 50.0))

    prev_stats: MissionStatsSnapshot = take_mission_stats_snapshot(mission, boarded_count=boarded_count)

    # --- Airport Special Ops mission: placeholder entity state ---
    airport_bus_state = None
    airport_hostage_state = None
    airport_enemy_state = None
    airport_tech_state = None
    airport_objective_state = None
    airport_cutscene_state = None
    airport_meal_truck_state = None

    if selected_mission_id == "airport":
        airport_bus_state = create_bus_state(start_x=2200, ground_y=heli_settings.ground_y)
        airport_hostage_state = create_airport_hostage_state(total_hostages=16, pickup_x=1232.0)
        airport_enemy_state = create_airport_enemy_state()
        airport_tech_state = create_mission_tech_state()
        airport_objective_state = create_airport_objective_state(hostage_deadline_s=120.0)
        airport_cutscene_state = create_airport_cutscene_state()
        airport_meal_truck_state = create_airport_meal_truck_state(
            start_x=1120.0,
            ground_y=heli_settings.ground_y,
            plane_lz_x=1232.0,
        )

    def apply_mission_preview_wrapper() -> None:
        nonlocal helicopter, mission, accumulator, prev_stats, campaign_sentiment
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
        mission.sentiment = float(campaign_sentiment)
        mission.audio = audio
        runtime.mission_end_return_seconds = 0.0
        audio.log_audio_channel_snapshot(tag="mission_preview", logger=logger)

    def reset_game_wrapper() -> None:
        nonlocal helicopter, mission, accumulator, prev_stats, campaign_sentiment
        nonlocal prev_btn_a_down, prev_btn_b_down, prev_btn_x_down, prev_btn_y_down, prev_btn_start_down
        nonlocal prev_btn_rb_down, prev_btn_lb_down, prev_btn_back_down
        nonlocal city_objective_overlay_timer, airport_bus_state, airport_hostage_state, airport_enemy_state, airport_tech_state, airport_objective_state, airport_meal_truck_state, airport_cutscene_state
        # Stop chopper warning beeps on game reset
        audio.stop_chopper_warning_beeps()
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
        runtime.mission_end_return_seconds = 0.0
        mission.sentiment = float(campaign_sentiment)
        mission.audio = audio
        audio.log_audio_channel_snapshot(tag="restart", logger=logger)
        prev_btn_a_down = False
        prev_btn_b_down = False
        prev_btn_x_down = False
        prev_btn_y_down = False
        prev_btn_start_down = False
        prev_btn_rb_down = False
        prev_btn_lb_down = False
        prev_btn_back_down = False
        city_objective_overlay_timer = get_mission_objective_overlay_duration(mission_id=selected_mission_id)
        
        # Initialize mission-specific state
        if selected_mission_id == "airport":
            airport_bus_state = create_bus_state(start_x=2200, ground_y=heli_settings.ground_y)
            airport_hostage_state = create_airport_hostage_state(total_hostages=16, pickup_x=1232.0)
            airport_enemy_state = create_airport_enemy_state()
            airport_tech_state = create_mission_tech_state()
            airport_objective_state = create_airport_objective_state(hostage_deadline_s=120.0)
            airport_cutscene_state = create_airport_cutscene_state()
            airport_meal_truck_state = create_airport_meal_truck_state(
                start_x=1120.0,
                ground_y=heli_settings.ground_y,
                plane_lz_x=1232.0,
            )

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

    # Track doors state before cutscene
    doors_open_before_cutscene = False
    
    # Track previous mode to detect transitions
    prev_loop_mode = mode

    while running:
        frame_dt = clock.tick(120) / 1000.0
        accumulator += frame_dt

        # --- VIP KIA overlay logic ---
        if hasattr(mission, "hostages"):
            vip_hostage = next((h for h in mission.hostages if getattr(h, "is_vip", False)), None)
            if vip_hostage:
                if vip_hostage.state.name != "KIA":
                    # Reset overlay flag if VIP is alive again (new mission, respawn, etc.)
                    vip_kia_overlay_shown = False
                elif (
                    vip_hostage.state.name == "KIA"
                    and vip_kia_overlay_timer <= 0.0
                    and not vip_kia_overlay_shown
                ):
                    vip_kia_overlay_timer = 3.0  # Show for 3 seconds
                    vip_kia_overlay_shown = True

        # Weather cycling (optional: cycle weather every N seconds)
        if not debug_mode:
            weather_timer += frame_dt
            if weather_timer > weather_duration:
                weather_mode = random.choice(["clear", "rain", "fog", "dust", "storm"])
                weather_timer = 0.0
                weather_duration = random.uniform(18, 40)

        # Update weather systems
        if weather_mode == "rain":
            rain.update(frame_dt, area_width=window.width, area_height=window.height)
        if weather_mode == "fog":
            fog.update(frame_dt, area_width=window.width, area_height=window.height)
        if weather_mode == "dust":
            dust.update(frame_dt, heli_pos=helicopter.pos, heli_vel=helicopter.vel, ground_y=heli_settings.ground_y)
        if weather_mode == "storm":
            rain.update(frame_dt, area_width=window.width, area_height=window.height)
            fog.update(frame_dt, area_width=window.width, area_height=window.height)
            # Lightning logic
            hit_player, strike_x = lightning.update(frame_dt, helicopter_x=helicopter.pos.x, helicopter_y=helicopter.pos.y)
            if hit_player:
                hud_disabled_timer = 3.0
                set_toast("⚡ ELECTRONIC WARFARE: HUD/Targeting disabled!")
        if hud_disabled_timer > 0.0:
            hud_disabled_timer -= frame_dt

        skip_hint = (
            "Enter/Space or A/Start: Skip" if get_active_joystick(joysticks) is not None else "Enter/Space: Skip"
        )

        for event in pygame.event.get():
            # Toggle thermal mode with T key
            if event.type == pygame.KEYDOWN and event.key == pygame.K_t:
                toggle_thermal_mode()
                set_toast("Thermal mode toggled (T)")
            # Debug: trigger BARAK missile launch sequence with F9
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F9:
                for e in mission.enemies:
                    if getattr(e, "kind", None) == EnemyKind.BARAK_MRAD and e.alive:
                        # Stop vehicle
                        e.vel.x = 0.0
                        # Begin missile silo deploy sequence
                        e.mrad_state = BARAK_STATE_DEPLOY
                        e.mrad_state_seconds = 0.0
                        e.mrad_reload_seconds = 0.0
                        e.launcher_angle = 0.0  # Start horizontal
                        e.launcher_ext_progress = 0.0  # Start retracted
                        e.missile_fired = False  # Allow re-trigger
                        if hasattr(mission, "audio") and mission.audio is not None:
                            if hasattr(mission.audio, "play_barak_mrad_deploy"):
                                mission.audio.play_barak_mrad_deploy()
                        set_toast("DEBUG: BARAK missile launch sequence triggered (F9)")
                        break
            elif event.type == pygame.QUIT:
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
                handled_mission_end, next_mode = handle_mission_end_keyboard_navigation(
                    key=event.key,
                    mode=mode,
                    mission_ended=bool(mission.ended),
                    set_toast=set_toast,
                )
                if handled_mission_end:
                    mode = next_mode
                    continue

                handled_quit_confirm, keep_running, quit_confirm = handle_pause_quit_confirm_keydown(
                    mode=mode,
                    quit_confirm=runtime.quit_confirm,
                    key=event.key,
                )
                if handled_quit_confirm:
                    if not keep_running:
                        logger.info(f"PAUSE MENU: Keyboard confirm quit (Enter/Space) on quit_confirm, exiting game")
                        running = False
                    else:
                        logger.info(f"PAUSE MENU: Keyboard cancel quit (Escape) on quit_confirm, returning to pause menu")
                    runtime.quit_confirm = quit_confirm
                    continue
                handled_debug_key, debug_mode, debug_weather_index, debug_toast, selected_weather_mode = handle_debug_weather_keydown(
                    key=event.key,
                    debug_mode=debug_mode,
                    debug_weather_index=debug_weather_index,
                    debug_weather_modes=debug_weather_modes,
                )
                if handled_debug_key:
                    if selected_weather_mode is not None:
                        set_debug_weather_mode(selected_weather_mode)
                    if debug_toast:
                        set_toast(debug_toast)
                (
                    mode,
                    runtime.pause_focus,
                    runtime.muted,
                    selected_mission_index,
                    selected_mission_id,
                    selected_chopper_index,
                    selected_chopper_asset,
                    debug,
                    runtime.quit_confirm
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
                    pause_focus=runtime.pause_focus,
                    muted=runtime.muted,
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
                    debug=debug,
                    quit_confirm=runtime.quit_confirm
                )
            elif event.type == pygame.JOYBUTTONDOWN:
                if logger:
                    logger.debug("GAMEPAD BUTTONDOWN: button=%s", event.button)
                # Map gamepad buttons to actions
                # X (2): fire, B (1): flare, A (0): doors, Y (3): reverse, Back (6): facing, Start (7): pause/restart
                handled_mission_end, next_mode = handle_mission_end_gamepad_navigation(
                    button=event.button,
                    mode=mode,
                    set_toast=set_toast,
                )
                if handled_mission_end:
                    mode = next_mode
                elif mode == "playing":
                    if event.button == 2:  # X button: fire
                        if logger:
                            logger.debug("Fire button pressed (button=2) in playing mode")
                        if not getattr(mission, "crash_active", False):
                            spawn_projectile_from_helicopter_logged(mission, helicopter, logger)
                            if helicopter.facing is Facing.FORWARD:
                                audio.play_bomb()
                            else:
                                audio.play_shoot()
                    elif event.button == 1:  # B button: flare
                        if logger:
                            logger.debug("Flare button pressed (button=1) in playing mode")
                        try_start_flare_salvo(flares, mission=mission, helicopter=helicopter, audio=audio)
                    elif event.button == 0:  # A button: doors
                        if not getattr(mission, "crash_active", False):
                            toggle_doors_with_logging(helicopter, mission, audio, logger, boarded_count, set_toast)
                    elif event.button == 3:  # Y button: reverse
                        if not getattr(mission, "crash_active", False):
                            helicopter.reverse_flip()
                    elif event.button == 6:  # Back button: facing
                        if not getattr(mission, "crash_active", False):
                            helicopter.cycle_facing()
                # audio=audio,
                # logger=logger,
                # chopper_choices=chopper_choices,
                # mission_choices=mission_choices,
                # pause_focus=pause_focus,
                # muted=muted,
                # set_toast=set_toast,
                # reset_game=reset_game_wrapper,
                # apply_mission_preview=apply_mission_preview_wrapper,
                # skip_intro=lambda: skip_intro(cutscenes.intro),
                # skip_mission_cutscene=lambda: skip_mission_cutscene(cutscenes.mission),
                # toggle_particles_wrapper=toggle_particles_wrapper,
                # toggle_flashes_wrapper=toggle_flashes_wrapper,
                # toggle_screenshake_wrapper=toggle_screenshake_wrapper,
                # spawn_projectile_from_helicopter_logged=spawn_projectile_from_helicopter_logged,
                # try_start_flare_salvo=try_start_flare_salvo,
                # toggle_doors_with_logging=toggle_doors_with_logging,
                # Facing=Facing,
                # DebugSettings=DebugSettings,
                # boarded_count=boarded_count,
                # flares=flares,
                # selected_mission_index=selected_mission_index,
                # selected_mission_id=selected_mission_id,
                # selected_chopper_index=selected_chopper_index,
                # selected_chopper_asset=selected_chopper_asset,
                # debug=debug
                # )
            # Quit confirmation: if quit_confirm is True and A is pressed, exit; if B is pressed, cancel
            if runtime.quit_confirm:
                if a_down and not prev_btn_a_down:
                    running = False
                elif b_down and not prev_btn_b_down:
                    runtime.quit_confirm = False

        # Check if we transitioned from select_chopper to cutscene via keyboard
        # (gamepad path handles this inline)
        if prev_loop_mode == "select_chopper" and mode == "cutscene" and cutscenes.mission.video is None:
            # Start mission cutscene after chopper selection (keyboard path)
            cutscene_path_after_selection = assets_dir / "city-seige-intro.avi"
            cutscene_started = start_mission_cutscene(
                cutscenes.mission,
                cutscene_path=cutscene_path_after_selection,
                logger=logger,
                event_id="mission_start",
                mission_id=selected_mission_id,
            )
            if not cutscene_started:
                # If cutscene can't be loaded, go directly to playing
                mode = "playing"
        
        # Update previous mode for next iteration
        prev_loop_mode = mode

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

            # --- DEBUG: Print all button states when any button is pressed ---
            # (Suppressed to avoid log spam)
            # if any([
            #     a_down, b_down, x_down, y_down, start_down, rb_down, lb_down, back_down
            # ]):
            #     try:
            #         num_buttons = active_js.get_numbuttons()
            #         button_states = [active_js.get_button(i) for i,v in enumerate(button_states)]
            #         logger.info(f"GAMEPAD BUTTONS: {[f'B{i}={v}' for i,v in enumerate(button_states)]}")
            #     except Exception as e:
            #         logger.info(f"GAMEPAD BUTTONS: error {e}")

            # Debug overlay toggle (gamepad).
            if lb_down and not prev_btn_lb_down:
                debug = DebugSettings(show_overlay=not debug.show_overlay)
                set_toast(f"Debug overlay: {'ON' if debug.show_overlay else 'OFF'}")



            # --- GAMEPAD PAUSE BUTTON HANDLING ---
            if start_down and not prev_btn_start_down:
                logger.info(f"GAMEPAD: Start button pressed (start_down={start_down}, prev_btn_start_down={prev_btn_start_down}, mode={mode})")

            if mode != "playing" and (start_down and not prev_btn_start_down):
                logger.info(f"GAMEPAD: Start button pressed but pause not triggered (mode={mode})")

            prev_mode = mode
            mode, just_paused_with_start, toggled_pause_state, clear_quit_confirm = handle_gamepad_pause_button(
                mode=mode,
                start_down=start_down,
                prev_btn_start_down=prev_btn_start_down,
                b_down=b_down,
                prev_btn_b_down=prev_btn_b_down,
                just_paused_with_start=just_paused_with_start,
            )
            if toggled_pause_state:
                if mode == "paused":
                    audio.play_pause_toggle()
                    audio.set_pause_menu_active(True)
                else:
                    audio.set_pause_menu_active(False)
                    audio.play_pause_toggle()
            if prev_mode == "playing" and mode == "paused":
                logger.info(f"PAUSE: Gamepad Start pressed, entering pause menu (mode=playing)")
                runtime.pause_focus = "choppers"
            if prev_mode == "paused" and mode == "playing":
                logger.info(f"UNPAUSE: Gamepad Start or B pressed, resuming game (mode=paused)")
            if clear_quit_confirm:
                runtime.quit_confirm = False

            if mode == "select_chopper":
                prev_mode = mode
                mode, selected_chopper_index, chopper_selection_changed, chopper_confirmed = handle_select_chopper_gamepad(
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
                    selected_chopper_index=selected_chopper_index,
                    chopper_count=len(chopper_choices),
                )
                if chopper_selection_changed:
                    selected_chopper_asset = chopper_choices[selected_chopper_index][0]
                    audio.play_menu_select()
                if chopper_confirmed:
                    set_toast(f"Chopper selected: {chopper_choices[selected_chopper_index][1]}")
                    if selected_mission_id == "city":
                        play_satellite_reallocating()
                    reset_game_wrapper()
                    # Start mission cutscene after chopper selection
                    cutscene_path_after_selection = assets_dir / "city-seige-intro.avi"
                    cutscene_started = start_mission_cutscene(
                        cutscenes.mission,
                        cutscene_path=cutscene_path_after_selection,
                        logger=logger,
                        event_id="mission_start",
                        mission_id=selected_mission_id,
                    )
                    if not cutscene_started:
                        # If cutscene can't be loaded, go directly to playing
                        mode = "playing"
                elif prev_mode == "select_chopper" and mode == "select_mission":
                    set_toast("Back to Mission Select")
            elif mode == "intro":
                skip_btn = should_skip_on_gamepad_buttons(
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
                if skip_btn:
                    mode = "select_mission"
                    skip_intro(cutscenes.intro)
            elif mode == "cutscene":
                skip_btn = should_skip_on_gamepad_buttons(
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
                if skip_btn:
                    mode = "playing"
                    skip_mission_cutscene(cutscenes.mission)
            elif mode == "select_mission":
                prev_mode = mode
                mode, selected_mission_index, mission_selection_changed = handle_select_mission_gamepad(
                    menu_dir=menu_dir,
                    prev_menu_dir=prev_menu_dir,
                    a_down=a_down,
                    prev_btn_a_down=prev_btn_a_down,
                    start_down=start_down,
                    prev_btn_start_down=prev_btn_start_down,
                    selected_mission_index=selected_mission_index,
                    mission_count=len(mission_choices),
                )
                if mission_selection_changed:
                    selected_mission_id = mission_choices[selected_mission_index][0]
                    audio.play_menu_select()
                    apply_mission_preview_wrapper()
                if prev_mode == "select_mission" and mode == "select_chopper":
                    set_toast(f"Mission selected: {mission_choices[selected_mission_index][1]}")
            elif mode == "paused":
                paused = resolve_paused_mode_inputs(
                    pause_focus=runtime.pause_focus,
                    quit_confirm=runtime.quit_confirm,
                    selected_chopper_index=selected_chopper_index,
                    chopper_count=len(chopper_choices),
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
                    crash_active=bool(getattr(mission, "crash_active", False)),
                )

                runtime.pause_focus = paused.pause_focus
                runtime.quit_confirm = paused.quit_confirm
                if paused.selected_chopper_index != selected_chopper_index:
                    selected_chopper_index = paused.selected_chopper_index
                    selected_chopper_asset = chopper_choices[selected_chopper_index][0]
                    helicopter.skin_asset = selected_chopper_asset
                if paused.play_menu_select:
                    audio.play_menu_select()

                if paused.toggle_particles:
                    toggle_particles_wrapper()
                if paused.toggle_flashes:
                    toggle_flashes_wrapper()
                if paused.toggle_screenshake:
                    toggle_screenshake_wrapper()

                if paused.action != "none":
                    if paused.action == "restart_mission":
                        logger.info(f"PAUSE MENU: A pressed on restart_mission")
                        if selected_mission_id == "city":
                            play_satellite_reallocating()
                        reset_game_wrapper()
                        mode = "playing"
                        audio.set_pause_menu_active(False)
                        audio.play_pause_toggle()
                        runtime.quit_confirm = False
                    elif paused.action == "restart_game":
                        logger.info(f"PAUSE MENU: A pressed on restart_game")
                        mode = "select_mission"
                        set_toast("Restart Game")
                        audio.set_pause_menu_active(False)
                        audio.play_pause_toggle()
                        runtime.quit_confirm = False
                    elif paused.action == "toggle_mute":
                        logger.info(f"PAUSE MENU: A pressed on mute (muted={not runtime.muted})")
                        runtime.muted = not runtime.muted
                        audio.set_muted(runtime.muted)
                        runtime.quit_confirm = False
                    elif paused.action == "quit_prompt":
                        logger.info(f"PAUSE MENU: A pressed on quit, showing confirmation dialog")
                    elif paused.action == "quit_exit":
                        logger.info(f"PAUSE MENU: A pressed on quit_confirm, exiting game (gamepad A)")
                        running = False

                if paused.cancel_quit_confirm:
                    logger.info(f"PAUSE MENU: B pressed on quit_confirm, canceling quit and returning to pause menu")
                    runtime.quit_confirm = False

                if paused.trigger_flare:
                    try_start_flare_salvo(flares, mission=mission, helicopter=helicopter, audio=audio)

                if paused.toggle_doors:
                    toggle_doors_with_logging(helicopter, mission, audio, logger, boarded_count, set_toast)
                if paused.reverse_flip:
                    helicopter.reverse_flip()
                if paused.cycle_facing:
                    helicopter.cycle_facing()
                if paused.fire_weapon:
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

        helicopter_input = build_helicopter_input(
            mode=mode,
            kb_tilt_left=kb_tilt_left,
            kb_tilt_right=kb_tilt_right,
            kb_lift_up=kb_lift_up,
            kb_lift_down=kb_lift_down,
            kb_brake=kb_brake,
            gp_tilt_left=gp_tilt_left,
            gp_tilt_right=gp_tilt_right,
            gp_lift_up=gp_lift_up,
            gp_lift_down=gp_lift_down,
        )

        # Fixed-timestep update.
        # Clamp accumulator to avoid spiral of death if the window stalls.
        if accumulator > 0.25:
            accumulator = 0.25


        while accumulator >= tick.dt:
            if mode == "playing":
                playing_step = run_playing_fixed_step(
                    mode=mode,
                    mission=mission,
                    helicopter=helicopter,
                    helicopter_input=helicopter_input,
                    tick_dt=tick.dt,
                    physics=physics,
                    heli_settings=heli_settings,
                    audio=audio,
                    flares=flares,
                    screenshake=screenshake,
                    screenshake_enabled=screenshake_enabled,
                    logger=logger,
                    prev_stats=prev_stats,
                    boarded_count=boarded_count,
                    set_toast=set_toast,
                    mission_end_delay_s=MISSION_END_RETURN_DELAY_S,
                    campaign_sentiment=campaign_sentiment,
                    mission_end_return_seconds=runtime.mission_end_return_seconds,
                    doors_open_before_cutscene=doors_open_before_cutscene,
                    mission_cutscene_state=cutscenes.mission,
                    assets_dir=assets_dir,
                    update_flares_fn=update_flares,
                    update_helicopter_fn=update_helicopter,
                    hostage_crush_check_fn=hostage_crush_check_logged,
                    rough_landing_feedback_fn=rough_landing_feedback,
                    update_mission_fn=update_mission,
                    start_mission_cutscene_fn=start_mission_cutscene,
                )
                mode = playing_step.next_mode
                campaign_sentiment = playing_step.campaign_sentiment
                runtime.mission_end_return_seconds = playing_step.mission_end_return_seconds
                doors_open_before_cutscene = playing_step.doors_open_before_cutscene
                
                # --- Airport Special Ops: update placeholder logic ---
                if selected_mission_id == "airport":
                    if airport_bus_state is not None:
                        airport_bus_state = update_bus_ai(airport_bus_state, tick.dt, audio=audio)
                    airport_hostage_state = update_airport_hostage_logic(
                        airport_hostage_state,
                        tick.dt,
                        bus_state=airport_bus_state,
                        helicopter=helicopter,
                        mission=mission,
                        audio=audio,
                        meal_truck_state=airport_meal_truck_state,
                        tech_state=airport_tech_state,
                    )
                    airport_tech_state = update_mission_tech(
                        airport_tech_state,
                        tick.dt,
                        helicopter=helicopter,
                        meal_truck_state=airport_meal_truck_state,
                        bus_state=airport_bus_state,
                    )
                    airport_meal_truck_state = update_airport_meal_truck(
                        airport_meal_truck_state,
                        tick.dt,
                        helicopter=helicopter,
                        tech_state=airport_tech_state,
                        bus_state=airport_bus_state,
                    )
                    airport_target_x = get_airport_priority_target_x(
                        bus_state=airport_bus_state,
                        meal_truck_state=airport_meal_truck_state,
                        tech_state=airport_tech_state,
                    )
                    airport_enemy_state = update_airport_enemy_spawns(
                        airport_enemy_state,
                        tick.dt,
                        mission=mission,
                        bus_state=airport_bus_state,
                        target_x=airport_target_x,
                    )
                    _airport_ff_hits = apply_airport_bus_friendly_fire(
                        airport_bus_state,
                        mission,
                        logger=logger,
                    )
                    airport_objective_state = update_airport_objectives(
                        airport_objective_state,
                        tick.dt,
                        mission=mission,
                        hostage_state=airport_hostage_state,
                        bus_state=airport_bus_state,
                        meal_truck_state=airport_meal_truck_state,
                        tech_state=airport_tech_state,
                    )
                    airport_cutscene_state = update_airport_cutscene_state(
                        airport_cutscene_state,
                        tick.dt,
                        meal_truck_state=airport_meal_truck_state,
                        hostage_state=airport_hostage_state,
                        tech_state=airport_tech_state,
                    )

                    # NOTE: Helicopter parking logic removed in redesign
                    # Tech deploys from chopper to meal truck, chopper is free to move after deployment
                    # (Previous logic: kept helicopter parked/invuln while tech was deployed)
                
                if playing_step.continue_fixed_loop:
                    continue

            accumulator -= tick.dt

        toast.update(frame_dt)

        intro_finished = bool(mode == "intro" and update_intro(cutscenes.intro, frame_dt))
        cutscene_finished = bool(mode == "cutscene" and update_mission_cutscene(cutscenes.mission, frame_dt))

        mode_transition = resolve_post_frame_mode_transitions(
            mode=mode,
            frame_dt=frame_dt,
            mission_end_return_seconds=runtime.mission_end_return_seconds,
            intro_finished=intro_finished,
            cutscene_finished=cutscene_finished,
        )
        mode = mode_transition.mode
        runtime.mission_end_return_seconds = mode_transition.mission_end_return_seconds

        if mode_transition.restore_doors_after_cutscene:
            # Restore doors state after cutscene and log.
            prev_state = helicopter.doors_open
            helicopter.doors_open = doors_open_before_cutscene
            logger.info(f"DOORS: restored after cutscene | was_open={prev_state} | restored_open={helicopter.doors_open}")
            audio.log_audio_channel_snapshot(tag="cutscene_exit", logger=logger)

        if mode_transition.mission_end_auto_returned:
            set_toast("Mission ended: returning to Mission Select")

        update_weather_effects(
            particles_enabled=particles_enabled,
            mode=mode,
            frame_dt=frame_dt,
            weather_mode=weather_mode,
            sky_smoke=sky_smoke,
            rain=rain,
            fog=fog,
            dust=dust,
            storm_clouds=storm_clouds,
            lightning=lightning,
            helicopter=helicopter,
            heli_settings=heli_settings,
            screen=screen,
            window=window,
        )

        # Side-scrolling camera (world x -> screen x).
        camera_x = compute_camera_x(
            world_width=float(mission.world_width),
            view_width=float(screen.get_width()),
            helicopter_x=float(helicopter.pos.x),
        )

        # Update audio (ducking is applied via bus volumes).
        audio.set_cinematic_ducked(mode == "cutscene", factor=0.5)
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
            draw_weather_particles(
                target=target,
                particles_enabled=particles_enabled,
                weather_mode=weather_mode,
                sky_smoke=sky_smoke,
                rain=rain,
                fog=fog,
                dust=dust,
                storm_clouds=storm_clouds,
                lightning=lightning,
                ground_y=float(heli_settings.ground_y),
            )
            draw_ground(target, heli_settings.ground_y)
            draw_mission(target, mission, camera_x=camera_x, enable_particles=particles_enabled)
            
            # --- Airport Special Ops: placeholder rendering (drawn on top of normal mission entities) ---
            if selected_mission_id == "airport":
                # Render active bus state
                if airport_bus_state is not None:
                    draw_airport_bus(target, airport_bus_state, camera_x)
                draw_airport_hostages(
                    target,
                    airport_hostage_state,
                    camera_x=camera_x,
                    ground_y=heli_settings.ground_y,
                    bus_state=airport_bus_state,
                )
                draw_airport_enemies(target, airport_enemy_state, camera_x=camera_x)
                draw_airport_mission_tech(target, airport_tech_state, camera_x=camera_x, helicopter=helicopter)
                draw_airport_meal_truck(target, airport_meal_truck_state, camera_x=camera_x)
                draw_airport_objectives(
                    target,
                    airport_objective_state,
                    camera_x=camera_x,
                    ground_y=heli_settings.ground_y,
                    bus_state=airport_bus_state,
                )
                draw_airport_cutscene_markers(
                    target,
                    airport_cutscene_state,
                    camera_x=camera_x,
                    ground_y=heli_settings.ground_y,
                    pickup_x=float(getattr(airport_hostage_state, "pickup_x", 1232.0)) if airport_hostage_state is not None else 1232.0,
                )
            
            draw_flares(target, mission, camera_x=camera_x, enable_particles=particles_enabled)
            draw_helicopter_damage_fx(target, mission, camera_x=camera_x, enable_particles=particles_enabled)
            draw_helicopter(target, helicopter, camera_x=camera_x, boarded=boarded_count(mission))
            draw_impact_sparks(target, mission, camera_x=camera_x, enable_particles=particles_enabled)
            # Draw black clouds above chopper for extra difficulty (rendered last, above chopper)
            if weather_mode == "storm":
                storm_clouds.draw(target, layer='black')
            # HUD/targeting disabled by lightning
            if mode == "playing":
                vip_kia_overlay_timer, city_objective_overlay_timer = draw_playing_hud_and_overlays(
                    target=target,
                    screen=screen,
                    mission=mission,
                    helicopter=helicopter,
                    hud_disabled_timer=hud_disabled_timer,
                    vip_kia_overlay_timer=vip_kia_overlay_timer,
                    city_objective_overlay_timer=city_objective_overlay_timer,
                    frame_dt=frame_dt,
                    draw_hud_fn=draw_hud,
                )
            else:
                draw_mode_overlays(
                    mode=mode,
                    target=target,
                    mission_choices=mission_choices,
                    selected_mission_index=selected_mission_index,
                    chopper_choices=chopper_choices,
                    selected_chopper_index=selected_chopper_index,
                    pause_focus=runtime.pause_focus,
                    muted=runtime.muted,
                    quit_confirm=runtime.quit_confirm,
                    paused_hint=PAUSED_MENU_HINT,
                    draw_mission_select_overlay_fn=draw_mission_select_overlay,
                    draw_chopper_select_overlay_fn=draw_chopper_select_overlay,
                )
            render_frame_post_fx(
                mode=mode,
                target=target,
                screen=screen,
                shake_x=shake_x,
                shake_y=shake_y,
                debug_mode=debug_mode,
                debug_show_overlay=bool(debug.show_overlay),
                toast_message=str(toast.message or ""),
                flashes_enabled=bool(flashes_enabled),
                helicopter=helicopter,
                mission=mission,
                overlay=overlay,
                fps=float(clock.get_fps()),
                draw_debug_overlay_fn=draw_debug_overlay,
                draw_toast_fn=draw_toast,
                draw_damage_flash_fn=draw_damage_flash,
            )

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    run()
