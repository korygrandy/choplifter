from __future__ import annotations

import unittest

from src.choplifter.render.world import _countdown_seconds_label


class MissionEndCountdownOverlayTests(unittest.TestCase):
    def test_countdown_label_shows_realtime_tenths(self) -> None:
        self.assertEqual(_countdown_seconds_label(5.0), "Returning to Mission Select in 5.0s")
        self.assertEqual(_countdown_seconds_label(4.01), "Returning to Mission Select in 4.1s")
        self.assertEqual(_countdown_seconds_label(4.0), "Returning to Mission Select in 4.0s")
        self.assertEqual(_countdown_seconds_label(3.0), "Returning to Mission Select in 3.0s")
        self.assertEqual(_countdown_seconds_label(2.0), "Returning to Mission Select in 2.0s")
        self.assertEqual(_countdown_seconds_label(1.0), "Returning to Mission Select in 1.0s")

    def test_countdown_label_hides_at_zero_or_below(self) -> None:
        self.assertEqual(_countdown_seconds_label(0.0), "")
        self.assertEqual(_countdown_seconds_label(-1.0), "")


if __name__ == "__main__":
    unittest.main()
