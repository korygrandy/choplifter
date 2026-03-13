from typing import Callable

from ..render.backgrounds import bg_asset_exists

def apply_mission_preview(
    create_mission_and_helicopter: Callable,
    heli_settings,
    selected_mission_id,
    selected_chopper_asset,
    take_mission_stats_snapshot: Callable,
    boarded_count: Callable,
    sky_smoke,
    audio,
    set_toast: Callable,
    mission,
):
    mission, helicopter = create_mission_and_helicopter(
        heli_settings=heli_settings,
        mission_id=selected_mission_id,
        chopper_asset=selected_chopper_asset,
    )
    accumulator = 0.0
    sky_smoke.reset()
    if hasattr(audio, "stop_persistent_channels"):
        audio.stop_persistent_channels()
    else:
        audio.stop_flying()
    prev_stats = take_mission_stats_snapshot(mission, boarded_count=boarded_count)
    bg = getattr(mission, "bg_asset", "")
    if bg and not bg_asset_exists(str(bg)) and set_toast:
        set_toast(f"Missing background: {bg}")
    return mission, helicopter, accumulator, prev_stats

def reset_game(
    create_mission_and_helicopter: Callable,
    heli_settings,
    selected_mission_id,
    selected_chopper_asset,
    take_mission_stats_snapshot: Callable,
    boarded_count: Callable,
    sky_smoke,
    audio,
    reset_flares: Callable,
    logger,
    flares,
):
    mission, helicopter = create_mission_and_helicopter(
        heli_settings=heli_settings,
        mission_id=selected_mission_id,
        chopper_asset=selected_chopper_asset,
    )
    accumulator = 0.0
    sky_smoke.reset()
    if hasattr(audio, "stop_persistent_channels"):
        audio.stop_persistent_channels()
    else:
        audio.stop_flying()
    prev_stats = take_mission_stats_snapshot(mission, boarded_count=boarded_count)
    reset_flares(flares)
    logger.info("RESET: mission restarted")
    logger.info(f"DOORS: after reset | doors_open={helicopter.doors_open}")
    return mission, helicopter, accumulator, prev_stats
