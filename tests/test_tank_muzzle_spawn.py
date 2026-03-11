from __future__ import annotations

import math
from types import SimpleNamespace
import unittest

from src.choplifter.entities import Enemy
from src.choplifter.enemy_update import _tank_turret_muzzle_pos
from src.choplifter.game_types import EnemyKind
from src.choplifter.math2d import Vec2


class TankMuzzleSpawnTests(unittest.TestCase):
    def test_airport_tank_uses_long_barrel_tip(self) -> None:
        mission = SimpleNamespace(mission_id="airport")
        enemy = Enemy(
            kind=EnemyKind.TANK,
            pos=Vec2(200.0, 292.0),
            vel=Vec2(0.0, 0.0),
            health=100.0,
            turret_angle=0.0,
        )

        muzzle = _tank_turret_muzzle_pos(mission, enemy)

        self.assertAlmostEqual(muzzle.x, 248.0)
        self.assertAlmostEqual(muzzle.y, 274.0)

    def test_standard_tank_keeps_short_barrel_tip(self) -> None:
        mission = SimpleNamespace(mission_id="city")
        enemy = Enemy(
            kind=EnemyKind.TANK,
            pos=Vec2(200.0, 292.0),
            vel=Vec2(0.0, 0.0),
            health=100.0,
            turret_angle=math.pi,
        )

        muzzle = _tank_turret_muzzle_pos(mission, enemy)

        self.assertAlmostEqual(muzzle.x, 176.0)
        self.assertAlmostEqual(muzzle.y, 274.0)


if __name__ == "__main__":
    unittest.main()