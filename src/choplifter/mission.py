
from __future__ import annotations

import logging
import pygame
import math
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
from .mission_crash import _handle_crash_and_respawn
from .mission_hostages import _update_hostages


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
