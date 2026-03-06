
from __future__ import annotations

import logging

from .mission_configs import (
    LevelConfig,
    get_mission_config_by_id,
)
from .settings import HelicopterSettings
from .helicopter import Helicopter
from .game_types import HostageState, EnemyKind
from .entities import BaseZone, MissionStats
from .mission_state import MissionState
from .mission_helpers import boarded_count
from .mission_player_fire import spawn_projectile_from_helicopter, spawn_projectile_from_helicopter_logged
from .mission_flow import update_mission as _update_mission_impl
from .mission_ending import _end_mission
from .mission_hostages import (
    hostage_crush_check,
    hostage_crush_check_logged,
)

# Explicit compatibility surface for modules importing from mission.py.
__all__ = [
    "BaseZone",
    "EnemyKind",
    "HelicopterSettings",
    "HostageState",
    "LevelConfig",
    "MissionState",
    "MissionStats",
    "boarded_count",
    "get_mission_config_by_id",
    "hostage_crush_check",
    "hostage_crush_check_logged",
    "spawn_projectile_from_helicopter",
    "spawn_projectile_from_helicopter_logged",
    "update_mission",
]


def update_mission(
    mission: MissionState,
    helicopter: Helicopter,
    dt: float,
    heli: HelicopterSettings,
    logger: logging.Logger | None = None,
) -> None:
    _update_mission_impl(mission, helicopter, dt, heli, logger, end_mission=_end_mission)
