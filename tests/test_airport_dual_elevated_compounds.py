from __future__ import annotations

from types import SimpleNamespace
import unittest
import pytest

from src.choplifter.hostage_logic import AirportHostageState, update_airport_hostage_logic
from src.choplifter.mission_configs import create_airport_special_ops_config
from src.choplifter.mission_state import MissionState
from src.choplifter.settings import HelicopterSettings


pytestmark = pytest.mark.airport_smoke


class AirportDualElevatedCompoundsTests(unittest.TestCase):
    def test_airport_mission_raises_two_left_compounds(self) -> None:
        heli = HelicopterSettings()
        level = create_airport_special_ops_config()
        mission = MissionState.create_from_level_config(heli, level, mission_id="airport")

        self.assertGreaterEqual(len(mission.compounds), 3)
        base_y = float(heli.ground_y - level.compound_height)

        self.assertAlmostEqual(float(mission.compounds[0].pos.y), base_y - 60.0)
        self.assertAlmostEqual(float(mission.compounds[1].pos.y), base_y - 60.0)
        self.assertAlmostEqual(float(mission.compounds[2].pos.y), base_y)

    def test_truck_loaded_state_can_start_loading_second_elevated_terminal(self) -> None:
        hostage_state = AirportHostageState(
            total_hostages=6,
            boarded_hostages=0,
            rescued_hostages=0,
            meal_truck_loaded_hostages=2,
            state="truck_loaded",
            terminal_pickup_xs=(1200.0, 1500.0),
            terminal_remaining=[0, 3],
            pickup_x=1500.0,
            active_terminal_index=1,
        )

        bus_state = SimpleNamespace(x=1800.0, stop_x=500.0)
        helicopter = SimpleNamespace(pos=SimpleNamespace(x=0.0, y=0.0))
        mission = SimpleNamespace(elapsed_seconds=60.0)
        meal_truck_state = SimpleNamespace(
            x=1548.0,
            extension_progress=1.0,
            box_state="extended",
            tech_has_deployed=True,
        )
        tech_state = SimpleNamespace(is_deployed=True)

        out = update_airport_hostage_logic(
            hostage_state,
            0.016,
            bus_state=bus_state,
            helicopter=helicopter,
            mission=mission,
            meal_truck_state=meal_truck_state,
            tech_state=tech_state,
        )

        self.assertEqual(out.state, "truck_loading")
        self.assertEqual(out.loading_terminal_index, 1)
        self.assertEqual(out.pickup_x, 1500.0)

    def test_truck_loading_stops_when_truck_moves_more_than_5px_past_right_lz_edge(self) -> None:
        hostage_state = AirportHostageState(
            total_hostages=6,
            boarded_hostages=0,
            rescued_hostages=0,
            meal_truck_loaded_hostages=0,
            state="truck_loading",
            terminal_pickup_xs=(1200.0, 1500.0),
            terminal_remaining=[0, 3],
            pickup_x=1500.0,
            active_terminal_index=1,
            loading_terminal_index=1,
            loading_terminal_initial_count=3,
            boarding_started_s=10.0,
        )

        bus_state = SimpleNamespace(x=1800.0, stop_x=500.0)
        helicopter = SimpleNamespace(pos=SimpleNamespace(x=0.0, y=0.0))
        mission = SimpleNamespace(elapsed_seconds=11.0)
        meal_truck_state = SimpleNamespace(
            x=1561.0,
            extension_progress=1.0,
            box_state="extended",
            tech_has_deployed=True,
        )
        tech_state = SimpleNamespace(is_deployed=True)

        out = update_airport_hostage_logic(
            hostage_state,
            0.016,
            bus_state=bus_state,
            helicopter=helicopter,
            mission=mission,
            meal_truck_state=meal_truck_state,
            tech_state=tech_state,
        )

        self.assertEqual(out.state, "waiting")
        self.assertEqual(out.meal_truck_loaded_hostages, 0)
        self.assertEqual(out.loading_terminal_index, -1)

    def test_truck_loading_stops_to_truck_loaded_when_partial_passengers_already_loaded(self) -> None:
        hostage_state = AirportHostageState(
            total_hostages=6,
            boarded_hostages=0,
            rescued_hostages=0,
            meal_truck_loaded_hostages=2,
            state="truck_loading",
            terminal_pickup_xs=(1200.0, 1500.0),
            terminal_remaining=[0, 3],
            pickup_x=1500.0,
            active_terminal_index=1,
            loading_terminal_index=1,
            loading_terminal_initial_count=3,
            boarding_started_s=10.0,
        )

        bus_state = SimpleNamespace(x=1800.0, stop_x=500.0)
        helicopter = SimpleNamespace(pos=SimpleNamespace(x=0.0, y=0.0))
        mission = SimpleNamespace(elapsed_seconds=11.0)
        meal_truck_state = SimpleNamespace(
            x=1561.0,
            extension_progress=1.0,
            box_state="extended",
            tech_has_deployed=True,
        )
        tech_state = SimpleNamespace(is_deployed=True)

        out = update_airport_hostage_logic(
            hostage_state,
            0.016,
            bus_state=bus_state,
            helicopter=helicopter,
            mission=mission,
            meal_truck_state=meal_truck_state,
            tech_state=tech_state,
        )

        self.assertEqual(out.state, "truck_loaded")
        self.assertEqual(out.meal_truck_loaded_hostages, 2)
        self.assertEqual(out.loading_terminal_index, -1)

    def test_left_terminal_right_edge_zone_does_not_retrigger_loading_or_door_sfx(self) -> None:
        hostage_state = AirportHostageState(
            total_hostages=6,
            boarded_hostages=0,
            rescued_hostages=0,
            meal_truck_loaded_hostages=0,
            state="waiting",
            terminal_pickup_xs=(1200.0, 1500.0),
            terminal_remaining=[3, 0],
            pickup_x=1200.0,
            active_terminal_index=0,
            pickup_radius_px=28.0,
            pickup_passed_offset_px=27.0,
        )

        # This x is still inside near-terminal radius (<= 55 from center)
        # but beyond the tighter left-terminal loading boundary (> 50).
        meal_truck_state = SimpleNamespace(
            x=1252.0,
            extension_progress=1.0,
            box_state="extended",
            tech_has_deployed=True,
        )
        bus_state = SimpleNamespace(x=1800.0, stop_x=500.0)
        helicopter = SimpleNamespace(pos=SimpleNamespace(x=0.0, y=0.0))
        mission = SimpleNamespace(elapsed_seconds=42.0)
        tech_state = SimpleNamespace(is_deployed=True)

        audio_calls: list[str] = []

        class _Audio:
            def play_bus_door(self) -> None:
                audio_calls.append("bus_door")

        out = update_airport_hostage_logic(
            hostage_state,
            0.016,
            bus_state=bus_state,
            helicopter=helicopter,
            mission=mission,
            meal_truck_state=meal_truck_state,
            tech_state=tech_state,
            audio=_Audio(),
        )

        self.assertEqual(out.state, "waiting")
        self.assertEqual(audio_calls, [])

    def test_partial_loading_then_return_only_boards_remaining(self) -> None:
        hostage_state = AirportHostageState(
            total_hostages=6,
            boarded_hostages=0,
            rescued_hostages=0,
            meal_truck_loaded_hostages=0,
            state="truck_loading",
            terminal_pickup_xs=(1200.0, 1500.0),
            terminal_remaining=[3, 0],
            pickup_x=1200.0,
            active_terminal_index=0,
            loading_terminal_index=0,
            loading_terminal_initial_count=3,
            boarding_started_s=10.0,
        )

        bus_state = SimpleNamespace(x=1800.0, stop_x=500.0)
        helicopter = SimpleNamespace(pos=SimpleNamespace(x=0.0, y=0.0))
        tech_state = SimpleNamespace(is_deployed=True)

        # First pass: stay in LZ long enough to board one passenger.
        mission = SimpleNamespace(elapsed_seconds=11.0)
        meal_truck_state = SimpleNamespace(
            x=1227.0,
            extension_progress=1.0,
            box_state="extended",
            tech_has_deployed=True,
        )
        out = update_airport_hostage_logic(
            hostage_state,
            0.016,
            bus_state=bus_state,
            helicopter=helicopter,
            mission=mission,
            meal_truck_state=meal_truck_state,
            tech_state=tech_state,
        )

        # Second pass: move beyond right boundary and ensure partial load is preserved.
        mission.elapsed_seconds = 11.1
        meal_truck_state.x = 1256.0
        out = update_airport_hostage_logic(
            out,
            0.016,
            bus_state=bus_state,
            helicopter=helicopter,
            mission=mission,
            meal_truck_state=meal_truck_state,
            tech_state=tech_state,
        )

        self.assertEqual(out.state, "truck_loaded")
        self.assertEqual(out.meal_truck_loaded_hostages, 1)
        self.assertEqual(out.terminal_remaining[0], 2)

        # Re-enter same terminal LZ: only remaining 2 should be boardable.
        out.state = "truck_loaded"
        mission.elapsed_seconds = 12.0
        meal_truck_state.x = 1227.0
        out = update_airport_hostage_logic(
            out,
            0.016,
            bus_state=bus_state,
            helicopter=helicopter,
            mission=mission,
            meal_truck_state=meal_truck_state,
            tech_state=tech_state,
        )
        self.assertEqual(out.state, "truck_loading")
        self.assertEqual(out.loading_terminal_initial_count, 2)


if __name__ == "__main__":
    unittest.main()
