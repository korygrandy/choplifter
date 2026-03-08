from __future__ import annotations

import unittest

from src.choplifter.app.objective_overlay import (
    get_mission_objective_overlay,
    get_mission_objective_overlay_duration,
    get_city_siege_objective_overlay_duration,
    is_city_siege_mission,
    overlay_alpha,
    tick_overlay_timer,
)


class CitySiegeObjectiveOverlayTests(unittest.TestCase):
    def test_city_siege_mission_aliases(self) -> None:
        self.assertTrue(is_city_siege_mission("city"))
        self.assertTrue(is_city_siege_mission("CITY_CENTER"))
        self.assertTrue(is_city_siege_mission("mission1"))
        self.assertFalse(is_city_siege_mission("airport"))

    def test_duration_only_for_city_siege(self) -> None:
        self.assertEqual(get_city_siege_objective_overlay_duration(mission_id="city"), 3.0)
        self.assertEqual(get_city_siege_objective_overlay_duration(mission_id="airport"), 0.0)

    def test_mission_objective_overlay_messages(self) -> None:
        city_text, city_icon = get_mission_objective_overlay(mission_id="city")
        airport_text, airport_icon = get_mission_objective_overlay(mission_id="airport")
        worship_text, worship_icon = get_mission_objective_overlay(mission_id="worship")

        self.assertEqual(city_text, "Rescue the VIP hostage")
        self.assertTrue(city_icon)
        self.assertEqual(airport_text, "Rescue hostages and return them to base")
        self.assertFalse(airport_icon)
        self.assertEqual(worship_text, "Rescue hostages amid heavy resistance")
        self.assertFalse(worship_icon)

    def test_mission_objective_overlay_duration_for_all_missions(self) -> None:
        self.assertEqual(get_mission_objective_overlay_duration(mission_id="city"), 3.0)
        self.assertEqual(get_mission_objective_overlay_duration(mission_id="airport"), 3.0)
        self.assertEqual(get_mission_objective_overlay_duration(mission_id="worship"), 3.0)
        self.assertEqual(get_mission_objective_overlay_duration(mission_id="unknown"), 0.0)

    def test_tick_overlay_timer_clamps_to_zero(self) -> None:
        self.assertEqual(tick_overlay_timer(timer_s=3.0, frame_dt=0.25), 2.75)
        self.assertEqual(tick_overlay_timer(timer_s=0.1, frame_dt=1.0), 0.0)

    def test_overlay_alpha_fades_in_and_out(self) -> None:
        self.assertEqual(overlay_alpha(remaining_s=3.0), 0)
        self.assertGreater(overlay_alpha(remaining_s=2.8), 0)
        self.assertEqual(overlay_alpha(remaining_s=1.5), 255)
        self.assertLess(overlay_alpha(remaining_s=0.2), 255)
        self.assertEqual(overlay_alpha(remaining_s=0.0), 0)


if __name__ == "__main__":
    unittest.main()
