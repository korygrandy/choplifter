from __future__ import annotations

from types import SimpleNamespace
import unittest
import pytest

from src.choplifter.objective_manager import update_airport_objectives


pytestmark = pytest.mark.airport_smoke


class AirportObjectiveFlowTests(unittest.TestCase):
    def test_prompts_tech_reboard_when_elevated_rescue_done_but_total_not_met(self) -> None:
        mission = SimpleNamespace(elapsed_seconds=42.0, stats=SimpleNamespace(saved=8))
        hostage_state = SimpleNamespace(state="rescued", rescued_hostages=4, interrupted_transfers=0)
        tech_state = SimpleNamespace(state="waiting_at_lz", is_deployed=True, on_bus=False)

        objective = update_airport_objectives(
            None,
            0.016,
            mission=mission,
            hostage_state=hostage_state,
            tech_state=tech_state,
        )

        self.assertEqual(objective.mission_phase, "awaiting_tech_reboard")
        self.assertEqual(objective.status_text, "Land at tower LZ and pick up mission tech")

    def test_shows_resume_lower_rescue_after_tech_reboards_when_total_not_met(self) -> None:
        mission = SimpleNamespace(elapsed_seconds=42.0, stats=SimpleNamespace(saved=8))
        hostage_state = SimpleNamespace(state="rescued", rescued_hostages=4, interrupted_transfers=0)
        tech_state = SimpleNamespace(state="on_chopper", is_deployed=False, on_bus=False)

        objective = update_airport_objectives(
            None,
            0.016,
            mission=mission,
            hostage_state=hostage_state,
            tech_state=tech_state,
        )

        self.assertEqual(objective.mission_phase, "resume_lower_rescue")
        self.assertEqual(objective.status_text, "Resume lower-terminal rescues")

    def test_marks_complete_only_after_combined_rescue_target_met(self) -> None:
        mission = SimpleNamespace(elapsed_seconds=42.0, stats=SimpleNamespace(saved=9))
        hostage_state = SimpleNamespace(state="rescued", rescued_hostages=7, interrupted_transfers=0)
        tech_state = SimpleNamespace(state="on_chopper", is_deployed=False, on_bus=False)

        objective = update_airport_objectives(
            None,
            0.016,
            mission=mission,
            hostage_state=hostage_state,
            tech_state=tech_state,
        )

        self.assertEqual(objective.mission_phase, "mission_complete")
        self.assertEqual(objective.status_text, "All civilians rescued")

    def test_routes_truck_to_next_named_terminal_when_elevated_rescues_remain(self) -> None:
        mission = SimpleNamespace(elapsed_seconds=42.0, stats=SimpleNamespace(saved=4))
        hostage_state = SimpleNamespace(
            state="truck_loaded",
            rescued_hostages=0,
            interrupted_transfers=0,
            terminal_remaining=[0, 3],
            terminal_pickup_xs=(1200.0, 1500.0),
            active_terminal_index=1,
        )
        tech_state = SimpleNamespace(state="deployed_to_truck", is_deployed=True, on_bus=False)

        objective = update_airport_objectives(
            None,
            0.016,
            mission=mission,
            hostage_state=hostage_state,
            tech_state=tech_state,
        )

        self.assertEqual(objective.mission_phase, "truck_driving_to_bunker")
        self.assertEqual(objective.status_text, "Drive meal truck to jetway terminal")


if __name__ == "__main__":
    unittest.main()
