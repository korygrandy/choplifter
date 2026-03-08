from __future__ import annotations

from types import SimpleNamespace
import unittest

from src.choplifter.helicopter import Facing
from src.choplifter.math2d import Vec2
from src.choplifter.mission_projectiles import (
    _barak_find_flare_decoy,
    _barak_homing_target,
    _barak_roll_diversion,
    _turn_toward_angle,
)


class BarakFlareDiversionTests(unittest.TestCase):
    def test_find_flare_decoy_prefers_nearest_active_particle(self) -> None:
        mission = SimpleNamespace(
            flares=SimpleNamespace(
                particles=[
                    SimpleNamespace(pos=Vec2(400.0, 240.0), age=0.4, ttl=1.4),
                    SimpleNamespace(pos=Vec2(230.0, 175.0), age=0.2, ttl=1.1),
                    SimpleNamespace(pos=Vec2(900.0, 100.0), age=0.1, ttl=1.0),
                ]
            )
        )
        decoy = _barak_find_flare_decoy(
            mission=mission,
            missile_pos=Vec2(200.0, 180.0),
            radius=300.0,
            max_flare_age_s=1.65,
        )
        self.assertIsNotNone(decoy)
        self.assertEqual((decoy.x, decoy.y), (230.0, 175.0))

    def test_find_flare_decoy_ignores_old_or_out_of_range_particles(self) -> None:
        mission = SimpleNamespace(
            flares=SimpleNamespace(
                particles=[
                    SimpleNamespace(pos=Vec2(230.0, 175.0), age=3.2, ttl=3.5),
                    SimpleNamespace(pos=Vec2(1200.0, 175.0), age=0.2, ttl=1.0),
                ]
            )
        )
        decoy = _barak_find_flare_decoy(
            mission=mission,
            missile_pos=Vec2(200.0, 180.0),
            radius=280.0,
            max_flare_age_s=1.0,
        )
        self.assertIsNone(decoy)

    def test_roll_diversion_obeys_chance_bounds_and_threshold(self) -> None:
        self.assertFalse(_barak_roll_diversion(chance=0.0, random_value=0.0))
        self.assertTrue(_barak_roll_diversion(chance=1.0, random_value=1.0))
        self.assertTrue(_barak_roll_diversion(chance=0.6, random_value=0.59))
        self.assertFalse(_barak_roll_diversion(chance=0.6, random_value=0.61))

    def test_homing_target_diverts_to_upward_decoy_when_allowed(self) -> None:
        mission = SimpleNamespace(
            tuning=SimpleNamespace(
                barak_flare_diversion_radius=320.0,
                barak_flare_diversion_max_flare_age_s=1.8,
                barak_flare_diversion_chance=1.0,
            ),
            flares=SimpleNamespace(
                particles=[SimpleNamespace(pos=Vec2(520.0, 160.0), age=0.2, ttl=1.1)]
            ),
        )
        missile = SimpleNamespace(
            pos=Vec2(500.0, 220.0),
            flare_diversion_resolved=False,
            flare_diversion_allowed=False,
            flare_seen_post_liftoff=True,
        )
        helicopter = SimpleNamespace(pos=Vec2(740.0, 240.0), facing=Facing.RIGHT)

        target, diverted = _barak_homing_target(mission=mission, missile=missile, helicopter=helicopter)
        self.assertTrue(diverted)
        self.assertTrue(missile.flare_diversion_resolved)
        self.assertTrue(missile.flare_diversion_allowed)
        self.assertLess(target.y, missile.pos.y)

    def test_homing_target_falls_back_to_heli_when_roll_fails(self) -> None:
        mission = SimpleNamespace(
            tuning=SimpleNamespace(
                barak_flare_diversion_radius=320.0,
                barak_flare_diversion_max_flare_age_s=1.8,
                barak_flare_diversion_chance=0.0,
            ),
            flares=SimpleNamespace(
                particles=[SimpleNamespace(pos=Vec2(520.0, 160.0), age=0.2, ttl=1.1)]
            ),
        )
        missile = SimpleNamespace(
            pos=Vec2(500.0, 220.0),
            flare_diversion_resolved=False,
            flare_diversion_allowed=False,
            flare_seen_post_liftoff=True,
        )
        helicopter = SimpleNamespace(pos=Vec2(740.0, 240.0), facing=Facing.RIGHT)

        target, diverted = _barak_homing_target(mission=mission, missile=missile, helicopter=helicopter)
        self.assertFalse(diverted)
        self.assertTrue(missile.flare_diversion_resolved)
        self.assertFalse(missile.flare_diversion_allowed)
        self.assertGreater(target.x, missile.pos.x)

    def test_homing_target_requires_post_liftoff_flare_latch(self) -> None:
        mission = SimpleNamespace(
            tuning=SimpleNamespace(
                barak_flare_diversion_radius=320.0,
                barak_flare_diversion_max_flare_age_s=1.8,
                barak_flare_diversion_chance=1.0,
            ),
            flares=SimpleNamespace(
                particles=[SimpleNamespace(pos=Vec2(520.0, 160.0), age=0.2, ttl=1.1)]
            ),
        )
        missile = SimpleNamespace(
            pos=Vec2(500.0, 220.0),
            flare_diversion_resolved=False,
            flare_diversion_allowed=False,
            flare_seen_post_liftoff=False,
        )
        helicopter = SimpleNamespace(pos=Vec2(740.0, 240.0), facing=Facing.RIGHT)

        target, diverted = _barak_homing_target(mission=mission, missile=missile, helicopter=helicopter)
        self.assertFalse(diverted)
        self.assertFalse(missile.flare_diversion_resolved)
        self.assertFalse(missile.flare_diversion_allowed)
        self.assertGreater(target.x, missile.pos.x)

    def test_homing_target_diverts_upward_even_when_particles_expire_after_latch(self) -> None:
        mission = SimpleNamespace(
            tuning=SimpleNamespace(
                barak_flare_diversion_radius=320.0,
                barak_flare_diversion_max_flare_age_s=1.8,
                barak_flare_diversion_chance=1.0,
            ),
            flares=SimpleNamespace(particles=[]),
        )
        missile = SimpleNamespace(
            pos=Vec2(500.0, 220.0),
            flare_diversion_resolved=False,
            flare_diversion_allowed=False,
            flare_seen_post_liftoff=True,
        )
        helicopter = SimpleNamespace(pos=Vec2(740.0, 240.0), facing=Facing.RIGHT)

        target, diverted = _barak_homing_target(mission=mission, missile=missile, helicopter=helicopter)
        self.assertTrue(diverted)
        self.assertEqual(target.x, missile.pos.x)
        self.assertLess(target.y, missile.pos.y)

    def test_turn_toward_angle_caps_steering_rate(self) -> None:
        current = 0.0
        target = 1.2
        new_angle = _turn_toward_angle(current=current, target=target, max_step=0.25)
        self.assertAlmostEqual(new_angle, 0.25, places=5)


if __name__ == "__main__":
    unittest.main()
