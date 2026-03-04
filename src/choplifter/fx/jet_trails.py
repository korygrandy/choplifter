from __future__ import annotations

import random

from ..math2d import Vec2
from .particles import FxParticle


class JetTrailSystem:
    def __init__(self, *, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self.particles: list[FxParticle] = []

        self.max_particles = 220
        self.smoke_ttl_min_s = 0.55
        self.smoke_ttl_max_s = 1.10
        self.smoke_radius_min = 4.0
        self.smoke_radius_max = 8.0

    def reset(self) -> None:
        self.particles.clear()

    def emit_trail(self, pos: Vec2, vel: Vec2) -> None:
        if len(self.particles) >= self.max_particles:
            return

        # Spawn slightly behind the jet in its travel direction.
        sign = 1.0 if float(vel.x) >= 0.0 else -1.0
        jitter_x = self._rng.uniform(-4.0, 4.0)
        jitter_y = self._rng.uniform(-3.0, 3.0)
        tail = Vec2(float(pos.x) - sign * 26.0 + jitter_x, float(pos.y) + 4.0 + jitter_y)

        vx = -float(vel.x) * 0.10 + self._rng.uniform(-14.0, 14.0)
        vy = self._rng.uniform(-6.0, 6.0)

        ttl = self._rng.uniform(self.smoke_ttl_min_s, self.smoke_ttl_max_s)
        radius = self._rng.uniform(self.smoke_radius_min, self.smoke_radius_max)

        self.particles.append(
            FxParticle(
                pos=tail,
                vel=Vec2(vx, vy),
                age=0.0,
                ttl=ttl,
                radius=radius,
                kind="smoke",
            )
        )

    def update(self, dt: float) -> None:
        if dt <= 0.0:
            return

        alive: list[FxParticle] = []
        for p in self.particles:
            p.age += dt
            if p.age >= p.ttl:
                continue

            # Gentle rise and dispersion.
            p.vel.y -= 9.0 * dt
            p.pos = Vec2(p.pos.x + p.vel.x * dt, p.pos.y + p.vel.y * dt)
            alive.append(p)

        self.particles = alive
