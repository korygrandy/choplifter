from __future__ import annotations

"""Mission helper functions extracted from mission.py."""

import logging
import math
from typing import TYPE_CHECKING

from .barak_mrad import BARAK_LAUNCHER_VISIBLE_STATES
from .entities import Compound, Enemy, Hostage, Projectile
from .game_types import EnemyKind, HostageState
from .math2d import Vec2, clamp
from .mission_configs import MissionTuning
from .settings import HelicopterSettings

if TYPE_CHECKING:
    from .helicopter import Helicopter
    from .mission_state import MissionState


SENTIMENT_WEIGHT_SAVED = 2.5
SENTIMENT_WEIGHT_KIA_PLAYER = -4.0
SENTIMENT_WEIGHT_KIA_ENEMY = -2.5
SENTIMENT_WEIGHT_LOST_IN_TRANSIT = -3.5
# Guardrail: cap how much sentiment can move in one update tick.
SENTIMENT_MAX_DELTA_PER_UPDATE = 18.0


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


def _distance_point_to_segment_sq(point: Vec2, start: Vec2, end: Vec2) -> float:
    seg_x = end.x - start.x
    seg_y = end.y - start.y
    seg_len_sq = seg_x * seg_x + seg_y * seg_y
    if seg_len_sq <= 1e-6:
        dx = point.x - start.x
        dy = point.y - start.y
        return dx * dx + dy * dy

    t = clamp(((point.x - start.x) * seg_x + (point.y - start.y) * seg_y) / seg_len_sq, 0.0, 1.0)
    nearest_x = start.x + seg_x * t
    nearest_y = start.y + seg_y * t
    dx = point.x - nearest_x
    dy = point.y - nearest_y
    return dx * dx + dy * dy


def _distance_segment_to_segment_sq(a0: Vec2, a1: Vec2, b0: Vec2, b1: Vec2) -> float:
    # Closest-distance approximation for short projectile steps against thin geometry.
    return min(
        _distance_point_to_segment_sq(a0, b0, b1),
        _distance_point_to_segment_sq(a1, b0, b1),
        _distance_point_to_segment_sq(b0, a0, a1),
        _distance_point_to_segment_sq(b1, a0, a1),
    )


def _projectile_hits_barak_launcher(p: Projectile, e: Enemy, previous_pos: Vec2 | None = None) -> bool:
    if str(getattr(e, "mrad_state", "")) not in BARAK_LAUNCHER_VISIBLE_STATES:
        return False

    angle = float(getattr(e, "launcher_angle", 0.0))
    ext_progress = clamp(float(getattr(e, "launcher_ext_progress", 0.0)), 0.0, 1.0)
    launcher_base = Vec2(e.pos.x - 40.0, e.pos.y - 28.0)
    launcher_length = 36.0 + 44.0 * ext_progress
    launcher_tip = Vec2(
        launcher_base.x + launcher_length * math.cos(angle),
        launcher_base.y - launcher_length * math.sin(angle),
    )
    launcher_radius = 12.0
    if previous_pos is None:
        return _distance_point_to_segment_sq(p.pos, launcher_base, launcher_tip) <= launcher_radius * launcher_radius
    return _distance_segment_to_segment_sq(previous_pos, p.pos, launcher_base, launcher_tip) <= launcher_radius * launcher_radius


def _projectile_hits_enemy(
    p: Projectile,
    e: Enemy,
    heli: HelicopterSettings,
    tuning: MissionTuning,
    previous_pos: Vec2 | None = None,
) -> bool:
    if e.kind is EnemyKind.TANK:
        w, h = 44.0, 18.0
        left = e.pos.x - w * 0.5
        top = heli.ground_y - h
        return left <= p.pos.x <= left + w and top <= p.pos.y <= top + h

    if e.kind is EnemyKind.BARAK_MRAD:
        # MRAP body is taller/wider than the legacy tank box, especially readable while moving.
        w, h = 56.0, 32.0
        left = e.pos.x - w * 0.5
        top = heli.ground_y - h
        body_hit = left <= p.pos.x <= left + w and top <= p.pos.y <= top + h
        return body_hit or _projectile_hits_barak_launcher(p, e, previous_pos)

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


def sentiment_band_label(sentiment: float) -> str:
    s = float(clamp(sentiment, 0.0, 100.0))
    if s >= 80.0:
        return "Excellent"
    if s >= 65.0:
        return "Good"
    if s >= 45.0:
        return "Mixed"
    if s >= 25.0:
        return "Poor"
    return "Critical"


def sentiment_progression_pressure_multiplier(sentiment: float) -> float:
    # Explicit progression tie-in by sentiment band.
    # Higher sentiment: slightly less pressure. Lower sentiment: slightly more pressure.
    band = sentiment_band_label(sentiment)
    if band == "Excellent":
        return 0.88
    if band == "Good":
        return 0.94
    if band == "Mixed":
        return 1.00
    if band == "Poor":
        return 1.10
    return 1.18


def sentiment_contributions(*, saved: int, kia_player: int, kia_enemy: int, lost_in_transit: int) -> dict[str, float]:
    return {
        "saved": float(saved) * SENTIMENT_WEIGHT_SAVED,
        "kia_player": float(kia_player) * SENTIMENT_WEIGHT_KIA_PLAYER,
        "kia_enemy": float(kia_enemy) * SENTIMENT_WEIGHT_KIA_ENEMY,
        "lost_in_transit": float(lost_in_transit) * SENTIMENT_WEIGHT_LOST_IN_TRANSIT,
    }


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
        delta_parts = sentiment_contributions(
            saved=dsaved,
            kia_player=dkia_player,
            kia_enemy=dkia_enemy,
            lost_in_transit=dlost,
        )
        delta_total = (
            float(delta_parts["saved"])
            + float(delta_parts["kia_player"])
            + float(delta_parts["kia_enemy"])
            + float(delta_parts["lost_in_transit"])
        )
        delta_total = clamp(delta_total, -SENTIMENT_MAX_DELTA_PER_UPDATE, SENTIMENT_MAX_DELTA_PER_UPDATE)
        mission.sentiment += delta_total
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
