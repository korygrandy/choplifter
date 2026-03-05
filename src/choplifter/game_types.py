from __future__ import annotations

from enum import Enum


class HostageState(Enum):
    IDLE = 0
    PANIC = 1
    MOVING_TO_LZ = 2
    WAITING = 3
    BOARDED = 4
    EXITING = 5
    SAVED = 6
    KIA = 7
    FALLING = 8


class ProjectileKind(Enum):
    BULLET = 1
    BOMB = 2
    ENEMY_BULLET = 3
    ENEMY_ARTILLERY = 4


class EnemyKind(Enum):
    TANK = 1
    JET = 2
    AIR_MINE = 3
