from __future__ import annotations

from dataclasses import dataclass

from .fixed_step_iteration import run_playing_fixed_step_iteration


@dataclass
class FixedStepLoopResult:
    mode: str
    accumulator: float
    campaign_sentiment: float
    mission_end_return_seconds: float
    doors_open_before_cutscene: bool
    meal_truck_driver_mode: bool
    meal_truck_lift_command_extended: bool


def run_fixed_step_loop(
    *,
    mode: str,
    accumulator: float,
    tick_dt: float,
    mission: object,
    helicopter: object,
    helicopter_input: object,
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
) -> FixedStepLoopResult:
    """Run the accumulator-driven fixed-step loop and return updated loop/runtime state."""
    next_mode = mode
    next_accumulator = float(accumulator)
    next_campaign_sentiment = float(campaign_sentiment)
    next_mission_end_return_seconds = float(mission_end_return_seconds)
    next_doors_open_before_cutscene = bool(doors_open_before_cutscene)
    next_meal_truck_driver_mode = bool(meal_truck_driver_mode)
    next_meal_truck_lift_command_extended = bool(meal_truck_lift_command_extended)

    while next_accumulator >= tick_dt:
        step_iteration = run_playing_fixed_step_iteration(
            mode=next_mode,
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
            campaign_sentiment=next_campaign_sentiment,
            mission_end_return_seconds=next_mission_end_return_seconds,
            doors_open_before_cutscene=next_doors_open_before_cutscene,
            mission_cutscene_state=mission_cutscene_state,
            assets_dir=assets_dir,
            update_flares_fn=update_flares_fn,
            update_helicopter_fn=update_helicopter_fn,
            hostage_crush_check_fn=hostage_crush_check_fn,
            rough_landing_feedback_fn=rough_landing_feedback_fn,
            update_mission_fn=update_mission_fn,
            start_mission_cutscene_fn=start_mission_cutscene_fn,
            selected_mission_id=selected_mission_id,
            airport_runtime=airport_runtime,
            bus_driver_input=bus_driver_input,
            bus_driver_mode=bus_driver_mode,
            truck_driver_input=truck_driver_input,
            meal_truck_driver_mode=next_meal_truck_driver_mode,
            meal_truck_lift_command_extended=next_meal_truck_lift_command_extended,
        )
        next_mode = step_iteration.mode
        next_campaign_sentiment = step_iteration.campaign_sentiment
        next_mission_end_return_seconds = step_iteration.mission_end_return_seconds
        next_doors_open_before_cutscene = step_iteration.doors_open_before_cutscene
        next_meal_truck_driver_mode = step_iteration.meal_truck_driver_mode
        next_meal_truck_lift_command_extended = step_iteration.meal_truck_lift_command_extended

        if step_iteration.continue_fixed_loop:
            continue

        next_accumulator -= tick_dt

    return FixedStepLoopResult(
        mode=next_mode,
        accumulator=next_accumulator,
        campaign_sentiment=next_campaign_sentiment,
        mission_end_return_seconds=next_mission_end_return_seconds,
        doors_open_before_cutscene=next_doors_open_before_cutscene,
        meal_truck_driver_mode=next_meal_truck_driver_mode,
        meal_truck_lift_command_extended=next_meal_truck_lift_command_extended,
    )
