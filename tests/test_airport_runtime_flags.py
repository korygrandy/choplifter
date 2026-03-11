from __future__ import annotations

from types import SimpleNamespace
import unittest

from src.choplifter.app.airport_runtime_flags import sync_airport_runtime_flags


class AirportRuntimeFlagsTests(unittest.TestCase):
    def _mission(self) -> SimpleNamespace:
        return SimpleNamespace(
            engineer_remote_control_active=False,
            player_driving_vehicle=False,
            engineer_off_chopper=False,
            barak_suppressed=False,
        )

    def test_off_chopper_does_not_suppress_barak_without_driver_mode(self) -> None:
        mission = self._mission()
        tech = SimpleNamespace(state="waiting_at_lz")

        sync_airport_runtime_flags(
            mission=mission,
            selected_mission_id="airport",
            airport_tech_state=tech,
            meal_truck_driver_mode=False,
            bus_driver_mode=False,
        )

        self.assertTrue(mission.engineer_off_chopper)
        self.assertFalse(mission.engineer_remote_control_active)
        self.assertFalse(mission.player_driving_vehicle)
        self.assertFalse(mission.barak_suppressed)

    def test_meal_truck_driver_mode_suppresses_barak(self) -> None:
        mission = self._mission()
        tech = SimpleNamespace(state="waiting_at_lz")

        sync_airport_runtime_flags(
            mission=mission,
            selected_mission_id="airport",
            airport_tech_state=tech,
            meal_truck_driver_mode=True,
            bus_driver_mode=False,
        )

        self.assertTrue(mission.engineer_remote_control_active)
        self.assertTrue(mission.player_driving_vehicle)
        self.assertTrue(mission.barak_suppressed)

    def test_non_airport_resets_flags(self) -> None:
        mission = self._mission()
        mission.engineer_remote_control_active = True
        mission.player_driving_vehicle = True
        mission.engineer_off_chopper = True
        mission.barak_suppressed = True

        sync_airport_runtime_flags(
            mission=mission,
            selected_mission_id="city",
            airport_tech_state=SimpleNamespace(state="waiting_at_lz"),
            meal_truck_driver_mode=True,
            bus_driver_mode=True,
        )

        self.assertFalse(mission.engineer_remote_control_active)
        self.assertFalse(mission.player_driving_vehicle)
        self.assertFalse(mission.engineer_off_chopper)
        self.assertFalse(mission.barak_suppressed)

    def test_entering_driver_mode_retires_active_barak_missiles(self) -> None:
        mission = self._mission()
        mission.projectiles = [
            SimpleNamespace(alive=True, is_barak_missile=True),
            SimpleNamespace(alive=True, is_barak_missile=False),
        ]

        sync_airport_runtime_flags(
            mission=mission,
            selected_mission_id="airport",
            airport_tech_state=SimpleNamespace(state="on_chopper"),
            meal_truck_driver_mode=False,
            bus_driver_mode=False,
        )
        self.assertTrue(mission.projectiles[0].alive)
        self.assertTrue(mission.projectiles[1].alive)

        sync_airport_runtime_flags(
            mission=mission,
            selected_mission_id="airport",
            airport_tech_state=SimpleNamespace(state="waiting_at_lz"),
            meal_truck_driver_mode=False,
            bus_driver_mode=True,
        )
        self.assertFalse(mission.projectiles[0].alive)
        self.assertTrue(mission.projectiles[1].alive)


if __name__ == "__main__":
    unittest.main()
