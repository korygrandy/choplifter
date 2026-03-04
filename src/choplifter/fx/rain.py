from __future__ import annotations

import random
from ..math2d import Vec2, clamp
from .particles import FxParticle

class RainSystem:
    def __init__(self, *, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self.particles: list[FxParticle] = []
        self.max_particles = 180
        self.spawn_accum = 0.0
        self.rain_ttl_min_s = 0.5
        self.rain_ttl_max_s = 1.2
        self.rain_radius = 2.0
        self.base_rate_per_s = 90.0

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
                self._spawn_rain(area_width, area_height)
        alive: list[FxParticle] = []
        for p in self.particles:
            p.age += dt
            if p.age >= p.ttl:
                continue
            # Rain falls straight down, slight wind drift
            p.vel.x *= 0.98
            p.pos = Vec2(p.pos.x + p.vel.x * dt, p.pos.y + p.vel.y * dt)
            alive.append(p)
        self.particles = alive

    def _spawn_rain(self, area_width: float, area_height: float) -> None:
        x = self._rng.uniform(0, area_width)
        y = self._rng.uniform(-20, 0)
        vel_x = self._rng.uniform(-10, 10)
        vel_y = self._rng.uniform(320, 400)
        ttl = self._rng.uniform(self.rain_ttl_min_s, self.rain_ttl_max_s)
        p = FxParticle(
            pos=Vec2(x, y),
            vel=Vec2(vel_x, vel_y),
            age=0.0,
            ttl=ttl,
            radius=self.rain_radius,
            kind="rain",
        )
        self.particles.append(p)
