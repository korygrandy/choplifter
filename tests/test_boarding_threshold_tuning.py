from __future__ import annotations

import unittest

from src.choplifter.mission_configs import MissionTuning


class BoardingThresholdTuningTests(unittest.TestCase):
    def test_defaults_reflect_playtest_tuning(self) -> None:
        tuning = MissionTuning()

        self.assertEqual(tuning.hostage_controlled_start_radius, 260.0)
        self.assertEqual(tuning.hostage_chaotic_start_radius, 340.0)
        self.assertEqual(tuning.hostage_boarding_radius, 64.0)

    def test_thresholds_are_positive(self) -> None:
        tuning = MissionTuning()

        self.assertGreater(tuning.hostage_controlled_start_radius, 0.0)
        self.assertGreater(tuning.hostage_chaotic_start_radius, 0.0)
        self.assertGreater(tuning.hostage_boarding_radius, 0.0)

    def test_airborne_fall_delay_defaults(self) -> None:
        tuning = MissionTuning()

        self.assertEqual(tuning.airborne_fall_delay_min_s, 2.0)
        self.assertEqual(tuning.airborne_fall_delay_max_s, 3.0)

    def test_airborne_fall_delay_override(self) -> None:
        tuning = MissionTuning(airborne_fall_delay_min_s=2.4, airborne_fall_delay_max_s=2.9)

        self.assertEqual(tuning.airborne_fall_delay_min_s, 2.4)
        self.assertEqual(tuning.airborne_fall_delay_max_s, 2.9)


if __name__ == "__main__":
    unittest.main()
