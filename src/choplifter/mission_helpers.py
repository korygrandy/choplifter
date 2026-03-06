from .math2d import Vec2
from .entities import Projectile, Enemy, Compound
from .settings import HelicopterSettings
from .mission_configs import MissionTuning
from .game_types import EnemyKind
import logging
def _hits_circle(a: Vec2, b: Vec2, radius: float) -> bool:
    dx = a.x - b.x
    dy = a.y - b.y
    return dx * dx + dy * dy <= radius * radius

def _projectile_hits_enemy(p: Projectile, e: Enemy, heli: HelicopterSettings, tuning: MissionTuning) -> bool:
    if e.kind is EnemyKind.TANK:
        w, h = 44.0, 18.0
        left = e.pos.x - w * 0.5
        top = heli.ground_y - h
        return left <= p.pos.x <= left + w and top <= p.pos.y <= top + h

    if e.kind is EnemyKind.JET:
        return _hits_circle(p.pos, e.pos, radius=20.0)

    if e.kind is EnemyKind.AIR_MINE:
        return _hits_circle(p.pos, e.pos, radius=tuning.mine_projectile_radius)

    return False

def _log_compound_health_if_needed(c: Compound, logger: logging.Logger | None, reason: str) -> None:
    if logger is None:
        return

    health = max(0.0, c.health)

    # Log only when health crosses buckets of 20 (avoids log spam).
    bucket = int(health // 20.0)
    if bucket == c.log_bucket:
        return

    c.log_bucket = bucket
    logger.info("Compound %s: x=%.0f health=%.0f", reason, c.pos.x, health)
"""
mission_helpers.py

Contains clear-cut mission helper functions extracted from mission.py.
"""
from .game_types import HostageState
from .entities import Hostage
from .mission_state import MissionState

def boarded_count(mission: MissionState) -> int:
    return sum(1 for h in mission.hostages if h.state is HostageState.BOARDED)

def on_foot(hostage: Hostage) -> bool:
    return hostage.state in (HostageState.PANIC, HostageState.MOVING_TO_LZ, HostageState.WAITING, HostageState.EXITING)
