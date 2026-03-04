from __future__ import annotations

from dataclasses import dataclass
import math
import random

from .math2d import Vec2, clamp


@dataclass
class FxParticle:
    pos: Vec2
    vel: Vec2
    age: float
    ttl: float
    radius: float
    kind: str  # "ember" | "smoke"


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

    def emit_hit(self, pos: Vec2, incoming_vel: Vec2) -> None:
        if len(self.particles) >= self.max_particles:
            return

        ivx, ivy = float(incoming_vel.x), float(incoming_vel.y)
        mag = math.hypot(ivx, ivy)
        if mag > 0.001:
            nx = -ivx / mag
            ny = -ivy / mag
        else:
            nx, ny = 0.0, -1.0

        count = int(self.spark_count)
        for _ in range(count):
            if len(self.particles) >= self.max_particles:
                break

            spread = self._rng.uniform(-math.pi * 0.65, math.pi * 0.65)
            base_ang = math.atan2(ny, nx)
            ang = base_ang + spread

            speed = self._rng.uniform(75.0, 180.0)
            vx = math.cos(ang) * speed + self._rng.uniform(-20.0, 20.0)
            vy = math.sin(ang) * speed + self._rng.uniform(-20.0, 20.0)

            ttl = self._rng.uniform(self.spark_ttl_min_s, self.spark_ttl_max_s)
            radius = self._rng.uniform(self.spark_radius_min, self.spark_radius_max)

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
