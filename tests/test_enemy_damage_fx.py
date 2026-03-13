from __future__ import annotations

import unittest

from src.choplifter.entities import Enemy
from src.choplifter.fx.enemy_damage_fx import EnemyDamageFxSystem
from src.choplifter.game_types import EnemyKind
from src.choplifter.math2d import Vec2


class EnemyDamageFxTests(unittest.TestCase):
    def test_tank_below_half_health_emits_smoke(self) -> None:
        fx = EnemyDamageFxSystem(seed=1)
        enemy = Enemy(
            kind=EnemyKind.TANK,
            pos=Vec2(200.0, 292.0),
            vel=Vec2(0.0, 0.0),
            health=54.0,
            max_health=110.0,
        )

        fx.update(0.25, enemies=[enemy], tank_health=110.0)

        self.assertTrue(any(getattr(p, "kind", "") == "smoke" for p in fx.particles))

    def test_tank_above_half_health_emits_no_smoke(self) -> None:
        fx = EnemyDamageFxSystem(seed=1)
        enemy = Enemy(
            kind=EnemyKind.TANK,
            pos=Vec2(200.0, 292.0),
            vel=Vec2(0.0, 0.0),
            health=56.0,
            max_health=110.0,
        )

        fx.update(0.25, enemies=[enemy], tank_health=110.0)

        self.assertEqual(len(fx.particles), 0)