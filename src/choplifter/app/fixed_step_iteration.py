from __future__ import annotations

from dataclasses import dataclass

from .airport_update import AirportRuntimeContext, apply_airport_playing_tick_update
from .game_update import run_playing_fixed_step


@dataclass
class PlayingFixedStepIterationResult:
    mode: str
    campaign_sentiment: float
    mission_end_return_seconds: float
    doors_open_before_cutscene: bool
    meal_truck_driver_mode: bool
    meal_truck_lift_command_extended: bool
    continue_fixed_loop: bool


def run_playing_fixed_step_iteration(
    *,
    mode: str,
    mission: object,
    helicopter: object,
    helicopter_input: object,
    tick_dt: float,
    physics: object,
    heli_settings: object,
    audio: object,
    flares: object,
    screenshake: object,
    screenshake_enabled: bool,
    logger: object,
    prev_stats: object,
    boarded_count: object,
    set_toast: object,
    mission_end_delay_s: float,
    campaign_sentiment: float,
    mission_end_return_seconds: float,
    doors_open_before_cutscene: bool,
    mission_cutscene_state: object,
    assets_dir: object,
    update_flares_fn: object,
    update_helicopter_fn: object,
    hostage_crush_check_fn: object,
    rough_landing_feedback_fn: object,
    update_mission_fn: object,
    start_mission_cutscene_fn: object,
    selected_mission_id: str,
    airport_runtime: object,
    bus_driver_input: object,
    bus_driver_mode: bool,
    truck_driver_input: object,
    meal_truck_driver_mode: bool,
    meal_truck_lift_command_extended: bool,
) -> PlayingFixedStepIterationResult:
    """Run one playing fixed-step iteration and apply airport per-tick updates when enabled."""
    if mode != "playing":
        return PlayingFixedStepIterationResult(
            mode=mode,
            campaign_sentiment=float(campaign_sentiment),
            mission_end_return_seconds=float(mission_end_return_seconds),
            doors_open_before_cutscene=bool(doors_open_before_cutscene),
            meal_truck_driver_mode=bool(meal_truck_driver_mode),
            meal_truck_lift_command_extended=bool(meal_truck_lift_command_extended),
            continue_fixed_loop=False,
        )

    playing_step = run_playing_fixed_step(
        mode=mode,
        mission=mission,
        helicopter=helicopter,
        helicopter_input=helicopter_input,
        tick_dt=tick_dt,
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
        mission_end_delay_s=mission_end_delay_s,
        campaign_sentiment=campaign_sentiment,
        mission_end_return_seconds=mission_end_return_seconds,
        doors_open_before_cutscene=doors_open_before_cutscene,
        mission_cutscene_state=mission_cutscene_state,
        assets_dir=assets_dir,
        update_flares_fn=update_flares_fn,
        update_helicopter_fn=update_helicopter_fn,
        hostage_crush_check_fn=hostage_crush_check_fn,
        rough_landing_feedback_fn=rough_landing_feedback_fn,
        update_mission_fn=update_mission_fn,
        start_mission_cutscene_fn=start_mission_cutscene_fn,
    )

    next_meal_truck_driver_mode = bool(meal_truck_driver_mode)
    next_meal_truck_lift_command_extended = bool(meal_truck_lift_command_extended)

    if selected_mission_id == "airport":
        airport_update = apply_airport_playing_tick_update(
            context=AirportRuntimeContext(
                airport_runtime=airport_runtime,
                bus_driver_input=bus_driver_input,
                bus_driver_mode=bus_driver_mode,
                truck_driver_input=truck_driver_input,
                meal_truck_driver_mode=next_meal_truck_driver_mode,
                meal_truck_lift_command_extended=next_meal_truck_lift_command_extended,
            ),
            tick_dt=tick_dt,
            audio=audio,
            helicopter=helicopter,
            mission=mission,
            heli_settings=heli_settings,
            set_toast=set_toast,
            logger=logger,
        )
        next_meal_truck_driver_mode = airport_update.meal_truck_driver_mode
        next_meal_truck_lift_command_extended = airport_update.meal_truck_lift_command_extended

    return PlayingFixedStepIterationResult(
        mode=playing_step.next_mode,
        campaign_sentiment=float(playing_step.campaign_sentiment),
        mission_end_return_seconds=float(playing_step.mission_end_return_seconds),
        doors_open_before_cutscene=bool(playing_step.doors_open_before_cutscene),
        meal_truck_driver_mode=next_meal_truck_driver_mode,
        meal_truck_lift_command_extended=next_meal_truck_lift_command_extended,
        continue_fixed_loop=bool(playing_step.continue_fixed_loop),
    )
