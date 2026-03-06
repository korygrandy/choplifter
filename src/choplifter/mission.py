
from __future__ import annotations

import logging
from .math2d import Vec2
from .mission_configs import (
    LevelConfig,
    get_mission_config_by_id,
)
from .settings import HelicopterSettings
from .helicopter import Helicopter, Facing
from .game_types import ProjectileKind, HostageState, EnemyKind



from .entities import Projectile, BaseZone, MissionStats

from .mission_state import MissionState
from .mission_helpers import boarded_count, on_foot, _update_sentiment, _update_fuel, _log_progress_if_changed
from .enemy_update import _update_enemies
from .mission_projectiles import _update_projectiles
from .mission_crash import _handle_crash_and_respawn
from .mission_compounds import _update_compounds_and_release
from .mission_hostages import (
    _update_hostages,
    _handle_unload,
    hostage_crush_check as _hostage_crush_check,
    hostage_crush_check_logged as _hostage_crush_check_logged,
)
from .mission_combat import _mine_explode, _spawn_enemy_bullet_toward, _damage_helicopter


def spawn_projectile_from_helicopter(mission: MissionState, helicopter: Helicopter) -> None:
    # Minimal: side-facing shoots bullets, forward-facing drops a bomb.
    if mission.ended:
        return

    if helicopter.facing is Facing.FORWARD:
        mission.projectiles.append(
            Projectile(
                kind=ProjectileKind.BOMB,
                pos=Vec2(helicopter.pos.x, helicopter.pos.y + 10.0),
                vel=Vec2(0.0, 3.0),
                ttl=2.5,
            )
        )
        return

    direction = -1.0 if helicopter.facing is Facing.LEFT else 1.0
    mission.projectiles.append(
        Projectile(
            kind=ProjectileKind.BULLET,
            pos=Vec2(helicopter.pos.x + direction * 40.0, helicopter.pos.y),
            vel=Vec2(direction * 95.0, 0.0),
            ttl=1.2,
        )
    )


def spawn_projectile_from_helicopter_logged(
    mission: MissionState,
    helicopter: Helicopter,
    logger: logging.Logger | None,
) -> None:
    spawn_projectile_from_helicopter(mission, helicopter)
    if logger is None:
        return
    if helicopter.facing is Facing.FORWARD:
        logger.info("Fire: BOMB")
    else:
        logger.info("Fire: BULLET")


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

    # World-space particle systems must be advanced every tick.
    mission.burning.update(dt)
    mission.impact_sparks.update(dt)
    mission.jet_trails.update(dt)
    mission.dust_storm.update(dt, heli_pos=helicopter.pos, heli_vel=helicopter.vel, ground_y=heli.ground_y)
    mission.heli_damage_fx.update(dt, heli_pos=helicopter.pos, heli_vel=helicopter.vel, damage=helicopter.damage)
    mission.explosions.update(dt)
    mission.flares.update(dt)

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
    if mission.ended:
        return

    mission.ended = True
    mission.end_text = end_text
    mission.end_reason = reason

    if logger is not None:
        logger.info("END: %s", reason)
        logger.info(
            "END_STATS: saved=%d boarded=%d kia_by_player=%d kia_by_enemy=%d lost_in_transit=%d enemies_destroyed=%d crashes=%d",
            mission.stats.saved,
            boarded_count(mission),
            mission.stats.kia_by_player,
            mission.stats.kia_by_enemy,
            mission.stats.lost_in_transit,
            mission.stats.enemies_destroyed,
            mission.crashes,
        )
