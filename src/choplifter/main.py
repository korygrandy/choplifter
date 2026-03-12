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
from .helicopter import Facing, Helicopter, HelicopterInput, update_helicopter
from . import haptics
from .mission import update_mission
from .mission_ending import _end_mission
from .mission_configs import get_mission_config_by_id
from .mission_helpers import boarded_count
from .mission_hostages import hostage_crush_check_logged
from .mission_player_fire import spawn_projectile_from_helicopter_logged
from .mission_state import MissionState
from .rendering import (
    bg_asset_exists,
    draw_chopper_select_overlay,
    draw_damage_flash,
    draw_enemy_damage_fx,
    draw_explosion_particles,
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
from .bus_ai import BusDriverInput
from .vehicle_assets import TruckDriverInput
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
from .app.input import get_active_joystick, read_active_gamepad_snapshot
from .app.feedback import ScreenShakeState, rough_landing_feedback, update_screenshake_target
from .app.flares import FlareState, reset_flares, try_start_flare_salvo, update_flares
from .app.gamepads import init_connected_joysticks, handle_joy_device_added, handle_joy_device_removed
from .app.toast import ToastState
from .app.ui_constants import MISSION_END_RETURN_DELAY_S, PAUSED_MENU_HINT
from .app.gamepad_button_state import GamepadButtonState
from .app.session import create_mission_and_helicopter
from .app.flow import apply_mission_preview, reset_game
from .app.stats_snapshot import MissionStatsSnapshot, take_mission_stats_snapshot
from .app.accessibility_toggles import toggle_particles, toggle_flashes, toggle_screenshake
from .app.doors import check_airport_truck_retract_toast, check_tech_lz_door_toast, toggle_doors_with_logging
from .app.runtime_state import GameRuntimeState
from .app.airport_runtime_flags import sync_airport_runtime_flags
from .app.bus_door_flow import apply_airport_bus_door_transitions
from .app.weapon_lock import chopper_weapons_locked
from .app.airport_session import create_empty_airport_runtime, initialize_airport_runtime
from .app.objective_overlay import get_mission_objective_overlay_duration
from .app.vehicle_driver_modes import handle_airport_driver_mode_doors
from .sprite_preloader import preload_mission_sprites
from .game_logging import set_console_log_debug
from .app.airport_tick import update_airport_mission_tick
from .app.game_update import (
    build_helicopter_input,
    run_playing_fixed_step,
)
from .app.mode_update import resolve_post_frame_mode_transitions
from .app.frame_update import update_weather_effects, update_camera_tracking
from .app.frame_render import draw_airport_world_overlays, draw_mode_overlays, draw_playing_hud_and_overlays, draw_weather_particles, render_frame_post_fx
from .app.event_loop import (
    handle_debug_weather_keydown,
    handle_gamepad_pause_button,
    handle_mission_end_gamepad_navigation,
    handle_mission_end_keyboard_navigation,
    handle_playing_gamepad_button,
    handle_playing_keyboard_special_cases,
    handle_pause_quit_confirm_keydown,
    apply_paused_gameplay_shortcuts,
    apply_paused_menu_decision,
    route_gamepad_mode_inputs,
    resolve_paused_mode_inputs,
    handle_select_chopper_gamepad,
)


def draw_debug_overlay(target):
    font = pygame.font.SysFont(None, 32)
    overlay = font.render("DEBUG MODE", True, (255, 0, 0))
    target.blit(overlay, (12, 12))


def run() -> None:
    vip_kia_overlay_timer = 0.0
    vip_kia_overlay_shown = False
    city_objective_overlay_timer = 0.0
    from .render.world import draw_mission_end_overlay, toggle_thermal_mode

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
    gamepad_buttons = GamepadButtonState()

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
    airport_runtime = create_empty_airport_runtime()
    airport_meal_truck_spawn_x = 1060.0  # Left of leftmost compound, tech drives it to elevated bunker
    airport_total_rescue_target = 16

    if selected_mission_id == "airport":
        airport_runtime = initialize_airport_runtime(
            mission=mission,
            ground_y=heli_settings.ground_y,
            total_rescue_target=airport_total_rescue_target,
            meal_truck_spawn_x=airport_meal_truck_spawn_x,
            hostage_deadline_s=120.0,
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
        nonlocal city_objective_overlay_timer, airport_runtime
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
        gamepad_buttons.reset()
        runtime.meal_truck_driver_mode = False
        runtime.meal_truck_lift_command_extended = False
        runtime.bus_driver_mode = False
        
        # Initialize mission-specific state
        if selected_mission_id == "airport":
            airport_runtime = initialize_airport_runtime(
                mission=mission,
                ground_y=heli_settings.ground_y,
                total_rescue_target=airport_total_rescue_target,
                meal_truck_spawn_x=airport_meal_truck_spawn_x,
                hostage_deadline_s=120.0,
            )
        else:
            airport_runtime = create_empty_airport_runtime()

        preload_mission_sprites(selected_mission_id, selected_chopper_asset)

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

    def can_exit_meal_truck_driver_mode() -> bool:
        # Engineer can only exit meal truck if within ~100px (one helicopter width) of the helicopter
        if airport_runtime.meal_truck_state is None:
            return False
        truck_x = float(getattr(airport_runtime.meal_truck_state, "x", 0.0))
        heli_x = float(getattr(helicopter.pos, "x", 0.0))
        distance = abs(truck_x - heli_x)
        max_distance = 100.0  # One helicopter sprite width
        return distance <= max_distance
    
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
                gamepad_buttons.clear_on_disconnect()
            elif event.type == pygame.KEYDOWN:
                handled_mission_end, next_mode = handle_mission_end_keyboard_navigation(
                    key=event.key,
                    mode=mode,
                    mission_ended=bool(mission.ended),
                    set_toast=set_toast,
                )
                if handled_mission_end:
                    prev_mode = mode
                    mode = next_mode
                    if prev_mode != mode and mode == "paused":
                        runtime.pause_focus = "choppers"
                        audio.play_pause_toggle()
                        audio.set_pause_menu_active(True)
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
                    set_console_log_debug(debug_mode)
                    if selected_weather_mode is not None:
                        set_debug_weather_mode(selected_weather_mode)
                    if debug_toast:
                        set_toast(debug_toast)
                
                # Handle doors key for meal truck driver mode (before normal doors handling)
                doors_key_pressed = mode == "playing" and matches_key(event.key, controls.doors) and not getattr(mission, "crash_active", False)
                # Handle fire key for lift toggle in meal truck driver mode
                fire_key_pressed = mode == "playing" and matches_key(event.key, controls.fire) and not getattr(mission, "crash_active", False)
                playing_keyboard = handle_playing_keyboard_special_cases(
                    selected_mission_id=selected_mission_id,
                    doors_key_pressed=doors_key_pressed,
                    fire_key_pressed=fire_key_pressed,
                    meal_truck_driver_mode=runtime.meal_truck_driver_mode,
                    meal_truck_lift_command_extended=runtime.meal_truck_lift_command_extended,
                    bus_driver_mode=runtime.bus_driver_mode,
                    airport_meal_truck_state=airport_runtime.meal_truck_state,
                    airport_bus_state=airport_runtime.bus_state,
                    airport_tech_state=airport_runtime.tech_state,
                    helicopter=helicopter,
                    heli_ground_y=heli_settings.ground_y,
                )
                runtime.meal_truck_driver_mode = playing_keyboard.meal_truck_driver_mode
                runtime.meal_truck_lift_command_extended = playing_keyboard.meal_truck_lift_command_extended
                runtime.bus_driver_mode = playing_keyboard.bus_driver_mode
                if playing_keyboard.handled:
                    continue
                
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
                    quit_confirm=runtime.quit_confirm,
                    helicopter_weapon_locked=chopper_weapons_locked(
                        meal_truck_driver_mode=bool(runtime.meal_truck_driver_mode),
                        bus_driver_mode=bool(runtime.bus_driver_mode),
                        engineer_remote_control_active=bool(getattr(mission, "engineer_remote_control_active", False)),
                    ),
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
                    prev_mode = mode
                    mode = next_mode
                    if prev_mode != mode and mode == "paused":
                        runtime.pause_focus = "choppers"
                        audio.play_pause_toggle()
                        audio.set_pause_menu_active(True)
                elif mode == "playing":
                    playing_gamepad = handle_playing_gamepad_button(
                        button=event.button,
                        selected_mission_id=selected_mission_id,
                        mission=mission,
                        helicopter=helicopter,
                        audio=audio,
                        logger=logger,
                        flares=flares,
                        meal_truck_driver_mode=runtime.meal_truck_driver_mode,
                        meal_truck_lift_command_extended=runtime.meal_truck_lift_command_extended,
                        bus_driver_mode=runtime.bus_driver_mode,
                        airport_meal_truck_state=airport_runtime.meal_truck_state,
                        airport_bus_state=airport_runtime.bus_state,
                        airport_tech_state=airport_runtime.tech_state,
                        heli_ground_y=heli_settings.ground_y,
                        spawn_projectile_from_helicopter_logged=spawn_projectile_from_helicopter_logged,
                        try_start_flare_salvo=try_start_flare_salvo,
                        toggle_doors_with_logging=toggle_doors_with_logging,
                        boarded_count=boarded_count,
                        set_toast=set_toast,
                        chopper_weapons_locked=chopper_weapons_locked,
                        Facing=Facing,
                    )
                    runtime.meal_truck_driver_mode = playing_gamepad.meal_truck_driver_mode
                    runtime.meal_truck_lift_command_extended = playing_gamepad.meal_truck_lift_command_extended
                    runtime.bus_driver_mode = playing_gamepad.bus_driver_mode
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

        active_gamepad = read_active_gamepad_snapshot(
            joysticks,
            button_state=gamepad_buttons,
            deadzone=float(accessibility.gamepad_deadzone),
            trigger_threshold01=float(accessibility.trigger_threshold),
        )
        active_js = active_gamepad.joystick if active_gamepad is not None else None
        haptics.set_active_joystick(active_js)

        if active_gamepad is not None:
            gp = active_gamepad.readout
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
            prev_btn_a_down = active_gamepad.prev_a_down
            prev_btn_b_down = active_gamepad.prev_b_down
            prev_btn_x_down = active_gamepad.prev_x_down
            prev_btn_y_down = active_gamepad.prev_y_down
            prev_btn_start_down = active_gamepad.prev_start_down
            prev_btn_rb_down = active_gamepad.prev_rb_down
            prev_btn_lb_down = active_gamepad.prev_lb_down
            prev_btn_back_down = active_gamepad.prev_back_down

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
                just_paused_with_start=runtime.just_paused_with_start,
            )
            runtime.just_paused_with_start = just_paused_with_start
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

            if mode != "paused":
                prev_mode = mode
                gamepad_mode = route_gamepad_mode_inputs(
                    mode=mode,
                    menu_dir=menu_dir,
                    prev_menu_dir=runtime.prev_menu_dir,
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
                    selected_chopper_index=selected_chopper_index,
                    chopper_count=len(chopper_choices),
                    selected_mission_index=selected_mission_index,
                    mission_count=len(mission_choices),
                )
                mode = gamepad_mode.mode
                selected_chopper_index = gamepad_mode.selected_chopper_index
                selected_mission_index = gamepad_mode.selected_mission_index

                if gamepad_mode.chopper_selection_changed:
                    selected_chopper_asset = chopper_choices[selected_chopper_index][0]
                    audio.play_menu_select()
                if gamepad_mode.chopper_confirmed:
                    set_toast(f"Chopper selected: {chopper_choices[selected_chopper_index][1]}")
                    if selected_mission_id == "city":
                        play_satellite_reallocating()
                    reset_game_wrapper()
                    cutscene_path_after_selection = assets_dir / "city-seige-intro.avi"
                    cutscene_started = start_mission_cutscene(
                        cutscenes.mission,
                        cutscene_path=cutscene_path_after_selection,
                        logger=logger,
                        event_id="mission_start",
                        mission_id=selected_mission_id,
                    )
                    if not cutscene_started:
                        mode = "playing"
                elif prev_mode == "select_chopper" and gamepad_mode.selected_mission_backtracked:
                    set_toast("Back to Mission Select")

                if gamepad_mode.skip_intro_requested:
                    skip_intro(cutscenes.intro)
                if gamepad_mode.skip_cutscene_requested:
                    skip_mission_cutscene(cutscenes.mission)

                if gamepad_mode.mission_selection_changed:
                    selected_mission_id = mission_choices[selected_mission_index][0]
                    audio.play_menu_select()
                    apply_mission_preview_wrapper()
                if prev_mode == "select_mission" and gamepad_mode.selected_mission_backtracked:
                    set_toast(f"Mission selected: {mission_choices[selected_mission_index][1]}")

            elif mode == "paused":
                paused = resolve_paused_mode_inputs(
                    pause_focus=runtime.pause_focus,
                    quit_confirm=runtime.quit_confirm,
                    selected_chopper_index=selected_chopper_index,
                    chopper_count=len(chopper_choices),
                    menu_vert=menu_vert,
                    prev_menu_vert=runtime.prev_menu_vert,
                    menu_dir=menu_dir,
                    prev_menu_dir=runtime.prev_menu_dir,
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
                paused_applied = apply_paused_menu_decision(
                    paused=paused,
                    mode=mode,
                    running=running,
                    selected_chopper_index=selected_chopper_index,
                    selected_chopper_asset=selected_chopper_asset,
                    muted=runtime.muted,
                    selected_mission_id=selected_mission_id,
                    chopper_choices=chopper_choices,
                    helicopter=helicopter,
                    audio=audio,
                    logger=logger,
                    play_satellite_reallocating=play_satellite_reallocating,
                    reset_game=reset_game_wrapper,
                    set_toast=set_toast,
                    toggle_particles=toggle_particles_wrapper,
                    toggle_flashes=toggle_flashes_wrapper,
                    toggle_screenshake=toggle_screenshake_wrapper,
                )
                mode = paused_applied.mode
                running = paused_applied.running
                selected_chopper_index = paused_applied.selected_chopper_index
                selected_chopper_asset = paused_applied.selected_chopper_asset
                runtime.muted = paused_applied.muted
                runtime.quit_confirm = paused_applied.quit_confirm

                apply_paused_gameplay_shortcuts(
                    paused=paused,
                    meal_truck_driver_mode=runtime.meal_truck_driver_mode,
                    bus_driver_mode=runtime.bus_driver_mode,
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

            gamepad_buttons.snapshot(
                a_down=a_down,
                b_down=b_down,
                x_down=x_down,
                y_down=y_down,
                start_down=start_down,
                rb_down=rb_down,
                lb_down=lb_down,
                back_down=back_down,
            )
            runtime.prev_menu_dir = menu_dir
            runtime.prev_menu_vert = menu_vert

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

        # Keep mission-level engineer/vehicle flags in sync for combat and AI gating.
        sync_airport_runtime_flags(
            mission=mission,
            selected_mission_id=selected_mission_id,
            airport_tech_state=airport_runtime.tech_state,
            meal_truck_driver_mode=bool(runtime.meal_truck_driver_mode),
            bus_driver_mode=bool(runtime.bus_driver_mode),
        )
        
        # Build truck driver input (reuses tilt/lift controls: left=move left, right=move right, up=extend lift)
        truck_driver_input = TruckDriverInput(
            move_left=(kb_tilt_left or gp_tilt_left) if mode == "playing" and runtime.meal_truck_driver_mode else False,
            move_right=(kb_tilt_right or gp_tilt_right) if mode == "playing" and runtime.meal_truck_driver_mode else False,
            extend_lift=runtime.meal_truck_lift_command_extended if mode == "playing" and runtime.meal_truck_driver_mode else False,
        )
        
        # When in driver mode, disable helicopter controls
        if runtime.meal_truck_driver_mode:
            helicopter_input = HelicopterInput(
                tilt_left=False,
                tilt_right=False,
                lift_up=False,
                lift_down=False,
                brake=False,
            )

        # Build bus driver input (reuses tilt controls: left/right moves bus)
        bus_driver_input = BusDriverInput(
            move_left=(kb_tilt_left or gp_tilt_left) if mode == "playing" and runtime.bus_driver_mode else False,
            move_right=(kb_tilt_right or gp_tilt_right) if mode == "playing" and runtime.bus_driver_mode else False,
        )
        # When in bus driver mode, disable helicopter controls too
        if runtime.bus_driver_mode:
            helicopter_input = HelicopterInput(
                tilt_left=False,
                tilt_right=False,
                lift_up=False,
                lift_down=False,
                brake=False,
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
                    doors_open_before_cutscene=runtime.doors_open_before_cutscene,
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
                runtime.doors_open_before_cutscene = playing_step.doors_open_before_cutscene
                
                # --- Airport Special Ops: update per-tick logic ---
                if selected_mission_id == "airport":
                    _airport_tick = update_airport_mission_tick(
                        bus_state=airport_runtime.bus_state,
                        hostage_state=airport_runtime.hostage_state,
                        tech_state=airport_runtime.tech_state,
                        meal_truck_state=airport_runtime.meal_truck_state,
                        enemy_state=airport_runtime.enemy_state,
                        objective_state=airport_runtime.objective_state,
                        cutscene_state=airport_runtime.cutscene_state,
                        dt=tick.dt,
                        audio=audio,
                        helicopter=helicopter,
                        mission=mission,
                        heli_settings=heli_settings,
                        bus_driver_input=bus_driver_input,
                        bus_driver_mode=runtime.bus_driver_mode,
                        truck_driver_input=truck_driver_input,
                        meal_truck_driver_mode=runtime.meal_truck_driver_mode,
                        meal_truck_lift_command_extended=runtime.meal_truck_lift_command_extended,
                        set_toast=set_toast,
                        logger=logger,
                        airport_total_rescue_target=airport_total_rescue_target,
                    )
                    airport_runtime.bus_state = _airport_tick.bus_state
                    airport_runtime.hostage_state = _airport_tick.hostage_state
                    airport_runtime.tech_state = _airport_tick.tech_state
                    airport_runtime.meal_truck_state = _airport_tick.meal_truck_state
                    airport_runtime.enemy_state = _airport_tick.enemy_state
                    airport_runtime.objective_state = _airport_tick.objective_state
                    airport_runtime.cutscene_state = _airport_tick.cutscene_state
                    runtime.meal_truck_driver_mode = _airport_tick.meal_truck_driver_mode
                    runtime.meal_truck_lift_command_extended = _airport_tick.meal_truck_lift_command_extended
                
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
            helicopter.doors_open = runtime.doors_open_before_cutscene
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
        camera_update = update_camera_tracking(
            selected_mission_id=selected_mission_id,
            helicopter_x=float(helicopter.pos.x),
            meal_truck_driver_mode=bool(runtime.meal_truck_driver_mode),
            bus_driver_mode=bool(runtime.bus_driver_mode),
            airport_meal_truck_state=airport_runtime.meal_truck_state,
            airport_bus_state=airport_runtime.bus_state,
            camera_x_smoothed=runtime.camera_x_smoothed,
            frame_dt=frame_dt,
            world_width=float(mission.world_width),
            view_width=float(screen.get_width()),
        )
        camera_x = camera_update.camera_x
        runtime.camera_x_smoothed = camera_update.camera_x_smoothed

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
                draw_airport_world_overlays(
                    target=target,
                    camera_x=camera_x,
                    helicopter=helicopter,
                    mission=mission,
                    heli_ground_y=heli_settings.ground_y,
                    airport_bus_state=airport_runtime.bus_state,
                    airport_hostage_state=airport_runtime.hostage_state,
                    airport_enemy_state=airport_runtime.enemy_state,
                    airport_tech_state=airport_runtime.tech_state,
                    airport_objective_state=airport_runtime.objective_state,
                    airport_meal_truck_state=airport_runtime.meal_truck_state,
                    airport_cutscene_state=airport_runtime.cutscene_state,
                )
            
            draw_flares(target, mission, camera_x=camera_x, enable_particles=particles_enabled)
            draw_explosion_particles(target, mission, camera_x=camera_x)
            draw_enemy_damage_fx(target, mission, camera_x=camera_x, enable_particles=particles_enabled)
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
                    driver_mode_active=runtime.meal_truck_driver_mode,
                    debug_mode=debug_mode,
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

            # Keep mission-end debrief above all world/weather/chopper layers.
            draw_mission_end_overlay(target, mission)

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
