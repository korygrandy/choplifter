from __future__ import annotations

import logging
import math
from typing import Callable

from . import haptics
from .game_types import EnemyKind, HostageState, ProjectileKind
from .helicopter import Helicopter
from .math2d import Vec2, clamp
from .mission_helpers import (
    _hits_circle,
    _log_compound_health_if_needed,
    _projectile_hits_enemy,
    on_foot,
)
from .mission_state import MissionState
from .settings import HelicopterSettings


def _update_projectiles(
    mission: MissionState,
    dt: float,
    heli: HelicopterSettings,
    logger: logging.Logger | None,
    helicopter: Helicopter,
    *,
    damage_helicopter: Callable[[MissionState, Helicopter, float, logging.Logger | None, str], None],
) -> None:
    gravity = 28.0

    for p in mission.projectiles:
        if not p.alive:
            continue

        p.ttl -= dt
        if p.ttl <= 0.0:
            p.alive = False
            continue

        if p.kind is ProjectileKind.BOMB:
            p.vel.y += gravity * dt

        p.pos.x += p.vel.x * dt
        p.pos.y += p.vel.y * dt

        # BARAK MRAD missile: staged behavior (liftoff -> rotate -> homing).
        if getattr(p, "is_barak_missile", False):
            if p.missile_state == "liftoff":
                if p.launch_pos is None:
                    p.launch_pos = p.pos.copy()
                p.current_angle = math.pi / 2
                p.vel = Vec2(0.0, -240.0)
                if p.pos.y <= p.launch_pos.y - 40.0:
                    dx = helicopter.pos.x - p.pos.x
                    if dx > 0:
                        p.rotate_dir = -1
                        p.target_angle = math.pi
                    else:
                        p.rotate_dir = 1
                        p.target_angle = 0.0
                    p.missile_state = "rotating"
                    p.rotation_progress = 0.0
                    p.vel = Vec2(0.0, 0.0)
            elif p.missile_state == "rotating":
                start_angle = math.pi / 2
                end_angle = p.target_angle
                p.rotation_progress += dt * 2.0
                if p.rotation_progress >= 1.0:
                    p.rotation_progress = 1.0
                    p.current_angle = end_angle
                    p.missile_state = "homing"
                else:
                    p.current_angle = start_angle + (end_angle - start_angle) * p.rotation_progress
                    p.vel = Vec2(0.0, 0.0)
            elif p.missile_state == "homing":
                dx = helicopter.pos.x - p.pos.x
                dy = (helicopter.pos.y + 24.0) - p.pos.y
                angle = math.atan2(dy, dx)
                speed = 360.0 * 3.0
                p.vel = Vec2(math.cos(angle) * speed, math.sin(angle) * speed)
                p.current_angle = angle

        # Enemy collision (player projectiles only).
        if p.kind in (ProjectileKind.BULLET, ProjectileKind.BOMB):
            for e in mission.enemies:
                if not e.alive:
                    continue
                if _projectile_hits_enemy(p, e, heli, mission.tuning):
                    if p.kind is ProjectileKind.BULLET:
                        e.health -= 10.0
                    else:
                        e.health -= 40.0
                    if e.health <= 0.0:
                        e.alive = False
                        mission.stats.enemies_destroyed += 1
                        if e.kind is EnemyKind.TANK:
                            mission.stats.tanks_destroyed += 1
                            # Persist a burning effect at the destroyed cannon/tank location.
                            mission.burning.add_site(e.pos, intensity=1.0)
                        if logger is not None:
                            logger.info("ENEMY_DOWN: %s", e.kind.name)
                    p.alive = False
                    break

        if not p.alive:
            continue

        # Helicopter collision (enemy projectiles only).
        if p.kind in (ProjectileKind.ENEMY_BULLET, ProjectileKind.ENEMY_ARTILLERY):
            if _hits_circle(p.pos, helicopter.pos, radius=26.0):
                if getattr(p, "is_barak_missile", False):
                    damage_helicopter(mission, helicopter, 18.0, logger, source="BARAK_MISSILE")
                elif p.kind is ProjectileKind.ENEMY_ARTILLERY:
                    mission.stats.artillery_hits += 1
                    mission.impact_sparks.emit_hit(p.pos, p.vel, strength=1.25)
                    damage_helicopter(mission, helicopter, 10.0, logger, source="ARTILLERY")
                else:
                    damage_helicopter(mission, helicopter, 10.0, logger, source="ENEMY_BULLET")
                p.alive = False
                continue

        # Ground collision.
        if p.pos.y >= heli.ground_y - 6.0:
            if p.kind is ProjectileKind.BOMB:
                _bomb_explode(mission, p.pos, logger)
            p.alive = False
            continue

        # Compound collision (player projectiles only).
        for c in mission.compounds:
            if c.health <= 0:
                continue
            if c.contains_point(p.pos):
                if p.kind is ProjectileKind.BULLET:
                    c.health -= 12.0
                elif p.kind is ProjectileKind.BOMB:
                    c.health -= 40.0
                else:
                    continue
                _log_compound_health_if_needed(c, logger, reason="hit")
                p.alive = False
                break

        if not p.alive:
            continue

        # Hostage hits.
        for h in mission.hostages:
            if not on_foot(h):
                continue
            dx = h.pos.x - p.pos.x
            dy = h.pos.y - p.pos.y
            if dx * dx + dy * dy <= 12.0 * 12.0:
                h.state = HostageState.KIA
                if p.kind in (ProjectileKind.ENEMY_BULLET, ProjectileKind.ENEMY_ARTILLERY):
                    mission.stats.kia_by_enemy += 1
                else:
                    mission.stats.kia_by_player += 1
                p.alive = False
                break

    # Compact list.
    mission.projectiles = [p for p in mission.projectiles if p.alive]


def _bomb_explode(mission: MissionState, pos: Vec2, logger: logging.Logger | None) -> None:
    # Small AoE for collateral + compound damage.
    radius = 42.0
    r2 = radius * radius

    for c in mission.compounds:
        if c.health <= 0:
            continue
        cx = clamp(pos.x, c.pos.x, c.pos.x + c.width)
        cy = clamp(pos.y, c.pos.y, c.pos.y + c.height)
        dx = pos.x - cx
        dy = pos.y - cy
        if dx * dx + dy * dy <= r2:
            c.health -= 30.0
            _log_compound_health_if_needed(c, logger, reason="blast")

    for h in mission.hostages:
        if not on_foot(h):
            continue
        dx = h.pos.x - pos.x
        dy = h.pos.y - pos.y
        if dx * dx + dy * dy <= r2:
            h.state = HostageState.KIA
            mission.stats.kia_by_player += 1

    for e in mission.enemies:
        if not e.alive:
            continue
        dx = e.pos.x - pos.x
        dy = e.pos.y - pos.y
        if dx * dx + dy * dy <= r2:
            e.health -= 55.0
            if e.health <= 0.0:
                e.alive = False
                mission.stats.enemies_destroyed += 1
                if e.kind is EnemyKind.TANK:
                    mission.stats.tanks_destroyed += 1
                    mission.burning.add_site(e.pos, intensity=1.0)
                    haptics.rumble_tank_destroyed(logger=logger)
                if logger is not None:
                    logger.info("ENEMY_DOWN: %s", e.kind.name)
