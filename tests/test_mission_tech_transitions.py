from __future__ import annotations

from types import SimpleNamespace
import unittest
import pytest

from src.choplifter.mission_tech import MissionTechState, update_mission_tech


pytestmark = pytest.mark.airport_smoke


class MissionTechTransitionTests(unittest.TestCase):
    def test_transferring_enters_boarding_bus_then_transfer_complete_and_closes_bus_doors(self) -> None:
        tech_state = MissionTechState(
            state="transferring",
            on_bus=False,
            is_deployed=True,
            tech_x=1300.0,
            tech_y=210.0,
            deploy_timer_s=3.0,
        )
        meal_truck_state = SimpleNamespace(x=1320.0, y=210.0)
        class _Audio:
            def __init__(self) -> None:
                self.calls = 0

            def play_hang_on_yall(self) -> None:
                self.calls += 1

        audio = _Audio()

        bus_state = SimpleNamespace(
            x=1160.0,
            y=210.0,
            width=64,
            door_state="closed",
            door_animation_progress=0.0,
        )
        hostage_state = SimpleNamespace(state="boarded", boarded_hostages=8, rescued_hostages=0, total_hostages=8)

        first = update_mission_tech(
            tech_state,
            0.016,
            meal_truck_state=meal_truck_state,
            bus_state=bus_state,
            hostage_state=hostage_state,
            audio=audio,
        )

        self.assertEqual(first.state, "boarding_bus")
        self.assertEqual(first.boarding_animation_state, "boarding_bus")
        self.assertEqual(bus_state.door_state, "opening")
        expected_anchor = 1160.0 + 64.0 * 0.68
        self.assertLessEqual(abs(float(first.boarding_end_x) - expected_anchor), 2.0)
        self.assertEqual(audio.calls, 1)

        second = update_mission_tech(
            first,
            1.0,
            meal_truck_state=meal_truck_state,
            bus_state=bus_state,
            hostage_state=hostage_state,
        )

        self.assertEqual(second.state, "transfer_complete")
        self.assertTrue(second.on_bus)
        self.assertEqual(bus_state.door_state, "closing")

    def test_transfer_complete_moves_to_waiting_at_lz_when_bus_reaches_tower_lz(self) -> None:
        tech_state = MissionTechState(
            state="transfer_complete",
            on_bus=True,
            is_deployed=True,
            tech_x=1200.0,
            tech_y=210.0,
            deploy_timer_s=5.0,
        )
        bus_state = SimpleNamespace(
            x=620.0,
            y=210.0,
            stop_x=500.0,
            door_state="closed",
            door_animation_progress=0.0,
        )
        hostage_state = SimpleNamespace(rescued_hostages=2, total_hostages=8)

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

    def test_mission_tech_does_not_fall_before_airborne_grace_window(self) -> None:
        tech_state = MissionTechState(
            state="on_chopper",
            tech_x=400.0,
            tech_y=150.0,
            fall_airborne_timer=2.3,
            fall_delay_s=2.8,
        )
        helicopter = SimpleNamespace(
            grounded=False,
            doors_open=True,
            pos=SimpleNamespace(x=400.0, y=150.0),
        )

        updated = update_mission_tech(
            tech_state,
            0.2,
            helicopter=helicopter,
        )

        self.assertEqual(updated.state, "on_chopper")

    def test_mission_tech_falls_after_airborne_grace_window(self) -> None:
        tech_state = MissionTechState(
            state="on_chopper",
            tech_x=400.0,
            tech_y=150.0,
            fall_airborne_timer=2.15,
            fall_delay_s=2.2,
        )
        helicopter = SimpleNamespace(
            grounded=False,
            doors_open=True,
            pos=SimpleNamespace(x=400.0, y=150.0),
        )

        updated = update_mission_tech(
            tech_state,
            0.1,
            helicopter=helicopter,
        )

        self.assertEqual(updated.state, "falling")


if __name__ == "__main__":
    unittest.main()
