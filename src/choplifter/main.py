from .game_types import EnemyKind
from .barak_mrad import BARAK_STATE_DEPLOY

from pathlib import Path
import random
import pygame

from .audio import AudioBank
from .audio_extra import play_satellite_reallocating
from .accessibility import load_accessibility
from .controls import load_controls, pressed
from .debug_overlay import DebugOverlay
from .game_logging import create_session_logger
from .helicopter import Facing, Helicopter, update_helicopter
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
    start_mission_intro_or_playing,
    start_mission_cutscene,
    draw_mission_cutscene,
    update_mission_cutscene,
    skip_mission_cutscene,
)
from .app.state import CutsceneState, IntroCutsceneState, MissionCutsceneState
from .app.input import build_skip_hint, read_active_gamepad_snapshot
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
from .app.main_loop_context import MainLoopContext
from .app.airport_runtime_flags import sync_airport_runtime_flags
from .app.bus_door_flow import apply_airport_bus_door_transitions
from .app.driver_inputs import build_driver_inputs
from .app.loop_state_updates import apply_joybutton_result, apply_keydown_result, apply_nonpaused_gamepad_result
from .app.weapon_lock import chopper_weapons_locked
from .app.airport_session import configure_airport_runtime_for_mission, create_empty_airport_runtime
from .app.airport_render import draw_airport_world_overlays
from .app.main_loop_context_sync import load_frame_locals_from_context, store_frame_locals_to_context
from .app.airport_update import AirportRuntimeContext, apply_airport_playing_tick_update
from .app.objective_overlay import get_mission_objective_overlay_duration
from .app.vehicle_driver_modes import handle_airport_driver_mode_doors
from .sprite_preloader import preload_mission_sprites
from .game_logging import set_console_log_debug
from .app.game_update import (
    build_helicopter_input,
    run_playing_fixed_step,
)
from .app.mode_update import resolve_post_frame_mode_transitions
from .app.frame_update import (
    advance_weather_runtime,
    apply_weather_runtime_update,
    update_camera_tracking,
    update_vip_overlay_state,
    update_weather_effects,
)
from .app.frame_render import draw_mode_overlays, draw_playing_hud_and_overlays, draw_weather_particles, render_frame_post_fx
from .app.event_loop import (
    handle_global_debug_keydown,
    handle_gamepad_pause_flow,
    handle_keydown_event,
    handle_joybuttondown_event,
    apply_paused_gameplay_shortcuts,
    apply_paused_menu_decision,
    handle_nonpaused_gamepad_mode_flow,
    handle_paused_gamepad_mode_flow,
    resolve_paused_mode_inputs,
)


def draw_debug_overlay(target):
    font = pygame.font.SysFont(None, 32)
    overlay = font.render("DEBUG MODE", True, (255, 0, 0))
    target.blit(overlay, (12, 12))


