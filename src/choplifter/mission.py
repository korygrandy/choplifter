
from __future__ import annotations

import logging
import pygame
import math
import random
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
from .helicopter import Helicopter, Facing
from .game_types import ProjectileKind, HostageState, EnemyKind
from . import haptics



from .entities import Hostage, Compound, Projectile, Enemy, BaseZone, MissionStats

from .mission_state import MissionState
from .mission_helpers import boarded_count, on_foot, _hits_circle, _projectile_hits_enemy, _log_compound_health_if_needed, _update_sentiment, _update_fuel, _log_progress_if_changed, _difficulty_scale
from .enemy_update import _update_enemies
from .mission_projectiles import _update_projectiles


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
    _update_hostages(mission, helicopter, dt, heli)
    _handle_unload(mission, helicopter, heli, dt)

    _handle_crash_and_respawn(mission, helicopter, dt, heli, logger)
    if mission.ended:
        return

    _update_sentiment(mission)

    _log_progress_if_changed(mission, logger)

    if mission.stats.saved >= 20:
        _end_mission(mission, "THE END", "RESCUE SUCCESS", logger)


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


        if logger is not None:
            logger.debug(
                "FLASH: kind=damage source=%s amount=%.2f damage=%.1f->%.1f rgb=%s",
                source,
                float(amount),
                float(before),
                float(helicopter.damage),
                helicopter.damage_flash_rgb,
            )
        if source == "BARAK_MISSILE":
            haptics.rumble_barak_missile_hit(logger=logger)
        elif source == "ARTILLERY":
            haptics.rumble_artillery_hit(logger=logger)
        else:
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
