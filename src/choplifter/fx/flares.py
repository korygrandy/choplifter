from __future__ import annotations

import math
import random

from ..math2d import Vec2, clamp
from .particles import FxParticle


class FlareSystem:
    """A short-lived flare fountain emitted behind the helicopter.

    Kept intentionally simple: spawns ember-like FX particles with a bit of
    gravity so they arc downward as they trail.
    """

    def __init__(self, *, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self.particles: list[FxParticle] = []

        self.max_particles = 260

        # Burst characteristics (called per activation).
        self.burst_count = 42
        self.ttl_min_s = 0.75
        self.ttl_max_s = 1.25
        self.radius_min = 1.6
        self.radius_max = 3.2

        # Motion.
        self.back_speed_min = 140.0
        self.back_speed_max = 240.0
        self.up_speed_min = -60.0
        self.up_speed_max = 35.0
        self.gravity = 210.0

        # Visual strength multiplier consumed by the renderer.
        self.intensity_min = 0.75
        self.intensity_max = 1.15

    def reset(self) -> None:
        self.particles.clear()

    def emit_fountain(
        self,
        pos: Vec2,
        *,
        facing_x: float,
        heli_vel: Vec2 | None = None,
        rotate_clockwise_deg: float = 0.0,
        ttl_mult: float = 1.0,
        drag: float | None = None,
        up_speed_min: float | None = None,
        up_speed_max: float | None = None,
        back_speed_mult: float = 1.0,
    ) -> None:
        if len(self.particles) >= self.max_particles:
            return

        rotate_deg = float(rotate_clockwise_deg)

        ttl_mult_f = float(ttl_mult)
        if not math.isfinite(ttl_mult_f) or ttl_mult_f <= 0.0:
            ttl_mult_f = 1.0

        back_mult = float(back_speed_mult)
        if not math.isfinite(back_mult) or back_mult <= 0.0:
            back_mult = 1.0

        up_min = float(self.up_speed_min if up_speed_min is None else up_speed_min)
        up_max = float(self.up_speed_max if up_speed_max is None else up_speed_max)
        if up_max < up_min:
            up_min, up_max = up_max, up_min

        # facing_x: -1 (left) / +1 (right) / 0 (unknown)
        fx = float(facing_x)
        if fx == 0.0:
            fx = 1.0

        # Spawn slightly behind the helicopter.
        behind_sign = -1.0 if fx >= 0.0 else 1.0
        base_x = float(pos.x) + behind_sign * 34.0
        base_y = float(pos.y) + 10.0

        # Apply clockwise rotation consistently relative to the emission direction.
        # (When emitting leftward, screen-space rotation must be inverted.)
        rotate_rad = 0.0
        if rotate_deg != 0.0:
            rot_sign = 1.0 if behind_sign >= 0.0 else -1.0
            rotate_rad = math.radians(rotate_deg * rot_sign)
        cos_r = math.cos(rotate_rad) if rotate_rad != 0.0 else 1.0
        sin_r = math.sin(rotate_rad) if rotate_rad != 0.0 else 0.0

        hvx = float(heli_vel.x) if heli_vel is not None else 0.0
        hvy = float(heli_vel.y) if heli_vel is not None else 0.0

        count = int(self.burst_count)
        for _ in range(count):
            if len(self.particles) >= self.max_particles:
                break

            # Narrow-ish cone backward with a little vertical spray.
            jitter_x = self._rng.uniform(-6.0, 6.0)
            jitter_y = self._rng.uniform(-4.0, 4.0)
            spawn = Vec2(base_x + jitter_x, base_y + jitter_y)

            back_speed = self._rng.uniform(self.back_speed_min, self.back_speed_max) * back_mult
            vx = behind_sign * back_speed + (-hvx * 0.12) + self._rng.uniform(-35.0, 35.0)
            vy = self._rng.uniform(up_min, up_max) + (-hvy * 0.06)

            if rotate_rad != 0.0:
                # Clockwise rotation in screen coordinates (x right, y down).
                rx = (vx * cos_r) + (vy * sin_r)
                ry = (-vx * sin_r) + (vy * cos_r)
                vx, vy = rx, ry

            ttl = self._rng.uniform(self.ttl_min_s, self.ttl_max_s) * ttl_mult_f
            radius = self._rng.uniform(self.radius_min, self.radius_max)
            intensity = self._rng.uniform(self.intensity_min, self.intensity_max)

            p = FxParticle(
                pos=spawn,
                vel=Vec2(vx, vy),
                age=0.0,
                ttl=ttl,
                radius=radius,
                kind="ember",
            )
            setattr(p, "intensity", intensity)
            if drag is not None:
                try:
                    drag_f = float(drag)
                    if math.isfinite(drag_f):
                        setattr(p, "drag", clamp(drag_f, 0.0, 1.0))
                except Exception:
                    pass
            self.particles.append(p)

    def update(self, dt: float) -> None:
        if dt <= 0.0:
            return

        alive: list[FxParticle] = []
        for p in self.particles:
            p.age += dt
            if p.age >= p.ttl:
                continue

            # Gravity and drag.
            p.vel.y += self.gravity * dt
            drag = float(getattr(p, "drag", 0.985))
            if not math.isfinite(drag):
                drag = 0.985
            drag = clamp(drag, 0.0, 1.0)
            p.vel.x *= drag
            p.vel.y *= drag
            p.pos = Vec2(p.pos.x + p.vel.x * dt, p.pos.y + p.vel.y * dt)
            alive.append(p)

        self.particles = alive