def run() -> None:
    from .render.world import draw_mission_end_overlay, toggle_thermal_mode

    def set_debug_weather_mode(mode):
        runtime.weather_mode = mode
        runtime.weather_timer = 0.0
        runtime.weather_duration = 9999.0  # Prevent auto-cycling

    debug_weather_modes = ["clear", "rain", "fog", "dust", "storm"]
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
    runtime.prev_loop_mode = mode
    runtime.weather_mode = random.choice(debug_weather_modes)
    runtime.weather_duration = random.uniform(18, 40)

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
    airport_runtime = configure_airport_runtime_for_mission(
        selected_mission_id=selected_mission_id,
        mission=mission,
        ground_y=heli_settings.ground_y,
        previous_runtime=create_empty_airport_runtime(),
        hostage_deadline_s=120.0,
    )
    loop_ctx = MainLoopContext(
        mission=mission,
        helicopter=helicopter,
        accumulator=0.0,
        prev_stats=prev_stats,
        campaign_sentiment=campaign_sentiment,
        airport_runtime=airport_runtime,
    )
    context_swapped = False

    def apply_mission_preview_wrapper() -> None:
        nonlocal context_swapped
        preview_mission, preview_helicopter, preview_accumulator, preview_prev_stats = apply_mission_preview(
            create_mission_and_helicopter,
            heli_settings,
            selected_mission_id,
            selected_chopper_asset,
            take_mission_stats_snapshot,
            boarded_count,
            sky_smoke,
            audio,
            set_toast,
            loop_ctx.mission,
        )
        loop_ctx.mission = preview_mission
        loop_ctx.helicopter = preview_helicopter
        loop_ctx.accumulator = preview_accumulator
        loop_ctx.prev_stats = preview_prev_stats
        loop_ctx.mission.sentiment = float(loop_ctx.campaign_sentiment)
        loop_ctx.mission.audio = audio
        runtime.mission_end_return_seconds = 0.0
        audio.log_audio_channel_snapshot(tag="mission_preview", logger=logger)
        context_swapped = True

    def reset_game_wrapper() -> None:
        nonlocal context_swapped
        # Stop chopper warning beeps on game reset
        audio.stop_chopper_warning_beeps()
        next_mission, next_helicopter, next_accumulator, next_prev_stats = reset_game(
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
        loop_ctx.mission = next_mission
        loop_ctx.helicopter = next_helicopter
        loop_ctx.accumulator = next_accumulator
        loop_ctx.prev_stats = next_prev_stats
        runtime.mission_end_return_seconds = 0.0
        loop_ctx.mission.sentiment = float(loop_ctx.campaign_sentiment)
        loop_ctx.mission.audio = audio
        audio.log_audio_channel_snapshot(tag="restart", logger=logger)
        gamepad_buttons.reset()
        runtime.city_objective_overlay_timer = 0.0
        runtime.vip_kia_overlay_timer = 0.0
        runtime.vip_kia_overlay_shown = False
        runtime.meal_truck_driver_mode = False
        runtime.meal_truck_lift_command_extended = False
        runtime.bus_driver_mode = False
        
        # Initialize mission-specific airport runtime state for setup/reset paths.
        loop_ctx.airport_runtime = configure_airport_runtime_for_mission(
            selected_mission_id=selected_mission_id,
            mission=loop_ctx.mission,
            ground_y=heli_settings.ground_y,
            previous_runtime=loop_ctx.airport_runtime,
            hostage_deadline_s=120.0,
        )

        preload_mission_sprites(selected_mission_id, selected_chopper_asset)
        context_swapped = True

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
    mission, helicopter, accumulator, prev_stats, campaign_sentiment, airport_runtime = load_frame_locals_from_context(
        loop_ctx=loop_ctx
    )
    
    while running:
        frame_dt = clock.tick(120) / 1000.0
        accumulator += frame_dt
        context_swapped = False

        vip_overlay_state = update_vip_overlay_state(
            mission=mission,
            vip_kia_overlay_timer=runtime.vip_kia_overlay_timer,
            vip_kia_overlay_shown=runtime.vip_kia_overlay_shown,
        )
        runtime.vip_kia_overlay_timer = vip_overlay_state.vip_kia_overlay_timer
        runtime.vip_kia_overlay_shown = vip_overlay_state.vip_kia_overlay_shown

        weather_runtime = advance_weather_runtime(
            debug_mode=runtime.debug_mode,
            debug_weather_modes=debug_weather_modes,
            frame_dt=frame_dt,
            weather_mode=runtime.weather_mode,
            weather_timer=runtime.weather_timer,
            weather_duration=runtime.weather_duration,
            hud_disabled_timer=runtime.hud_disabled_timer,
            rain=rain,
            fog=fog,
            dust=dust,
            lightning=lightning,
            helicopter=helicopter,
            heli_settings=heli_settings,
            window=window,
        )
        apply_weather_runtime_update(
            runtime=runtime,
            weather_runtime=weather_runtime,
            set_toast=set_toast,
        )

        skip_hint = build_skip_hint(joysticks)

        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and handle_global_debug_keydown(
                key=event.key,
                mission=mission,
                set_toast=set_toast,
                toggle_thermal_mode=toggle_thermal_mode,
                enemy_kind_barak_mrad=EnemyKind.BARAK_MRAD,
                barak_state_deploy=BARAK_STATE_DEPLOY,
            ):
                continue
            elif event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.JOYDEVICEADDED:
                handle_joy_device_added(event.device_index, joysticks=joysticks, logger=logger, set_toast=set_toast)
            elif event.type == pygame.JOYDEVICEREMOVED:
                handle_joy_device_removed(event.instance_id, joysticks=joysticks, logger=logger, set_toast=set_toast)
                gamepad_buttons.clear_on_disconnect()
            elif event.type == pygame.KEYDOWN:
                keydown_result = handle_keydown_event(
                    event,
                    mode=mode,
                    mission=mission,
                    controls=controls,
                    pause_focus=runtime.pause_focus,
                    quit_confirm=runtime.quit_confirm,
                    debug_mode=runtime.debug_mode,
                    debug_weather_index=runtime.debug_weather_index,
                    debug_weather_modes=debug_weather_modes,
                    selected_mission_id=selected_mission_id,
                    meal_truck_driver_mode=runtime.meal_truck_driver_mode,
                    meal_truck_lift_command_extended=runtime.meal_truck_lift_command_extended,
                    bus_driver_mode=runtime.bus_driver_mode,
                    airport_meal_truck_state=airport_runtime.meal_truck_state,
                    airport_bus_state=airport_runtime.bus_state,
                    airport_tech_state=airport_runtime.tech_state,
                    helicopter=helicopter,
                    heli_ground_y=heli_settings.ground_y,
                    audio=audio,
                    logger=logger,
                    set_toast=set_toast,
                    set_console_log_debug=set_console_log_debug,
                    set_debug_weather_mode=set_debug_weather_mode,
                    chopper_choices=chopper_choices,
                    mission_choices=mission_choices,
                    muted=runtime.muted,
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
                    selected_chopper_index=selected_chopper_index,
                    selected_chopper_asset=selected_chopper_asset,
                    debug=debug,
                    helicopter_weapon_locked=chopper_weapons_locked(
                        meal_truck_driver_mode=bool(runtime.meal_truck_driver_mode),
                        bus_driver_mode=bool(runtime.bus_driver_mode),
                        engineer_remote_control_active=bool(getattr(mission, "engineer_remote_control_active", False)),
                    ),
                )
                (
                    running,
                    mode,
                    selected_mission_index,
                    selected_mission_id,
                    selected_chopper_index,
                    selected_chopper_asset,
                    debug,
                ) = apply_keydown_result(
                    running=running,
                    mode=mode,
                    runtime=runtime,
                    selected_mission_index=selected_mission_index,
                    selected_mission_id=selected_mission_id,
                    selected_chopper_index=selected_chopper_index,
                    selected_chopper_asset=selected_chopper_asset,
                    debug=debug,
                    keydown_result=keydown_result,
                )
                if not running:
                    continue
            elif event.type == pygame.JOYBUTTONDOWN:
                if logger:
                    logger.debug("GAMEPAD BUTTONDOWN: button=%s", event.button)
                joybutton_result = handle_joybuttondown_event(
                    button=event.button,
                    mode=mode,
                    pause_focus=runtime.pause_focus,
                    set_toast=set_toast,
                    audio=audio,
                    selected_mission_id=selected_mission_id,
                    mission=mission,
                    helicopter=helicopter,
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
                    chopper_weapons_locked=chopper_weapons_locked,
                    Facing=Facing,
                )
                mode = apply_joybutton_result(
                    mode=mode,
                    runtime=runtime,
                    joybutton_result=joybutton_result,
                )

        # Check if we transitioned from select_chopper to cutscene via keyboard
        # (gamepad path handles this inline)
        if runtime.prev_loop_mode == "select_chopper" and mode == "cutscene" and cutscenes.mission.video is None:
            mode = start_mission_intro_or_playing(
                cutscenes.mission,
                assets_dir=assets_dir,
                logger=logger,
                mission_id=selected_mission_id,
            )

        # Defer city satellite SFX until gameplay actually begins.
        if runtime.prev_loop_mode == "select_chopper" and mode in ("cutscene", "playing") and selected_mission_id == "city":
            runtime.city_satellite_sfx_pending = True

        if runtime.city_satellite_sfx_pending and mode == "playing":
            play_satellite_reallocating()
            runtime.city_satellite_sfx_pending = False
        
        # Update previous mode for next iteration
        runtime.prev_loop_mode = mode

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
            pause_flow = handle_gamepad_pause_flow(
                mode=mode,
                pause_focus=runtime.pause_focus,
                just_paused_with_start=runtime.just_paused_with_start,
                quit_confirm=runtime.quit_confirm,
                start_down=start_down,
                prev_btn_start_down=prev_btn_start_down,
                b_down=b_down,
                prev_btn_b_down=prev_btn_b_down,
                a_down=a_down,
                prev_btn_a_down=prev_btn_a_down,
                audio=audio,
                logger=logger,
            )
            mode = pause_flow.mode
            runtime.pause_focus = pause_flow.pause_focus
            runtime.just_paused_with_start = pause_flow.just_paused_with_start
            runtime.quit_confirm = pause_flow.quit_confirm
            running = bool(running and pause_flow.running)


            if mode != "paused":
                nonpaused_result = handle_nonpaused_gamepad_mode_flow(
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
                    selected_mission_index=selected_mission_index,
                    selected_mission_id=selected_mission_id,
                    selected_chopper_asset=selected_chopper_asset,
                    chopper_choices=chopper_choices,
                    mission_choices=mission_choices,
                    audio=audio,
                    set_toast=set_toast,
                    play_satellite_reallocating=play_satellite_reallocating,
                    reset_game=reset_game_wrapper,
                    start_mission_intro_or_playing_fn=lambda mission_id: start_mission_intro_or_playing(
                        cutscenes.mission,
                        assets_dir=assets_dir,
                        logger=logger,
                        mission_id=mission_id,
                    ),
                    skip_intro=lambda: skip_intro(cutscenes.intro),
                    skip_mission_cutscene=lambda: skip_mission_cutscene(cutscenes.mission),
                    apply_mission_preview=apply_mission_preview_wrapper,
                )
                (
                    mode,
                    selected_chopper_index,
                    selected_mission_index,
                    selected_mission_id,
                    selected_chopper_asset,
                ) = apply_nonpaused_gamepad_result(
                    mode=mode,
                    selected_chopper_index=selected_chopper_index,
                    selected_mission_index=selected_mission_index,
                    selected_mission_id=selected_mission_id,
                    selected_chopper_asset=selected_chopper_asset,
                    nonpaused_result=nonpaused_result,
                )

            elif mode == "paused":
                (
                    runtime.pause_focus,
                    mode,
                    running,
                    selected_chopper_index,
                    selected_chopper_asset,
                    runtime.muted,
                    runtime.quit_confirm,
                ) = handle_paused_gamepad_mode_flow(
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
                    mode=mode,
                    running=running,
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
                    apply_paused_menu_decision=apply_paused_menu_decision,
                    apply_paused_gameplay_shortcuts=apply_paused_gameplay_shortcuts,
                    flares=flares,
                    meal_truck_driver_mode=runtime.meal_truck_driver_mode,
                    bus_driver_mode=runtime.bus_driver_mode,
                    mission=mission,
                    spawn_projectile_from_helicopter_logged=spawn_projectile_from_helicopter_logged,
                    try_start_flare_salvo=try_start_flare_salvo,
                    toggle_doors_with_logging=toggle_doors_with_logging,
                    boarded_count=boarded_count,
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

        if context_swapped:
            # Wrappers can swap mission/helicopter/session objects during keyboard/gamepad handling.
            mission, helicopter, accumulator, prev_stats, campaign_sentiment, airport_runtime = (
                load_frame_locals_from_context(loop_ctx=loop_ctx)
            )

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
        
        driver_inputs = build_driver_inputs(
            mode=mode,
            helicopter_input=helicopter_input,
            kb_tilt_left=kb_tilt_left,
            kb_tilt_right=kb_tilt_right,
            gp_tilt_left=gp_tilt_left,
            gp_tilt_right=gp_tilt_right,
            meal_truck_driver_mode=runtime.meal_truck_driver_mode,
            meal_truck_lift_command_extended=runtime.meal_truck_lift_command_extended,
            bus_driver_mode=runtime.bus_driver_mode,
        )
        helicopter_input = driver_inputs.helicopter_input
        truck_driver_input = driver_inputs.truck_driver_input
        bus_driver_input = driver_inputs.bus_driver_input

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
                    airport_update = apply_airport_playing_tick_update(
                        context=AirportRuntimeContext(
                            airport_runtime=airport_runtime,
                            bus_driver_input=bus_driver_input,
                            bus_driver_mode=runtime.bus_driver_mode,
                            truck_driver_input=truck_driver_input,
                            meal_truck_driver_mode=runtime.meal_truck_driver_mode,
                            meal_truck_lift_command_extended=runtime.meal_truck_lift_command_extended,
                        ),
                        tick_dt=tick.dt,
                        audio=audio,
                        helicopter=helicopter,
                        mission=mission,
                        heli_settings=heli_settings,
                        set_toast=set_toast,
                        logger=logger,
                    )
                    runtime.meal_truck_driver_mode = airport_update.meal_truck_driver_mode
                    runtime.meal_truck_lift_command_extended = airport_update.meal_truck_lift_command_extended
                
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
            weather_mode=runtime.weather_mode,
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
                weather_mode=runtime.weather_mode,
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
            if runtime.weather_mode == "storm":
                storm_clouds.draw(target, layer='black')
            # HUD/targeting disabled by lightning
            if mode == "playing":
                runtime.vip_kia_overlay_timer, runtime.city_objective_overlay_timer = draw_playing_hud_and_overlays(
                    target=target,
                    screen=screen,
                    mission=mission,
                    helicopter=helicopter,
                    hud_disabled_timer=runtime.hud_disabled_timer,
                    vip_kia_overlay_timer=runtime.vip_kia_overlay_timer,
                    city_objective_overlay_timer=runtime.city_objective_overlay_timer,
                    frame_dt=frame_dt,
                    draw_hud_fn=draw_hud,
                    driver_mode_active=runtime.meal_truck_driver_mode,
                    debug_mode=runtime.debug_mode,
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
                debug_mode=runtime.debug_mode,
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

        # Persist frame-local updates to shared loop context.
        store_frame_locals_to_context(
            loop_ctx=loop_ctx,
            mission=mission,
            helicopter=helicopter,
            accumulator=accumulator,
            prev_stats=prev_stats,
            campaign_sentiment=campaign_sentiment,
            airport_runtime=airport_runtime,
        )

    # Ensure all mixer channels are silenced before quitting the app.
    try:
        if audio is not None and hasattr(audio, "stop_persistent_channels"):
            audio.stop_persistent_channels()
        if pygame.mixer.get_init():
            pygame.mixer.stop()
            pygame.mixer.music.stop()
            pygame.mixer.quit()
    except Exception:
        pass

    pygame.quit()


if __name__ == "__main__":
    run()
