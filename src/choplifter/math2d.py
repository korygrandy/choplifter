from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass
class Vec2:
    x: float = 0.0
    y: float = 0.0

    def __add__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> "Vec2":
        return Vec2(self.x * scalar, self.y * scalar)

    def copy(self) -> "Vec2":
        return Vec2(self.x, self.y)


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def deg_to_rad(deg: float) -> float:
    return deg * math.pi / 180.0
