from __future__ import annotations

from types import SimpleNamespace
import unittest

from src.choplifter.helicopter import Facing
from src.choplifter.mission_projectiles import (
    _barak_collision_prefers_bus,
    _barak_ground_impact_can_damage,
    _barak_is_in_lz_zone,
    _hits_circle_or_swept,
    _barak_should_apply_damage,
    _barak_target_point,
)
from src.choplifter.math2d import Vec2


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
            airport_bus_state=SimpleNamespace(x=300.0, y=220.0, health=100.0),
        )
        self.assertFalse(_barak_collision_prefers_bus(mission=mission, diverted_collision=False))

        mission.player_driving_vehicle = True
        self.assertTrue(_barak_collision_prefers_bus(mission=mission, diverted_collision=False))
        self.assertFalse(_barak_collision_prefers_bus(mission=mission, diverted_collision=True))

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


if __name__ == "__main__":
    unittest.main()
