from __future__ import annotations

from types import SimpleNamespace
import unittest
import pytest

from src.choplifter.helicopter import Facing
from src.choplifter.entities import Projectile
from src.choplifter.game_types import EnemyKind, ProjectileKind
from src.choplifter.mission_configs import MissionTuning
from src.choplifter.mission_projectiles import (
    _barak_collision_prefers_bus,
    _barak_ground_impact_can_damage,
    _barak_is_in_lz_zone,
    _hits_circle_or_swept,
    _update_projectiles,
    _barak_should_apply_damage,
    _barak_target_point,
)
from src.choplifter.math2d import Vec2


pytestmark = pytest.mark.airport_smoke


class BarakGroundedCollisionTests(unittest.TestCase):
    def test_barak_target_point_tracks_nose_by_facing(self) -> None:
        heli_r = SimpleNamespace(pos=SimpleNamespace(x=100.0, y=200.0), facing=Facing.RIGHT)
        heli_l = SimpleNamespace(pos=SimpleNamespace(x=100.0, y=200.0), facing=Facing.LEFT)
        heli_f = SimpleNamespace(pos=SimpleNamespace(x=100.0, y=200.0), facing=Facing.FORWARD)

        t_r = _barak_target_point(heli_r)
        t_l = _barak_target_point(heli_l)
        t_f = _barak_target_point(heli_f)

        self.assertEqual((t_r.x, t_r.y), (132.0, 202.0))
        self.assertEqual((t_l.x, t_l.y), (68.0, 202.0))
        self.assertEqual((t_f.x, t_f.y), (110.0, 202.0))

    def test_airborne_barak_hit_applies_damage(self) -> None:
        self.assertTrue(_barak_should_apply_damage(grounded=False, in_lz=False))
        self.assertTrue(_barak_should_apply_damage(grounded=False, in_lz=True))

    def test_grounded_in_lz_barak_hit_is_suppressed(self) -> None:
        self.assertFalse(_barak_should_apply_damage(grounded=True, in_lz=True))

    def test_grounded_outside_lz_barak_hit_applies_damage(self) -> None:
        self.assertTrue(_barak_should_apply_damage(grounded=True, in_lz=False))

    def test_ground_impact_fallback_only_for_grounded_outside_lz_near_heli(self) -> None:
        self.assertTrue(
            _barak_ground_impact_can_damage(
                grounded=True,
                in_lz=False,
                impact_hits_helicopter=True,
            )
        )

    def test_collision_prefers_bus_only_when_player_driving_vehicle(self) -> None:
        mission = SimpleNamespace(
            player_driving_vehicle=False,
            mission_id="airport",
            airport_bus_state=SimpleNamespace(x=300.0, y=220.0, health=100.0),
            airport_hostage_state=SimpleNamespace(state="boarded"),
        )
        self.assertFalse(_barak_collision_prefers_bus(mission=mission, diverted_collision=False))

        mission.player_driving_vehicle = True
        self.assertTrue(_barak_collision_prefers_bus(mission=mission, diverted_collision=False))
        self.assertFalse(_barak_collision_prefers_bus(mission=mission, diverted_collision=True))

        mission.airport_hostage_state.state = "waiting"
        self.assertFalse(_barak_collision_prefers_bus(mission=mission, diverted_collision=False))

    def test_swept_collision_detects_high_speed_crossing(self) -> None:
        previous = Vec2(0.0, 0.0)
        current = Vec2(100.0, 0.0)
        center = Vec2(50.0, 0.0)
        self.assertTrue(_hits_circle_or_swept(previous=previous, current=current, center=center, radius=8.0))

    def test_swept_collision_ignores_non_intersecting_path(self) -> None:
        previous = Vec2(0.0, 0.0)
        current = Vec2(100.0, 0.0)
        center = Vec2(50.0, 30.0)
        self.assertFalse(_hits_circle_or_swept(previous=previous, current=current, center=center, radius=8.0))

    def test_lz_zone_includes_airport_tower_lz_band(self) -> None:
        mission = SimpleNamespace(
            mission_id="airport",
            base=SimpleNamespace(contains_point=lambda _p: False),
            airport_bus_state=None,
        )
        helicopter = SimpleNamespace(pos=SimpleNamespace(x=620.0, y=390.0))
        self.assertTrue(_barak_is_in_lz_zone(mission=mission, helicopter=helicopter))

    def test_lz_zone_tower_band_not_used_for_non_airport(self) -> None:
        mission = SimpleNamespace(
            mission_id="city",
            base=SimpleNamespace(contains_point=lambda _p: False),
            airport_bus_state=None,
        )
        helicopter = SimpleNamespace(pos=SimpleNamespace(x=620.0, y=390.0))
        self.assertFalse(_barak_is_in_lz_zone(mission=mission, helicopter=helicopter))
        self.assertFalse(
            _barak_ground_impact_can_damage(
                grounded=True,
                in_lz=True,
                impact_hits_helicopter=True,
            )
        )
        self.assertFalse(
            _barak_ground_impact_can_damage(
                grounded=False,
                in_lz=False,
                impact_hits_helicopter=True,
            )
        )
        self.assertFalse(
            _barak_ground_impact_can_damage(
                grounded=True,
                in_lz=False,
                impact_hits_helicopter=False,
            )
        )

    def test_grounded_safe_barak_nose_contact_still_explodes_and_retires_missile(self) -> None:
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

        mission = SimpleNamespace(
            projectiles=[
                Projectile(
                    kind=ProjectileKind.ENEMY_ARTILLERY,
                    pos=Vec2(129.0, 292.0),
                    vel=Vec2(110.0, 0.0),
                    ttl=1.0,
                    source=EnemyKind.BARAK_MRAD,
                    is_barak_missile=True,
                    missile_state="terminal",
                )
            ],
            enemies=[],
            tuning=MissionTuning(),
            flare_invuln_seconds=0.0,
            barak_suppressed=False,
            player_driving_vehicle=False,
            airport_bus_state=None,
            mission_id="airport",
            base=SimpleNamespace(contains_point=lambda _p: True),
            impact_sparks=_DummySparks(),
            burning=SimpleNamespace(add_site=lambda *_a, **_k: None),
            explosions=_DummyExplosions(),
            hostages=[],
            compounds=[],
            elapsed_seconds=0.0,
        )
        helicopter = SimpleNamespace(pos=Vec2(100.0, 290.0), vel=Vec2(0.0, 0.0), facing=Facing.RIGHT, grounded=True)
        heli = SimpleNamespace(ground_y=300.0)
        damage_calls: list[float] = []

        _update_projectiles(
            mission,
            0.1,
            heli,
            logger=None,
            helicopter=helicopter,
            damage_helicopter=lambda *_a, **_k: damage_calls.append(18.0),
        )

        self.assertEqual(len(mission.projectiles), 0)
        self.assertEqual(mission.explosions.explosion_calls, 1)
        self.assertEqual(mission.explosions.plume_calls, 1)
        self.assertEqual(len(damage_calls), 0)


if __name__ == "__main__":
    unittest.main()
