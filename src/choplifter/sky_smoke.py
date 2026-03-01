from __future__ import annotations

from dataclasses import dataclass
import random

import pygame

from .math2d import Vec2


@dataclass
class SmokePuff:
    pos: Vec2
    vel: Vec2
    age: float
    ttl: float
    radius: float


class SkySmokeSystem:
    def __init__(self, *, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self._puffs: list[SmokePuff] = []

        # Tunables (kept simple on purpose).
        self.spawn_rate_per_s = 0.55
        self.max_puffs = 28
        self.ttl_s_min = 2.8
        self.ttl_s_max = 5.2
        self.radius_min = 10.0
        self.radius_max = 28.0
        self.spawn_band_px = 32

        self.up_speed_min = 12.0
        self.up_speed_max = 26.0
        self.side_speed_min = -8.0
        self.side_speed_max = 8.0

        # Accumulator for stable spawn rate independent of FPS.
        self._spawn_accum = 0.0

        # Cached sprites by integer radius.
        self._sprite_cache: dict[int, pygame.Surface] = {}

    def reset(self) -> None:
        self._puffs.clear()
        self._spawn_accum = 0.0

    def update(self, dt: float, *, width: int, horizon_y: int) -> None:
        if dt <= 0.0:
            return

        # Spawn.
        if len(self._puffs) < self.max_puffs:
            self._spawn_accum += dt * self.spawn_rate_per_s
            while self._spawn_accum >= 1.0 and len(self._puffs) < self.max_puffs:
                self._spawn_accum -= 1.0
                self._spawn_one(width=width, horizon_y=horizon_y)

        # Update & cull.
        alive: list[SmokePuff] = []
        for p in self._puffs:
            p.age += dt
            if p.age >= p.ttl:
                continue
            p.pos = Vec2(p.pos.x + p.vel.x * dt, p.pos.y + p.vel.y * dt)

            # Soft horizontal wrap for endless skyline drift.
            if p.pos.x < -80:
                p.pos = Vec2(width + 80, p.pos.y)
            elif p.pos.x > width + 80:
                p.pos = Vec2(-80, p.pos.y)

            # Keep in the sky region; if it somehow dips below the horizon, drop it.
            if p.pos.y > horizon_y - 2:
                continue

            alive.append(p)

        self._puffs = alive

    def draw(self, screen: pygame.Surface, *, horizon_y: int) -> None:
        # Draw above the horizon only.
        for p in self._puffs:
            if p.pos.y >= horizon_y:
                continue

            t = p.age / p.ttl
            # Ease-out fade and a tiny expansion as it rises.
            alpha = int(170 * (1.0 - t) * (1.0 - t))
            if alpha <= 0:
                continue

            radius = p.radius * (1.0 + 0.25 * t)
            sprite = self._get_puff_sprite(int(max(1, radius)))
            sprite.set_alpha(alpha)

            screen.blit(sprite, (int(p.pos.x - sprite.get_width() / 2), int(p.pos.y - sprite.get_height() / 2)))

    def _spawn_one(self, *, width: int, horizon_y: int) -> None:
        x = self._rng.uniform(0.0, float(width))
        # Spawn in a thin band just above the horizon.
        y = float(horizon_y) - self._rng.uniform(6.0, float(max(8, self.spawn_band_px)))

        ttl = self._rng.uniform(self.ttl_s_min, self.ttl_s_max)
        radius = self._rng.uniform(self.radius_min, self.radius_max)

        vx = self._rng.uniform(self.side_speed_min, self.side_speed_max)
        vy = -self._rng.uniform(self.up_speed_min, self.up_speed_max)

        self._puffs.append(
            SmokePuff(
                pos=Vec2(x, y),
                vel=Vec2(vx, vy),
                age=0.0,
                ttl=ttl,
                radius=radius,
            )
        )

    def _get_puff_sprite(self, radius: int) -> pygame.Surface:
        cached = self._sprite_cache.get(radius)
        if cached is not None:
            return cached

        # A soft-looking puff: layered circles with decreasing alpha.
        size = radius * 2 + 6
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        cx = size // 2
        cy = size // 2

        # Big soft base.
        pygame.draw.circle(s, (230, 230, 230, 60), (cx, cy), radius)
        # Inner denser region.
        pygame.draw.circle(s, (240, 240, 240, 90), (cx - radius // 6, cy), max(1, int(radius * 0.75)))
        pygame.draw.circle(s, (245, 245, 245, 80), (cx + radius // 8, cy - radius // 10), max(1, int(radius * 0.65)))
        # Slight shadow edge to sell volume.
        pygame.draw.circle(s, (200, 200, 200, 55), (cx + radius // 5, cy + radius // 6), max(1, int(radius * 0.55)))

        self._sprite_cache[radius] = s
        return s
