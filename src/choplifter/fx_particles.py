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
            rate = self.smoke_rate_per_s * (0.60 + 0.80 * smoke_strength) * (1.0 + 0.60 * fire_strength)
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

        self.particles.append(
            FxParticle(
                pos=Vec2(base.x + jitter_x, base.y + jitter_y),
                vel=Vec2(vx, vy),
                age=0.0,
                ttl=ttl,
                radius=radius,
                kind="smoke",
            )
        )

    def _spawn_ember(self, base: Vec2, *, heli_vel: Vec2, strength: float) -> None:
        jitter_x = self._rng.uniform(-6.0, 6.0)
        jitter_y = self._rng.uniform(-4.0, 3.0)

        vx = -float(heli_vel.x) * 0.06 + self._rng.uniform(-60.0, 60.0)
        vy = -self._rng.uniform(70.0, 150.0) * (0.50 + 0.50 * strength)

        ttl = self._rng.uniform(self.ember_ttl_min_s, self.ember_ttl_max_s) * (0.80 + 0.40 * strength)
        radius = self._rng.uniform(self.ember_radius_min, self.ember_radius_max)

        self.particles.append(
            FxParticle(
                pos=Vec2(base.x + jitter_x, base.y + jitter_y),
                vel=Vec2(vx, vy),
                age=0.0,
                ttl=ttl,
                radius=radius,
                kind="ember",
            )
        )


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
