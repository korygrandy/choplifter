from __future__ import annotations

import random
from ..math2d import Vec2, clamp
from .particles import FxParticle

class WindBlownDustCloud:
    def __init__(self, *, x: float, y: float, vx: float, vy: float, radius: float, ttl: float, color: tuple[int, int, int], alpha: int):
        self.pos = Vec2(x, y)
        self.vel = Vec2(vx, vy)
        self.radius = radius
        self.ttl = ttl
        self.age = 0.0
        self.color = color
        self.alpha = alpha

    def update(self, dt: float):
        self.age += dt
        self.pos.x += self.vel.x * dt
        self.pos.y += self.vel.y * dt
        # Optionally fade out
        if self.age > self.ttl * 0.7:
            self.alpha = int(self.alpha * (1.0 - (self.age - self.ttl * 0.7) / (self.ttl * 0.3)))

    @property
    def is_alive(self):
        return self.age < self.ttl and self.alpha > 0

class WindBlownDustCloudSystem:
    def __init__(self, *, seed: int | None = None):
        self._rng = random.Random(seed)
        self.clouds: list[WindBlownDustCloud] = []
        self.max_clouds = 8
        self.spawn_accum = 0.0
        self.spawn_rate_per_s = 0.7

    def reset(self):
        self.clouds.clear()
        self.spawn_accum = 0.0

    def update(self, dt: float, *, ground_y: float, wind_vx: float, screen_w: float):
        if dt <= 0.0:
            return
        self.spawn_accum += dt * self.spawn_rate_per_s
        while self.spawn_accum >= 1.0 and len(self.clouds) < self.max_clouds:
            self.spawn_accum -= 1.0
            self._spawn_cloud(ground_y=ground_y, wind_vx=wind_vx, screen_w=screen_w)
        alive = []
        for c in self.clouds:
            c.update(dt)
            if c.is_alive:
                alive.append(c)
        self.clouds = alive

    def _spawn_cloud(self, *, ground_y: float, wind_vx: float, screen_w: float):
        x = -120 if wind_vx > 0 else screen_w + 120
        y = ground_y - self._rng.uniform(10, 40)
        vx = wind_vx * self._rng.uniform(0.7, 1.2) + self._rng.uniform(10, 30) * (1 if wind_vx > 0 else -1)
        vy = self._rng.uniform(-2, 2)
        radius = self._rng.uniform(60, 120)
        ttl = self._rng.uniform(5.0, 8.0)
        color = (200, 180, 120)
        alpha = self._rng.randint(60, 110)
        self.clouds.append(WindBlownDustCloud(x=x, y=y, vx=vx, vy=vy, radius=radius, ttl=ttl, color=color, alpha=alpha))
