from __future__ import annotations

import random

from ..entities import Enemy
from ..game_types import EnemyKind
from ..math2d import Vec2, clamp
from .particles import FxParticle


class EnemyDamageFxSystem:
    def __init__(self, *, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self.particles: list[FxParticle] = []
        self.max_particles = 260
        self.smoke_rate_per_s = 16.0
        self.smoke_ttl_min_s = 0.75
        self.smoke_ttl_max_s = 1.85
        self.smoke_radius_min = 5.0
        self.smoke_radius_max = 11.0

    def reset(self) -> None:
        self.particles.clear()

    def emit_hit_puff(self, pos: Vec2, *, incoming_vel: Vec2, strength: float = 1.0) -> None:
        if len(self.particles) >= self.max_particles:
            return

        strength = clamp(float(strength), 0.0, 1.0)
        ember_count = int(3 + 4 * strength)
        smoke_count = int(4 + 5 * strength)

        for _ in range(ember_count):
            if len(self.particles) >= self.max_particles:
                break
            p = FxParticle(
                pos=Vec2(float(pos.x) + self._rng.uniform(-4.0, 4.0), float(pos.y) + self._rng.uniform(-3.0, 3.0)),
                vel=Vec2(float(incoming_vel.x) * 0.12 + self._rng.uniform(-50.0, 50.0), -self._rng.uniform(35.0, 95.0)),
                age=0.0,
                ttl=self._rng.uniform(0.14, 0.34),
                radius=self._rng.uniform(1.2, 2.4),
                kind="ember",
            )
            p.intensity = 1.15
            self.particles.append(p)

        for _ in range(smoke_count):
            if len(self.particles) >= self.max_particles:
                break
            p = FxParticle(
                pos=Vec2(float(pos.x) + self._rng.uniform(-6.0, 6.0), float(pos.y) + self._rng.uniform(-5.0, 3.0)),
                vel=Vec2(float(incoming_vel.x) * 0.05 + self._rng.uniform(-14.0, 14.0), -self._rng.uniform(12.0, 28.0)),
                age=0.0,
                ttl=self._rng.uniform(0.28, 0.75),
                radius=self._rng.uniform(4.5, 8.0) * (0.85 + 0.45 * strength),
                kind="smoke",
                color=(155, 155, 155),
            )
            p.intensity = 1.35 + 0.45 * strength
            self.particles.append(p)

    def update(self, dt: float, *, enemies: list[Enemy], tank_health: float) -> None:
        if dt <= 0.0:
            return

        tank_health = max(1.0, float(tank_health))

        for enemy in enemies:
            if not bool(getattr(enemy, "alive", False)) or getattr(enemy, "kind", None) is not EnemyKind.TANK:
                continue

            max_health = float(getattr(enemy, "max_health", 0.0))
            if max_health <= 0.0:
                max_health = tank_health
            health = max(0.0, float(getattr(enemy, "health", max_health)))
            remaining_ratio = health / max_health
            if remaining_ratio > 0.5:
                setattr(enemy, "damage_smoke_spawn_accum", 0.0)
                continue

            strength = clamp((0.5 - remaining_ratio) / 0.35, 0.0, 1.0)
            rate = self.smoke_rate_per_s * (0.85 + 1.10 * strength)
            accum = float(getattr(enemy, "damage_smoke_spawn_accum", 0.0)) + dt * rate
            while accum >= 1.0 and len(self.particles) < self.max_particles:
                accum -= 1.0
                self._spawn_tank_smoke(enemy.pos, strength=strength)
            setattr(enemy, "damage_smoke_spawn_accum", accum)

        alive: list[FxParticle] = []
        for particle in self.particles:
            particle.age += dt
            if particle.age >= particle.ttl:
                continue

            if particle.kind == "ember":
                particle.vel.y -= 22.0 * dt
                particle.vel.x *= 0.982
                particle.vel.y *= 0.982
            else:
                particle.vel.y -= 8.0 * dt
                particle.vel.x *= 0.99
                particle.vel.y *= 0.99

            particle.pos = Vec2(particle.pos.x + particle.vel.x * dt, particle.pos.y + particle.vel.y * dt)
            alive.append(particle)

        self.particles = alive

    def _spawn_tank_smoke(self, base: Vec2, *, strength: float) -> None:
        color = (95, 95, 95) if strength < 0.55 else (55, 55, 55)
        p = FxParticle(
            pos=Vec2(float(base.x) + self._rng.uniform(-10.0, 10.0), float(base.y) - 15.0 + self._rng.uniform(-4.0, 3.0)),
            vel=Vec2(self._rng.uniform(-10.0, 10.0), -self._rng.uniform(18.0, 34.0) * (0.9 + 0.35 * strength)),
            age=0.0,
            ttl=self._rng.uniform(self.smoke_ttl_min_s, self.smoke_ttl_max_s) * (0.95 + 0.45 * strength),
            radius=self._rng.uniform(self.smoke_radius_min, self.smoke_radius_max) * (0.90 + 0.65 * strength),
            kind="smoke",
            color=color,
        )
        p.intensity = 1.35 + 0.55 * strength
        self.particles.append(p)