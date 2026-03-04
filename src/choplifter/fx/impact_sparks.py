from __future__ import annotations

import math
import random

from ..math2d import Vec2, clamp
from .particles import FxParticle


class ImpactSparkSystem:
    def __init__(self, *, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self.particles: list[FxParticle] = []

        self.max_particles = 160
        self.spark_count = 10
        self.spark_ttl_min_s = 0.10
        self.spark_ttl_max_s = 0.22
        self.spark_radius_min = 1.0
        self.spark_radius_max = 2.4

    def reset(self) -> None:
        self.particles.clear()

    def emit_hit(self, pos: Vec2, incoming_vel: Vec2, *, strength: float = 1.0) -> None:
        if len(self.particles) >= self.max_particles:
            return

        s = clamp(float(strength), 0.35, 2.25)

        ivx, ivy = float(incoming_vel.x), float(incoming_vel.y)
        mag = math.hypot(ivx, ivy)
        if mag > 0.001:
            nx = -ivx / mag
            ny = -ivy / mag
        else:
            nx, ny = 0.0, -1.0

        count = max(1, int(self.spark_count * (0.65 + 0.70 * s)))
        for _ in range(count):
            if len(self.particles) >= self.max_particles:
                break

            spread = self._rng.uniform(-math.pi * 0.65, math.pi * 0.65)
            base_ang = math.atan2(ny, nx)
            ang = base_ang + spread

            speed = self._rng.uniform(75.0, 180.0) * (0.70 + 0.55 * s)
            vx = math.cos(ang) * speed + self._rng.uniform(-20.0, 20.0)
            vy = math.sin(ang) * speed + self._rng.uniform(-20.0, 20.0)

            ttl = self._rng.uniform(self.spark_ttl_min_s, self.spark_ttl_max_s) * (0.85 + 0.35 * s)
            radius = self._rng.uniform(self.spark_radius_min, self.spark_radius_max) * (0.80 + 0.30 * s)

            self.particles.append(
                FxParticle(
                    pos=Vec2(float(pos.x), float(pos.y)),
                    vel=Vec2(vx, vy),
                    age=0.0,
                    ttl=ttl,
                    radius=radius,
                    kind="ember",
                )
            )

    def update(self, dt: float) -> None:
        if dt <= 0.0:
            return

        gravity = 220.0
        alive: list[FxParticle] = []
        for p in self.particles:
            p.age += dt
            if p.age >= p.ttl:
                continue

            p.vel.y += gravity * dt
            p.vel.x *= 0.98
            p.vel.y *= 0.98

            p.pos = Vec2(p.pos.x + p.vel.x * dt, p.pos.y + p.vel.y * dt)
            alive.append(p)

        self.particles = alive
