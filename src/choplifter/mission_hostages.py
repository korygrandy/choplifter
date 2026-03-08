from __future__ import annotations

import logging
import random
from typing import Callable

from .boarding_telemetry import BOARDING_FAIL_DOORS_CLOSED, BOARDING_FAIL_FULL, BOARDING_FAIL_NOT_GROUNDED, record_boarding_failure
from .game_types import HostageState
from .helicopter import Facing, Helicopter
from .math2d import Vec2, clamp
from .mission_helpers import on_foot
from .mission_state import MissionState
from .settings import HelicopterSettings


def _update_hostages(
    mission: MissionState,
    helicopter: Helicopter,
    dt: float,
    heli: HelicopterSettings,
    *,
    boarded_count_fn: Callable[[MissionState], int],
) -> None:
    gravity = 900.0  # px/sec^2
    logger = logging.getLogger("choplifter")

    # Falling logic.
    for h in mission.hostages:
        if h.state is HostageState.FALLING:
            h.vel.y += gravity * dt
            h.pos.x += h.vel.x * dt
            h.pos.y += h.vel.y * dt
            # Animate tumbling as they fall.
            h.fall_angle += 720.0 * dt  # 2 full spins per second
            # If hits ground, mark as KIA.
            if h.pos.y >= heli.ground_y - 6.0:
                h.pos.y = heli.ground_y - 6.0
                h.state = HostageState.KIA
                h.fall_angle = 0.0  # Reset angle on impact.
            continue

    # Hostage ejection logic: only one every 4-6s, only after 1s with doors open while airborne.
    now = getattr(mission, "elapsed_seconds", 0.0)

    # Track previous eligibility state for logging.
    prev_eligible = getattr(mission, "_prev_fall_eligible", None)
    eligible = helicopter.doors_open and not helicopter.grounded

    if eligible:
        mission.doors_open_maxvel_timer += dt
        if mission.doors_open_maxvel_timer > 1.0:
            if now >= getattr(mission, "next_fall_time", 0.0):
                boarded_hostages = [h for h in mission.hostages if h.state is HostageState.BOARDED]
                if boarded_hostages:
                    h = random.choice(boarded_hostages)
                    h.state = HostageState.FALLING
                    h.pos = Vec2(helicopter.pos.x, helicopter.pos.y + 10.0)
                    h.vel = Vec2(random.uniform(-60, 60), random.uniform(-80, -120))
                    mission.stats.lost_in_transit += 1
                    # Play scream SFX when a hostage falls.
                    if hasattr(mission, "audio") and mission.audio is not None:
                        try:
                            mission.audio.play_hostage_scream()
                        except Exception:
                            pass
                    # Log when a hostage actually falls.
                    if hasattr(mission, "_last_fall_time"):
                        last_fall = mission._last_fall_time
                        actual_interval = now - last_fall
                        logger.info(
                            f"[HOSTAGE FALL] Hostage fell | interval={actual_interval:.2f}s | now={now:.2f} | next_fall_time={mission.next_fall_time:.2f} | doors_open_maxvel_timer={mission.doors_open_maxvel_timer:.2f}"
                        )
                    else:
                        logger.info(
                            f"[HOSTAGE FALL] First fall | now={now:.2f} | next_fall_time={mission.next_fall_time:.2f} | doors_open_maxvel_timer={mission.doors_open_maxvel_timer:.2f}"
                        )
                    mission._last_fall_time = now
                    # Schedule next fall in 2-2.5 seconds.
                    mission.next_fall_time = now + random.uniform(2.0, 2.5)
    else:
        # Only log timer reset if eligibility just changed from True to False.
        if prev_eligible:
            reason = []
            if not helicopter.doors_open:
                reason.append("doors closed")
            if helicopter.grounded:
                reason.append("grounded")
            logger.info(
                f"[HOSTAGE FALL] Timer reset due to {', '.join(reason)} | now={now:.2f} | doors_open_maxvel_timer={mission.doors_open_maxvel_timer:.2f}"
            )
        mission.doors_open_maxvel_timer = 0.0
        # Reset next_fall_time so timer doesn't accumulate while not eligible.
        mission.next_fall_time = now + random.uniform(2.0, 2.5)

    # Track eligibility for next frame.
    mission._prev_fall_eligible = eligible

    capacity = heli.capacity
    boarded = boarded_count_fn(mission)

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
                # Mix both behaviors: sometimes a controlled queue, sometimes a chaotic rush.
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
                        # Small per-hostage variation so they do not march in lockstep.
                        base_speed *= random.uniform(0.9, 1.15)
                    h.move_speed = base_speed

        if h.state is HostageState.MOVING_TO_LZ:
            if not lz_available:
                if not helicopter.grounded:
                    record_boarding_failure(mission, BOARDING_FAIL_NOT_GROUNDED)
                elif not helicopter.doors_open:
                    record_boarding_failure(mission, BOARDING_FAIL_DOORS_CLOSED)
                elif boarded_count_fn(mission) >= capacity:
                    record_boarding_failure(mission, BOARDING_FAIL_FULL)
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
                boarded = boarded_count_fn(mission)
                if boarded < capacity:
                    h.state = HostageState.BOARDED
                    h.pos = Vec2(-9999.0, -9999.0)
                    h.move_speed = 0.0
                    moving_to_lz = max(0, moving_to_lz - 1)
                else:
                    record_boarding_failure(mission, BOARDING_FAIL_FULL)
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
    on_foot_fn: Callable[..., bool] | None = None,
) -> None:
    on_foot_fn = on_foot_fn or on_foot

    # Called on a landing event. If the landing was hard and a hostage is under the helicopter, crush them.
    if mission.ended:
        return

    if abs(last_landing_vy) <= safe_landing_vy:
        return

    crush_radius = 28.0
    r2 = crush_radius * crush_radius

    for h in mission.hostages:
        if not on_foot_fn(h):
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
    on_foot_fn: Callable[..., bool] | None = None,
) -> None:
    on_foot_fn = on_foot_fn or on_foot

    before = mission.stats.kia_by_player
    hostage_crush_check(
        mission,
        helicopter,
        last_landing_vy,
        safe_landing_vy=safe_landing_vy,
        on_foot_fn=on_foot_fn,
    )
    if logger is None:
        return
    if mission.stats.kia_by_player != before:
        logger.info("CRUSH: hard landing killed %d hostage(s)", mission.stats.kia_by_player - before)
