from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch
import unittest

from src.choplifter.entities import Enemy, Projectile
from src.choplifter.game_types import EnemyKind, ProjectileKind
from src.choplifter.math2d import Vec2
from src.choplifter.mission_configs import MissionTuning
from src.choplifter.mission_projectiles import _update_projectiles


class _DummyExplosions:
    def __init__(self) -> None:
        self.explosion_calls = 0
        self.plume_calls = 0

    def emit_explosion(self, *_args, **_kwargs) -> None:
        self.explosion_calls += 1

    def emit_fire_plume(self, *_args, **_kwargs) -> None:
        self.plume_calls += 1


class _DummySparks:
    def __init__(self) -> None:
        self.calls = 0

    def emit_hit(self, *_args, **_kwargs) -> None:
        self.calls += 1


class _DummyAudio:
    def __init__(self) -> None:
        self.barak_explosion_calls = 0

    def play_barak_explosion(self) -> None:
        self.barak_explosion_calls += 1


class GroundCannonDualBurstExplosionTests(unittest.TestCase):
    def _base_mission(self, *, projectile: Projectile, enemy: Enemy) -> SimpleNamespace:
        return SimpleNamespace(
            projectiles=[projectile],
            enemies=[enemy],
            tuning=MissionTuning(),
            stats=SimpleNamespace(enemies_destroyed=0, tanks_destroyed=0),
            impact_sparks=_DummySparks(),
            burning=SimpleNamespace(add_site=lambda *_a, **_k: None),
            hostages=[],
            compounds=[],
            base=SimpleNamespace(contains_point=lambda _p: False),
            mission_id="city",
            flare_invuln_seconds=0.0,
            explosions=_DummyExplosions(),
            audio=_DummyAudio(),
            barak_suppressed=False,
            elapsed_seconds=0.0,
        )

    def test_barak_death_triggers_immediate_and_delayed_second_burst(self) -> None:
        p = Projectile(kind=ProjectileKind.BULLET, pos=Vec2(100.0, 100.0), vel=Vec2(220.0, 0.0), ttl=1.0)
        e = Enemy(kind=EnemyKind.BARAK_MRAD, pos=Vec2(100.0, 100.0), vel=Vec2(0.0, 0.0), health=10.0)
        mission = self._base_mission(projectile=p, enemy=e)

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

        self.assertEqual(mission.explosions.explosion_calls, 1)
        self.assertEqual(mission.explosions.plume_calls, 1)
        self.assertEqual(mission.audio.barak_explosion_calls, 1)
        self.assertFalse(e.alive)

        # Advance past cook-off delay: missile should launch but not detonate yet.
        _update_projectiles(
            mission,
            0.3,
            heli,
            logger=None,
            helicopter=helicopter,
            damage_helicopter=lambda *_a, **_k: None,
        )
        self.assertEqual(mission.explosions.explosion_calls, 1)
        self.assertTrue(any(bool(getattr(px, "barak_cookoff_missile", False)) for px in mission.projectiles if px.alive))

        # Advance enough time for the spiral missile to detonate mid-air.
        _update_projectiles(
            mission,
            0.7,
            heli,
            logger=None,
            helicopter=helicopter,
            damage_helicopter=lambda *_a, **_k: None,
        )

        self.assertEqual(mission.explosions.explosion_calls, 2)
        self.assertEqual(mission.explosions.plume_calls, 2)

    def test_barak_second_burst_delay_follows_tuning(self) -> None:
        p = Projectile(kind=ProjectileKind.BULLET, pos=Vec2(140.0, 100.0), vel=Vec2(220.0, 0.0), ttl=1.0)
        e = Enemy(kind=EnemyKind.BARAK_MRAD, pos=Vec2(140.0, 100.0), vel=Vec2(0.0, 0.0), health=10.0)
        mission = self._base_mission(projectile=p, enemy=e)
        mission.tuning = MissionTuning(barak_destroy_second_burst_delay_s=0.45)

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

        # Before tuned delay expires: second burst should not have fired yet.
        _update_projectiles(
            mission,
            0.30,
            heli,
            logger=None,
            helicopter=helicopter,
            damage_helicopter=lambda *_a, **_k: None,
        )
        self.assertEqual(mission.explosions.explosion_calls, 1)

        # Delay crossed: cook-off missile launches, but airburst has not triggered yet.
        _update_projectiles(
            mission,
            0.20,
            heli,
            logger=None,
            helicopter=helicopter,
            damage_helicopter=lambda *_a, **_k: None,
        )
        self.assertEqual(mission.explosions.explosion_calls, 1)

        # After additional time, the spiral missile detonates as the second burst.
        _update_projectiles(
            mission,
            0.7,
            heli,
            logger=None,
            helicopter=helicopter,
            damage_helicopter=lambda *_a, **_k: None,
        )
        self.assertEqual(mission.explosions.explosion_calls, 2)

    def test_tank_death_does_not_trigger_delayed_second_burst(self) -> None:
        p = Projectile(kind=ProjectileKind.BULLET, pos=Vec2(120.0, 100.0), vel=Vec2(220.0, 0.0), ttl=1.0)
        e = Enemy(kind=EnemyKind.TANK, pos=Vec2(120.0, 100.0), vel=Vec2(0.0, 0.0), health=10.0)
        mission = self._base_mission(projectile=p, enemy=e)

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

        # Tank keeps standard destruction path (no queued delayed cook-off burst).
        self.assertEqual(mission.explosions.explosion_calls, 0)
        self.assertEqual(mission.explosions.plume_calls, 0)
        self.assertFalse(e.alive)

        _update_projectiles(
            mission,
            0.3,
            heli,
            logger=None,
            helicopter=helicopter,
            damage_helicopter=lambda *_a, **_k: None,
        )

        self.assertEqual(mission.explosions.explosion_calls, 0)
        self.assertEqual(mission.explosions.plume_calls, 0)


if __name__ == "__main__":
    unittest.main()
