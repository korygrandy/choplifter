from __future__ import annotations

import logging
import math
import random
from typing import Callable

from . import haptics
from .game_types import EnemyKind, HostageState, ProjectileKind
from .helicopter import Facing, Helicopter
from .math2d import Vec2, clamp
from .mission_helpers import (
    _hits_circle,
    _log_compound_health_if_needed,
    _projectile_hits_enemy,
    on_foot,
)
from .mission_state import MissionState
from .settings import HelicopterSettings


def _barak_should_apply_damage(*, grounded: bool, in_lz: bool) -> bool:
    """BARAK missiles are safe only while grounded inside the LZ/base zone."""
    return not (grounded and in_lz)


def _barak_ground_impact_can_damage(*, grounded: bool, in_lz: bool, impact_hits_helicopter: bool) -> bool:
    """Grounded-outside-LZ fallback: near-ground missile impacts can still damage."""
    return bool(grounded and impact_hits_helicopter and (not in_lz))


def _barak_target_point(helicopter: Helicopter) -> Vec2:
    """Preferred BARAK impact point: front-mid section of the helicopter nose."""
    if helicopter.facing is Facing.RIGHT:
        x_off = 32.0
    elif helicopter.facing is Facing.LEFT:
        x_off = -32.0
    else:
        x_off = 10.0
    return Vec2(helicopter.pos.x + x_off, helicopter.pos.y + 2.0)


def _angle_diff(current: float, target: float) -> float:
    return (target - current + math.pi) % (2.0 * math.pi) - math.pi


def _turn_toward_angle(*, current: float, target: float, max_step: float) -> float:
    if max_step <= 0.0:
        return target
    delta = _angle_diff(current, target)
    if abs(delta) <= max_step:
        return target
    return current + math.copysign(max_step, delta)


def _barak_roll_diversion(*, chance: float, random_value: float | None = None) -> bool:
    chance = clamp(float(chance), 0.0, 1.0)
    if chance <= 0.0:
        return False
    if chance >= 1.0:
        return True
    rv = random.random() if random_value is None else float(random_value)
    return rv <= chance


def _barak_find_flare_decoy(
    *,
    mission: MissionState,
    missile_pos: Vec2,
    radius: float,
    max_flare_age_s: float,
) -> Vec2 | None:
    flare_system = getattr(mission, "flares", None)
    particles = getattr(flare_system, "particles", None)
    if not particles:
        return None

    radius = max(0.0, float(radius))
    max_flare_age_s = max(0.0, float(max_flare_age_s))
    if radius <= 0.0 or max_flare_age_s <= 0.0:
        return None

    radius2 = radius * radius
    nearest: Vec2 | None = None
    nearest_d2: float | None = None

    for fp in particles:
        pos = getattr(fp, "pos", None)
        if pos is None:
            continue

        age = float(getattr(fp, "age", 9999.0))
        ttl = float(getattr(fp, "ttl", 0.0))
        if age < 0.0 or age > max_flare_age_s or age >= ttl:
            continue

        dx = float(pos.x) - missile_pos.x
        dy = float(pos.y) - missile_pos.y
        d2 = dx * dx + dy * dy
        if d2 > radius2:
            continue

        if nearest_d2 is None or d2 < nearest_d2:
            nearest = Vec2(float(pos.x), float(pos.y))
            nearest_d2 = d2

    return nearest


def _barak_homing_target(
    *,
    mission: MissionState,
    missile: object,
    helicopter: Helicopter,
    dt: float,
) -> tuple[Vec2, bool]:
    tuning = mission.tuning
    if not bool(getattr(missile, "flare_seen_post_liftoff", False)):
        return _barak_target_point(helicopter), False

    flare_pos = _barak_find_flare_decoy(
        mission=mission,
        missile_pos=missile.pos,
        radius=float(getattr(tuning, "barak_flare_diversion_radius", 0.0)),
        max_flare_age_s=float(getattr(tuning, "barak_flare_diversion_max_flare_age_s", 0.0)),
    )

    if not bool(getattr(missile, "flare_diversion_resolved", False)):
        chance = float(getattr(tuning, "barak_flare_diversion_chance", 1.0))
        missile.flare_diversion_allowed = _barak_roll_diversion(chance=chance)
        missile.flare_diversion_resolved = True

    if bool(getattr(missile, "flare_diversion_allowed", False)):
        heli_target = _barak_target_point(helicopter)

        if int(getattr(missile, "diversion_miss_side", 0)) == 0:
            side_hint = (flare_pos.x - heli_target.x) if flare_pos is not None else (missile.pos.x - heli_target.x)
            missile.diversion_miss_side = 1 if side_hint >= 0.0 else -1

        spin_rate_deg = float(getattr(tuning, "barak_flare_spin_rate_deg", 520.0))
        missile.diversion_spin_phase = float(getattr(missile, "diversion_spin_phase", 0.0)) + (
            math.radians(max(0.0, spin_rate_deg)) * max(0.0, dt)
        )

        near_miss_radius = max(24.0, float(getattr(tuning, "barak_flare_near_miss_radius_px", 34.0)))
        spin_amp = max(0.0, float(getattr(tuning, "barak_flare_spin_amplitude_px", 10.0)))
        side = 1.0 if int(getattr(missile, "diversion_miss_side", 1)) >= 0 else -1.0
        phase = float(getattr(missile, "diversion_spin_phase", 0.0))
        passed_nose = bool(getattr(missile, "diversion_pass_armed", False))

        if not passed_nose:
            # Phase 1: sell a near-hit by driving almost through the nose line with small side bias.
            offset_x = (side * near_miss_radius * 0.55) + (math.cos(phase) * spin_amp * 0.45)
            offset_y = math.sin(phase) * spin_amp * 0.35
        else:
            # Phase 2: after passing the nose, peel away in a wider arc before detonation.
            offset_x = (side * near_miss_radius * 2.20) + (math.cos(phase) * spin_amp * 1.35)
            offset_y = (-near_miss_radius * 0.90) + (math.sin(phase) * spin_amp * 1.10)
        return Vec2(heli_target.x + offset_x, heli_target.y + offset_y), True

    return _barak_target_point(helicopter), False


