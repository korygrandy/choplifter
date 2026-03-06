from __future__ import annotations

"""Mission helper functions extracted from mission.py."""

import logging
from typing import TYPE_CHECKING

from .entities import Compound, Enemy, Hostage, Projectile
from .game_types import EnemyKind, HostageState
from .math2d import Vec2, clamp
from .mission_configs import MissionTuning
from .settings import HelicopterSettings

if TYPE_CHECKING:
    from .helicopter import Helicopter
    from .mission_state import MissionState


def boarded_count(mission: "MissionState") -> int:
    return sum(1 for h in mission.hostages if h.state is HostageState.BOARDED)


def on_foot(hostage: Hostage) -> bool:
    return hostage.state in (
        HostageState.PANIC,
        HostageState.MOVING_TO_LZ,
        HostageState.WAITING,
        HostageState.EXITING,
    )


def _hits_circle(a: Vec2, b: Vec2, radius: float) -> bool:
    dx = a.x - b.x
    dy = a.y - b.y
    return dx * dx + dy * dy <= radius * radius


def _projectile_hits_enemy(
    p: Projectile,
    e: Enemy,
    heli: HelicopterSettings,
    tuning: MissionTuning,
) -> bool:
    if e.kind is EnemyKind.TANK:
        w, h = 44.0, 18.0
        left = e.pos.x - w * 0.5
        top = heli.ground_y - h
        return left <= p.pos.x <= left + w and top <= p.pos.y <= top + h

    if e.kind is EnemyKind.JET:
        return _hits_circle(p.pos, e.pos, radius=20.0)

    if e.kind is EnemyKind.AIR_MINE:
        return _hits_circle(p.pos, e.pos, radius=tuning.mine_projectile_radius)

    return False


def _log_compound_health_if_needed(c: Compound, logger: logging.Logger | None, reason: str) -> None:
    if logger is None:
        return

    health = max(0.0, c.health)

    # Log only when health crosses buckets of 20 (avoids log spam).
    bucket = int(health // 20.0)
    if bucket == c.log_bucket:
        return

    c.log_bucket = bucket
    logger.info("Compound %s: x=%.0f health=%.0f", reason, c.pos.x, health)


def _difficulty_scale(sentiment: float) -> float:
    # Map sentiment 0..100 to a difficulty scalar -1..+1.
    # Low sentiment => more pressure; high sentiment => slightly less.
    return clamp((50.0 - clamp(sentiment, 0.0, 100.0)) / 50.0, -1.0, 1.0)


def _update_sentiment(mission: "MissionState") -> None:
    # Minimal MVP interpretation:
    # - Rescues increase sentiment
    # - Any hostage deaths decrease sentiment (player-caused more severe)
    # - Lost-in-transit decreases sentiment
    saved = mission.stats.saved
    kia_player = mission.stats.kia_by_player
    kia_enemy = mission.stats.kia_by_enemy
    lost = mission.stats.lost_in_transit

    dsaved = saved - mission._sentiment_last_saved
    dkia_player = kia_player - mission._sentiment_last_kia_player
    dkia_enemy = kia_enemy - mission._sentiment_last_kia_enemy
    dlost = lost - mission._sentiment_last_lost_in_transit

    if dsaved or dkia_player or dkia_enemy or dlost:
        mission.sentiment += dsaved * 2.5
        mission.sentiment -= dkia_player * 4.0
        mission.sentiment -= dkia_enemy * 2.5
        mission.sentiment -= dlost * 3.5
        mission.sentiment = clamp(mission.sentiment, 0.0, 100.0)

    mission._sentiment_last_saved = saved
    mission._sentiment_last_kia_player = kia_player
    mission._sentiment_last_kia_enemy = kia_enemy
    mission._sentiment_last_lost_in_transit = lost


def _update_fuel(
    mission: "MissionState",
    helicopter: "Helicopter",
    dt: float,
    logger: logging.Logger | None,
) -> None:
    if mission.ended:
        return

    # Minimal MVP-lite: fuel drains over time, refuels at base.
    tuning = mission.tuning
    # Tune: make hovering/landing feel less punishing, but fast flight costs.
    drain_base_per_s = tuning.fuel_drain_base_per_s
    drain_airborne_per_s = tuning.fuel_drain_airborne_per_s
    drain_speed_per_s = tuning.fuel_drain_speed_per_s
    refuel_per_s = tuning.fuel_refuel_per_s

    at_base = mission.base.contains_point(helicopter.pos) and helicopter.grounded
    if at_base:
        helicopter.fuel = min(100.0, helicopter.fuel + refuel_per_s * dt)
    else:
        speed = abs(helicopter.vel.x) + abs(helicopter.vel.y)
        speed_factor = clamp(speed / 50.0, 0.0, 1.0)
        drain = drain_base_per_s
        if not helicopter.grounded:
            drain += drain_airborne_per_s
            drain += drain_speed_per_s * speed_factor
        helicopter.fuel = max(0.0, helicopter.fuel - drain * dt)

    fuel_int = int(helicopter.fuel)
    if logger is not None and fuel_int != mission._last_logged_fuel_int:
        if fuel_int in (75, 50, 25, 10, 5, 0):
            logger.info("FUEL: %d", fuel_int)
    mission._last_logged_fuel_int = fuel_int


def _log_progress_if_changed(mission: "MissionState", logger: logging.Logger | None) -> None:
    if logger is None:
        return

    boarded = boarded_count(mission)
    if boarded != mission._last_logged_boarded:
        mission._last_logged_boarded = boarded
        logger.info("BOARDING: boarded=%d", boarded)

    if mission.stats.saved != mission._last_logged_saved:
        delta = mission.stats.saved - mission._last_logged_saved
        mission._last_logged_saved = mission.stats.saved
        logger.info("UNLOAD: +%d saved (total=%d)", delta, mission.stats.saved)

    if mission.stats.kia_by_player != mission._last_logged_kia_player:
        delta = mission.stats.kia_by_player - mission._last_logged_kia_player
        mission._last_logged_kia_player = mission.stats.kia_by_player
        logger.info("COLLATERAL: +%d KIA_by_player (total=%d)", delta, mission.stats.kia_by_player)

    if mission.stats.kia_by_enemy != mission._last_logged_kia_enemy:
        delta = mission.stats.kia_by_enemy - mission._last_logged_kia_enemy
        mission._last_logged_kia_enemy = mission.stats.kia_by_enemy
        logger.info("ENEMY_FIRE: +%d KIA_by_enemy (total=%d)", delta, mission.stats.kia_by_enemy)

    if mission.stats.enemies_destroyed != mission._last_logged_enemies_destroyed:
        delta = mission.stats.enemies_destroyed - mission._last_logged_enemies_destroyed
        mission._last_logged_enemies_destroyed = mission.stats.enemies_destroyed
        logger.info("ENEMIES: +%d destroyed (total=%d)", delta, mission.stats.enemies_destroyed)

    # Log sentiment as it crosses buckets (keeps logs readable).
    bucket = int(clamp(mission.sentiment, 0.0, 100.0) // 10)
    if bucket != mission._last_logged_sentiment_bucket:
        mission._last_logged_sentiment_bucket = bucket
        logger.info("SENTIMENT: %.0f", clamp(mission.sentiment, 0.0, 100.0))
