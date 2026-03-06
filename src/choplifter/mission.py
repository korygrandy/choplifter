from __future__ import annotations

from dataclasses import field
import logging
import math
import random

from .burning_particles import BurningParticleSystem
from .fx_particles import DustStormSystem, ExplosionSystem, FlareSystem, HelicopterDamageFxSystem, ImpactSparkSystem, JetTrailSystem
import pygame
from .game_types import EnemyKind, HostageState, ProjectileKind
from .helicopter import Facing, Helicopter
from .math2d import Vec2, clamp
from .mission_configs import (
    LevelConfig,
    MissionTuning,
    create_airport_special_ops_config,
    create_city_center_config,
    create_level_1_config,
    create_worship_center_warfare_config,
    get_mission_config_by_id,
)
from .settings import HelicopterSettings
from . import haptics



from .entities import Hostage, Compound, Projectile, Enemy, BaseZone, MissionStats

from .mission_state import MissionState
from .mission_helpers import boarded_count, on_foot, _hits_circle, _projectile_hits_enemy, _log_compound_health_if_needed


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

    # Particle effects (world-space).
    mission.burning.update(dt)
    mission.impact_sparks.update(dt)
    mission.jet_trails.update(dt)
    mission.dust_storm.update(dt, heli_pos=helicopter.pos, heli_vel=helicopter.vel, ground_y=heli.ground_y)
    mission.heli_damage_fx.update(dt, heli_pos=helicopter.pos, heli_vel=helicopter.vel, damage=helicopter.damage)
    mission.explosions.update(dt)
    mission.flares.update(dt)

    # If we're in a crash animation, run the crash sequence and skip gameplay updates.
    if mission.crash_active:
        _update_crash_sequence(mission, helicopter, dt, heli, logger)
        return

    _update_enemies(mission, helicopter, dt, heli, logger)

    _update_projectiles(mission, dt, heli, logger, helicopter)
    _update_compounds_and_release(mission, heli, logger)
    _update_hostages(mission, helicopter, dt, heli)
    _handle_unload(mission, helicopter, heli, dt)

    # --- Mission Success: VIP rescued ---
    # If the VIP is present and has been SAVED, trigger mission success immediately
    vip_hostage = next((h for h in mission.hostages if getattr(h, "is_vip", False)), None)
    if vip_hostage is not None and vip_hostage.state is HostageState.SAVED and not mission.ended:
        _end_mission(mission, "THE END", "VIP RESCUED SUCCESS", logger)

    _handle_crash_and_respawn(mission, helicopter, dt, heli, logger)
    if mission.ended:
        return

    _update_sentiment(mission)

    _log_progress_if_changed(mission, logger)

    if mission.stats.saved >= 20:
        _end_mission(mission, "THE END", "RESCUE SUCCESS", logger)


