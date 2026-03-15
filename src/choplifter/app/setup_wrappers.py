from __future__ import annotations

from .objective_overlay import get_mission_objective_overlay_duration


def apply_mission_preview_to_context(
    *,
    loop_ctx: object,
    runtime: object,
    create_mission_and_helicopter_fn: object,
    heli_settings: object,
    selected_mission_id: str,
    selected_chopper_asset: str,
    take_mission_stats_snapshot_fn: object,
    boarded_count_fn: object,
    sky_smoke: object,
    audio: object,
    set_toast: object,
    apply_mission_preview_fn: object,
    logger: object,
) -> None:
    """Apply mission preview and update shared loop context/runtime fields."""
    preview_mission, preview_helicopter, preview_accumulator, preview_prev_stats = apply_mission_preview_fn(
        create_mission_and_helicopter_fn,
        heli_settings,
        selected_mission_id,
        selected_chopper_asset,
        take_mission_stats_snapshot_fn,
        boarded_count_fn,
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


def reset_game_to_context(
    *,
    loop_ctx: object,
    runtime: object,
    create_mission_and_helicopter_fn: object,
    heli_settings: object,
    selected_mission_id: str,
    selected_chopper_asset: str,
    take_mission_stats_snapshot_fn: object,
    boarded_count_fn: object,
    sky_smoke: object,
    audio: object,
    reset_flares_fn: object,
    logger: object,
    flares: object,
    reset_game_fn: object,
    gamepad_buttons: object,
    configure_airport_runtime_for_mission_fn: object,
    preload_mission_sprites_fn: object,
) -> None:
    """Reset mission state and sync loop context/runtime fields for a fresh run."""
    audio.stop_chopper_warning_beeps()

    next_mission, next_helicopter, next_accumulator, next_prev_stats = reset_game_fn(
        create_mission_and_helicopter_fn,
        heli_settings,
        selected_mission_id,
        selected_chopper_asset,
        take_mission_stats_snapshot_fn,
        boarded_count_fn,
        sky_smoke,
        audio,
        reset_flares_fn,
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
    runtime.city_objective_overlay_timer = get_mission_objective_overlay_duration(
        mission_id=selected_mission_id,
    )
    runtime.vip_kia_overlay_timer = 0.0
    runtime.vip_kia_overlay_shown = False
    runtime.tech_kia_overlay_timer = 0.0
    runtime.tech_kia_overlay_shown = False
    runtime.hostage_kia_overlay_timer = 0.0
    runtime.hostage_kia_overlay_shown = False
    runtime.meal_truck_driver_mode = False
    runtime.meal_truck_lift_command_extended = False
    runtime.bus_driver_mode = False

    loop_ctx.airport_runtime = configure_airport_runtime_for_mission_fn(
        selected_mission_id=selected_mission_id,
        mission=loop_ctx.mission,
        ground_y=heli_settings.ground_y,
        previous_runtime=loop_ctx.airport_runtime,
        hostage_deadline_s=120.0,
    )

    preload_mission_sprites_fn(selected_mission_id, selected_chopper_asset)
