from __future__ import annotations

from types import SimpleNamespace
import unittest

from src.choplifter.helicopter import Facing
from src.choplifter.math2d import Vec2
from src.choplifter.mission_projectiles import (
    _barak_diversion_collision_target,
    _barak_find_flare_decoy,
    _barak_homing_target,
    _barak_is_successfully_diverted,
    _barak_roll_diversion,
    _barak_should_explode_after_near_miss,
    _barak_target_point,
    _turn_toward_angle,
)
from src.choplifter.mission_configs import MissionTuning


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
                barak_flare_near_miss_radius_px=34.0,
                barak_flare_spin_rate_deg=520.0,
                barak_flare_spin_amplitude_px=10.0,
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
            diversion_spin_phase=0.0,
            diversion_miss_side=0,
        )
        helicopter = SimpleNamespace(pos=Vec2(740.0, 240.0), facing=Facing.RIGHT)

        target, diverted = _barak_homing_target(mission=mission, missile=missile, helicopter=helicopter, dt=0.1)
        heli_target = _barak_target_point(helicopter)
        dist = ((target.x - heli_target.x) ** 2 + (target.y - heli_target.y) ** 2) ** 0.5
        self.assertTrue(diverted)
        self.assertTrue(missile.flare_diversion_resolved)
        self.assertTrue(missile.flare_diversion_allowed)
        self.assertGreater(dist, 10.0)
        self.assertLess(dist, 70.0)
        self.assertNotEqual(missile.diversion_miss_side, 0)
        self.assertGreater(missile.diversion_spin_phase, 0.0)

    def test_homing_target_falls_back_to_heli_when_roll_fails(self) -> None:
        mission = SimpleNamespace(
            tuning=SimpleNamespace(
                barak_flare_diversion_radius=320.0,
                barak_flare_diversion_max_flare_age_s=1.8,
                barak_flare_diversion_chance=0.0,
                barak_flare_near_miss_radius_px=34.0,
                barak_flare_spin_rate_deg=520.0,
                barak_flare_spin_amplitude_px=10.0,
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
            diversion_spin_phase=0.0,
            diversion_miss_side=0,
        )
        helicopter = SimpleNamespace(pos=Vec2(740.0, 240.0), facing=Facing.RIGHT)

        target, diverted = _barak_homing_target(mission=mission, missile=missile, helicopter=helicopter, dt=0.1)
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
                barak_flare_near_miss_radius_px=34.0,
                barak_flare_spin_rate_deg=520.0,
                barak_flare_spin_amplitude_px=10.0,
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
            diversion_spin_phase=0.0,
            diversion_miss_side=0,
        )
        helicopter = SimpleNamespace(pos=Vec2(740.0, 240.0), facing=Facing.RIGHT)

        target, diverted = _barak_homing_target(mission=mission, missile=missile, helicopter=helicopter, dt=0.1)
        self.assertFalse(diverted)
        self.assertFalse(missile.flare_diversion_resolved)
        self.assertFalse(missile.flare_diversion_allowed)
        self.assertGreater(target.x, missile.pos.x)

    def test_homing_target_diverts_near_miss_even_when_particles_expire_after_latch(self) -> None:
        mission = SimpleNamespace(
            tuning=SimpleNamespace(
                barak_flare_diversion_radius=320.0,
                barak_flare_diversion_max_flare_age_s=1.8,
                barak_flare_diversion_chance=1.0,
                barak_flare_near_miss_radius_px=34.0,
                barak_flare_spin_rate_deg=520.0,
                barak_flare_spin_amplitude_px=10.0,
            ),
            flares=SimpleNamespace(particles=[]),
        )
        missile = SimpleNamespace(
            pos=Vec2(500.0, 220.0),
            flare_diversion_resolved=False,
            flare_diversion_allowed=False,
            flare_seen_post_liftoff=True,
            diversion_spin_phase=0.0,
            diversion_miss_side=0,
        )
        helicopter = SimpleNamespace(pos=Vec2(740.0, 240.0), facing=Facing.RIGHT)

        target, diverted = _barak_homing_target(mission=mission, missile=missile, helicopter=helicopter, dt=0.1)
        heli_target = _barak_target_point(helicopter)
        dist = ((target.x - heli_target.x) ** 2 + (target.y - heli_target.y) ** 2) ** 0.5
        self.assertTrue(diverted)
        self.assertGreater(dist, 10.0)
        self.assertLess(dist, 70.0)

    def test_turn_toward_angle_caps_steering_rate(self) -> None:
        current = 0.0
        target = 1.2
        new_angle = _turn_toward_angle(current=current, target=target, max_step=0.25)
        self.assertAlmostEqual(new_angle, 0.25, places=5)

    def test_default_diversion_success_rate_is_sixty_six_percent(self) -> None:
        self.assertAlmostEqual(MissionTuning().barak_flare_diversion_chance, 0.66, places=6)

    def test_diversion_collision_target_offsets_away_from_nose(self) -> None:
        mission = SimpleNamespace(tuning=SimpleNamespace(barak_flare_near_miss_radius_px=42.0))
        missile = SimpleNamespace(
            pos=Vec2(700.0, 220.0),
            flare_seen_post_liftoff=True,
            flare_diversion_allowed=True,
            diversion_miss_side=1,
        )
        helicopter = SimpleNamespace(pos=Vec2(740.0, 240.0), facing=Facing.RIGHT)

        base = _barak_target_point(helicopter)
        target = _barak_diversion_collision_target(mission=mission, missile=missile, helicopter=helicopter)
        self.assertGreater(target.x - base.x, 27.0)

    def test_near_miss_explosion_arms_on_close_then_triggers_on_exit(self) -> None:
        missile = SimpleNamespace(diversion_pass_armed=False, diversion_prev_nose_distance=-1.0)

        self.assertFalse(
            _barak_should_explode_after_near_miss(
                missile=missile,
                distance_to_nose=49.0,
                arm_radius=54.0,
                detonate_distance=68.0,
            )
        )
        self.assertTrue(missile.diversion_pass_armed)
        self.assertFalse(
            _barak_should_explode_after_near_miss(
                missile=missile,
                distance_to_nose=61.0,
                arm_radius=54.0,
                detonate_distance=68.0,
            )
        )
        self.assertTrue(
            _barak_should_explode_after_near_miss(
                missile=missile,
                distance_to_nose=72.0,
                arm_radius=54.0,
                detonate_distance=68.0,
            )
        )

    def test_near_miss_explosion_does_not_trigger_without_close_pass(self) -> None:
        missile = SimpleNamespace(diversion_pass_armed=False, diversion_prev_nose_distance=-1.0)
        self.assertFalse(
            _barak_should_explode_after_near_miss(
                missile=missile,
                distance_to_nose=90.0,
                arm_radius=54.0,
                detonate_distance=68.0,
            )
        )

    def test_diverted_target_loops_away_after_pass(self) -> None:
        mission = SimpleNamespace(
            tuning=SimpleNamespace(
                barak_flare_diversion_radius=320.0,
                barak_flare_diversion_max_flare_age_s=1.8,
                barak_flare_diversion_chance=1.0,
                barak_flare_near_miss_radius_px=42.0,
                barak_flare_spin_rate_deg=520.0,
                barak_flare_spin_amplitude_px=10.0,
            ),
            flares=SimpleNamespace(
                particles=[SimpleNamespace(pos=Vec2(520.0, 160.0), age=0.2, ttl=1.1)]
            ),
        )
        helicopter = SimpleNamespace(pos=Vec2(740.0, 240.0), facing=Facing.RIGHT)
        heli_target = _barak_target_point(helicopter)

        approach = SimpleNamespace(
            pos=Vec2(500.0, 220.0),
            flare_diversion_resolved=False,
            flare_diversion_allowed=False,
            flare_seen_post_liftoff=True,
            diversion_spin_phase=0.0,
            diversion_miss_side=0,
            diversion_pass_armed=False,
        )
        approach_target, approach_diverted = _barak_homing_target(
            mission=mission,
            missile=approach,
            helicopter=helicopter,
            dt=0.1,
        )

        loop_away = SimpleNamespace(
            pos=Vec2(500.0, 220.0),
            flare_diversion_resolved=True,
            flare_diversion_allowed=True,
            flare_seen_post_liftoff=True,
            diversion_spin_phase=approach.diversion_spin_phase,
            diversion_miss_side=approach.diversion_miss_side,
            diversion_pass_armed=True,
        )
        away_target, away_diverted = _barak_homing_target(
            mission=mission,
            missile=loop_away,
            helicopter=helicopter,
            dt=0.1,
        )

        approach_dist = ((approach_target.x - heli_target.x) ** 2 + (approach_target.y - heli_target.y) ** 2) ** 0.5
        away_dist = ((away_target.x - heli_target.x) ** 2 + (away_target.y - heli_target.y) ** 2) ** 0.5
        self.assertTrue(approach_diverted)
        self.assertTrue(away_diverted)
        self.assertGreater(away_dist, approach_dist + 10.0)

    def test_successful_diversion_flag_requires_latch_and_allow(self) -> None:
        self.assertFalse(_barak_is_successfully_diverted(SimpleNamespace(flare_seen_post_liftoff=False, flare_diversion_allowed=True)))
        self.assertFalse(_barak_is_successfully_diverted(SimpleNamespace(flare_seen_post_liftoff=True, flare_diversion_allowed=False)))
        self.assertTrue(_barak_is_successfully_diverted(SimpleNamespace(flare_seen_post_liftoff=True, flare_diversion_allowed=True)))


if __name__ == "__main__":
    unittest.main()
