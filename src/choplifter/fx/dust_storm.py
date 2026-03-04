from __future__ import annotations

import random

from ..math2d import Vec2, clamp
from .particles import FxParticle


class DustStormSystem:
    def __init__(self, *, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self.particles: list[FxParticle] = []

        self.max_particles = 260
        self.spawn_accum = 0.0

        self.dust_ttl_min_s = 0.45
        self.dust_ttl_max_s = 1.00
        self.dust_radius_min = 6.0
        self.dust_radius_max = 12.0

        self.near_ground_y_threshold = 110.0
        self.base_rate_per_s = 55.0

    def reset(self) -> None:
        self.particles.clear()
        self.spawn_accum = 0.0

    def update(self, dt: float, *, heli_pos: Vec2, heli_vel: Vec2, ground_y: float) -> None:
        if dt <= 0.0:
            return

        altitude = float(ground_y) - float(heli_pos.y)
        t = (self.near_ground_y_threshold - altitude) / max(1.0, self.near_ground_y_threshold)
        strength = clamp(t, 0.0, 1.0)

        speed01 = clamp(abs(float(heli_vel.x)) / 220.0, 0.0, 1.0)
        rate = self.base_rate_per_s * strength * (0.35 + 0.65 * speed01)

        if rate > 0.01 and len(self.particles) < self.max_particles:
            self.spawn_accum += dt * rate
            while self.spawn_accum >= 1.0 and len(self.particles) < self.max_particles:
                self.spawn_accum -= 1.0
                self._spawn_dust(heli_pos=heli_pos, heli_vel=heli_vel, ground_y=ground_y, strength=strength)

        alive: list[FxParticle] = []
        for p in self.particles:
            p.age += dt
            if p.age >= p.ttl:
                continue

            # Drift and rise.
            p.vel.y -= 6.0 * dt
            p.vel.x *= 0.985
            p.vel.y *= 0.985
            p.pos = Vec2(p.pos.x + p.vel.x * dt, p.pos.y + p.vel.y * dt)
            alive.append(p)

        self.particles = alive

    def _spawn_dust(self, *, heli_pos: Vec2, heli_vel: Vec2, ground_y: float, strength: float) -> None:
        jitter_x = self._rng.uniform(-34.0, 34.0)
        y = float(ground_y) - self._rng.uniform(0.0, 8.0)
        x = float(heli_pos.x) + jitter_x

        wash = clamp(float(heli_vel.x) * 0.25, -120.0, 120.0)
        vx = -wash + self._rng.uniform(-35.0, 35.0) * (0.35 + 0.65 * strength)
        vy = self._rng.uniform(-12.0, 6.0)

        ttl = self._rng.uniform(self.dust_ttl_min_s, self.dust_ttl_max_s) * (0.75 + 0.35 * strength)
        radius = self._rng.uniform(self.dust_radius_min, self.dust_radius_max) * (0.75 + 0.60 * strength)

        self.particles.append(
            FxParticle(
                pos=Vec2(x, y),
                vel=Vec2(vx, vy),
                age=0.0,
                ttl=ttl,
                radius=radius,
                kind="smoke",
            )
        )
