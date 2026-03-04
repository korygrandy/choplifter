from __future__ import annotations

from ..helicopter import Facing, Helicopter
from ..mission import MissionState, get_mission_config_by_id


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
