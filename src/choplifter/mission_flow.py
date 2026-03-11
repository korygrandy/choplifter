from __future__ import annotations

import logging
from typing import Callable

from .enemy_update import _update_enemies
from .helicopter import Helicopter
from .mission_combat import _damage_helicopter, _mine_explode, _spawn_enemy_bullet_toward
from .mission_compounds import _update_compounds_and_release
from .mission_crash import _handle_crash_and_respawn
from .mission_helpers import boarded_count, _log_progress_if_changed, _update_fuel, _update_sentiment
from .mission_hostages import _handle_unload, _update_hostages
from .mission_particles import _update_world_particles
from .mission_projectiles import _update_projectiles
from .mission_state import MissionState
from .settings import HelicopterSettings


def update_mission(
    mission: MissionState,
    helicopter: Helicopter,
    dt: float,
    heli: HelicopterSettings,
    logger: logging.Logger | None = None,
    *,
    end_mission: Callable[[MissionState, str, str, logging.Logger | None], None],
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
        end_mission(mission, "THE END", "OUT OF FUEL", logger)
        return

    _update_world_particles(mission, helicopter, dt, heli)

    if hasattr(mission, "supply_drops") and mission.supply_drops is not None:
        mission.supply_drops.update(
            mission=mission,
            helicopter=helicopter,
            dt=dt,
            ground_y=heli.ground_y,
        )

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

    _handle_crash_and_respawn(mission, helicopter, dt, heli, logger, end_mission=end_mission)
    if mission.ended:
        return

    _update_sentiment(mission)

    _log_progress_if_changed(mission, logger)

    mission_id = str(getattr(mission, "mission_id", "")).lower()
    is_airport_mission = mission_id in ("airport", "airport_special_ops", "mission2", "m2")
    if (not is_airport_mission) and mission.stats.saved >= 20:
        end_mission(mission, "THE END", "RESCUE SUCCESS", logger)
