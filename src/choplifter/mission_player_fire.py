from __future__ import annotations

import logging

from .entities import Projectile
from .game_types import ProjectileKind
from .helicopter import Facing, Helicopter
from .math2d import Vec2
from .mission_state import MissionState
from .supply_drops import consume_player_weapon


def spawn_projectile_from_helicopter(mission: MissionState, helicopter: Helicopter) -> bool:
    # Minimal: side-facing shoots bullets, forward-facing drops a bomb.
    if mission.ended:
        return False

    if not consume_player_weapon(mission, facing_name=helicopter.facing.name):
        return False

    if helicopter.facing is Facing.FORWARD:
        mission.projectiles.append(
            Projectile(
                kind=ProjectileKind.BOMB,
                pos=Vec2(helicopter.pos.x, helicopter.pos.y + 10.0),
                vel=Vec2(0.0, 3.0),
                ttl=2.5,
            )
        )
        return True

    direction = -1.0 if helicopter.facing is Facing.LEFT else 1.0
    mission.projectiles.append(
        Projectile(
            kind=ProjectileKind.BULLET,
            pos=Vec2(helicopter.pos.x + direction * 40.0, helicopter.pos.y),
            vel=Vec2(direction * 95.0, 0.0),
            ttl=1.2,
        )
    )
    return True


def spawn_projectile_from_helicopter_logged(
    mission: MissionState,
    helicopter: Helicopter,
    logger: logging.Logger | None,
) -> None:
    fired = spawn_projectile_from_helicopter(mission, helicopter)
    if logger is None:
        return
    if not fired:
        logger.info("Fire: DRY")
        return
    if helicopter.facing is Facing.FORWARD:
        logger.info("Fire: BOMB")
    else:
        logger.info("Fire: BULLET")
