from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch
import pytest

from src.choplifter.app.airport_tick import update_airport_mission_tick


pytestmark = pytest.mark.airport_smoke


class AirportTickEscortToastTests(unittest.TestCase):
    def test_shows_escort_attack_toast_once_when_tech_led_bus_escort_begins(self) -> None:
        bus_state = SimpleNamespace(x=500.0, y=0.0, stop_x=500.0, is_moving=True)
        hostage_state = SimpleNamespace(
            state="boarded",
            terminal_remaining=[0, 0],
            rescued_hostages=0,
            pickup_x=1500.0,
            interrupted_transfers=0,
        )
        tech_state = SimpleNamespace(state="transfer_complete", on_bus=True, is_deployed=True)
        meal_truck_state = SimpleNamespace(x=1200.0, plane_lz_x=1500.0, extension_progress=0.0)
        enemy_state = SimpleNamespace()
        objective_state = SimpleNamespace(mission_phase="escort_to_lz", status_text="Escort bus to tower LZ")
        cutscene_state = SimpleNamespace()

        mission = SimpleNamespace(
            ended=False,
            tuning=SimpleNamespace(),
            world_width=2800.0,
            stats=SimpleNamespace(saved=0),
        )
        heli_settings = SimpleNamespace(ground_y=320.0)
        helicopter = SimpleNamespace(pos=SimpleNamespace(x=0.0, y=0.0))
        audio = SimpleNamespace()

        toast_messages: list[str] = []

        with (
            patch("src.choplifter.app.airport_tick.update_bus_ai", side_effect=lambda state, *_a, **_k: state),
            patch("src.choplifter.app.airport_tick.update_airport_hostage_logic", side_effect=lambda state, *_a, **_k: state),
            patch("src.choplifter.app.airport_tick.apply_airport_bus_door_transitions"),
            patch("src.choplifter.app.airport_tick.update_mission_tech", side_effect=lambda state, *_a, **_k: state),
            patch("src.choplifter.app.airport_tick.check_tech_lz_door_toast"),
            patch("src.choplifter.app.airport_tick.update_airport_meal_truck", side_effect=lambda state, *_a, **_k: state),
            patch("src.choplifter.app.airport_tick.check_airport_truck_retract_toast"),
            patch("src.choplifter.app.airport_tick.get_airport_priority_target_x", return_value=500.0),
            patch("src.choplifter.app.airport_tick.update_airport_enemy_spawns", side_effect=lambda state, *_a, **_k: state),
            patch("src.choplifter.app.airport_tick.apply_airport_bus_friendly_fire", return_value=0),
            patch("src.choplifter.app.airport_tick.update_airport_objectives", side_effect=lambda state, *_a, **_k: state),
            patch("src.choplifter.app.airport_tick.update_airport_cutscene_state", side_effect=lambda state, *_a, **_k: state),
            patch("src.choplifter.app.airport_tick._end_mission"),
        ):
            update_airport_mission_tick(
                bus_state=bus_state,
                hostage_state=hostage_state,
                tech_state=tech_state,
                meal_truck_state=meal_truck_state,
                enemy_state=enemy_state,
                objective_state=objective_state,
                cutscene_state=cutscene_state,
                dt=0.016,
                audio=audio,
                helicopter=helicopter,
                mission=mission,
                heli_settings=heli_settings,
                bus_driver_input=0.0,
                bus_driver_mode=False,
                truck_driver_input=0.0,
                meal_truck_driver_mode=False,
                meal_truck_lift_command_extended=False,
                set_toast=lambda msg: toast_messages.append(str(msg)),
                logger=None,
                airport_total_rescue_target=99,
            )
            update_airport_mission_tick(
                bus_state=bus_state,
                hostage_state=hostage_state,
                tech_state=tech_state,
                meal_truck_state=meal_truck_state,
                enemy_state=enemy_state,
                objective_state=objective_state,
                cutscene_state=cutscene_state,
                dt=0.016,
                audio=audio,
                helicopter=helicopter,
                mission=mission,
                heli_settings=heli_settings,
                bus_driver_input=0.0,
                bus_driver_mode=False,
                truck_driver_input=0.0,
                meal_truck_driver_mode=False,
                meal_truck_lift_command_extended=False,
                set_toast=lambda msg: toast_messages.append(str(msg)),
                logger=None,
                airport_total_rescue_target=99,
            )

        self.assertEqual(len(toast_messages), 1)
        self.assertEqual(
            toast_messages[0],
            "Escort under attack: fend off drones, minesweepers, and raider mines",
        )


if __name__ == "__main__":
    unittest.main()
