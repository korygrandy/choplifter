from __future__ import annotations

import unittest

from src.choplifter.game_types import EnemyKind
from src.choplifter.threat_tells import THREAT_TELL_MATRIX


class ThreatTellMatrixTests(unittest.TestCase):
    def test_matrix_covers_primary_threat_enemies(self) -> None:
        self.assertIn(EnemyKind.TANK, THREAT_TELL_MATRIX)
        self.assertIn(EnemyKind.JET, THREAT_TELL_MATRIX)
        self.assertIn(EnemyKind.AIR_MINE, THREAT_TELL_MATRIX)

    def test_matrix_entries_have_required_fields(self) -> None:
        for kind in (EnemyKind.TANK, EnemyKind.JET, EnemyKind.AIR_MINE):
            tell = THREAT_TELL_MATRIX[kind]
            self.assertTrue(tell.cue)
            self.assertGreater(tell.lead_time_s, 0.0)
            self.assertGreater(tell.effective_range_px, 0.0)

    def test_known_baseline_values(self) -> None:
        self.assertAlmostEqual(THREAT_TELL_MATRIX[EnemyKind.TANK].lead_time_s, 0.30, places=2)
        self.assertAlmostEqual(THREAT_TELL_MATRIX[EnemyKind.JET].lead_time_s, 1.2, places=2)
        self.assertAlmostEqual(THREAT_TELL_MATRIX[EnemyKind.AIR_MINE].effective_range_px, 170.0, places=2)


if __name__ == "__main__":
    unittest.main()
