from __future__ import annotations

from types import SimpleNamespace
import unittest

from src.choplifter.airport_fuselage import (
    FUSELAGE_DAMAGE_STAGE_HALF,
    FUSELAGE_DAMAGE_STAGE_INTACT,
    FUSELAGE_DAMAGE_STAGE_TOTAL,
    get_airport_fuselage_damage_stage,
    is_airport_fuselage_boarding_unlocked,
)
from src.choplifter.hostage_logic import create_airport_hostage_state, update_airport_hostage_logic


def _make_compound(*, x: float, y: float, health: float, is_open: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        pos=SimpleNamespace(x=float(x), y=float(y)),
        width=90.0,
        height=60.0,
        health=float(health),
        is_open=bool(is_open),
    )


class AirportFuselageDamageTests(unittest.TestCase):
    def test_damage_stage_advances_by_health_ratio_and_is_monotonic(self) -> None:
        mission = SimpleNamespace(
            mission_id="airport",
            compounds=[
                _make_compound(x=1000.0, y=220.0, health=130.0),
                _make_compound(x=1300.0, y=220.0, health=130.0),
                _make_compound(x=1500.0, y=340.0, health=130.0),
            ],
        )

        self.assertEqual(get_airport_fuselage_damage_stage(mission), FUSELAGE_DAMAGE_STAGE_INTACT)

        mission.compounds[0].health = 80.0
        self.assertEqual(get_airport_fuselage_damage_stage(mission), FUSELAGE_DAMAGE_STAGE_HALF)

        mission.compounds[0].health = 20.0
        self.assertEqual(get_airport_fuselage_damage_stage(mission), FUSELAGE_DAMAGE_STAGE_TOTAL)

        mission.compounds[0].health = 120.0
        self.assertEqual(get_airport_fuselage_damage_stage(mission), FUSELAGE_DAMAGE_STAGE_TOTAL)

    def test_boarding_unlocks_only_at_total_damage_stage(self) -> None:
        mission = SimpleNamespace(
            mission_id="airport",
            compounds=[
                _make_compound(x=1000.0, y=220.0, health=130.0),
                _make_compound(x=1300.0, y=220.0, health=130.0),
            ],
        )

        mission.compounds[0].health = 75.0
        self.assertFalse(is_airport_fuselage_boarding_unlocked(mission))

        mission.compounds[0].health = 20.0
        self.assertTrue(is_airport_fuselage_boarding_unlocked(mission))

    def test_waiting_state_does_not_start_loading_until_stage_two(self) -> None:
        mission = SimpleNamespace(
            mission_id="airport",
            compounds=[
                _make_compound(x=1000.0, y=220.0, health=130.0),
                _make_compound(x=1300.0, y=220.0, health=130.0),
            ],
            elapsed_seconds=10.0,
        )
        hostage_state = create_airport_hostage_state(total_hostages=4, pickup_points=[1000.0])
        bus_state = SimpleNamespace(x=1600.0, stop_x=500.0)
        helicopter = SimpleNamespace()
        meal_truck_state = SimpleNamespace(
            extension_progress=1.0,
            box_state="extended",
            x=1027.0,
            tech_has_deployed=False,
        )
        tech_state = SimpleNamespace(is_deployed=True)

        hostage_state = update_airport_hostage_logic(
            hostage_state,
            0.016,
            bus_state=bus_state,
            helicopter=helicopter,
            mission=mission,
            audio=None,
            meal_truck_state=meal_truck_state,
            tech_state=tech_state,
        )
        self.assertEqual(hostage_state.state, "waiting")

        mission.compounds[0].health = 20.0
        mission.elapsed_seconds = 11.0
        hostage_state = update_airport_hostage_logic(
            hostage_state,
            0.016,
            bus_state=bus_state,
            helicopter=helicopter,
            mission=mission,
            audio=None,
            meal_truck_state=meal_truck_state,
            tech_state=tech_state,
        )
        self.assertEqual(hostage_state.state, "truck_loading")


if __name__ == "__main__":
    unittest.main()
