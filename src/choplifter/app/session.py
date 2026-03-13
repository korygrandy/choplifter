from __future__ import annotations

from ..helicopter import Facing, Helicopter
from ..mission_configs import get_mission_config_by_id
from ..mission_state import MissionState
from .main_loop_context import MainLoopContext


def create_mission_and_helicopter(
    *,
    heli_settings: object,
    mission_id: str,
    chopper_asset: str,
) -> tuple[MissionState, Helicopter]:
    mission = MissionState.create_from_level_config(
        heli_settings,
        get_mission_config_by_id(mission_id),
        mission_id=mission_id,
    )
    helicopter = Helicopter.spawn(
        heli_settings,
        start_x=mission.base.pos.x + mission.base.width * 0.5,
        skin_asset=chopper_asset,
    )
    helicopter.facing = Facing.LEFT
    return mission, helicopter


def initialize_main_loop_context(
    *,
    heli_settings: object,
    selected_mission_id: str,
    selected_chopper_asset: str,
    audio: object,
    create_mission_and_helicopter_fn: object,
    take_mission_stats_snapshot_fn: object,
    boarded_count_fn: object,
    configure_airport_runtime_for_mission_fn: object,
    create_empty_airport_runtime_fn: object,
) -> MainLoopContext:
    """Create initial mission, runtime-adjacent state, and shared loop context."""
    mission, helicopter = create_mission_and_helicopter_fn(
        heli_settings=heli_settings,
        mission_id=selected_mission_id,
        chopper_asset=selected_chopper_asset,
    )
    mission.audio = audio
    campaign_sentiment = float(getattr(mission, "sentiment", 50.0))
    prev_stats = take_mission_stats_snapshot_fn(mission, boarded_count=boarded_count_fn)
    airport_runtime = configure_airport_runtime_for_mission_fn(
        selected_mission_id=selected_mission_id,
        mission=mission,
        ground_y=heli_settings.ground_y,
        previous_runtime=create_empty_airport_runtime_fn(),
        hostage_deadline_s=120.0,
    )
    return MainLoopContext(
        mission=mission,
        helicopter=helicopter,
        accumulator=0.0,
        prev_stats=prev_stats,
        campaign_sentiment=campaign_sentiment,
        airport_runtime=airport_runtime,
    )
