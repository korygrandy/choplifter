from __future__ import annotations

from dataclasses import dataclass, field
import math
import random

from .math2d import Vec2, clamp


@dataclass
class SupplyDrop:
    pos: Vec2
    vel: Vec2
    kind: str  # "bullets" | "bombs" | "health"
    age_s: float = 0.0
    sway_phase: float = 0.0
    sway_freq_hz: float = 1.2
    sway_amp_px: float = 22.0
    landed: bool = False
    landed_age_s: float = 0.0
    alive: bool = True


@dataclass
class SupplyDropManager:
    drops: list[SupplyDrop] = field(default_factory=list)
    spawn_timer_s: float = 10.0
    spawn_min_interval_s: float = 14.0
    spawn_max_interval_s: float = 26.0
    gravity: float = 22.0
    max_alive: int = 2
    collect_radius_px: float = 34.0
    ground_lifetime_s: float = 5.0
    health_restore_amount: float = 28.0

    _spawn_counter: int = 0
    _rng: random.Random = field(default_factory=lambda: random.Random(1337))

    def reset(self) -> None:
        self.drops.clear()
        self.spawn_timer_s = 10.0
        self._spawn_counter = 0

    def _next_spawn_interval(self) -> float:
        lo = min(self.spawn_min_interval_s, self.spawn_max_interval_s)
        hi = max(self.spawn_min_interval_s, self.spawn_max_interval_s)
        return self._rng.uniform(lo, hi)

    def _spawn_drop(self, *, helicopter: object, world_width: float) -> None:
        facing_x = float(getattr(getattr(helicopter, "facing", None), "value", 1.0) or 1.0)
        sign = 1.0 if facing_x >= 0.0 else -1.0
        x = float(getattr(helicopter, "pos").x) + sign * self._rng.uniform(220.0, 360.0)
        x = clamp(x, 60.0, max(60.0, world_width - 60.0))
        y = max(26.0, float(getattr(helicopter, "pos").y) - self._rng.uniform(120.0, 180.0))

        kind = self._next_drop_kind()
        self._spawn_counter += 1
        self.drops.append(
            SupplyDrop(
                pos=Vec2(x, y),
                vel=Vec2(0.0, 8.0),
                kind=kind,
                sway_phase=self._rng.uniform(0.0, math.tau),
                sway_freq_hz=self._rng.uniform(0.8, 1.5),
                sway_amp_px=self._rng.uniform(14.0, 26.0),
            )
        )

    def _next_drop_kind(self) -> str:
        # Temporary balance mode: all supply drops are health drops.
        return "health"

    def update(self, *, mission: object, helicopter: object, dt: float, ground_y: float) -> None:
        if dt <= 0.0:
            return

        self.spawn_timer_s -= dt
        if self.spawn_timer_s <= 0.0 and len([d for d in self.drops if d.alive]) < max(1, int(self.max_alive)):
            self._spawn_drop(helicopter=helicopter, world_width=float(getattr(mission, "world_width", 1280.0)))
            self.spawn_timer_s = self._next_spawn_interval()
        elif self.spawn_timer_s <= 0.0:
            self.spawn_timer_s = 1.5

        heli_pos = getattr(helicopter, "pos")
        collect_r2 = float(self.collect_radius_px) * float(self.collect_radius_px)
        for d in self.drops:
            if not d.alive:
                continue

            d.age_s += dt
            if not d.landed:
                sway_vx = math.sin((d.age_s * math.tau * d.sway_freq_hz) + d.sway_phase) * d.sway_amp_px
                d.vel.x = sway_vx
                d.vel.y += self.gravity * dt

                d.pos.x += d.vel.x * dt
                d.pos.y += d.vel.y * dt

                d.pos.x = clamp(d.pos.x, 20.0, max(20.0, float(getattr(mission, "world_width", 1280.0)) - 20.0))

            dx = d.pos.x - float(heli_pos.x)
            dy = d.pos.y - float(heli_pos.y)
            if dx * dx + dy * dy <= collect_r2:
                self._grant_drop_reward(mission=mission, helicopter=helicopter, kind=d.kind)
                d.alive = False
                continue

            if not d.landed and d.pos.y >= ground_y - 4.0:
                d.landed = True
                d.landed_age_s = 0.0
                d.pos.y = ground_y - 4.0
                d.vel = Vec2(0.0, 0.0)
                continue

            if d.landed:
                d.landed_age_s += dt
                if d.landed_age_s >= max(0.0, float(self.ground_lifetime_s)):
                    d.alive = False

        self.drops = [d for d in self.drops if d.alive]

    def _grant_drop_reward(self, *, mission: object, helicopter: object, kind: str) -> None:
        if kind == "health":
            current_damage = float(getattr(helicopter, "damage", 0.0))
            restore = max(0.0, float(self.health_restore_amount))
            setattr(helicopter, "damage", max(0.0, current_damage - restore))
            return
        if kind == "bombs":
            current = int(getattr(mission, "munitions_bombs", 0))
            setattr(mission, "munitions_bombs", current + 4)
            return
        current = int(getattr(mission, "munitions_bullets", 0))
        setattr(mission, "munitions_bullets", current + 45)


def can_fire_player_weapon(mission: object, *, facing_name: str) -> bool:
    if facing_name == "FORWARD":
        return int(getattr(mission, "munitions_bombs", 0)) > 0
    return int(getattr(mission, "munitions_bullets", 0)) > 0


def consume_player_weapon(mission: object, *, facing_name: str) -> bool:
    if facing_name == "FORWARD":
        bombs = int(getattr(mission, "munitions_bombs", 0))
        if bombs <= 0:
            return False
        setattr(mission, "munitions_bombs", bombs - 1)
        return True
    bullets = int(getattr(mission, "munitions_bullets", 0))
    if bullets <= 0:
        return False
    setattr(mission, "munitions_bullets", bullets - 1)
    return True
