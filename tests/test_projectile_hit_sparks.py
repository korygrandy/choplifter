from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from src.choplifter.entities import Enemy, Projectile
from src.choplifter.game_types import EnemyKind, ProjectileKind
from src.choplifter.math2d import Vec2
from src.choplifter.mission_configs import MissionTuning
from src.choplifter.mission_projectiles import _update_projectiles


class _DummySparks:
    def __init__(self) -> None:
        self.calls = 0

    def emit_hit(self, *_args, **_kwargs) -> None:
        self.calls += 1


class ProjectileHitSparkTests(unittest.TestCase):
    def _base_mission(self, *, projectile: Projectile, enemy: Enemy, sparks: _DummySparks) -> SimpleNamespace:
        return SimpleNamespace(
            projectiles=[projectile],
            enemies=[enemy],
            tuning=MissionTuning(),
            stats=SimpleNamespace(enemies_destroyed=0, tanks_destroyed=0),
            impact_sparks=sparks,
            burning=SimpleNamespace(add_site=lambda *_a, **_k: None),
            hostages=[],
            compounds=[],
            base=SimpleNamespace(contains_point=lambda _p: False),
            mission_id="city",
            flare_invuln_seconds=0.0,
            explosions=SimpleNamespace(
                emit_fire_plume=lambda *_a, **_k: None,
                emit_explosion=lambda *_a, **_k: None,
            ),
            barak_suppressed=False,
            elapsed_seconds=0.0,
        )

    def test_bullet_hit_on_tank_emits_sparks(self) -> None:
        p = Projectile(kind=ProjectileKind.BULLET, pos=Vec2(100.0, 100.0), vel=Vec2(220.0, 0.0), ttl=1.0)
        e = Enemy(kind=EnemyKind.TANK, pos=Vec2(100.0, 100.0), vel=Vec2(0.0, 0.0), health=100.0)
        sparks = _DummySparks()
        mission = self._base_mission(projectile=p, enemy=e, sparks=sparks)

        heli = SimpleNamespace(ground_y=300.0)
        helicopter = SimpleNamespace(pos=Vec2(0.0, 0.0), vel=Vec2(0.0, 0.0), facing=None, grounded=False)

        with patch("src.choplifter.mission_projectiles._projectile_hits_enemy", return_value=True):
            _update_projectiles(
                mission,
                0.0,
                heli,
                logger=None,
                helicopter=helicopter,
                damage_helicopter=lambda *_a, **_k: None,
            )

        self.assertEqual(sparks.calls, 1)

    def test_bullet_hit_on_barak_emits_sparks(self) -> None:
        p = Projectile(kind=ProjectileKind.BULLET, pos=Vec2(140.0, 100.0), vel=Vec2(220.0, 0.0), ttl=1.0)
        e = Enemy(kind=EnemyKind.BARAK_MRAD, pos=Vec2(140.0, 100.0), vel=Vec2(0.0, 0.0), health=100.0)
        sparks = _DummySparks()
        mission = self._base_mission(projectile=p, enemy=e, sparks=sparks)

        heli = SimpleNamespace(ground_y=300.0)
        helicopter = SimpleNamespace(pos=Vec2(0.0, 0.0), vel=Vec2(0.0, 0.0), facing=None, grounded=False)

        with patch("src.choplifter.mission_projectiles._projectile_hits_enemy", return_value=True):
            _update_projectiles(
                mission,
                0.0,
                heli,
                logger=None,
                helicopter=helicopter,
                damage_helicopter=lambda *_a, **_k: None,
            )

        self.assertEqual(sparks.calls, 1)

    def test_bomb_hit_does_not_emit_bullet_sparks(self) -> None:
        p = Projectile(kind=ProjectileKind.BOMB, pos=Vec2(180.0, 100.0), vel=Vec2(0.0, 0.0), ttl=1.0)
        e = Enemy(kind=EnemyKind.TANK, pos=Vec2(180.0, 100.0), vel=Vec2(0.0, 0.0), health=100.0)
        sparks = _DummySparks()
        mission = self._base_mission(projectile=p, enemy=e, sparks=sparks)

        heli = SimpleNamespace(ground_y=300.0)
        helicopter = SimpleNamespace(pos=Vec2(0.0, 0.0), vel=Vec2(0.0, 0.0), facing=None, grounded=False)

        with patch("src.choplifter.mission_projectiles._projectile_hits_enemy", return_value=True):
            _update_projectiles(
                mission,
                0.0,
                heli,
                logger=None,
                helicopter=helicopter,
                damage_helicopter=lambda *_a, **_k: None,
            )

        self.assertEqual(sparks.calls, 0)


if __name__ == "__main__":
    unittest.main()
