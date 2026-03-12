from .game_types import EnemyKind
from .barak_mrad import BARAK_STATE_DEPLOY

import pygame

from .audio_extra import play_satellite_reallocating
from .helicopter import Facing, update_helicopter
from .mission import update_mission
from .mission_helpers import boarded_count
from .mission_hostages import hostage_crush_check_logged
from .mission_player_fire import spawn_projectile_from_helicopter_logged
# --- Airport Special Ops mission modules ---
from .settings import DebugSettings, FixedTickSettings, HelicopterSettings, WindowSettings
from .physics_config import load_physics_settings
from .app.cutscenes import (
    skip_intro,
    start_mission_intro_or_playing,
    start_mission_cutscene,
    skip_mission_cutscene,
)
from .app.input import build_skip_hint
from .app.feedback import rough_landing_feedback, update_screenshake_target
from .app.flares import reset_flares, try_start_flare_salvo, update_flares
from .app.ui_constants import MISSION_END_RETURN_DELAY_S
from .app.session import create_mission_and_helicopter, initialize_main_loop_context
from .app.flow import apply_mission_preview, reset_game
from .app.stats_snapshot import take_mission_stats_snapshot
from .app.accessibility_toggles import toggle_particles, toggle_flashes, toggle_screenshake
from .app.doors import toggle_doors_with_logging
from .app.airport_runtime_flags import sync_airport_runtime_flags
from .app.fixed_step_preamble import prepare_fixed_step_preamble
from .app.frame_inputs import read_frame_input_snapshot
from .app.gamepad_frame_flow import process_active_gamepad_frame
from .app.post_fixed_step_phase import run_post_fixed_step_phase
from .app.run_bootstrap import initialize_run_bootstrap
from .app.run_shutdown import finalize_run_shutdown
from .app.setup_wrappers import apply_mission_preview_to_context, reset_game_to_context
from .app.loop_mode_adjustments import apply_post_input_mode_adjustments
from .app.weapon_lock import chopper_weapons_locked
from .app.airport_session import configure_airport_runtime_for_mission, create_empty_airport_runtime
from .app.main_loop_context_sync import load_frame_locals_from_context
from .sprite_preloader import preload_mission_sprites
from .game_logging import set_console_log_debug
from .app.game_update import (
    build_helicopter_input,
)
from .app.fixed_step_loop import run_fixed_step_loop
from .app.frame_update import (
    run_frame_preamble,
)
from .app.event_loop import (
    process_pygame_events,
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

    bootstrap = initialize_run_bootstrap(window=window, debug_weather_modes=debug_weather_modes)
    logger = bootstrap.logger
    controls = bootstrap.controls
    accessibility = bootstrap.accessibility
    audio = bootstrap.audio
    joysticks = bootstrap.joysticks
    screenshake = bootstrap.screenshake
    toast = bootstrap.toast
    gamepad_buttons = bootstrap.gamepad_buttons
    set_toast = bootstrap.set_toast
    particles_enabled = bootstrap.particles_enabled
    flashes_enabled = bootstrap.flashes_enabled
    screenshake_enabled = bootstrap.screenshake_enabled
    screen = bootstrap.screen
    assets_dir = bootstrap.assets_dir
    cutscenes = bootstrap.cutscenes
    clock = bootstrap.clock
    overlay = bootstrap.overlay
    sky_smoke = bootstrap.sky_smoke
    rain = bootstrap.rain
    fog = bootstrap.fog
    dust = bootstrap.dust
    lightning = bootstrap.lightning
    storm_clouds = bootstrap.storm_clouds
    mission_choices = bootstrap.mission_choices
    selected_mission_index = bootstrap.selected_mission_index
    selected_mission_id = bootstrap.selected_mission_id
    chopper_choices = bootstrap.chopper_choices
    selected_chopper_index = bootstrap.selected_chopper_index
    selected_chopper_asset = bootstrap.selected_chopper_asset
    mode = bootstrap.mode
    runtime = bootstrap.runtime
    flares = bootstrap.flares
    loop_ctx = initialize_main_loop_context(
        heli_settings=heli_settings,
        selected_mission_id=selected_mission_id,
        selected_chopper_asset=selected_chopper_asset,
        audio=audio,
        create_mission_and_helicopter_fn=create_mission_and_helicopter,
        take_mission_stats_snapshot_fn=take_mission_stats_snapshot,
        boarded_count_fn=boarded_count,
        configure_airport_runtime_for_mission_fn=configure_airport_runtime_for_mission,
        create_empty_airport_runtime_fn=create_empty_airport_runtime,
    )
    context_swapped = False

    def apply_mission_preview_wrapper() -> None:
        nonlocal context_swapped
        apply_mission_preview_to_context(
            loop_ctx=loop_ctx,
            runtime=runtime,
            create_mission_and_helicopter_fn=create_mission_and_helicopter,
            heli_settings=heli_settings,
            selected_mission_id=selected_mission_id,
            selected_chopper_asset=selected_chopper_asset,
            take_mission_stats_snapshot_fn=take_mission_stats_snapshot,
            boarded_count_fn=boarded_count,
            sky_smoke=sky_smoke,
            audio=audio,
            set_toast=set_toast,
            apply_mission_preview_fn=apply_mission_preview,
            logger=logger,
        )
        context_swapped = True

    def reset_game_wrapper() -> None:
        nonlocal context_swapped
        reset_game_to_context(
            loop_ctx=loop_ctx,
            runtime=runtime,
            create_mission_and_helicopter_fn=create_mission_and_helicopter,
            heli_settings=heli_settings,
            selected_mission_id=selected_mission_id,
            selected_chopper_asset=selected_chopper_asset,
            take_mission_stats_snapshot_fn=take_mission_stats_snapshot,
            boarded_count_fn=boarded_count,
            sky_smoke=sky_smoke,
            audio=audio,
            reset_flares_fn=reset_flares,
            logger=logger,
            flares=flares,
            reset_game_fn=reset_game,
            gamepad_buttons=gamepad_buttons,
            configure_airport_runtime_for_mission_fn=configure_airport_runtime_for_mission,
            preload_mission_sprites_fn=preload_mission_sprites,
        )
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

        frame_preamble = run_frame_preamble(
            mission=mission,
            runtime=runtime,
            frame_dt=frame_dt,
            debug_weather_modes=debug_weather_modes,
            rain=rain,
            fog=fog,
            dust=dust,
            lightning=lightning,
            helicopter=helicopter,
            heli_settings=heli_settings,
            window=window,
            joysticks=joysticks,
            set_toast=set_toast,
            build_skip_hint_fn=build_skip_hint,
        )
        skip_hint = frame_preamble.skip_hint

        event_dispatch = process_pygame_events(
            running=running,
            mode=mode,
            runtime=runtime,
            mission=mission,
            controls=controls,
            debug_weather_modes=debug_weather_modes,
            selected_mission_index=selected_mission_index,
            selected_mission_id=selected_mission_id,
            selected_chopper_index=selected_chopper_index,
            selected_chopper_asset=selected_chopper_asset,
            debug=debug,
            airport_runtime=airport_runtime,
            helicopter=helicopter,
            heli_ground_y=heli_settings.ground_y,
            chopper_choices=chopper_choices,
            mission_choices=mission_choices,
            audio=audio,
            logger=logger,
            set_toast=set_toast,
            set_console_log_debug=set_console_log_debug,
            set_debug_weather_mode=set_debug_weather_mode,
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
            facing_enum=Facing,
            debug_settings=DebugSettings,
            boarded_count=boarded_count,
            flares=flares,
            chopper_weapons_locked_fn=chopper_weapons_locked,
            toggle_thermal_mode=toggle_thermal_mode,
            enemy_kind_barak_mrad=EnemyKind.BARAK_MRAD,
            barak_state_deploy=BARAK_STATE_DEPLOY,
            joysticks=joysticks,
            gamepad_buttons=gamepad_buttons,
        )
        running = event_dispatch.running
        mode = event_dispatch.mode
        selected_mission_index = event_dispatch.selected_mission_index
        selected_mission_id = event_dispatch.selected_mission_id
        selected_chopper_index = event_dispatch.selected_chopper_index
        selected_chopper_asset = event_dispatch.selected_chopper_asset
        debug = event_dispatch.debug

        mode = apply_post_input_mode_adjustments(
            mode=mode,
            selected_mission_id=selected_mission_id,
            runtime=runtime,
            cutscene_video=cutscenes.mission.video,
            start_mission_intro_or_playing_fn=lambda mission_id: start_mission_intro_or_playing(
                cutscenes.mission,
                assets_dir=assets_dir,
                logger=logger,
                mission_id=mission_id,
            ),
            play_satellite_reallocating_fn=play_satellite_reallocating,
        ).mode

        frame_inputs = read_frame_input_snapshot(
            controls=controls,
            joysticks=joysticks,
            gamepad_buttons=gamepad_buttons,
            gamepad_deadzone=float(accessibility.gamepad_deadzone),
            trigger_threshold=float(accessibility.trigger_threshold),
        )
        kb_tilt_left = frame_inputs.kb_tilt_left
        kb_tilt_right = frame_inputs.kb_tilt_right
        kb_lift_up = frame_inputs.kb_lift_up
        kb_lift_down = frame_inputs.kb_lift_down
        kb_brake = frame_inputs.kb_brake

        gp_tilt_left = False
        gp_tilt_right = False
        gp_lift_up = False
        gp_lift_down = False

        active_gamepad = frame_inputs.active_gamepad

        if active_gamepad is not None:
            gamepad_frame = process_active_gamepad_frame(
                active_gamepad=active_gamepad,
                running=running,
                mode=mode,
                runtime=runtime,
                selected_chopper_index=selected_chopper_index,
                selected_mission_index=selected_mission_index,
                selected_mission_id=selected_mission_id,
                selected_chopper_asset=selected_chopper_asset,
                debug=debug,
                debug_settings=DebugSettings,
                mission=mission,
                helicopter=helicopter,
                audio=audio,
                logger=logger,
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
                toggle_particles=toggle_particles_wrapper,
                toggle_flashes=toggle_flashes_wrapper,
                toggle_screenshake=toggle_screenshake_wrapper,
                apply_paused_menu_decision=None,
                apply_paused_gameplay_shortcuts=None,
                spawn_projectile_from_helicopter_logged=spawn_projectile_from_helicopter_logged,
                try_start_flare_salvo=try_start_flare_salvo,
                toggle_doors_with_logging=toggle_doors_with_logging,
                boarded_count=boarded_count,
                chopper_weapons_locked=chopper_weapons_locked,
                facing_enum=Facing,
                chopper_choices=chopper_choices,
                mission_choices=mission_choices,
                flares=flares,
                airport_runtime=airport_runtime,
                gamepad_buttons=gamepad_buttons,
            )
            running = gamepad_frame.running
            mode = gamepad_frame.mode
            selected_chopper_index = gamepad_frame.selected_chopper_index
            selected_mission_index = gamepad_frame.selected_mission_index
            selected_mission_id = gamepad_frame.selected_mission_id
            selected_chopper_asset = gamepad_frame.selected_chopper_asset
            debug = gamepad_frame.debug
            gp_tilt_left = gamepad_frame.gp_tilt_left
            gp_tilt_right = gamepad_frame.gp_tilt_right
            gp_lift_up = gamepad_frame.gp_lift_up
            gp_lift_down = gamepad_frame.gp_lift_down

        fixed_step_preamble = prepare_fixed_step_preamble(
            context_swapped=context_swapped,
            loop_ctx=loop_ctx,
            mission=mission,
            helicopter=helicopter,
            accumulator=accumulator,
            prev_stats=prev_stats,
            campaign_sentiment=campaign_sentiment,
            airport_runtime=airport_runtime,
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
            runtime=runtime,
            selected_mission_id=selected_mission_id,
            build_helicopter_input_fn=build_helicopter_input,
            sync_airport_runtime_flags_fn=sync_airport_runtime_flags,
        )
        mission = fixed_step_preamble.mission
        helicopter = fixed_step_preamble.helicopter
        accumulator = fixed_step_preamble.accumulator
        prev_stats = fixed_step_preamble.prev_stats
        campaign_sentiment = fixed_step_preamble.campaign_sentiment
        airport_runtime = fixed_step_preamble.airport_runtime
        helicopter_input = fixed_step_preamble.helicopter_input
        truck_driver_input = fixed_step_preamble.truck_driver_input
        bus_driver_input = fixed_step_preamble.bus_driver_input
        fixed_step_loop = run_fixed_step_loop(
            mode=mode,
            accumulator=accumulator,
            tick_dt=tick.dt,
            mission=mission,
            helicopter=helicopter,
            helicopter_input=helicopter_input,
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
            selected_mission_id=selected_mission_id,
            airport_runtime=airport_runtime,
            bus_driver_input=bus_driver_input,
            bus_driver_mode=runtime.bus_driver_mode,
            truck_driver_input=truck_driver_input,
            meal_truck_driver_mode=runtime.meal_truck_driver_mode,
            meal_truck_lift_command_extended=runtime.meal_truck_lift_command_extended,
        )
        mode = fixed_step_loop.mode
        accumulator = fixed_step_loop.accumulator
        campaign_sentiment = fixed_step_loop.campaign_sentiment
        runtime.mission_end_return_seconds = fixed_step_loop.mission_end_return_seconds
        runtime.doors_open_before_cutscene = fixed_step_loop.doors_open_before_cutscene
        runtime.meal_truck_driver_mode = fixed_step_loop.meal_truck_driver_mode
        runtime.meal_truck_lift_command_extended = fixed_step_loop.meal_truck_lift_command_extended

        mode = run_post_fixed_step_phase(
            mode=mode,
            frame_dt=frame_dt,
            runtime=runtime,
            toast=toast,
            cutscenes=cutscenes,
            mission=mission,
            helicopter=helicopter,
            selected_mission_id=selected_mission_id,
            particles_enabled=particles_enabled,
            heli_settings=heli_settings,
            airport_runtime=airport_runtime,
            screenshake=screenshake,
            screenshake_enabled=screenshake_enabled,
            audio=audio,
            sky_smoke=sky_smoke,
            rain=rain,
            fog=fog,
            dust=dust,
            storm_clouds=storm_clouds,
            lightning=lightning,
            screen=screen,
            window=window,
            update_screenshake_target_fn=update_screenshake_target,
            skip_hint=skip_hint,
            mission_choices=mission_choices,
            selected_mission_index=selected_mission_index,
            chopper_choices=chopper_choices,
            selected_chopper_index=selected_chopper_index,
            debug_show_overlay=bool(debug.show_overlay),
            flashes_enabled=bool(flashes_enabled),
            overlay=overlay,
            fps=float(clock.get_fps()),
            draw_debug_overlay_fn=draw_debug_overlay,
            set_toast=set_toast,
            logger=logger,
            loop_ctx=loop_ctx,
            accumulator=accumulator,
            prev_stats=prev_stats,
            campaign_sentiment=campaign_sentiment,
        )

    finalize_run_shutdown(audio=audio)


if __name__ == "__main__":
    run()
