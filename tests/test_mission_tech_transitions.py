from __future__ import annotations

from types import SimpleNamespace
import unittest
import pytest

from src.choplifter.mission_tech import MissionTechState, update_mission_tech


pytestmark = pytest.mark.airport_smoke


class MissionTechTransitionTests(unittest.TestCase):
    def test_transfer_complete_moves_to_waiting_at_lz_after_elevated_rescue_complete(self) -> None:
        tech_state = MissionTechState(
            state="transfer_complete",
            on_bus=True,
            is_deployed=True,
            tech_x=1200.0,
            tech_y=210.0,
            deploy_timer_s=5.0,
        )
        bus_state = SimpleNamespace(
            x=1225.0,
            y=210.0,
            stop_x=500.0,
            door_state="closed",
            door_animation_progress=0.0,
        )
        hostage_state = SimpleNamespace(rescued_hostages=8, total_hostages=8)

        updated = update_mission_tech(
            tech_state,
            0.016,
            bus_state=bus_state,
            hostage_state=hostage_state,
        )

        self.assertEqual(updated.state, "waiting_at_lz")
        self.assertFalse(updated.on_bus)
        self.assertTrue(updated.is_deployed)
        self.assertEqual(updated.boarding_animation_state, "disembarking")
        self.assertEqual(updated.lz_wait_x, 420.0)
        self.assertEqual(updated.lz_wait_y, 210.0)
        self.assertEqual(bus_state.door_state, "opening")

    def test_waiting_at_lz_reboards_to_chopper_and_closes_bus_door(self) -> None:
        tech_state = MissionTechState(
            state="waiting_at_lz",
            on_bus=False,
            is_deployed=True,
            tech_x=420.0,
            tech_y=210.0,
            lz_wait_x=420.0,
            lz_wait_y=210.0,
            boarding_animation_state="idle",
        )
        helicopter = SimpleNamespace(
            grounded=True,
            doors_open=True,
            pos=SimpleNamespace(x=450.0, y=190.0),
        )
        bus_state = SimpleNamespace(door_state="open", door_animation_progress=0.5)

        updated = update_mission_tech(
            tech_state,
            0.016,
            helicopter=helicopter,
            bus_state=bus_state,
        )

        self.assertEqual(updated.state, "on_chopper")
        self.assertFalse(updated.is_deployed)
        self.assertFalse(updated.on_bus)
        self.assertEqual(updated.tech_x, 450.0)
        self.assertEqual(updated.tech_y, 190.0)
        self.assertEqual(updated.boarding_animation_state, "returning")
        self.assertEqual(bus_state.door_state, "closing")
        self.assertEqual(bus_state.door_animation_progress, 0.0)


if __name__ == "__main__":
    unittest.main()