def _barak_diversion_collision_target(*, mission: MissionState, missile: object, helicopter: Helicopter) -> Vec2:
    base = _barak_target_point(helicopter)
    if not (
        bool(getattr(missile, "flare_seen_post_liftoff", False))
        and bool(getattr(missile, "flare_diversion_allowed", False))
    ):
        return base

    side = int(getattr(missile, "diversion_miss_side", 0))
    if side == 0:
        side = 1 if missile.pos.x >= base.x else -1

    near_miss_radius = max(26.0, float(getattr(mission.tuning, "barak_flare_near_miss_radius_px", 42.0)))
    # Keep the collision center outside normal direct-hit radius while still looking like a close shave.
    collision_offset = max(28.0, near_miss_radius * 0.9)
    return Vec2(base.x + (1.0 if side >= 0 else -1.0) * collision_offset, base.y)


def _barak_is_successfully_diverted(missile: object) -> bool:
    return bool(getattr(missile, "flare_seen_post_liftoff", False)) and bool(
        getattr(missile, "flare_diversion_allowed", False)
    )


def _barak_should_explode_after_near_miss(
    *,
    missile: object,
    distance_to_nose: float,
    arm_radius: float,
    detonate_distance: float,
) -> bool:
    armed = bool(getattr(missile, "diversion_pass_armed", False))
    prev_dist = float(getattr(missile, "diversion_prev_nose_distance", -1.0))

    if (not armed) and distance_to_nose <= arm_radius:
        missile.diversion_pass_armed = True
        armed = True

    should_explode = bool(
        armed
        and prev_dist >= 0.0
        and distance_to_nose >= detonate_distance
        and distance_to_nose > prev_dist + 1.0
    )
    missile.diversion_prev_nose_distance = distance_to_nose
    return should_explode


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
            if p.missile_state != "liftoff" and float(getattr(mission, "flare_invuln_seconds", 0.0)) > 0.0:
                p.flare_seen_post_liftoff = True

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
                target, diverted = _barak_homing_target(
                    mission=mission,
                    missile=p,
                    helicopter=helicopter,
                    dt=dt,
                )
                dx = target.x - p.pos.x
                dy = target.y - p.pos.y
                desired_angle = math.atan2(dy, dx)
                speed = 360.0 * 3.0
                if diverted:
                    max_turn_rate_deg = float(getattr(mission.tuning, "barak_flare_diversion_turn_rate_deg", 220.0))
                    max_turn_step = max(0.0, math.radians(max_turn_rate_deg)) * dt
                    current_angle = float(getattr(p, "current_angle", desired_angle))
                    p.current_angle = _turn_toward_angle(
                        current=current_angle,
                        target=desired_angle,
                        max_step=max_turn_step,
                    )
                else:
                    # Preserve pre-diversion hit reliability: non-diverted BARAK homing tracks directly.
                    p.current_angle = desired_angle
                if diverted and logger is not None:
                    logger.debug("BARAK_DIVERTED: target=(%.1f, %.1f)", target.x, target.y)
                p.vel = Vec2(math.cos(p.current_angle) * speed, math.sin(p.current_angle) * speed)

                if diverted:
                    nose = _barak_target_point(helicopter)
                    dist_to_nose = math.hypot(p.pos.x - nose.x, p.pos.y - nose.y)
                    arm_radius = max(
                        30.0,
                        float(getattr(mission.tuning, "barak_flare_near_miss_arm_radius_px", 54.0)),
                    )
                    detonate_distance = max(
                        arm_radius + 6.0,
                        float(getattr(mission.tuning, "barak_flare_post_pass_explode_distance_px", 68.0)),
                    )
                    if _barak_should_explode_after_near_miss(
                        missile=p,
                        distance_to_nose=dist_to_nose,
                        arm_radius=arm_radius,
                        detonate_distance=detonate_distance,
                    ):
                        mission.explosions.emit_fire_plume(p.pos, strength=0.78)
                        mission.explosions.emit_explosion(p.pos, strength=0.64)
                        mission.impact_sparks.emit_hit(p.pos, p.vel, strength=1.08)
                        mission.burning.add_site(p.pos, intensity=0.26)
                        if logger is not None:
                            logger.debug("BARAK_DIVERTED_NEAR_MISS_DETONATE: dist=%.1f", dist_to_nose)
                        p.alive = False
                        continue

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
            if getattr(p, "is_barak_missile", False):
                barak_target = _barak_diversion_collision_target(
                    mission=mission,
                    missile=p,
                    helicopter=helicopter,
                )
                diverted_collision = _barak_is_successfully_diverted(p)
                hit_radius = 14.0 if diverted_collision else 22.0
            else:
                barak_target = helicopter.pos
                hit_radius = 26.0
            if _hits_circle(p.pos, barak_target, radius=hit_radius):
                if getattr(p, "is_barak_missile", False):
                    in_lz = bool(mission.base.contains_point(helicopter.pos))
                    apply_damage = (not diverted_collision) and _barak_should_apply_damage(
                        grounded=bool(helicopter.grounded),
                        in_lz=in_lz,
                    )
                    if logger is not None:
                        logger.debug(
                            "BARAK_COLLISION: mode=direct_hit diverted=%s grounded=%s in_lz=%s apply_damage=%s target=(%.1f,%.1f)",
                            diverted_collision,
                            bool(helicopter.grounded),
                            in_lz,
                            apply_damage,
                            barak_target.x,
                            barak_target.y,
                        )
                    mission.explosions.emit_fire_plume(barak_target, strength=1.0)
                    mission.explosions.emit_explosion(barak_target, strength=0.85)
                    mission.impact_sparks.emit_hit(barak_target, p.vel, strength=1.35)
                    mission.burning.add_site(barak_target, intensity=0.55)
                    if apply_damage:
                        damage_helicopter(mission, helicopter, 18.0, logger, source="BARAK_MISSILE")
                elif p.kind is ProjectileKind.ENEMY_ARTILLERY:
                    mission.stats.artillery_hits += 1
                    mission.impact_sparks.emit_hit(p.pos, p.vel, strength=1.25)
                    damage_helicopter(mission, helicopter, 10.0, logger, source="ARTILLERY")
                else:
                    mission.impact_sparks.emit_hit(p.pos, p.vel, strength=0.95)
                    damage_helicopter(mission, helicopter, 10.0, logger, source="ENEMY_BULLET")
                p.alive = False
                continue

        # Ground collision.
        if p.pos.y >= heli.ground_y - 6.0:
            if getattr(p, "is_barak_missile", False):
                in_lz = bool(mission.base.contains_point(helicopter.pos))
                barak_target = _barak_diversion_collision_target(
                    mission=mission,
                    missile=p,
                    helicopter=helicopter,
                )
                diverted_collision = _barak_is_successfully_diverted(p)
                near_ground_radius = 22.0 if diverted_collision else 36.0
                near_ground_impact = _hits_circle(p.pos, barak_target, radius=near_ground_radius)
                apply_damage = (not diverted_collision) and _barak_ground_impact_can_damage(
                    grounded=bool(helicopter.grounded),
                    in_lz=in_lz,
                    impact_hits_helicopter=near_ground_impact,
                )
                impact_pos = barak_target if apply_damage else p.pos
                if logger is not None:
                    logger.debug(
                        "BARAK_COLLISION: mode=ground_impact diverted=%s grounded=%s in_lz=%s near=%s apply_damage=%s target=(%.1f,%.1f)",
                        diverted_collision,
                        bool(helicopter.grounded),
                        in_lz,
                        near_ground_impact,
                        apply_damage,
                        barak_target.x,
                        barak_target.y,
                    )
                mission.explosions.emit_fire_plume(impact_pos, strength=0.92)
                mission.explosions.emit_explosion(impact_pos, strength=0.72)
                mission.impact_sparks.emit_hit(impact_pos, p.vel, strength=1.20)
                mission.burning.add_site(impact_pos, intensity=0.40)
                if apply_damage:
                    damage_helicopter(mission, helicopter, 18.0, logger, source="BARAK_MISSILE")
            elif p.kind is ProjectileKind.BOMB:
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
