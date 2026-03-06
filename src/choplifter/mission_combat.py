from __future__ import annotations

import logging
import math

import pygame

from . import haptics
from .entities import Projectile
from .game_types import EnemyKind, HostageState, ProjectileKind
from .helicopter import Helicopter
from .math2d import Vec2, clamp
from .mission_helpers import on_foot
from .mission_state import MissionState


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
        # Normalize damage amounts (10 is common) so bullets do not feel overly punchy.
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

        # Play warning beeps if damage crosses threshold (e.g., 70%).
        if hasattr(mission, "audio") and mission.audio is not None and mission.audio.chopper_warning_beeps is not None:
            try:
                # Start looping as soon as damage >= 70.
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
