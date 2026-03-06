from __future__ import annotations

import logging
import math
import random
from typing import Callable

import pygame

from .game_types import HostageState
from .helicopter import Facing, Helicopter
from .math2d import Vec2, clamp
from .mission_state import MissionState
from .settings import HelicopterSettings


def _handle_crash_and_respawn(
    mission: MissionState,
    helicopter: Helicopter,
    dt: float,
    heli: HelicopterSettings,
    logger: logging.Logger | None,
    *,
    end_mission: Callable[[MissionState, str, str, logging.Logger | None], None],
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
        end_mission(mission, "THE END", f"CRASHED {mission.crashes} TIMES", logger)
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

        # Play warning beeps in a loop during crash spin.
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

            # Stop warning beeps on ground contact.
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
