from __future__ import annotations

from dataclasses import dataclass

from .driver_inputs import build_driver_inputs
from .main_loop_context_sync import load_frame_locals_from_context


@dataclass
class FixedStepPreambleResult:
    mission: object
    helicopter: object
    accumulator: float
    prev_stats: object
    campaign_sentiment: float
    airport_runtime: object
    helicopter_input: object
    truck_driver_input: object
    bus_driver_input: object


def prepare_fixed_step_preamble(
    *,
    context_swapped: bool,
    loop_ctx: object,
    mission: object,
    helicopter: object,
    accumulator: float,
    prev_stats: object,
    campaign_sentiment: float,
    airport_runtime: object,
    mode: str,
    kb_tilt_left: bool,
    kb_tilt_right: bool,
    kb_lift_up: bool,
    kb_lift_down: bool,
    kb_brake: bool,
    gp_tilt_left: bool,
    gp_tilt_right: bool,
    gp_lift_up: bool,
    gp_lift_down: bool,
    runtime: object,
    selected_mission_id: str,
    build_helicopter_input_fn: object,
    sync_airport_runtime_flags_fn: object,
) -> FixedStepPreambleResult:
    """Prepare loop state and driver inputs before running fixed-step simulation."""
    next_mission = mission
    next_helicopter = helicopter
    next_accumulator = float(accumulator)
    next_prev_stats = prev_stats
    next_campaign_sentiment = float(campaign_sentiment)
    next_airport_runtime = airport_runtime

    if context_swapped:
        (
            next_mission,
            next_helicopter,
            next_accumulator,
            next_prev_stats,
            next_campaign_sentiment,
            next_airport_runtime,
        ) = load_frame_locals_from_context(loop_ctx=loop_ctx)

    helicopter_input = build_helicopter_input_fn(
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

    sync_airport_runtime_flags_fn(
        mission=next_mission,
        selected_mission_id=selected_mission_id,
        airport_tech_state=next_airport_runtime.tech_state,
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

    if next_accumulator > 0.25:
        next_accumulator = 0.25

    return FixedStepPreambleResult(
        mission=next_mission,
        helicopter=next_helicopter,
        accumulator=next_accumulator,
        prev_stats=next_prev_stats,
        campaign_sentiment=next_campaign_sentiment,
        airport_runtime=next_airport_runtime,
        helicopter_input=driver_inputs.helicopter_input,
        truck_driver_input=driver_inputs.truck_driver_input,
        bus_driver_input=driver_inputs.bus_driver_input,
    )
