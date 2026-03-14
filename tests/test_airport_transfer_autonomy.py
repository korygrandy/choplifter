from __future__ import annotations

from types import SimpleNamespace
import unittest
import pytest

from src.choplifter.vehicle_assets import AirportMealTruckState, update_airport_meal_truck


pytestmark = pytest.mark.airport_smoke


class AirportTransferAutonomyTests(unittest.TestCase):
    def test_meal_truck_autonomously_returns_toward_bus_during_transferring(self) -> None:
        truck = AirportMealTruckState(
            x=1500.0,
            y=210.0,
            plane_lz_x=1500.0,
            speed_px_per_s=80.0,
            tech_has_deployed=True,
            at_plane_lz=True,
        )
        tech_state = SimpleNamespace(state="transferring")
        bus_state = SimpleNamespace(x=1100.0, y=210.0)

        updated = update_airport_meal_truck(
            truck,
            1.0,
            tech_state=tech_state,
            bus_state=bus_state,
        )

        self.assertLess(updated.x, 1500.0)
        self.assertFalse(updated.facing_right)

    def test_truck_deployment_flag_clears_when_tech_is_back_on_chopper(self) -> None:
        truck = AirportMealTruckState(
            x=1400.0,
            y=210.0,
            plane_lz_x=1500.0,
            speed_px_per_s=80.0,
            tech_has_deployed=True,
        )
        tech_state = SimpleNamespace(state="on_chopper")
        bus_state = SimpleNamespace(x=1100.0, y=210.0)

        updated = update_airport_meal_truck(
            truck,
            1.0,
            tech_state=tech_state,
            bus_state=bus_state,
        )

        self.assertFalse(updated.tech_has_deployed)
        self.assertEqual(updated.x, 1400.0)


if __name__ == "__main__":
    unittest.main()
