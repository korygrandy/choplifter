from __future__ import annotations

from dataclasses import dataclass

from ..math2d import Vec2


@dataclass
class FxParticle:
    pos: Vec2
    vel: Vec2
    age: float
    ttl: float
    radius: float
    kind: str  # "ember" | "smoke"
