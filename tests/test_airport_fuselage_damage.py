from __future__ import annotations

from types import SimpleNamespace
import unittest

from src.choplifter.airport_fuselage import (
    FUSELAGE_DAMAGE_STAGE_HALF,
    FUSELAGE_DAMAGE_STAGE_INTACT,
    FUSELAGE_DAMAGE_STAGE_TOTAL,
    FUSELAGE_DAMAGE_THRESHOLD_HALF,
    FUSELAGE_DAMAGE_THRESHOLD_TOTAL,
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
    def test_damage_stage_advances_at_exact_damage_thresholds_and_is_monotonic(self) -> None:
        start_health = FUSELAGE_DAMAGE_THRESHOLD_TOTAL + 30.0
        mission = SimpleNamespace(
            mission_id="airport",
            compounds=[
                _make_compound(x=1000.0, y=220.0, health=start_health),
                _make_compound(x=1300.0, y=220.0, health=start_health),
                _make_compound(x=1500.0, y=340.0, health=start_health),
            ],
        )

        self.assertEqual(get_airport_fuselage_damage_stage(mission), FUSELAGE_DAMAGE_STAGE_INTACT)

        mission.compounds[0].health = start_health - (FUSELAGE_DAMAGE_THRESHOLD_HALF - 1.0)
        self.assertEqual(get_airport_fuselage_damage_stage(mission), FUSELAGE_DAMAGE_STAGE_INTACT)

        mission.compounds[0].health = start_health - FUSELAGE_DAMAGE_THRESHOLD_HALF
        self.assertEqual(get_airport_fuselage_damage_stage(mission), FUSELAGE_DAMAGE_STAGE_HALF)

        mission.compounds[0].health = start_health - (FUSELAGE_DAMAGE_THRESHOLD_TOTAL - 1.0)
        self.assertEqual(get_airport_fuselage_damage_stage(mission), FUSELAGE_DAMAGE_STAGE_HALF)

        mission.compounds[0].health = start_health - FUSELAGE_DAMAGE_THRESHOLD_TOTAL
        self.assertEqual(get_airport_fuselage_damage_stage(mission), FUSELAGE_DAMAGE_STAGE_TOTAL)

        mission.compounds[0].health = 128.0
        self.assertEqual(get_airport_fuselage_damage_stage(mission), FUSELAGE_DAMAGE_STAGE_TOTAL)

    def test_boarding_unlocks_only_at_total_damage_stage(self) -> None:
        start_health = FUSELAGE_DAMAGE_THRESHOLD_TOTAL + 30.0
        mission = SimpleNamespace(
            mission_id="airport",
            compounds=[
                _make_compound(x=1000.0, y=220.0, health=start_health),
                _make_compound(x=1300.0, y=220.0, health=start_health),
            ],
        )

        mission.compounds[0].health = start_health - FUSELAGE_DAMAGE_THRESHOLD_HALF
        self.assertFalse(is_airport_fuselage_boarding_unlocked(mission))

        mission.compounds[0].health = start_health - FUSELAGE_DAMAGE_THRESHOLD_TOTAL
        self.assertTrue(is_airport_fuselage_boarding_unlocked(mission))

    def test_open_fuselage_forces_visible_half_stage_before_total(self) -> None:
        mission = SimpleNamespace(
            mission_id="airport",
            elapsed_seconds=10.0,
            compounds=[
                _make_compound(x=1000.0, y=220.0, health=130.0, is_open=False),
                _make_compound(x=1300.0, y=220.0, health=130.0, is_open=False),
            ],
        )

        # Opening at low damage should still show half stage first.
        mission.compounds[0].health = 110.0
        mission.compounds[0].is_open = True
        self.assertEqual(get_airport_fuselage_damage_stage(mission), FUSELAGE_DAMAGE_STAGE_HALF)

        # During the hold window, stage remains half.
        mission.elapsed_seconds = 10.2
        self.assertEqual(get_airport_fuselage_damage_stage(mission), FUSELAGE_DAMAGE_STAGE_HALF)

        # After the hold window, open fuselage can advance to total stage.
        mission.elapsed_seconds = 10.9
        self.assertEqual(get_airport_fuselage_damage_stage(mission), FUSELAGE_DAMAGE_STAGE_TOTAL)

    def test_waiting_state_does_not_start_loading_until_stage_two(self) -> None:
        start_health = FUSELAGE_DAMAGE_THRESHOLD_TOTAL + 30.0
        mission = SimpleNamespace(
            mission_id="airport",
            enforce_fuselage_boarding_gate=True,
            compounds=[
                _make_compound(x=1000.0, y=220.0, health=start_health),
                _make_compound(x=1300.0, y=220.0, health=start_health),
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

        mission.compounds[0].health = start_health - FUSELAGE_DAMAGE_THRESHOLD_TOTAL
        mission.compounds[0].is_open = True
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

    def test_terminal_boarding_requires_terminal_compound_open(self) -> None:
        start_health = FUSELAGE_DAMAGE_THRESHOLD_TOTAL + 30.0
        mission = SimpleNamespace(
            mission_id="airport",
            enforce_fuselage_boarding_gate=True,
            compounds=[
                _make_compound(x=1000.0, y=220.0, health=start_health, is_open=False),
                _make_compound(x=1300.0, y=220.0, health=start_health, is_open=False),
            ],
            elapsed_seconds=10.0,
            airport_fuselage_damage_stage=FUSELAGE_DAMAGE_STAGE_TOTAL,
            airport_fuselage_max_health=start_health,
        )
        hostage_state = create_airport_hostage_state(total_hostages=4, pickup_points=[1000.0, 1300.0])
        hostage_state.terminal_remaining = [2, 2]
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

        mission.compounds[0].is_open = True
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

    def test_second_terminal_requires_its_own_compound_open(self) -> None:
        start_health = FUSELAGE_DAMAGE_THRESHOLD_TOTAL + 30.0
        mission = SimpleNamespace(
            mission_id="airport",
            enforce_fuselage_boarding_gate=True,
            compounds=[
                _make_compound(x=1000.0, y=220.0, health=start_health, is_open=True),
                _make_compound(x=1300.0, y=220.0, health=start_health, is_open=False),
            ],
            elapsed_seconds=10.0,
            airport_fuselage_damage_stage=FUSELAGE_DAMAGE_STAGE_TOTAL,
            airport_fuselage_max_health=start_health,
        )
        hostage_state = create_airport_hostage_state(total_hostages=4, pickup_points=[1000.0, 1300.0])
        hostage_state.terminal_remaining = [0, 2]
        bus_state = SimpleNamespace(x=1600.0, stop_x=500.0)
        helicopter = SimpleNamespace()
        meal_truck_state = SimpleNamespace(
            extension_progress=1.0,
            box_state="extended",
            x=1327.0,
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

        mission.compounds[1].is_open = True
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

    def test_unlock_beep_plays_once_per_terminal_when_terminal_opens(self) -> None:
        mission = SimpleNamespace(
            mission_id="airport",
            compounds=[
                _make_compound(x=1000.0, y=220.0, health=100.0, is_open=False),
                _make_compound(x=1300.0, y=220.0, health=100.0, is_open=False),
            ],
            elapsed_seconds=10.0,
        )
        hostage_state = create_airport_hostage_state(total_hostages=4, pickup_points=[1000.0, 1300.0])
        hostage_state.terminal_remaining = [2, 2]

        bus_state = SimpleNamespace(x=1600.0, stop_x=500.0)
        helicopter = SimpleNamespace()

        class _Audio:
            def __init__(self) -> None:
                self.bus_door_calls = 0

            def play_bus_door(self) -> None:
                self.bus_door_calls += 1

        audio = _Audio()

        hostage_state = update_airport_hostage_logic(
            hostage_state,
            0.016,
            bus_state=bus_state,
            helicopter=helicopter,
            mission=mission,
            audio=audio,
            meal_truck_state=None,
            tech_state=None,
        )
        self.assertEqual(audio.bus_door_calls, 0)

        mission.compounds[0].is_open = True
        hostage_state = update_airport_hostage_logic(
            hostage_state,
            0.016,
            bus_state=bus_state,
            helicopter=helicopter,
            mission=mission,
            audio=audio,
            meal_truck_state=None,
            tech_state=None,
        )
        self.assertEqual(audio.bus_door_calls, 1)

        mission.compounds[1].is_open = True
        hostage_state = update_airport_hostage_logic(
            hostage_state,
            0.016,
            bus_state=bus_state,
            helicopter=helicopter,
            mission=mission,
            audio=audio,
            meal_truck_state=None,
            tech_state=None,
        )
        self.assertEqual(audio.bus_door_calls, 2)

        hostage_state = update_airport_hostage_logic(
            hostage_state,
            0.016,
            bus_state=bus_state,
            helicopter=helicopter,
            mission=mission,
            audio=audio,
            meal_truck_state=None,
            tech_state=None,
        )
        self.assertEqual(audio.bus_door_calls, 2)


if __name__ == "__main__":
    unittest.main()
