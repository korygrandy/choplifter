from __future__ import annotations

import unittest
import pytest

from src.choplifter.render.world import _sentiment_reason_lines


pytestmark = pytest.mark.airport_smoke


class AirportEndDebriefBonusTests(unittest.TestCase):
    def test_debrief_shows_riskier_path_bonus_when_upper_first(self) -> None:
        lines = _sentiment_reason_lines(
            saved=3,
            kia_player=0,
            kia_enemy=0,
            lost_in_transit=0,
            mission_id="airport",
            route_bonus_awarded=True,
            route_bonus_value=3.0,
            first_route="elevated",
        )

        self.assertTrue(any("Riskier Path Bonus" in line and "+3.0" in line for line in lines))
        self.assertTrue(any("Riskier Path Bonus: EARNED" in line for line in lines))
        self.assertTrue(any("Upper Terminals rescued first" in line for line in lines))

    def test_debrief_shows_riskier_path_not_earned_for_lower_first(self) -> None:
        lines = _sentiment_reason_lines(
            saved=3,
            kia_player=0,
            kia_enemy=0,
            lost_in_transit=0,
            mission_id="airport",
            route_bonus_awarded=True,
            route_bonus_value=2.0,
            first_route="lower",
        )

        self.assertTrue(any("Route Bonus" in line and "+2.0" in line for line in lines))
        self.assertTrue(any("Riskier Path Bonus: NOT EARNED" in line for line in lines))
        self.assertTrue(any("rescue Upper Terminals first" in line for line in lines))


if __name__ == "__main__":
    unittest.main()
