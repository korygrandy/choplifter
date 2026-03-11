from __future__ import annotations

from types import SimpleNamespace
import unittest

from src.choplifter.objective_manager import update_airport_objectives


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


if __name__ == "__main__":
    unittest.main()
