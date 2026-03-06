
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
from .mission_helpers import boarded_count, on_foot, _update_sentiment, _update_fuel, _log_progress_if_changed
from .mission_player_fire import spawn_projectile_from_helicopter, spawn_projectile_from_helicopter_logged
from .mission_particles import _update_world_particles
from .enemy_update import _update_enemies
from .mission_projectiles import _update_projectiles
from .mission_crash import _handle_crash_and_respawn
from .mission_compounds import _update_compounds_and_release
from .mission_ending import _end_mission as _end_mission_impl
from .mission_hostages import (
    _update_hostages,
    _handle_unload,
    hostage_crush_check as _hostage_crush_check,
    hostage_crush_check_logged as _hostage_crush_check_logged,
)
from .mission_combat import _mine_explode, _spawn_enemy_bullet_toward, _damage_helicopter


def update_mission(
    mission: MissionState,
    helicopter: Helicopter,
    dt: float,
    heli: HelicopterSettings,
    logger: logging.Logger | None = None,
) -> None:
    if mission.ended:
        return

    mission.elapsed_seconds += dt

    if mission.invuln_seconds > 0.0:
        mission.invuln_seconds = max(0.0, mission.invuln_seconds - dt)

    if mission.flare_invuln_seconds > 0.0:
        mission.flare_invuln_seconds = max(0.0, mission.flare_invuln_seconds - dt)

    _update_fuel(mission, helicopter, dt, logger)
    if helicopter.fuel <= 0.0:
        _end_mission(mission, "THE END", "OUT OF FUEL", logger)
        return

    _update_world_particles(mission, helicopter, dt, heli)

    _update_enemies(
        mission,
        helicopter,
        dt,
        heli,
        logger,
        mine_explode=_mine_explode,
        spawn_enemy_bullet_toward=_spawn_enemy_bullet_toward,
        damage_helicopter=_damage_helicopter,
    )

    _update_projectiles(
        mission,
        dt,
        heli,
        logger,
        helicopter,
        damage_helicopter=_damage_helicopter,
    )
    _update_compounds_and_release(mission, heli, logger)
    _update_hostages(mission, helicopter, dt, heli, boarded_count_fn=boarded_count)
    _handle_unload(mission, helicopter, heli, dt)

    _handle_crash_and_respawn(mission, helicopter, dt, heli, logger, end_mission=_end_mission)
    if mission.ended:
        return

    _update_sentiment(mission)

    _log_progress_if_changed(mission, logger)

    if mission.stats.saved >= 20:
        _end_mission(mission, "THE END", "RESCUE SUCCESS", logger)


def hostage_crush_check(
    mission: MissionState,
    helicopter: Helicopter,
    last_landing_vy: float,
    *,
    safe_landing_vy: float,
) -> None:
    _hostage_crush_check(
        mission,
        helicopter,
        last_landing_vy,
        safe_landing_vy=safe_landing_vy,
        on_foot_fn=on_foot,
    )


def hostage_crush_check_logged(
    mission: MissionState,
    helicopter: Helicopter,
    last_landing_vy: float,
    *,
    safe_landing_vy: float,
    logger: logging.Logger | None,
) -> None:
    _hostage_crush_check_logged(
        mission,
        helicopter,
        last_landing_vy,
        safe_landing_vy=safe_landing_vy,
        logger=logger,
        on_foot_fn=on_foot,
    )


def _end_mission(mission: MissionState, end_text: str, reason: str, logger: logging.Logger | None) -> None:
    _end_mission_impl(
        mission,
        end_text,
        reason,
        logger,
        boarded_count_fn=boarded_count,
    )
