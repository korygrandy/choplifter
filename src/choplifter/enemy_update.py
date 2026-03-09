from __future__ import annotations

import logging
import math
import random
from typing import Callable

from .entities import Enemy, Projectile
from .game_types import EnemyKind, ProjectileKind
from .helicopter import Facing, Helicopter
from .math2d import Vec2, clamp
from .barak_mrad import (
    BARAK_STATE_DEPLOY,
    BARAK_STATE_LAUNCH,
    BARAK_STATE_MOVE,
    BARAK_STATE_RELOAD,
    BARAK_STATE_RETRACT,
)
from .mission_helpers import _difficulty_scale, _hits_circle, sentiment_progression_pressure_multiplier
from .mission_state import MissionState
from .settings import HelicopterSettings


def _transition_barak_state(e: Enemy, new_state: str, *, logger: logging.Logger | None, reason: str) -> None:
    old_state = str(getattr(e, "mrad_state", BARAK_STATE_MOVE))
    if old_state == new_state:
        return
    e.mrad_state = new_state
    e.mrad_state_seconds = 0.0
    if logger is not None:
        logger.debug("BARAK_STATE: %s -> %s (%s)", old_state, new_state, reason)


def _emit_barak_transition_fx(mission: MissionState, e: Enemy, *, strength: float) -> None:
    try:
        mission.impact_sparks.emit_hit(Vec2(e.pos.x - 32.0, e.pos.y - 26.0), Vec2(0.0, -10.0), strength=strength)
    except Exception:
        pass


def _barak_next_reload_seconds(tuning: object) -> float:
    lo = float(getattr(tuning, "barak_reload_min_seconds", getattr(tuning, "barak_reload_seconds", 4.0)))
    hi = float(getattr(tuning, "barak_reload_max_seconds", getattr(tuning, "barak_reload_seconds", 4.0)))
    lo, hi = min(lo, hi), max(lo, hi)
    return max(0.25, random.uniform(lo, hi))


