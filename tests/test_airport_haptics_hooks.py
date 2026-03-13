from __future__ import annotations

import unittest
from unittest.mock import call, patch
import pytest

from src.choplifter.app.airport_tick import _apply_airport_transition_haptics


pytestmark = pytest.mark.airport_smoke


class AirportHapticsHookTests(unittest.TestCase):
    def test_transition_helper_emits_expected_events(self) -> None:
        with patch("src.choplifter.app.airport_tick.haptics.rumble_airport_event") as rumble_event:
            _apply_airport_transition_haptics(
                prev_tech_state_name="on_chopper",
                tech_state_name="deployed_to_truck",
                prev_hostage_state_name="waiting",
                new_hostage_state_name="truck_loading",
                prev_box_state="retracting",
                box_state="extended",
                logger=None,
            )

            self.assertEqual(
                rumble_event.call_args_list,
                [
                    call(event="tech_deploy", logger=None),
                    call(event="lift_extended", logger=None),
                    call(event="load_start", logger=None),
                ],
            )

    def test_completion_and_failure_edges_emit_once(self) -> None:
        with patch("src.choplifter.app.airport_tick.haptics.rumble_airport_event") as rumble_event:
            _apply_airport_transition_haptics(
                prev_tech_state_name="transferring",
                tech_state_name="waiting_at_lz",
                prev_hostage_state_name="boarded",
                new_hostage_state_name="rescued",
                prev_box_state="extended",
                box_state="extended",
                logger=None,
            )
            _apply_airport_transition_haptics(
                prev_tech_state_name="waiting_at_lz",
                tech_state_name="kia",
                prev_hostage_state_name="rescued",
                new_hostage_state_name="rescued",
                prev_box_state="extended",
                box_state="extended",
                logger=None,
            )

            self.assertIn(call(event="rescue_complete", logger=None), rumble_event.call_args_list)
            self.assertIn(call(event="tech_waiting_lz", logger=None), rumble_event.call_args_list)
            self.assertIn(call(event="tech_kia", logger=None), rumble_event.call_args_list)


if __name__ == "__main__":
    unittest.main()
