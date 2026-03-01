from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WindowSettings:
    width: int = 1280
    height: int = 720
    title: str = "Choplifter Returns - Middleast Rescue"
    vsync: bool = True


@dataclass(frozen=True)
class FixedTickSettings:
    hz: int = 60

    @property
    def dt(self) -> float:
        return 1.0 / float(self.hz)


@dataclass(frozen=True)
class PhysicsSettings:
    gravity: float = 18.0
    engine_power: float = 22.0
    friction: float = 0.985
    max_speed_x: float = 35.0
    max_speed_y: float = 35.0

    max_tilt_deg: float = 35.0
    tilt_rate_deg_per_s: float = 160.0
    tilt_return_rate_deg_per_s: float = 90.0

    safe_landing_vy: float = 1.5


@dataclass(frozen=True)
class HelicopterSettings:
    capacity: int = 16
    ground_y: float = 620.0
    rotor_clearance: float = 18.0


@dataclass(frozen=True)
class DebugSettings:
    show_overlay: bool = True
