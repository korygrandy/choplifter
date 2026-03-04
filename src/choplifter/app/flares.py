from __future__ import annotations

from dataclasses import dataclass
import random

from ..math2d import Vec2


@dataclass
class FlareState:
    cooldown_s: float = 0.0
    salvo_remaining: int = 0
    salvo_timer_s: float = 0.0
    salvo_gap_s: float = 0.12

    front_remaining: int = 0
    front_timer_s: float = 0.0
    front_gap_s: float = 0.10


def reset_flares(state: FlareState) -> None:
    state.cooldown_s = 0.0
    state.salvo_remaining = 0
    state.salvo_timer_s = 0.0
    state.front_remaining = 0
    state.front_timer_s = 0.0


def _emit_flare_burst(
    *,
    mission: object,
    helicopter: object,
    dir_sign: float,
    y_min: float,
    y_max: float,
    facing_mult: float = 1.0,
    **emit_kwargs: object,
) -> None:
    fx = float(getattr(getattr(helicopter, "facing", None), "value", 1))
    if fx == 0.0:
        fx = 1.0
    facing_sign = 1.0 if fx >= 0.0 else -1.0
    offset_x = facing_sign * float(dir_sign) * random.uniform(18.0, 52.0)
    offset_y = random.uniform(float(y_min), float(y_max))
    spawn_pos = getattr(helicopter, "pos") + Vec2(offset_x, offset_y)
    getattr(mission, "flares").emit_fountain(
        spawn_pos,
        facing_x=fx * float(facing_mult),
        heli_vel=getattr(helicopter, "vel"),
        **emit_kwargs,
    )


def _emit_flare_burst_behind(*, mission: object, helicopter: object) -> None:
    _emit_flare_burst(mission=mission, helicopter=helicopter, dir_sign=-1.0, y_min=4.0, y_max=18.0)


def _emit_flare_burst_front(*, mission: object, helicopter: object) -> None:
    # Emit forward (opposite of rear bursts) by flipping facing_x.
    _emit_flare_burst(
        mission=mission,
        helicopter=helicopter,
        dir_sign=1.0,
        y_min=0.0,
        y_max=14.0,
        facing_mult=-1.0,
        rotate_clockwise_deg=15.0,
        # Longer, slower-fading front trails.
        ttl_mult=1.55,
        drag=0.992,
        # Bias upward so gravity creates a clearer arc.
        up_speed_min=-135.0,
        up_speed_max=-15.0,
        back_speed_mult=1.08,
    )


def try_start_flare_salvo(state: FlareState, *, mission: object, helicopter: object, audio: object) -> None:
    if bool(getattr(mission, "crash_active", False)):
        return
    if state.cooldown_s > 0.0:
        return
    if state.salvo_remaining > 0 or state.front_remaining > 0:
        return

    try:
        getattr(audio, "play_flare_defense")()
        mission.flare_invuln_seconds = max(float(getattr(mission, "flare_invuln_seconds", 0.0)), 3.0)
        _emit_flare_burst_front(mission=mission, helicopter=helicopter)

        # Fire the front burst immediately, then delay the rear salvo.
        state.salvo_remaining = 3
        state.salvo_timer_s = 1.0
        state.front_remaining = 1
        state.front_timer_s = state.front_gap_s
        state.cooldown_s = 5.0
    except Exception:
        state.salvo_remaining = 0
        state.salvo_timer_s = 0.0
        state.front_remaining = 0
        state.front_timer_s = 0.0


def update_flares(state: FlareState, *, mission: object, helicopter: object, dt: float) -> None:
    state.cooldown_s = max(0.0, state.cooldown_s - dt)

    if bool(getattr(mission, "crash_active", False)):
        state.salvo_remaining = 0
        state.salvo_timer_s = 0.0
        state.front_remaining = 0
        state.front_timer_s = 0.0
        return

    if state.salvo_remaining > 0:
        state.salvo_timer_s -= dt
        while state.salvo_remaining > 0 and state.salvo_timer_s <= 0.0:
            try:
                _emit_flare_burst_behind(mission=mission, helicopter=helicopter)
            except Exception:
                state.salvo_remaining = 0
                state.salvo_timer_s = 0.0
                break
            state.salvo_remaining -= 1
            state.salvo_timer_s += state.salvo_gap_s

    if state.front_remaining > 0:
        state.front_timer_s -= dt
        while state.front_remaining > 0 and state.front_timer_s <= 0.0:
            try:
                _emit_flare_burst_front(mission=mission, helicopter=helicopter)
            except Exception:
                state.front_remaining = 0
                state.front_timer_s = 0.0
                break
            state.front_remaining -= 1
            state.front_timer_s += state.front_gap_s