def _update_enemies(
    mission: MissionState,
    helicopter: Helicopter,
    dt: float,
    heli: HelicopterSettings,
    logger: logging.Logger | None,
    *,
    mine_explode: Callable[[MissionState, Vec2, Helicopter, logging.Logger | None], None],
    spawn_enemy_bullet_toward: Callable[..., None],
    damage_helicopter: Callable[[MissionState, Helicopter, float, logging.Logger | None, str], None],
) -> None:
    difficulty = _difficulty_scale(mission.sentiment)
    tuning = mission.tuning
    mission.tank_warning_seconds = max(0.0, float(getattr(mission, "tank_warning_seconds", 0.0)) - dt)
    mission.tank_warning_cooldown_s = max(0.0, float(getattr(mission, "tank_warning_cooldown_s", 0.0)) - dt)
    mission.jet_warning_seconds = max(0.0, float(getattr(mission, "jet_warning_seconds", 0.0)) - dt)
    mission.jet_warning_cooldown_s = max(0.0, float(getattr(mission, "jet_warning_cooldown_s", 0.0)) - dt)
    mission.mine_warning_seconds = max(0.0, float(getattr(mission, "mine_warning_seconds", 0.0)) - dt)
    mission.mine_warning_cooldown_s = max(0.0, float(getattr(mission, "mine_warning_cooldown_s", 0.0)) - dt)
    mission.mine_warning_distance = float(getattr(mission, "mine_warning_distance", 9999.0))

    # Time-based pressure ramp:
    # - First 60s: easier
    # - Next 60s: ramp back to normal
    # pressure > 1 => more frequent threats; < 1 => less.
    ramp_t = clamp((mission.elapsed_seconds - 60.0) / 60.0, 0.0, 1.0)
    pressure = (0.75 * (1.0 - ramp_t)) + (1.00 * ramp_t)
    pressure *= float(sentiment_progression_pressure_multiplier(mission.sentiment))

    # Spawn a delayed initial air mine (used to keep the first minute calmer).
    if mission.pending_air_mine_pos is not None:
        mission.pending_air_mine_seconds -= dt
        if mission.pending_air_mine_seconds <= 0.0:
            mission.enemies.append(
                Enemy(
                    kind=EnemyKind.AIR_MINE,
                    pos=Vec2(mission.pending_air_mine_pos.x, mission.pending_air_mine_pos.y),
                    vel=Vec2(0.0, 0.0),
                    health=tuning.mine_health,
                    ttl=tuning.mine_ttl_s,
                )
            )
            if logger is not None:
                logger.info("MINE: spawned")
            mission.pending_air_mine_pos = None

    # Periodic air mine spawns.
    mission.mine_spawn_seconds -= dt
    if mission.mine_spawn_seconds <= 0.0:
        alive_mines = sum(1 for e in mission.enemies if e.alive and e.kind is EnemyKind.AIR_MINE)
        if alive_mines < max(0, int(tuning.mine_max_alive)):
            interval = (tuning.mine_spawn_base_interval_s / pressure) * (1.0 - 0.10 * difficulty)
            mission.mine_spawn_seconds = clamp(
                interval,
                tuning.mine_spawn_min_interval_s,
                tuning.mine_spawn_max_interval_s,
            )

            # Deterministic pseudo-random spawn height (keeps behavior stable without adding RNG state).
            # Uses elapsed time as input; returns value in [0, 1).
            r01 = math.sin(mission.elapsed_seconds * 12.9898) * 43758.5453
            r01 = r01 - math.floor(r01)
            y = tuning.mine_spawn_y_min + (tuning.mine_spawn_y_max - tuning.mine_spawn_y_min) * r01
            y = clamp(y, 60.0, heli.ground_y - 80.0)

            # Spawn ahead of the helicopter's facing direction.
            sign = 1.0 if helicopter.facing is Facing.RIGHT else -1.0
            x = helicopter.pos.x + sign * tuning.mine_spawn_margin_x
            x = clamp(x, 40.0, mission.world_width - 40.0)

            mission.enemies.append(
                Enemy(
                    kind=EnemyKind.AIR_MINE,
                    pos=Vec2(x, y),
                    vel=Vec2(0.0, 0.0),
                    health=tuning.mine_health,
                    ttl=tuning.mine_ttl_s,
                )
            )
            if logger is not None:
                logger.info("MINE: spawned")
        else:
            # Try again soon once the mine count drops.
            mission.mine_spawn_seconds = 1.0

    # Periodic jet spawns.
    mission.jet_spawn_seconds -= dt
    if mission.jet_spawn_seconds <= 0.0:
        # Slight scaling based on sentiment.
        interval = (tuning.jet_spawn_base_interval_s / pressure) * (1.0 - 0.22 * difficulty)
        mission.jet_spawn_seconds = clamp(interval, tuning.jet_spawn_min_interval_s, tuning.jet_spawn_max_interval_s)
        y = tuning.jet_spawn_y
        if helicopter.pos.x > mission.world_width * 0.5:
            x = -tuning.jet_spawn_margin_x
            vx = tuning.jet_speed_x
            mission.jet_warning_from_right = False
        else:
            x = mission.world_width + tuning.jet_spawn_margin_x
            vx = -tuning.jet_speed_x
            mission.jet_warning_from_right = True
        mission.enemies.append(
            Enemy(
                kind=EnemyKind.JET,
                pos=Vec2(x, y),
                vel=Vec2(vx, 0.0),
                health=tuning.jet_health,
                cooldown=0.6,
                ttl=tuning.jet_ttl_s,
                trail_enabled=(int(mission.elapsed_seconds * 1.7) % 2 == 0),
            )
        )
        if mission.jet_warning_cooldown_s <= 0.0:
            mission.jet_warning_seconds = 1.2
            mission.jet_warning_cooldown_s = 1.3
            if hasattr(mission, "audio") and mission.audio is not None:
                try:
                    mission.audio.play_jet_flyby()
                except Exception:
                    pass
        if logger is not None:
            logger.info("JET: spawned")

    for e in mission.enemies:
        if not e.alive:
            continue

        e.ttl -= dt
        if e.ttl <= 0.0:
            e.alive = False
            continue

        e.cooldown = max(0.0, e.cooldown - dt)
        e.fire_tell_seconds = max(0.0, e.fire_tell_seconds - dt)
        e.muzzle_flash_seconds = max(0.0, e.muzzle_flash_seconds - dt)

        # --- BARAK MRAD MOVEMENT, DEPLOYMENT, AND AIMING LOGIC ---
        if e.kind is EnemyKind.BARAK_MRAD:
            e.mrad_state_seconds = float(getattr(e, "mrad_state_seconds", 0.0)) + dt
            
            # Determine target position: use leftmost compound if available, otherwise fallback to world center
            if mission.compounds:
                leftmost = min(mission.compounds, key=lambda c: c.pos.x)
                target_x = leftmost.pos.x + leftmost.width + 24.0
            else:
                # For missions without compounds (e.g., Airport), target the middle of the world
                target_x = mission.world_width * 0.5

            # Fail-safe recovery path in case any state gets stuck.
            if e.mrad_state_seconds > max(0.5, float(getattr(tuning, "barak_state_fail_safe_s", 8.0))):
                if e.mrad_state in (BARAK_STATE_DEPLOY, BARAK_STATE_LAUNCH):
                    _transition_barak_state(e, BARAK_STATE_RETRACT, logger=logger, reason="fail_safe")
                elif e.mrad_state == BARAK_STATE_RETRACT:
                    _transition_barak_state(e, BARAK_STATE_RELOAD, logger=logger, reason="fail_safe")
                    e.mrad_reload_seconds = _barak_next_reload_seconds(tuning)
                elif e.mrad_state == BARAK_STATE_RELOAD:
                    _transition_barak_state(e, BARAK_STATE_MOVE, logger=logger, reason="fail_safe")
                else:
                    _transition_barak_state(e, BARAK_STATE_DEPLOY, logger=logger, reason="fail_safe")

            if e.mrad_state == BARAK_STATE_MOVE:
                if e.pos.x < target_x:
                    e.pos.x += e.vel.x * dt
                    if e.pos.x >= target_x:
                        e.pos.x = target_x
                        e.vel.x = 0.0
                        e.entered_screen = True
                        _transition_barak_state(e, BARAK_STATE_DEPLOY, logger=logger, reason="arrived")
                        _emit_barak_transition_fx(mission, e, strength=0.45)
                        if hasattr(mission, "audio") and mission.audio is not None:
                            if hasattr(mission.audio, "play_barak_mrad_deploy"):
                                mission.audio.play_barak_mrad_deploy()
                else:
                    e.vel.x = 0.0
                    e.entered_screen = True
                    _transition_barak_state(e, BARAK_STATE_DEPLOY, logger=logger, reason="already_in_position")
                    _emit_barak_transition_fx(mission, e, strength=0.45)
                    if hasattr(mission, "audio") and mission.audio is not None:
                        if hasattr(mission.audio, "play_barak_mrad_deploy"):
                            mission.audio.play_barak_mrad_deploy()
            elif e.mrad_state == BARAK_STATE_DEPLOY:
                # Synchronize rotation and extension to full launch posture.
                deploy_speed = float(getattr(tuning, "barak_deploy_angle_speed_rad_s", 1.5))
                ext_speed = float(getattr(tuning, "barak_deploy_extension_speed_s", 1.2))
                target_angle = math.pi / 2
                angle_done = False
                ext_done = False
                if abs(e.launcher_angle - target_angle) < deploy_speed * dt:
                    e.launcher_angle = target_angle
                    angle_done = True
                else:
                    if e.launcher_angle < target_angle:
                        e.launcher_angle += deploy_speed * dt
                    else:
                        e.launcher_angle -= deploy_speed * dt
                # Animate extension progress (0 to 1)
                if e.launcher_ext_progress < 1.0:
                    e.launcher_ext_progress += ext_speed * dt
                    if e.launcher_ext_progress > 1.0:
                        e.launcher_ext_progress = 1.0
                else:
                    ext_done = True
                if angle_done and ext_done:
                    _transition_barak_state(e, BARAK_STATE_LAUNCH, logger=logger, reason="deploy_complete")
            elif e.mrad_state == BARAK_STATE_LAUNCH:
                e.launcher_ext_progress = 1.0
                if not e.missile_fired:
                    launcher_length = 44.0 * e.launcher_ext_progress
                    missile_pos = Vec2(
                        e.pos.x - 40 + launcher_length * math.cos(e.launcher_angle),
                        e.pos.y - 28.0 - launcher_length * math.sin(e.launcher_angle),
                    )
                    missile_angle = e.launcher_angle
                    missile_speed = 120.0
                    missile_vel = Vec2(
                        math.cos(missile_angle) * missile_speed,
                        -abs(math.sin(missile_angle)) * missile_speed,
                    )
                    mission.projectiles.append(
                        Projectile(
                            kind=ProjectileKind.ENEMY_BULLET,  # Use ENEMY_BULLET for now; can define new kind if needed
                            pos=missile_pos,
                            vel=missile_vel,
                            ttl=9999.0,  # Effectively unlimited
                            source=EnemyKind.BARAK_MRAD,
                            is_barak_missile=True,
                            current_angle=missile_angle,
                        )
                    )
                    e.missile_fired = True
                    if logger is not None:
                        logger.debug("BARAK MRAD missile launched at %s", missile_pos)
                    # Play Barak MRAD missile launch SFX
                    if hasattr(mission, "audio") and mission.audio is not None:
                        if hasattr(mission.audio, "play_barak_mrad_launch"):
                            mission.audio.play_barak_mrad_launch()
                _transition_barak_state(e, BARAK_STATE_RETRACT, logger=logger, reason="launch_complete")
                _emit_barak_transition_fx(mission, e, strength=0.52)
            elif e.mrad_state == BARAK_STATE_RETRACT:
                retract_angle_speed = float(getattr(tuning, "barak_retract_angle_speed_rad_s", 1.9))
                retract_ext_speed = float(getattr(tuning, "barak_retract_extension_speed_s", 1.4))
                target_angle = 0.0
                angle_done = False
                if abs(e.launcher_angle - target_angle) <= retract_angle_speed * dt:
                    e.launcher_angle = target_angle
                    angle_done = True
                elif e.launcher_angle < target_angle:
                    e.launcher_angle += retract_angle_speed * dt
                else:
                    e.launcher_angle -= retract_angle_speed * dt

                if e.launcher_ext_progress > 0.0:
                    e.launcher_ext_progress = max(0.0, e.launcher_ext_progress - retract_ext_speed * dt)

                if angle_done and e.launcher_ext_progress <= 0.0:
                    e.missile_fired = False
                    e.mrad_reload_seconds = _barak_next_reload_seconds(tuning)
                    _transition_barak_state(e, BARAK_STATE_RELOAD, logger=logger, reason="retract_complete")
                    _emit_barak_transition_fx(mission, e, strength=0.30)
            elif e.mrad_state == BARAK_STATE_RELOAD:
                e.launcher_angle = 0.0
                e.launcher_ext_progress = 0.0
                e.mrad_reload_seconds = max(0.0, float(getattr(e, "mrad_reload_seconds", 0.0)) - dt)
                if e.mrad_reload_seconds <= 0.0:
                    _transition_barak_state(e, BARAK_STATE_MOVE, logger=logger, reason="reload_complete")
            continue

        if e.kind is EnemyKind.TANK:
            # Turret tracking logic (smooth rotation)
            dx = helicopter.pos.x - e.pos.x
            dy = helicopter.pos.y - e.pos.y
            target_angle = math.atan2(dy, dx)

            # Smoothly interpolate turret_angle toward target_angle (shortest path)
            def angle_diff(a: float, b: float) -> float:
                d = (b - a + math.pi) % (2 * math.pi) - math.pi
                return d

            max_turn_speed = 2.5  # radians/sec, tune as needed
            angle_delta = angle_diff(e.turret_angle, target_angle)
            max_step = max_turn_speed * dt
            if abs(angle_delta) < max_step:
                e.turret_angle = target_angle
            else:
                e.turret_angle += max_step if angle_delta > 0 else -max_step
                # Keep angle in [-pi, pi]
                e.turret_angle = (e.turret_angle + math.pi) % (2 * math.pi) - math.pi

            in_fire_window = (
                abs(dx) <= tuning.tank_fire_range_x
                and helicopter.pos.y <= heli.ground_y - tuning.tank_fire_min_altitude_clearance_y
            )

            if in_fire_window and e.cooldown <= 0.0:
                # Two-stage attack: first arm and show tell, then fire when tell elapses.
                if (not e.fire_tell_armed) and e.fire_tell_seconds <= 0.0:
                    e.fire_tell_armed = True
                    e.fire_tell_seconds = max(0.05, float(tuning.tank_prefire_tell_s))
                elif e.fire_tell_armed and e.fire_tell_seconds <= 0.0:
                    tank_cd = (tuning.tank_fire_base_cooldown_s / pressure) * (1.0 - 0.12 * difficulty)
                    e.cooldown = clamp(tank_cd, tuning.tank_fire_min_cooldown_s, tuning.tank_fire_max_cooldown_s)
                    e.muzzle_flash_seconds = max(0.04, float(tuning.tank_muzzle_flash_s))
                    e.fire_tell_armed = False
                    spawn_enemy_bullet_toward(
                        mission,
                        e.pos,
                        helicopter.pos,
                        kind=ProjectileKind.ENEMY_ARTILLERY,
                        source=EnemyKind.TANK,
                    )
                    mission.stats.artillery_fired += 1
                    if logger is not None:
                        logger.info("TANK_FIRE")

            # Cancel the tell if target breaks the firing window before the shot.
            if (not in_fire_window) and (e.fire_tell_seconds > 0.0 or e.fire_tell_armed):
                e.fire_tell_seconds = 0.0
                e.fire_tell_armed = False

            if e.fire_tell_seconds > 0.0 and mission.tank_warning_cooldown_s <= 0.0:
                mission.tank_warning_seconds = max(mission.tank_warning_seconds, 0.22)
                mission.tank_warning_from_right = bool(e.pos.x > helicopter.pos.x)
                mission.tank_warning_cooldown_s = 0.55

        elif e.kind is EnemyKind.JET:
            e.pos.x += e.vel.x * dt
            e.pos.y += e.vel.y * dt

            if not e.entered_screen and 0.0 <= e.pos.x <= mission.world_width:
                e.entered_screen = True
                mission.stats.jets_entered += 1
                if logger is not None:
                    logger.info("JET: entered")

            if abs(helicopter.pos.x - e.pos.x) <= tuning.jet_fire_range_x and e.cooldown <= 0.0:
                jet_cd = (tuning.jet_fire_base_cooldown_s / pressure) * (1.0 - 0.10 * difficulty)
                e.cooldown = clamp(jet_cd, tuning.jet_fire_min_cooldown_s, tuning.jet_fire_max_cooldown_s)
                spawn_enemy_bullet_toward(mission, e.pos, helicopter.pos, source=EnemyKind.JET)

            if e.entered_screen and e.trail_enabled:
                e.trail_spawn_accum += dt * 18.0
                while e.trail_spawn_accum >= 1.0:
                    e.trail_spawn_accum -= 1.0
                    mission.jet_trails.emit_trail(e.pos, e.vel)

            if _hits_circle(e.pos, helicopter.pos, radius=tuning.jet_collision_radius):
                damage_helicopter(mission, helicopter, tuning.jet_touch_damage, logger, source="JET")
                if hasattr(mission, "audio") and mission.audio is not None:
                    try:
                        mission.audio.play_midair_collision()
                    except Exception:
                        pass

        elif e.kind is EnemyKind.AIR_MINE:
            to_heli = Vec2(helicopter.pos.x - e.pos.x, helicopter.pos.y - e.pos.y)
            dist = math.hypot(to_heli.x, to_heli.y)
            if dist <= 170.0 and mission.mine_warning_cooldown_s <= 0.0:
                closing_speed = 0.0
                if dist > 0.001:
                    closing_speed = (to_heli.x * e.vel.x + to_heli.y * e.vel.y) / dist
                if closing_speed >= 35.0:
                    mission.mine_warning_seconds = max(mission.mine_warning_seconds, 0.45)
                    mission.mine_warning_distance = min(float(mission.mine_warning_distance), float(dist))
                    mission.mine_warning_cooldown_s = 0.80
            if dist > 0.001:
                nx = to_heli.x / dist
                ny = to_heli.y / dist
            else:
                nx, ny = 0.0, 0.0

            desired_speed = clamp(
                (tuning.mine_base_speed * pressure) * (1.0 + 0.15 * difficulty),
                tuning.mine_min_speed,
                tuning.mine_max_speed,
            )
            desired_vx = nx * desired_speed
            desired_vy = ny * desired_speed
            steer = tuning.mine_steer
            e.vel.x += (desired_vx - e.vel.x) * steer * dt
            e.vel.y += (desired_vy - e.vel.y) * steer * dt

            e.pos.x += e.vel.x * dt
            e.pos.y += e.vel.y * dt

            # Keep mines in the playable air space.
            e.pos.x = clamp(e.pos.x, 20.0, mission.world_width - 20.0)
            e.pos.y = clamp(e.pos.y, 50.0, heli.ground_y - 60.0)

            if _hits_circle(e.pos, helicopter.pos, radius=tuning.mine_touch_radius):
                mine_explode(mission, e.pos, helicopter, logger)
                e.alive = False

    mission.enemies = [e for e in mission.enemies if e.alive]
