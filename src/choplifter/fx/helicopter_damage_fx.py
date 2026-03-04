from __future__ import annotations

import random

from ..math2d import Vec2, clamp
from .particles import FxParticle


class HelicopterDamageFxSystem:
    """Smoke/fire particle emissions based on helicopter damage.

    Uses FxParticle so existing rendering helper `_draw_fx_particles` can draw it.

    Damage is assumed to be a 0..100 scale.
    - When remaining health <= 50% (damage >= 50): emit smoke.
    - When remaining health <= 30% (damage >= 70): emit embers + heavier smoke.
    """

    def __init__(self, *, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self.particles: list[FxParticle] = []

        self.max_particles = 300
        self.smoke_spawn_accum = 0.0
        self.ember_spawn_accum = 0.0

        self.smoke_rate_per_s = 34.0
        self.ember_rate_per_s = 22.0

        self.smoke_ttl_min_s = 0.90
        self.smoke_ttl_max_s = 2.10
        self.smoke_radius_min = 7.0
        self.smoke_radius_max = 15.0

        self.ember_ttl_min_s = 0.22
        self.ember_ttl_max_s = 0.55
        self.ember_radius_min = 1.6
        self.ember_radius_max = 3.4

    def reset(self) -> None:
        self.particles.clear()
        self.smoke_spawn_accum = 0.0
        self.ember_spawn_accum = 0.0

    def update(self, dt: float, *, heli_pos: Vec2, heli_vel: Vec2, damage: float) -> None:
        if dt <= 0.0:
            return

        dmg = clamp(float(damage), 0.0, 100.0)

        smoke_active = dmg >= 50.0
        fire_active = dmg >= 70.0

        # Threshold mapping: 50..90 ramps up smoke, 70..100 adds embers.
        smoke_strength = clamp((dmg - 50.0) / 40.0, 0.0, 1.0)
        fire_strength = clamp((dmg - 70.0) / 30.0, 0.0, 1.0)

        # Nothing to do until smoke threshold.
        if not smoke_active and not fire_active and not self.particles:
            return

        # Damage FX origin: closer to the helicopter body so it's readable.
        vx = float(heli_vel.x)
        sign = 0.0 if abs(vx) < 1.0 else (1.0 if vx >= 0.0 else -1.0)
        base = Vec2(float(heli_pos.x) - sign * 16.0, float(heli_pos.y) - 12.0)

        if len(self.particles) < self.max_particles and smoke_active:
            # Ensure a visible baseline at threshold; scale up into heavy smoke.
            rate = self.smoke_rate_per_s * (0.90 + 0.90 * smoke_strength) * (1.0 + 0.55 * fire_strength)
            self.smoke_spawn_accum += dt * rate
            while self.smoke_spawn_accum >= 1.0 and len(self.particles) < self.max_particles:
                self.smoke_spawn_accum -= 1.0
                self._spawn_smoke(base, heli_vel=heli_vel, strength=smoke_strength)
        if len(self.particles) < self.max_particles and fire_active:
            # Embers should start being noticeable right when fire begins.
            rate = self.ember_rate_per_s * (0.55 + 0.85 * fire_strength)
            self.ember_spawn_accum += dt * rate
            while self.ember_spawn_accum >= 1.0 and len(self.particles) < self.max_particles:
                self.ember_spawn_accum -= 1.0
                self._spawn_ember(base, heli_vel=heli_vel, strength=fire_strength)

        # Update + cull.
        alive: list[FxParticle] = []
        for p in self.particles:
            p.age += dt
            if p.age >= p.ttl:
                continue

            if p.kind == "ember":
                p.vel.y -= 24.0 * dt
                p.vel.x *= 0.985
                p.vel.y *= 0.985
            else:
                p.vel.y -= 10.0 * dt
                p.vel.x *= 0.99
                p.vel.y *= 0.99

            p.pos = Vec2(p.pos.x + p.vel.x * dt, p.pos.y + p.vel.y * dt)
            alive.append(p)

        self.particles = alive

    def _spawn_smoke(self, base: Vec2, *, heli_vel: Vec2, strength: float) -> None:
        jitter_x = self._rng.uniform(-10.0, 10.0)
        jitter_y = self._rng.uniform(-10.0, 6.0)

        vx = -float(heli_vel.x) * 0.10 + self._rng.uniform(-16.0, 16.0)
        vy = self._rng.uniform(-18.0, 2.0)

        ttl = self._rng.uniform(self.smoke_ttl_min_s, self.smoke_ttl_max_s) * (0.90 + 0.45 * strength)
        radius = self._rng.uniform(self.smoke_radius_min, self.smoke_radius_max) * (0.85 + 0.70 * strength)

        p = FxParticle(
            pos=Vec2(base.x + jitter_x, base.y + jitter_y),
            vel=Vec2(vx, vy),
            age=0.0,
            ttl=ttl,
            radius=radius,
            kind="smoke",
        )
        # Per-particle alpha boost so low-damage smoke reads on bright backgrounds.
        p.intensity = 1.65 + 0.75 * clamp(float(strength), 0.0, 1.0)
        self.particles.append(p)

    def _spawn_ember(self, base: Vec2, *, heli_vel: Vec2, strength: float) -> None:
        jitter_x = self._rng.uniform(-6.0, 6.0)
        jitter_y = self._rng.uniform(-4.0, 3.0)

        vx = -float(heli_vel.x) * 0.06 + self._rng.uniform(-60.0, 60.0)
        vy = -self._rng.uniform(70.0, 150.0) * (0.50 + 0.50 * strength)

        ttl = self._rng.uniform(self.ember_ttl_min_s, self.ember_ttl_max_s) * (0.80 + 0.40 * strength)
        radius = self._rng.uniform(self.ember_radius_min, self.ember_radius_max)

        p = FxParticle(
            pos=Vec2(base.x + jitter_x, base.y + jitter_y),
            vel=Vec2(vx, vy),
            age=0.0,
            ttl=ttl,
            radius=radius,
            kind="ember",
        )
        p.intensity = 1.10 + 0.50 * clamp(float(strength), 0.0, 1.0)
        self.particles.append(p)
