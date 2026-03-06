from __future__ import annotations
import math
from .entities import Enemy
from .game_types import EnemyKind, ProjectileKind
from .math2d import Vec2, clamp
from .settings import HelicopterSettings
from .mission_helpers import _difficulty_scale
from .mission_state import MissionState
from .entities import Projectile
from .helicopter import Helicopter, Facing
import logging

def _update_enemies(
    mission: MissionState,
    helicopter: Helicopter,
    dt: float,
    heli: HelicopterSettings,
    logger: logging.Logger | None,
) -> None:
    difficulty = _difficulty_scale(mission.sentiment)
    tuning = mission.tuning

    # Time-based pressure ramp:
    # - First 60s: easier
    # - Next 60s: ramp back to normal
    # pressure > 1 => more frequent threats; < 1 => less.
    ramp_t = clamp((mission.elapsed_seconds - 60.0) / 60.0, 0.0, 1.0)
    pressure = (0.75 * (1.0 - ramp_t)) + (1.00 * ramp_t)

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
        else:
            x = mission.world_width + tuning.jet_spawn_margin_x
            vx = -tuning.jet_speed_x
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

        # --- BARAK MRAD MOVEMENT, DEPLOYMENT, AND AIMING LOGIC ---
        if e.kind is EnemyKind.BARAK_MRAD:
            if mission.compounds:
                leftmost = min(mission.compounds, key=lambda c: c.pos.x)
                target_x = leftmost.pos.x + leftmost.width + 24.0
                if e.mrad_state == "moving":
                    if e.pos.x < target_x:
                        e.pos.x += e.vel.x * dt
                        if e.pos.x >= target_x:
                            e.pos.x = target_x
                            e.vel.x = 0.0
                            e.entered_screen = True
                            e.mrad_state = "deploying"
                    else:
                        e.vel.x = 0.0
                        e.entered_screen = True
                        e.mrad_state = "deploying"
                elif e.mrad_state == "deploying":
                    # Animate launcher_angle from 0 (horizontal) to pi/2 (vertical)
                    deploy_speed = 1.5  # radians/sec
                    ext_speed = 1.2     # extension per second
                    target_angle = math.pi / 2
                    angle_done = False
                    ext_done = False
                    # Animate angle
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
                    # Only finish deploying when both are done
                    if angle_done and ext_done:
                        e.mrad_state = "launching"
                elif e.mrad_state == "launching":
                    # Missile launch logic: spawn missile once, play launch animation, then transition to 'done'
                    e.launcher_ext_progress = 1.0
                    if not e.missile_fired:
                        # Missile launches straight up from the tip of the launcher
                        # Calculate missile start position based on launcher geometry
                        launcher_length = 44.0 * e.launcher_ext_progress
                        # Offset missile 30px left relative to BARAK sprite
                        missile_pos = Vec2(
                            e.pos.x - 40 + launcher_length * math.cos(e.launcher_angle),
                            e.pos.y - 28.0 - launcher_length * math.sin(e.launcher_angle)
                        )
                        missile_angle = e.launcher_angle  # Should be vertical (pi/2)
                        missile_speed = 120.0
                        missile_vel = Vec2(math.cos(missile_angle) * missile_speed, -abs(math.sin(missile_angle)) * missile_speed)
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
                        # Debug: print/log missile launch event
                        print("[DEBUG] BARAK MRAD missile launched at pos:", missile_pos)
                        if logger is not None:
                            logger.info(f"BARAK MRAD missile launched at {missile_pos}")
                        # Play Barak MRAD missile launch SFX
                        if hasattr(mission, "audio") and mission.audio is not None:
                            if hasattr(mission.audio, "play_barak_mrad_launch"):
                                mission.audio.play_barak_mrad_launch()
                    # After firing, transition to 'done' state
                    e.mrad_state = "done"
            continue

        if e.kind is EnemyKind.TANK:
            # Turret tracking logic (smooth rotation)
            dx = helicopter.pos.x - e.pos.x
            dy = helicopter.pos.y - e.pos.y
            target_angle = math.atan2(dy, dx)
            # Smoothly interpolate turret_angle toward target_angle (shortest path)
            def angle_diff(a, b):
                d = a - b
                while d > math.pi:
                    d -= 2 * math.pi
                while d < -math.pi:
                    d += 2 * math.pi
                return d
            diff = angle_diff(target_angle, e.turret_angle)
            max_turn = 1.8 * dt
            if abs(diff) < max_turn:
                e.turret_angle = target_angle
            else:
                e.turret_angle += max_turn if diff > 0 else -max_turn
            # Clamp to [-pi, pi]
            if e.turret_angle > math.pi:
                e.turret_angle -= 2 * math.pi
            elif e.turret_angle < -math.pi:
                e.turret_angle += 2 * math.pi
