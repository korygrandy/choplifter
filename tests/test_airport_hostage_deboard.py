from __future__ import annotations

from types import SimpleNamespace
import unittest

from src.choplifter.hostage_logic import AirportHostageState, update_airport_hostage_logic


class AirportHostageDeboardTests(unittest.TestCase):
    def test_boarded_passengers_deboard_when_bus_enters_tower_lz_even_if_moving(self) -> None:
        hostage_state = AirportHostageState(
            total_hostages=4,
            boarded_hostages=3,
            rescued_hostages=0,
            state="boarded",
        )
        bus_state = SimpleNamespace(x=620.0, stop_x=500.0, is_moving=True)
        helicopter = SimpleNamespace(pos=SimpleNamespace(x=0.0, y=0.0))
        mission = SimpleNamespace(elapsed_seconds=42.0)

        out = update_airport_hostage_logic(
            hostage_state,
            0.016,
            bus_state=bus_state,
            helicopter=helicopter,
            mission=mission,
            audio=None,
            meal_truck_state=None,
            tech_state=None,
        )

        self.assertEqual(out.state, "rescued")
        self.assertEqual(out.rescued_hostages, 3)
        self.assertEqual(out.boarded_hostages, 0)


if __name__ == "__main__":
    unittest.main()
