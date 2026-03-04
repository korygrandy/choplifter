from __future__ import annotations

import math
import random

from ..math2d import Vec2, clamp
from .particles import FxParticle


class ExplosionSystem:
    """A short burst of embers + smoke, intended for impacts/explosions."""

    def __init__(self, *, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self.particles: list[FxParticle] = []
        self.max_particles = 420

    def reset(self) -> None:
        self.particles.clear()

    def emit_explosion(self, pos: Vec2, *, strength: float = 1.0) -> None:
        if len(self.particles) >= self.max_particles:
            return

        strength = clamp(float(strength), 0.0, 1.0)
        ember_count = int(32 + 36 * strength)
        smoke_count = int(18 + 26 * strength)

        # Embers: bright, fast, short-lived.
        for _ in range(ember_count):
            if len(self.particles) >= self.max_particles:
                break
            ang = self._rng.uniform(0.0, math.tau)
            speed = self._rng.uniform(140.0, 280.0) * (0.75 + 0.45 * strength)
            vx = math.cos(ang) * speed + self._rng.uniform(-30.0, 30.0)
            vy = math.sin(ang) * speed - self._rng.uniform(40.0, 120.0)
            ttl = self._rng.uniform(0.18, 0.55)
            radius = self._rng.uniform(1.2, 3.2)
            self.particles.append(
                FxParticle(
                    pos=Vec2(float(pos.x) + self._rng.uniform(-6.0, 6.0), float(pos.y) + self._rng.uniform(-6.0, 6.0)),
                    vel=Vec2(vx, vy),
                    age=0.0,
                    ttl=ttl,
                    radius=radius,
                    kind="ember",
                )
            )

        # Smoke: slower, longer-lived.
        for _ in range(smoke_count):
            if len(self.particles) >= self.max_particles:
                break
            ang = self._rng.uniform(0.0, math.tau)
            speed = self._rng.uniform(40.0, 120.0) * (0.60 + 0.55 * strength)
            vx = math.cos(ang) * speed + self._rng.uniform(-18.0, 18.0)
            vy = math.sin(ang) * speed - self._rng.uniform(20.0, 65.0)
            ttl = self._rng.uniform(0.65, 1.60) * (0.85 + 0.35 * strength)
            radius = self._rng.uniform(8.0, 18.0) * (0.75 + 0.60 * strength)
            self.particles.append(
                FxParticle(
                    pos=Vec2(float(pos.x) + self._rng.uniform(-10.0, 10.0), float(pos.y) + self._rng.uniform(-8.0, 8.0)),
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

        gravity = 260.0
        alive: list[FxParticle] = []
        for p in self.particles:
            p.age += dt
            if p.age >= p.ttl:
                continue

            if p.kind == "ember":
                p.vel.y += gravity * dt
                p.vel.x *= 0.975
                p.vel.y *= 0.975
            else:
                p.vel.y -= 14.0 * dt
                p.vel.x *= 0.985
                p.vel.y *= 0.985

            p.pos = Vec2(p.pos.x + p.vel.x * dt, p.pos.y + p.vel.y * dt)
            alive.append(p)

        self.particles = alive
