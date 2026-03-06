"""
entities.py

Contains dataclasses for all mission entities: Hostage, Compound, Projectile, Enemy, BaseZone, MissionStats.
"""
from dataclasses import dataclass, field
import math
from .math2d import Vec2
from .game_types import EnemyKind, HostageState, ProjectileKind

@dataclass
class Hostage:
    state: HostageState
    pos: Vec2
    health: float = 100.0
    saved_slot: int = -1
    move_speed: float = 0.0
    vel: Vec2 = field(default_factory=lambda: Vec2(0.0, 0.0))
    fall_angle: float = 0.0  # For tumbling animation when falling
    is_vip: bool = False  # True if this hostage is the VIP (HVT)

@dataclass
class Compound:
    pos: Vec2
    width: float
    height: float
    health: float
    is_open: bool
    hostage_start: int
    hostage_count: int
    log_bucket: int = -1

    def contains_point(self, p: Vec2) -> bool:
        return (
            self.pos.x <= p.x <= self.pos.x + self.width
            and self.pos.y <= p.y <= self.pos.y + self.height
        )

@dataclass
class Projectile:
    kind: ProjectileKind
    pos: Vec2
    vel: Vec2
    ttl: float
    source: "EnemyKind | None" = None
    alive: bool = True
    is_barak_missile: bool = False  # True if this is a Barak MRAD missile
    missile_state: str = "liftoff"  # "liftoff", "rotating", "homing"
    launch_pos: Vec2 = None
    rotation_progress: float = 0.0  # 0.0 to 1.0 for rotation animation
    rotate_dir: int = 0  # +1 for CW, -1 for CCW
    target_angle: float = 0.0  # angle to rotate to (radians)
    current_angle: float = math.pi/2  # vertical up

@dataclass
class Enemy:
    kind: EnemyKind
    pos: Vec2
    vel: Vec2
    health: float
    cooldown: float = 0.0
    ttl: float = 999.0
    alive: bool = True
    entered_screen: bool = False
    trail_enabled: bool = False
    trail_spawn_accum: float = 0.0
    turret_angle: float = 0.0  # Radians, only used for turrets
    # Barak MRAD-specific state
    mrad_state: str = "moving"  # moving, deploying, aiming, launching, done
    launcher_angle: float = 0.0  # Radians, for launcher deployment/aim
    missile_fired: bool = False
    launcher_ext_progress: float = 0.0  # 0.0 (retracted) to 1.0 (fully extended)

@dataclass(frozen=True)
class BaseZone:
    pos: Vec2
    width: float
    height: float

    def contains_point(self, p: Vec2) -> bool:
        return (
            self.pos.x <= p.x <= self.pos.x + self.width
            and self.pos.y <= p.y <= self.pos.y + self.height
        )

@dataclass
class MissionStats:
    saved: int = 0
    kia_by_player: int = 0
    kia_by_enemy: int = 0
    lost_in_transit: int = 0
    enemies_destroyed: int = 0
    tanks_destroyed: int = 0
    artillery_fired: int = 0
    artillery_hits: int = 0
    jets_entered: int = 0
    mines_detonated: int = 0
