from __future__ import annotations

import random
from ..math2d import Vec2
from .particles import FxParticle

class LightningStrike:
    def __init__(self, x: float, y_start: float, y_end: float, ttl: float = 0.25):
        self.x = x
        self.y_start = y_start
        self.y_end = y_end
        self.ttl = ttl
        self.age = 0.0
        self.active = True

    def update(self, dt: float):
        self.age += dt
        if self.age >= self.ttl:
            self.active = False

class LightningSystem:
    def __init__(self, *, area_width: float, area_height: float, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self.strikes: list[LightningStrike] = []
        self.cooldown = 0.0
        self.strike_interval_min = 6.0
        self.strike_interval_max = 18.0
        self.area_width = area_width
        self.area_height = area_height
        self.last_strike_x = None

    def reset(self):
        self.strikes.clear()
        self.cooldown = 0.0

    def update(self, dt: float, helicopter_x: float, helicopter_y: float) -> tuple[bool, float]:
        # Returns (hit_player, strike_x)
        self.cooldown -= dt
        hit_player = False
        strike_x = None
        if self.cooldown <= 0.0:
            x = self._rng.uniform(0, self.area_width)
            y_start = 0
            y_end = self.area_height
            strike = LightningStrike(x, y_start, y_end)
            self.strikes.append(strike)
            self.cooldown = self._rng.uniform(self.strike_interval_min, self.strike_interval_max)
            self.last_strike_x = x
            # Check if helicopter is hit (simple AABB, can refine)
            if abs(helicopter_x - x) < 32:  # 32px tolerance
                hit_player = True
                strike_x = x
        for strike in self.strikes:
            strike.update(dt)
        self.strikes = [s for s in self.strikes if s.active]
        return hit_player, self.last_strike_x

    def draw(self, surface, color=(255,255,200)):
        import pygame
        for strike in self.strikes:
            if strike.active:
                pygame.draw.line(surface, color, (strike.x, strike.y_start), (strike.x, strike.y_end), 4)
