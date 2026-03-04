from __future__ import annotations

import random
from ..math2d import Vec2, clamp
from .particles import FxParticle

class FogSystem:
    def __init__(self, *, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self.particles: list[FxParticle] = []
        self.max_particles = 80
        self.spawn_accum = 0.0
        self.fog_ttl_min_s = 2.5
        self.fog_ttl_max_s = 5.0
        self.fog_radius_min = 32.0
        self.fog_radius_max = 64.0
        self.base_rate_per_s = 8.0

    def reset(self) -> None:
        self.particles.clear()
        self.spawn_accum = 0.0

    def update(self, dt: float, *, area_width: float, area_height: float) -> None:
        if dt <= 0.0:
            return
        rate = self.base_rate_per_s
        if rate > 0.01 and len(self.particles) < self.max_particles:
            self.spawn_accum += dt * rate
            while self.spawn_accum >= 1.0 and len(self.particles) < self.max_particles:
                self.spawn_accum -= 1.0
                self._spawn_fog(area_width, area_height)
        alive: list[FxParticle] = []
        for p in self.particles:
            p.age += dt
            if p.age >= p.ttl:
                continue
            # Fog drifts slowly sideways
            p.vel.x *= 0.995
            p.vel.y *= 0.995
            p.pos = Vec2(p.pos.x + p.vel.x * dt, p.pos.y + p.vel.y * dt)
            alive.append(p)
        self.particles = alive

    def _spawn_fog(self, area_width: float, area_height: float) -> None:
        x = self._rng.uniform(0, area_width)
        y = self._rng.uniform(0, area_height * 0.7)
        vel_x = self._rng.uniform(8, 32)
        vel_y = self._rng.uniform(-2, 2)
        ttl = self._rng.uniform(self.fog_ttl_min_s, self.fog_ttl_max_s)
        radius = self._rng.uniform(self.fog_radius_min, self.fog_radius_max)
        p = FxParticle(
            pos=Vec2(x, y),
            vel=Vec2(vel_x, vel_y),
            age=0.0,
            ttl=ttl,
            radius=radius,
            kind="fog",
        )
        self.particles.append(p)
