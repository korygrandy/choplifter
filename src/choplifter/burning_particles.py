from __future__ import annotations

from dataclasses import dataclass
import random

from .math2d import Vec2, clamp


@dataclass
class BurningParticle:
    pos: Vec2
    vel: Vec2
    age: float
    ttl: float
    radius: float
    kind: str  # "ember" | "smoke"


@dataclass
class BurningSite:
    pos: Vec2
    age: float
    ttl: float
    intensity: float
    ember_spawn_accum: float = 0.0
    smoke_spawn_accum: float = 0.0


class BurningParticleSystem:
    def __init__(self, *, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self.sites: list[BurningSite] = []
        self.particles: list[BurningParticle] = []

        # Tunables.
        self.max_sites = 24
        self.max_particles = 260

        # How long a destroyed target burns.
        self.site_ttl_s = 18.0

        # Spawn rates at full intensity.
        self.ember_rate_per_s = 26.0
        self.smoke_rate_per_s = 10.0

        # Particle characteristics.
        self.ember_ttl_min_s = 0.25
        self.ember_ttl_max_s = 0.55
        self.smoke_ttl_min_s = 0.9
        self.smoke_ttl_max_s = 1.9

        self.ember_radius_min = 1.0
        self.ember_radius_max = 2.6
        self.smoke_radius_min = 5.0
        self.smoke_radius_max = 10.0

    def reset(self) -> None:
        self.sites.clear()
        self.particles.clear()

    def add_site(self, pos: Vec2, *, intensity: float = 1.0) -> None:
        if len(self.sites) >= self.max_sites:
            return

        intensity = clamp(float(intensity), 0.0, 1.0)
        self.sites.append(
            BurningSite(
                pos=Vec2(float(pos.x), float(pos.y)),
                age=0.0,
                ttl=self.site_ttl_s,
                intensity=intensity,
            )
        )

    def update(self, dt: float) -> None:
        if dt <= 0.0:
            return

        # Update sites and spawn particles.
        alive_sites: list[BurningSite] = []
        for site in self.sites:
            site.age += dt
            if site.age >= site.ttl:
                continue

            t = site.age / max(0.001, site.ttl)
            fade = (1.0 - t) * (1.0 - t)
            strength = clamp(site.intensity * fade, 0.0, 1.0)

            site.ember_spawn_accum += dt * (self.ember_rate_per_s * strength)
            site.smoke_spawn_accum += dt * (self.smoke_rate_per_s * strength)

            while site.ember_spawn_accum >= 1.0 and len(self.particles) < self.max_particles:
                site.ember_spawn_accum -= 1.0
                self._spawn_ember(site.pos, strength=strength)

            while site.smoke_spawn_accum >= 1.0 and len(self.particles) < self.max_particles:
                site.smoke_spawn_accum -= 1.0
                self._spawn_smoke(site.pos, strength=strength)

            alive_sites.append(site)

        self.sites = alive_sites

        # Update and cull particles.
        alive_particles: list[BurningParticle] = []
        for p in self.particles:
            p.age += dt
            if p.age >= p.ttl:
                continue

            # Slight upward drift; embers rise faster.
            if p.kind == "ember":
                p.vel.y -= 18.0 * dt
            else:
                p.vel.y -= 9.0 * dt

            p.pos = Vec2(p.pos.x + p.vel.x * dt, p.pos.y + p.vel.y * dt)

            alive_particles.append(p)

        self.particles = alive_particles

    def _spawn_ember(self, base: Vec2, *, strength: float) -> None:
        jitter_x = self._rng.uniform(-6.0, 6.0)
        jitter_y = self._rng.uniform(-2.0, 2.0)
        vx = self._rng.uniform(-25.0, 25.0)
        vy = -self._rng.uniform(35.0, 85.0) * (0.35 + 0.65 * strength)
        ttl = self._rng.uniform(self.ember_ttl_min_s, self.ember_ttl_max_s) * (0.75 + 0.45 * strength)
        radius = self._rng.uniform(self.ember_radius_min, self.ember_radius_max)
        self.particles.append(
            BurningParticle(
                pos=Vec2(base.x + jitter_x, base.y + jitter_y),
                vel=Vec2(vx, vy),
                age=0.0,
                ttl=ttl,
                radius=radius,
                kind="ember",
            )
        )

    def _spawn_smoke(self, base: Vec2, *, strength: float) -> None:
        jitter_x = self._rng.uniform(-10.0, 10.0)
        jitter_y = self._rng.uniform(-6.0, 2.0)
        vx = self._rng.uniform(-10.0, 10.0)
        vy = -self._rng.uniform(14.0, 32.0) * (0.40 + 0.60 * strength)
        ttl = self._rng.uniform(self.smoke_ttl_min_s, self.smoke_ttl_max_s) * (0.85 + 0.35 * strength)
        radius = self._rng.uniform(self.smoke_radius_min, self.smoke_radius_max) * (0.75 + 0.50 * strength)
        self.particles.append(
            BurningParticle(
                pos=Vec2(base.x + jitter_x, base.y + jitter_y),
                vel=Vec2(vx, vy),
                age=0.0,
                ttl=ttl,
                radius=radius,
                kind="smoke",
            )
        )
