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

    def test_cue_fires_for_fuselage_then_re_fires_for_jetway(self) -> None:
        """Cue must re-trigger when the truck moves to a second terminal."""
        from src.choplifter.cutscene_manager import AirportCutsceneState

        # Simulate state after cue already fired for fuselage terminal (index 0).
        cutscene_state = AirportCutsceneState(last_cued_terminal_index=0, cue_timer_s=0.0, cue_text="")

        hostage_state = AirportHostageState(
            terminal_pickup_xs=(1200.0, 1500.0),
            terminal_remaining=[0, 3],
            active_terminal_index=1,
            state="truck_loading",
        )

        updated = update_airport_cutscene_state(
            cutscene_state,
            0.016,
            meal_truck_state=type("MealTruck", (), {"extension_progress": 1.0})(),
            hostage_state=hostage_state,
            tech_state=type("Tech", (), {"is_deployed": True})(),
        )

        self.assertEqual(updated.cue_text, "Jetway terminal reached. Extraction window open.")
        self.assertEqual(updated.last_cued_terminal_index, 1)

    def test_cue_does_not_re_fire_for_same_terminal(self) -> None:
        """Cue must not repeat on the same terminal once it has fired."""
        from src.choplifter.cutscene_manager import AirportCutsceneState

        cutscene_state = AirportCutsceneState(last_cued_terminal_index=1, cue_timer_s=0.0, cue_text="already fired")

        hostage_state = AirportHostageState(
            terminal_pickup_xs=(1200.0, 1500.0),
            terminal_remaining=[0, 2],
            active_terminal_index=1,
            state="truck_loading",
        )

        updated = update_airport_cutscene_state(
            cutscene_state,
            0.016,
            meal_truck_state=type("MealTruck", (), {"extension_progress": 1.0})(),
            hostage_state=hostage_state,
            tech_state=type("Tech", (), {"is_deployed": True})(),
        )

        self.assertEqual(updated.cue_text, "already fired")


if __name__ == "__main__":
    unittest.main()
