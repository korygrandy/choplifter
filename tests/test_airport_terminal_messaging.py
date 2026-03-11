from __future__ import annotations

import unittest
import pytest

from src.choplifter.cutscene_manager import update_airport_cutscene_state
from src.choplifter.hostage_logic import AirportHostageState, get_airport_terminal_label


pytestmark = pytest.mark.airport_smoke


class AirportTerminalMessagingTests(unittest.TestCase):
    def test_left_terminal_is_named_fuselage_and_right_terminal_is_named_jetway(self) -> None:
        hostage_state = AirportHostageState(
            terminal_pickup_xs=(1200.0, 1500.0),
            terminal_remaining=[2, 2],
            active_terminal_index=0,
        )

        self.assertEqual(get_airport_terminal_label(hostage_state, 0), "fuselage")
        self.assertEqual(get_airport_terminal_label(hostage_state, 1), "jetway")

    def test_cutscene_cue_uses_active_terminal_name(self) -> None:
        hostage_state = AirportHostageState(
            terminal_pickup_xs=(1200.0, 1500.0),
            terminal_remaining=[2, 2],
            active_terminal_index=1,
            state="waiting",
        )

        cutscene_state = update_airport_cutscene_state(
            None,
            0.016,
            meal_truck_state=type("MealTruck", (), {"extension_progress": 1.0})(),
            hostage_state=hostage_state,
            tech_state=type("Tech", (), {"is_deployed": True})(),
        )

        self.assertEqual(cutscene_state.cue_text, "Jetway terminal reached. Extraction window open.")


if __name__ == "__main__":
    unittest.main()
