from __future__ import annotations

from types import SimpleNamespace
import unittest
import pytest

from src.choplifter.objective_manager import ESCORT_THREAT_WARNING_TEXT, update_airport_objectives


pytestmark = pytest.mark.airport_smoke


class AirportObjectiveFlowTests(unittest.TestCase):
    def test_shows_soft_hint_once_then_returns_to_deploy_message(self) -> None:
        mission = SimpleNamespace(elapsed_seconds=12.0, stats=SimpleNamespace(saved=0), sentiment=50.0)
        hostage_state = SimpleNamespace(
            state="waiting",
            rescued_hostages=0,
            interrupted_transfers=0,
            terminal_remaining=[2, 1],
        )

        objective = update_airport_objectives(
            None,
            0.016,
            mission=mission,
            hostage_state=hostage_state,
            tech_state=SimpleNamespace(state="on_chopper", is_deployed=False, on_bus=False),
        )

        self.assertEqual(objective.status_text, "Tip: any order works; elevated-first is riskiest (+bonus)")

        objective = update_airport_objectives(
            objective,
            0.016,
            mission=mission,
            hostage_state=hostage_state,
            tech_state=SimpleNamespace(state="on_chopper", is_deployed=False, on_bus=False),
        )

        self.assertEqual(objective.status_text, "Deploy mission tech to meal truck")

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
        self.assertEqual(objective.status_text, "Resume Lower Terminal rescues")

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
        self.assertEqual(objective.status_text, "Drive meal truck to Jetway Terminal")

    def test_awards_one_time_route_bonus_when_both_streams_progress(self) -> None:
        mission = SimpleNamespace(
            elapsed_seconds=52.0,
            mission_id="airport",
            stats=SimpleNamespace(saved=3),
            sentiment=45.0,
            airport_first_rescue_route="elevated",
            airport_route_bonus_awarded=False,
        )
        hostage_state = SimpleNamespace(state="rescued", rescued_hostages=2, interrupted_transfers=0)

        update_airport_objectives(
            None,
            0.016,
            mission=mission,
            hostage_state=hostage_state,
            tech_state=SimpleNamespace(state="on_chopper", is_deployed=False, on_bus=False),
        )

        self.assertTrue(bool(getattr(mission, "airport_route_bonus_awarded", False)))
        self.assertAlmostEqual(float(getattr(mission, "airport_route_bonus_value", 0.0)), 3.0)
        self.assertAlmostEqual(float(mission.sentiment), 48.0)

    def test_awards_lower_first_route_bonus_when_lower_path_started_first(self) -> None:
        mission = SimpleNamespace(
            elapsed_seconds=52.0,
            mission_id="airport",
            stats=SimpleNamespace(saved=3),
            sentiment=45.0,
            airport_first_rescue_route="lower",
            airport_route_bonus_awarded=False,
        )
        hostage_state = SimpleNamespace(state="rescued", rescued_hostages=2, interrupted_transfers=0)

        update_airport_objectives(
            None,
            0.016,
            mission=mission,
            hostage_state=hostage_state,
            tech_state=SimpleNamespace(state="on_chopper", is_deployed=False, on_bus=False),
        )

        self.assertTrue(bool(getattr(mission, "airport_route_bonus_awarded", False)))
        self.assertAlmostEqual(float(getattr(mission, "airport_route_bonus_value", 0.0)), 2.0)
        self.assertAlmostEqual(float(mission.sentiment), 47.0)

    def test_shows_escort_threat_warning_when_tech_is_on_bus(self) -> None:
        mission = SimpleNamespace(elapsed_seconds=24.0, stats=SimpleNamespace(saved=5))
        hostage_state = SimpleNamespace(state="boarded", rescued_hostages=4, interrupted_transfers=0)
        tech_state = SimpleNamespace(state="transfer_complete", is_deployed=True, on_bus=True)

        objective = update_airport_objectives(
            None,
            0.016,
            mission=mission,
            hostage_state=hostage_state,
            tech_state=tech_state,
        )

        self.assertEqual(objective.mission_phase, "escort_to_lz")
        self.assertEqual(objective.status_text, ESCORT_THREAT_WARNING_TEXT)


if __name__ == "__main__":
    unittest.main()
