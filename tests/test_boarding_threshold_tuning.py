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


if __name__ == "__main__":
    unittest.main()
