from __future__ import annotations

import math
import unittest

from src.choplifter.barak_mrad import BARAK_STATE_DEPLOY, BARAK_STATE_MOVE
from src.choplifter.entities import Enemy, Projectile
from src.choplifter.game_types import EnemyKind, ProjectileKind
from src.choplifter.math2d import Vec2
from src.choplifter.mission_configs import MissionTuning
from src.choplifter.mission_helpers import _projectile_hits_enemy
from src.choplifter.settings import HelicopterSettings


class BarakHoverDamageTests(unittest.TestCase):
    def test_hover_bullet_can_hit_deployed_barak_launcher(self) -> None:
        heli = HelicopterSettings(ground_y=300.0)
        tuning = MissionTuning()
        enemy = Enemy(
            kind=EnemyKind.BARAK_MRAD,
            pos=Vec2(180.0, 288.0),
            vel=Vec2(0.0, 0.0),
            health=100.0,
            mrad_state=BARAK_STATE_DEPLOY,
            launcher_angle=math.pi / 2,
            launcher_ext_progress=1.0,
        )
        projectile = Projectile(
            kind=ProjectileKind.BULLET,
            pos=Vec2(140.0, 238.0),
            vel=Vec2(95.0, 0.0),
            ttl=1.0,
        )

        self.assertTrue(_projectile_hits_enemy(projectile, enemy, heli, tuning))

    def test_same_high_shot_does_not_hit_tank_body(self) -> None:
        heli = HelicopterSettings(ground_y=300.0)
        tuning = MissionTuning()
        enemy = Enemy(
            kind=EnemyKind.TANK,
            pos=Vec2(180.0, 288.0),
            vel=Vec2(0.0, 0.0),
            health=100.0,
        )
        projectile = Projectile(
            kind=ProjectileKind.BULLET,
            pos=Vec2(140.0, 238.0),
            vel=Vec2(95.0, 0.0),
            ttl=1.0,
        )

        self.assertFalse(_projectile_hits_enemy(projectile, enemy, heli, tuning))

    def test_hover_bullet_swept_path_hits_launcher_even_if_endpoint_passes_beyond_it(self) -> None:
        heli = HelicopterSettings(ground_y=300.0)
        tuning = MissionTuning()
        enemy = Enemy(
            kind=EnemyKind.BARAK_MRAD,
            pos=Vec2(180.0, 288.0),
            vel=Vec2(0.0, 0.0),
            health=100.0,
            mrad_state=BARAK_STATE_DEPLOY,
            launcher_angle=math.pi / 2,
            launcher_ext_progress=1.0,
        )
        projectile = Projectile(
            kind=ProjectileKind.BULLET,
            pos=Vec2(140.0, 220.0),
            vel=Vec2(95.0, 0.0),
            ttl=1.0,
        )
        previous_pos = Vec2(140.0, 220.0)
        projectile.pos = Vec2(140.0 + 95.0, 220.0)

        self.assertTrue(_projectile_hits_enemy(projectile, enemy, heli, tuning, previous_pos=previous_pos))

    def test_hover_bullet_can_hit_moving_barak_vehicle_body(self) -> None:
        heli = HelicopterSettings(ground_y=300.0)
        tuning = MissionTuning()
        enemy = Enemy(
            kind=EnemyKind.BARAK_MRAD,
            pos=Vec2(180.0, 288.0),
            vel=Vec2(0.0, 0.0),
            health=100.0,
            mrad_state=BARAK_STATE_MOVE,
            launcher_angle=0.0,
            launcher_ext_progress=0.0,
        )
        projectile = Projectile(
            kind=ProjectileKind.BULLET,
            pos=Vec2(168.0, 274.0),
            vel=Vec2(95.0, 0.0),
            ttl=1.0,
        )

        self.assertTrue(_projectile_hits_enemy(projectile, enemy, heli, tuning))


if __name__ == "__main__":
    unittest.main()