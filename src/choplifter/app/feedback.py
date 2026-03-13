from __future__ import annotations

from dataclasses import dataclass
import random

import pygame

from .. import haptics


def _clamp01(v: float) -> float:
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v


@dataclass
class ScreenShakeState:
    remaining_s: float = 0.0
    total_s: float = 0.0
    strength: float = 0.0
    surface: pygame.Surface | None = None


def add_screenshake(state: ScreenShakeState, strength: float, *, enabled: bool) -> None:
    if not enabled:
        return

    s = _clamp01(float(strength))
    if s <= 0.0:
        return

    state.strength = max(state.strength, s)
    duration_s = 0.08 + 0.20 * s
    state.remaining_s = max(state.remaining_s, duration_s)
    state.total_s = max(state.total_s, state.remaining_s)


def rough_landing_feedback(
    *,
    state: ScreenShakeState,
    landing_vy: float,
    safe_landing_vy: float,
    invuln_seconds: float,
    ended: bool,
    audio: object,
    screenshake_enabled: bool,
) -> None:
    vy = abs(float(landing_vy))
    safe = max(0.001, float(safe_landing_vy))

    if vy <= safe or invuln_seconds > 0.0 or ended:
        return

    severity = (vy - safe) / (safe * 1.25)
    severity = _clamp01(severity)
    add_screenshake(state, 0.35 + 0.65 * severity, enabled=screenshake_enabled)
    if severity >= 0.60:
        # Higher severity -> stronger duck.
        getattr(audio, "trigger_duck")(strength=0.45 + 0.55 * severity)


def consume_mission_feedback(
    *,
    state: ScreenShakeState,
    mission: object,
    audio: object,
    screenshake_enabled: bool,
) -> None:
    shake_impulse = float(getattr(mission, "feedback_shake_impulse", 0.0))
    if shake_impulse > 0.0:
        add_screenshake(state, shake_impulse, enabled=screenshake_enabled)
        setattr(mission, "feedback_shake_impulse", 0.0)

    duck_strength = float(getattr(mission, "feedback_duck_strength", 0.0))
    if duck_strength > 0.0:
        # Only apply duck for bigger impacts.
        if duck_strength >= 0.55:
            getattr(audio, "trigger_duck")(strength=duck_strength)
        setattr(mission, "feedback_duck_strength", 0.0)

    if bool(getattr(mission, "crash_impact_sfx_pending", False)):
        add_screenshake(state, 1.0, enabled=screenshake_enabled)
        getattr(audio, "trigger_duck")(strength=1.0)
        haptics.rumble_chopper_crash()
        getattr(audio, "play_chopper_crash")()
        setattr(mission, "crash_impact_sfx_pending", False)


def update_screenshake_target(
    *,
    state: ScreenShakeState,
    frame_dt: float,
    enabled: bool,
    mode: str,
    screen: pygame.Surface,
) -> tuple[pygame.Surface, int, int]:
    shake_x = 0
    shake_y = 0

    if mode == "playing" and enabled and state.remaining_s > 0.0:
        state.remaining_s = max(0.0, state.remaining_s - frame_dt)
        t = state.remaining_s / max(0.001, state.total_s)
        amp = (1.5 + 6.0 * state.strength) * t
        shake_x = int(random.uniform(-amp, amp))
        shake_y = int(random.uniform(-amp, amp))
    elif state.remaining_s <= 0.0:
        state.remaining_s = 0.0
        state.total_s = 0.0
        state.strength = 0.0

    target = screen
    if mode == "playing" and enabled and (shake_x != 0 or shake_y != 0):
        if state.surface is None or state.surface.get_size() != screen.get_size():
            state.surface = pygame.Surface(screen.get_size())
        target = state.surface

    return target, shake_x, shake_y