def _update_projectiles(
    mission: MissionState,
    dt: float,
    heli: HelicopterSettings,
    logger: logging.Logger | None,
    helicopter: Helicopter,
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

        # Barak MRAD missile: two-phase logic
        if getattr(p, "is_barak_missile", False):
            # Phase 1: Liftoff
            if p.missile_state == "liftoff":
                if p.launch_pos is None:
                    p.launch_pos = p.pos.copy()
                p.current_angle = math.pi/2  # vertical up
                p.vel = Vec2(0.0, -240.0)  # 2x faster liftoff
                if p.pos.y <= p.launch_pos.y - 40.0:
                    # Determine rotation direction (INVERTED)
                    dx = helicopter.pos.x - p.pos.x
                    if dx > 0:
                        p.rotate_dir = -1  # CCW (was CW)
                        p.target_angle = math.pi  # left (was right)
                    else:
                        p.rotate_dir = 1  # CW (was CCW)
                        p.target_angle = 0.0  # right (was left)
                    p.missile_state = "rotating"
                    p.rotation_progress = 0.0
                    p.vel = Vec2(0.0, 0.0)
            # Phase 2: Rotating
            elif p.missile_state == "rotating":
                start_angle = math.pi/2
                end_angle = p.target_angle
                # Animate rotation (0.5s duration)
                p.rotation_progress += dt * 2.0
                if p.rotation_progress >= 1.0:
                    p.rotation_progress = 1.0
                    p.current_angle = end_angle
                    p.missile_state = "homing"
                    # Phase 3: Final boost (handled in homing phase)
                else:
                    # Interpolate angle
                    p.current_angle = start_angle + (end_angle - start_angle) * p.rotation_progress
                    p.vel = Vec2(0.0, 0.0)
            # Phase 3: Homing (continuous tracking)
            elif p.missile_state == "homing":
                # Continuously update velocity to track the helicopter
                dx = helicopter.pos.x - p.pos.x
                dy = (helicopter.pos.y + 24.0) - p.pos.y
                angle = math.atan2(dy, dx)
                speed = 360.0 * 3  # 3x faster
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
                            haptics.rumble_tank_destroyed(logger=logger)
                        if logger is not None:
                            logger.info("ENEMY_DOWN: %s", e.kind.name)
                    p.alive = False
                    break

        if not p.alive:
            continue

        # Helicopter collision (enemy projectiles only).
        if p.kind in (ProjectileKind.ENEMY_BULLET, ProjectileKind.ENEMY_ARTILLERY):
            if _hits_circle(p.pos, helicopter.pos, radius=26.0):
                # Special case: Barak MRAD missile
                if getattr(p, "is_barak_missile", False):
                    _damage_helicopter(mission, helicopter, 18.0, logger, source="BARAK_MISSILE")
                elif p.kind is ProjectileKind.ENEMY_ARTILLERY:
                    mission.stats.artillery_hits += 1
                    mission.impact_sparks.emit_hit(p.pos, p.vel, strength=1.25)
                    _damage_helicopter(mission, helicopter, 10.0, logger, source="ARTILLERY")
                else:
                    _damage_helicopter(mission, helicopter, 10.0, logger, source="ENEMY_BULLET")
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


def _update_compounds_and_release(mission: MissionState, heli: HelicopterSettings, logger: logging.Logger | None) -> None:
    for c in mission.compounds:
        if c.is_open:
            continue
        if c.health > 0.0:
            continue

        c.is_open = True
        if logger is not None:
            logger.info(
                "Compound opened: x=%.0f hostages=%d..%d",
                c.pos.x,
                c.hostage_start,
                c.hostage_start + c.hostage_count - 1,
            )
        # Spawn hostages at the compound entrance area.
        start = c.hostage_start
        end = start + c.hostage_count
        for i, h in enumerate(mission.hostages[start:end]):
            spread = (i % 8) * 10.0
            row = i // 8
            h.state = HostageState.PANIC
            h.pos = Vec2(c.pos.x + 10.0 + spread, heli.ground_y - 10.0 - row * 10.0)


def _update_hostages(mission: MissionState, helicopter: Helicopter, dt: float, heli: HelicopterSettings) -> None:
    gravity = 900.0  # px/sec^2
    import logging
    logger = logging.getLogger("choplifter")

    # --- Falling logic ---
    for h in mission.hostages:
        if h.state is HostageState.FALLING:
            h.vel.y += gravity * dt
            h.pos.x += h.vel.x * dt
            h.pos.y += h.vel.y * dt
            # Animate tumbling as they fall
            h.fall_angle += 720.0 * dt  # 2 full spins per second
            # If hits ground, mark as KIA
            if h.pos.y >= heli.ground_y - 6.0:
                h.pos.y = heli.ground_y - 6.0
                h.state = HostageState.KIA
                h.fall_angle = 0.0  # Reset angle on impact
            continue

    # --- Hostage ejection logic: only one every 4-6s, only after 1s at max velocity with doors open ---
    # max_speed_x = getattr(heli, 'max_speed_x', 400.0)  # fallback default
    # at_max_vel = abs(helicopter.vel.x) >= 0.98 * max_speed_x
    now = getattr(mission, 'elapsed_seconds', 0.0)

    # Track previous eligibility state for logging
    prev_eligible = getattr(mission, '_prev_fall_eligible', None)
    eligible = helicopter.doors_open and not helicopter.grounded

    # --- DEBUG: Log eligibility and timer state every frame when doors are open and airborne ---
    if helicopter.doors_open and not helicopter.grounded:
        logger.debug(
            f"[FALL DEBUG] eligible={eligible} | vel.x={helicopter.vel.x:.2f} | doors_open_maxvel_timer={mission.doors_open_maxvel_timer:.2f} | now={now:.2f} | next_fall_time={getattr(mission, 'next_fall_time', 0.0):.2f} | elapsed={getattr(mission, 'elapsed_seconds', 0.0):.2f}"
        )

    if eligible:
        mission.doors_open_maxvel_timer += dt
        if mission.doors_open_maxvel_timer > 1.0:
            if now >= getattr(mission, 'next_fall_time', 0.0):
                boarded_hostages = [h for h in mission.hostages if h.state is HostageState.BOARDED]
                if boarded_hostages:
                    h = random.choice(boarded_hostages)
                    h.state = HostageState.FALLING
                    h.pos = Vec2(helicopter.pos.x, helicopter.pos.y + 10.0)
                    h.vel = Vec2(random.uniform(-60, 60), random.uniform(-80, -120))
                    mission.stats.lost_in_transit += 1
                    # Play scream SFX when a hostage falls
                    if hasattr(mission, "audio") and mission.audio is not None:
                        try:
                            mission.audio.play_hostage_scream()
                        except Exception:
                            pass
                    # Log when a hostage actually falls
                    if hasattr(mission, '_last_fall_time'):
                        last_fall = mission._last_fall_time
                        actual_interval = now - last_fall
                        logger.info(f"[HOSTAGE FALL] Hostage fell | interval={actual_interval:.2f}s | now={now:.2f} | next_fall_time={mission.next_fall_time:.2f} | doors_open_maxvel_timer={mission.doors_open_maxvel_timer:.2f}")
                    else:
                        logger.info(f"[HOSTAGE FALL] First fall | now={now:.2f} | next_fall_time={mission.next_fall_time:.2f} | doors_open_maxvel_timer={mission.doors_open_maxvel_timer:.2f}")
                    mission._last_fall_time = now
                    # Schedule next fall in 2-2.5 seconds
                    mission.next_fall_time = now + random.uniform(2.0, 2.5)
    else:
        # Only log timer reset if eligibility just changed from True to False
        if prev_eligible:
            reason = []
            if not helicopter.doors_open:
                reason.append("doors closed")
            if helicopter.grounded:
                reason.append("grounded")
            # if not at_max_vel:
            #     reason.append("not at max velocity")
            logger.info(f"[HOSTAGE FALL] Timer reset due to {', '.join(reason)} | now={now:.2f} | doors_open_maxvel_timer={mission.doors_open_maxvel_timer:.2f}")
        mission.doors_open_maxvel_timer = 0.0
        # Reset next_fall_time so timer doesn't accumulate while not eligible
        mission.next_fall_time = now + random.uniform(2.0, 2.5)

    # Track eligibility for next frame
    mission._prev_fall_eligible = eligible

    capacity = heli.capacity
    boarded = boarded_count(mission)

    lz_available = helicopter.grounded and helicopter.doors_open and boarded < capacity

    # Boarding radius around helicopter.
    load_radius = 58.0
    load_r2 = load_radius * load_radius

    controlled_speed = mission.tuning.hostage_controlled_move_speed
    controlled_cap = max(1, int(mission.tuning.hostage_controlled_max_moving_to_lz))
    chaotic_speed = mission.tuning.hostage_chaotic_move_speed
    chaotic_cap = max(1, int(mission.tuning.hostage_chaotic_max_moving_to_lz))
    chaos_p = clamp(mission.tuning.hostage_chaos_probability, 0.0, 1.0)
    moving_to_lz = sum(1 for h in mission.hostages if h.state is HostageState.MOVING_TO_LZ)

    def saved_slot_pos(slot: int) -> Vec2:
        # Pack saved hostages inside the base zone.
        slot = max(0, int(slot))
        padding_x = 14.0
        padding_y = 16.0
        spacing_x = 14.0
        spacing_y = 14.0

        usable_w = max(1.0, mission.base.width - padding_x * 2.0)
        cols = max(1, int(usable_w // spacing_x))
        col = slot % cols
        row = slot // cols

        x = mission.base.pos.x + padding_x + col * spacing_x
        floor_y = heli.ground_y - 6.0
        y = max(mission.base.pos.y + padding_y, floor_y - row * spacing_y)
        return Vec2(x, y)

    for h in mission.hostages:
        if h.state is HostageState.SAVED:
            if h.saved_slot >= 0:
                h.pos = saved_slot_pos(h.saved_slot)
            continue

        if h.state is HostageState.EXITING:
            if h.saved_slot < 0:
                h.saved_slot = mission.next_saved_slot
                mission.next_saved_slot += 1
            target = saved_slot_pos(h.saved_slot)

            h.pos.y = heli.ground_y - 6.0
            direction = -1.0 if h.pos.x > target.x else 1.0
            h.pos.x += direction * 62.0 * dt

            if abs(h.pos.x - target.x) <= 2.0:
                h.pos = target
                h.state = HostageState.SAVED
                mission.stats.saved += 1
            continue

        if h.state is HostageState.PANIC:
            h.state = HostageState.WAITING

        if h.state is HostageState.WAITING:
            if lz_available:
                # Mix both behaviors: sometimes a controlled "queue", sometimes a chaotic rush.
                is_chaotic = random.random() < chaos_p
                cap = chaotic_cap if is_chaotic else controlled_cap
                start_radius = 320.0 if is_chaotic else 240.0

                if moving_to_lz >= cap:
                    continue

                # If close enough horizontally, start moving to LZ.
                if abs(h.pos.x - helicopter.pos.x) <= start_radius:
                    h.state = HostageState.MOVING_TO_LZ
                    moving_to_lz += 1

                    base_speed = chaotic_speed if is_chaotic else controlled_speed
                    if is_chaotic:
                        # Small per-hostage variation so they don't march in lockstep.
                        base_speed *= random.uniform(0.9, 1.15)
                    h.move_speed = base_speed

        if h.state is HostageState.MOVING_TO_LZ:
            if not lz_available:
                h.state = HostageState.WAITING
                h.move_speed = 0.0
                moving_to_lz = max(0, moving_to_lz - 1)
                continue

            direction = -1.0 if h.pos.x > helicopter.pos.x else 1.0
            speed = h.move_speed if h.move_speed > 0.0 else controlled_speed
            step = speed * dt
            dx_to_heli = helicopter.pos.x - h.pos.x
            if abs(dx_to_heli) <= step:
                h.pos.x = helicopter.pos.x
            else:
                h.pos.x += direction * step

            # Snap to helicopter and board.
            dx = h.pos.x - helicopter.pos.x
            dy = h.pos.y - helicopter.pos.y
            if dx * dx + dy * dy <= load_r2:
                boarded = boarded_count(mission)
                if boarded < capacity:
                    h.state = HostageState.BOARDED
                    h.pos = Vec2(-9999.0, -9999.0)
                    h.move_speed = 0.0
                    moving_to_lz = max(0, moving_to_lz - 1)
                else:
                    h.state = HostageState.WAITING
                    h.move_speed = 0.0
                    moving_to_lz = max(0, moving_to_lz - 1)


def _handle_unload(mission: MissionState, helicopter: Helicopter, heli: HelicopterSettings, dt: float) -> None:
    # Unload rule: must be grounded at base and doors open.
    if not helicopter.grounded or not helicopter.doors_open:
        mission.unload_release_seconds = 0.0
        return

    if not mission.base.contains_point(helicopter.pos):
        mission.unload_release_seconds = 0.0
        return

    mission.unload_release_seconds = max(0.0, mission.unload_release_seconds - dt)
    if mission.unload_release_seconds > 0.0:
        return

    # Release one passenger at a time so the player can see them exit.
    boarded = next((h for h in mission.hostages if h.state is HostageState.BOARDED), None)
    if boarded is None:
        return

    door_offset_x = 0.0
    if helicopter.facing is Facing.LEFT:
        door_offset_x = -18.0
    elif helicopter.facing is Facing.RIGHT:
        door_offset_x = 18.0

    boarded.state = HostageState.EXITING
    boarded.saved_slot = mission.next_saved_slot
    mission.next_saved_slot += 1
    boarded.pos = Vec2(helicopter.pos.x + door_offset_x, heli.ground_y - 6.0)

    mission.unload_release_seconds = 0.22


def hostage_crush_check(
    mission: MissionState,
    helicopter: Helicopter,
    last_landing_vy: float,
    *,
    safe_landing_vy: float,
) -> None:
    # Called on a landing event. If the landing was hard and a hostage is under the helicopter, crush them.
    if mission.ended:
        return

    if abs(last_landing_vy) <= safe_landing_vy:
        return

    crush_radius = 28.0
    r2 = crush_radius * crush_radius

    for h in mission.hostages:
        if not on_foot(h):
            continue
        dx = h.pos.x - helicopter.pos.x
        dy = h.pos.y - helicopter.pos.y
        if dx * dx + dy * dy <= r2:
            h.state = HostageState.KIA
            mission.stats.kia_by_player += 1


def hostage_crush_check_logged(
    mission: MissionState,
    helicopter: Helicopter,
    last_landing_vy: float,
    *,
    safe_landing_vy: float,
    logger: logging.Logger | None,
) -> None:
    before = mission.stats.kia_by_player
    hostage_crush_check(mission, helicopter, last_landing_vy, safe_landing_vy=safe_landing_vy)
    if logger is None:
        return
    if mission.stats.kia_by_player != before:
        logger.info("CRUSH: hard landing killed %d hostage(s)", mission.stats.kia_by_player - before)


def _log_progress_if_changed(mission: MissionState, logger: logging.Logger | None) -> None:
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


def _difficulty_scale(sentiment: float) -> float:
    # Map sentiment 0..100 to a difficulty scalar -1..+1.
    # Low sentiment => more pressure; high sentiment => slightly less.
    return clamp((50.0 - clamp(sentiment, 0.0, 100.0)) / 50.0, -1.0, 1.0)


def _update_sentiment(mission: MissionState) -> None:
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


def _update_fuel(mission: MissionState, helicopter: Helicopter, dt: float, logger: logging.Logger | None) -> None:
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

            # The following block referenced 'e' which is not defined here. If collision logic is needed, it should be handled in the enemy update loop, not mine spawn logic.
            # If you want to check for collisions between the helicopter and existing enemies, do so in the appropriate loop elsewhere.
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

            if (
                abs(dx) <= tuning.tank_fire_range_x
                and helicopter.pos.y <= heli.ground_y - tuning.tank_fire_min_altitude_clearance_y
                and e.cooldown <= 0.0
            ):
                tank_cd = (tuning.tank_fire_base_cooldown_s / pressure) * (1.0 - 0.12 * difficulty)
                e.cooldown = clamp(tank_cd, tuning.tank_fire_min_cooldown_s, tuning.tank_fire_max_cooldown_s)
                _spawn_enemy_bullet_toward(
                    mission,
                    e.pos,
                    helicopter.pos,
                    kind=ProjectileKind.ENEMY_ARTILLERY,
                    source=EnemyKind.TANK,
                )
                mission.stats.artillery_fired += 1
                if logger is not None:
                    logger.info("TANK_FIRE")

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
                _spawn_enemy_bullet_toward(mission, e.pos, helicopter.pos, source=EnemyKind.JET)

            if e.entered_screen and e.trail_enabled:
                e.trail_spawn_accum += dt * 18.0
                while e.trail_spawn_accum >= 1.0:
                    e.trail_spawn_accum -= 1.0
                    mission.jet_trails.emit_trail(e.pos, e.vel)

            if _hits_circle(e.pos, helicopter.pos, radius=tuning.jet_collision_radius):
                _damage_helicopter(mission, helicopter, tuning.jet_touch_damage, logger, source="JET")
                if hasattr(mission, "audio") and mission.audio is not None:
                    try:
                        mission.audio.play_midair_collision()
                    except Exception:
                        pass

        elif e.kind is EnemyKind.AIR_MINE:
            to_heli = Vec2(helicopter.pos.x - e.pos.x, helicopter.pos.y - e.pos.y)
            dist = math.hypot(to_heli.x, to_heli.y)
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
                _mine_explode(mission, e.pos, helicopter, logger)
                e.alive = False

    mission.enemies = [e for e in mission.enemies if e.alive]


def _mine_explode(
    mission: MissionState,
    pos: Vec2,
    helicopter: Helicopter,
    logger: logging.Logger | None,
) -> None:
    if logger is not None:
        logger.info("MINE: detonate")

    mission.stats.mines_detonated += 1

    _damage_helicopter(mission, helicopter, mission.tuning.mine_damage, logger, source="AIR_MINE")

    radius = 40.0
    r2 = radius * radius
    for h in mission.hostages:
        if not on_foot(h):
            continue
        dx = h.pos.x - pos.x
        dy = h.pos.y - pos.y
        if dx * dx + dy * dy <= r2:
            h.state = HostageState.KIA
            mission.stats.kia_by_enemy += 1


def _spawn_enemy_bullet_toward(
    mission: MissionState,
    start: Vec2,
    target: Vec2,
    *,
    kind: ProjectileKind = ProjectileKind.ENEMY_BULLET,
    source: EnemyKind | None = None,
) -> None:
    dx = target.x - start.x
    dy = target.y - start.y
    dist = math.hypot(dx, dy)
    if dist <= 0.001:
        dist = 1.0
    speed = 140.0
    vx = (dx / dist) * speed
    vy = (dy / dist) * speed
    mission.projectiles.append(
        Projectile(
            kind=kind,
            pos=Vec2(start.x, start.y - 10.0),
            vel=Vec2(vx, vy),
            ttl=2.0,
            source=source,
        )
    )






def _damage_helicopter(
    mission: MissionState,
    helicopter: Helicopter,
    amount: float,
    logger: logging.Logger | None,
    source: str,
) -> None:
    if mission.ended or mission.crash_active:
        return

    # Respawn i-frames (blocks all damage).
    if mission.invuln_seconds > 0.0:
        return

    # Flare i-frames (blocks only projectile/artillery damage).
    if mission.flare_invuln_seconds > 0.0 and source in ("ENEMY_BULLET", "ARTILLERY"):
        return

    before = helicopter.damage
    helicopter.damage = min(100.0, helicopter.damage + amount)
    if helicopter.damage > before:
        # Cinematic feedback: stash a short-lived impulse for the renderer/audio layer.
        # (We only store the strongest impulse seen in a tick; the main loop consumes + clears it.)
        # Normalize damage amounts (10 is common) so bullets don't feel overly punchy.
        base = clamp(float(amount) / 25.0, 0.0, 1.0)
        if source in ("ENEMY_BULLET",):
            shake = 0.80 + 0.60 * base  
        elif source in ("ARTILLERY",):
            shake = 0.60 + 0.40 * base 
        elif source in ("AIR_MINE",):
            shake = 0.48 + 0.42 * base
        elif source in ("JET",):
            shake = 0.28 + 0.32 * base
        elif source == "BARAK_MISSILE":
            shake = 0.10 + 0.18 * base

        else:
            shake = 0.18 + 0.30 * base

        mission.feedback_shake_impulse = max(mission.feedback_shake_impulse, clamp(shake, 0.0, 1.0))

        # Subtle audio "duck" only for bigger impacts.
        if source in ("ARTILLERY", "AIR_MINE", "JET") and shake >= 0.50:
            mission.feedback_duck_strength = max(mission.feedback_duck_strength, clamp(shake, 0.0, 1.0))

        # Screen flash: set a short timer + color based on damage source.
        # (Rendering is gated by accessibility.flashes_enabled.)
        helicopter.damage_flash_seconds = 0.12
        if source in ("ENEMY_BULLET", "ARTILLERY"):
            helicopter.damage_flash_rgb = (255, 40, 40)
        elif source == "JET":
            helicopter.damage_flash_rgb = (120, 120, 255)
        elif source == "AIR_MINE":
            helicopter.damage_flash_rgb = (255, 170, 60)
        else:
            helicopter.damage_flash_rgb = (255, 60, 60)

        # Play warning beeps if damage crosses threshold (e.g., 70%)
        if hasattr(mission, "audio") and mission.audio is not None and mission.audio.chopper_warning_beeps is not None:
            try:
                # Start looping as soon as damage >= 70
                if before < 70.0 and helicopter.damage >= 70.0:
                    ch = pygame.mixer.Channel(7)
                    if not ch.get_busy():
                        ch.play(mission.audio.chopper_warning_beeps, loops=-1)
            except Exception:
                pass


            haptics.rumble_hit(amount=amount, source=source, logger=logger)
    if logger is not None and int(before) != int(helicopter.damage):
        logger.info("HIT: %s damage=%.0f", source, helicopter.damage)


def _handle_crash_and_respawn(
    mission: MissionState,
    helicopter: Helicopter,
    dt: float,
    heli: HelicopterSettings,
    logger: logging.Logger | None,
) -> None:
    if mission.ended:
        return
    # If a crash animation is already running, advance it.
    if mission.crash_active:
        _update_crash_sequence(mission, helicopter, dt, heli, logger)
        return

    # Start crash sequence when damage maxes out.
    if helicopter.damage < 100.0:
        return

    mission.crashes += 1
    if logger is not None:
        logger.info("CRASH: count=%d", mission.crashes)

    # Consequence: any boarded hostages are lost when the aircraft goes down.
    lost_this_crash = 0
    for h in mission.hostages:
        if h.state is HostageState.BOARDED:
            h.state = HostageState.KIA
            lost_this_crash += 1
    if lost_this_crash:
        mission.stats.lost_in_transit += lost_this_crash
        if logger is not None:
            logger.info("LOST_IN_TRANSIT: +%d (total=%d)", lost_this_crash, mission.stats.lost_in_transit)

    if mission.crashes >= 3:
        _end_mission(mission, "THE END", f"CRASHED {mission.crashes} TIMES", logger)
        return

    # Begin crash animation.
    mission.crash_active = True
    mission.crash_seconds = 0.0
    mission.crash_impacted = False
    mission.crash_impact_seconds = 0.0
    mission.crash_impact_sfx_pending = False
    mission.crash_origin = Vec2(float(helicopter.pos.x), float(helicopter.pos.y))
    mission.crash_vel = Vec2(float(helicopter.vel.x) * 0.45, float(helicopter.vel.y))
    mission.crash_variant = 0 if random.random() < 0.5 else 1

    # Lock helicopter visuals/controls.
    helicopter.crashing = True
    helicopter.crash_variant = mission.crash_variant
    helicopter.crash_seconds = 0.0
    helicopter.crash_hide = False


def _update_crash_sequence(
    mission: MissionState,
    helicopter: Helicopter,
    dt: float,
    heli: HelicopterSettings,
    logger: logging.Logger | None,
) -> None:
    if not mission.crash_active or mission.ended:
        return

    ground_contact_y = float(heli.ground_y - heli.rotor_clearance)

    mission.crash_seconds += dt
    helicopter.crash_seconds = mission.crash_seconds

    if not mission.crash_impacted:
        # Midair phase: spin + descend.
        vx, vy = float(mission.crash_vel.x), float(mission.crash_vel.y)
        vy = min(420.0, vy + 520.0 * dt)
        vx *= 0.995

        mission.crash_vel = Vec2(vx, vy)
        t = mission.crash_seconds

        if mission.crash_variant == 0:
            # Level, fast spins with a gentle horizontal swirl.
            helicopter.crash_roll_deg = (t * 720.0) % 360.0
            swirl = math.sin(t * 3.4) * 55.0
            helicopter.pos = Vec2(mission.crash_origin.x + swirl, float(helicopter.pos.y) + vy * dt)
        else:
            # Tail-spin: angled, wobble + spin.
            base = -32.0 if vx >= 0.0 else 32.0
            wobble = math.sin(t * 9.0) * 14.0
            helicopter.crash_roll_deg = base + wobble + (t * 420.0) % 360.0
            helicopter.pos = Vec2(float(helicopter.pos.x) + vx * dt, float(helicopter.pos.y) + vy * dt)

        # Clamp into world bounds.
        helicopter.pos = Vec2(clamp(float(helicopter.pos.x), 0.0, float(mission.world_width)), float(helicopter.pos.y))

        # --- Play warning beeps in a loop during crash spin ---
        if hasattr(mission, "audio") and mission.audio is not None and mission.audio.chopper_warning_beeps is not None:
            ch = pygame.mixer.Channel(7)
            if not ch.get_busy():
                ch.play(mission.audio.chopper_warning_beeps, loops=-1)

        if float(helicopter.pos.y) >= ground_contact_y:
            mission.crash_impacted = True
            mission.crash_impact_seconds = 0.0
            mission.crash_impact_sfx_pending = True
            helicopter.pos = Vec2(float(helicopter.pos.x), ground_contact_y)
            helicopter.vel = Vec2(0.0, 0.0)
            mission.crash_vel = Vec2(0.0, 0.0)

            # Stop warning beeps on ground contact
            try:
                pygame.mixer.Channel(7).stop()
            except Exception:
                pass

            # Explosion on impact.
            impact_pos = Vec2(float(helicopter.pos.x), float(heli.ground_y) - 10.0)
            mission.explosions.emit_explosion(impact_pos, strength=1.0)
            mission.burning.add_site(impact_pos, intensity=1.0)
            mission.impact_sparks.emit_hit(impact_pos, incoming_vel=Vec2(0.0, 220.0), strength=2.0)

            helicopter.crash_hide = True
            if logger is not None:
                logger.info("CRASH_IMPACT: variant=%d", mission.crash_variant)
        return

    # Post-impact delay, then respawn.
    mission.crash_impact_seconds += dt
    if mission.crash_impact_seconds < 0.85:
        return

    # Respawn.
    mission.crash_active = False
    mission.crash_impact_sfx_pending = False
    helicopter.crashing = False
    helicopter.crash_hide = False
    helicopter.crash_roll_deg = 0.0
    helicopter.crash_variant = 0
    helicopter.crash_seconds = 0.0

    helicopter.damage = 0.0
    helicopter.fuel = max(0.0, helicopter.fuel - 20.0)
    helicopter.vel = Vec2(0.0, 0.0)
    helicopter.tilt_deg = 0.0
    helicopter.doors_open = False
    helicopter.facing = Facing.LEFT
    helicopter.pos = Vec2(mission.base.pos.x + mission.base.width * 0.5, heli.ground_y - 120.0)
    mission.invuln_seconds = 2.0
    mission.flare_invuln_seconds = 0.0

    if logger is not None:
        logger.info("RESPAWN: invuln=%.1fs fuel=%.0f", mission.invuln_seconds, helicopter.fuel)


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
