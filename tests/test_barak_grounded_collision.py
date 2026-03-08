from __future__ import annotations

from types import SimpleNamespace
import unittest

from src.choplifter.helicopter import Facing
from src.choplifter.mission_projectiles import (
    _barak_ground_impact_can_damage,
    _barak_should_apply_damage,
    _barak_target_point,
)


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
