from __future__ import annotations

from types import SimpleNamespace
import unittest
import pytest

from src.choplifter.app.bus_door_flow import apply_airport_bus_door_transitions
from src.choplifter.bus_ai import BusState, update_bus_ai


pytestmark = pytest.mark.airport_smoke


class BusDoorFlowTests(unittest.TestCase):
    def test_truck_driving_to_bus_plays_start_and_stop_audio_on_phase_change(self) -> None:
        bus = BusState(x=800.0, y=400.0)

        class _Audio:
            def __init__(self) -> None:
                self.accel_calls = 0
                self.brake_calls = 0

            def play_bus_accelerate(self) -> None:
                self.accel_calls += 1

            def play_bus_brakes(self) -> None:
                self.brake_calls += 1

        audio = _Audio()

        bus = update_bus_ai(bus, 0.05, audio=audio, mission_phase="truck_driving_to_bus", tech_on_bus=False)
        self.assertGreaterEqual(audio.accel_calls, 1)
        self.assertTrue(bus.is_moving)

        bus = update_bus_ai(bus, 0.05, audio=audio, mission_phase="waiting_for_tech_deploy", tech_on_bus=False)
        self.assertGreaterEqual(audio.brake_calls, 1)
        self.assertFalse(bus.is_moving)

    def test_boarding_then_deboarding_transitions(self) -> None:
        bus = BusState(x=600.0, y=400.0)
        audio = SimpleNamespace(play_bus_door=lambda: None)

        apply_airport_bus_door_transitions(
            bus_state=bus,
            audio=audio,
            prev_hostage_state="truck_loaded",
            new_hostage_state="transferring_to_bus",
        )
        self.assertEqual(bus.door_state, "opening")

        bus = update_bus_ai(bus, 0.31, mission_phase="truck_driving_to_bus", tech_on_bus=False)
        self.assertEqual(bus.door_state, "open")

        apply_airport_bus_door_transitions(
            bus_state=bus,
            audio=audio,
            prev_hostage_state="transferring_to_bus",
            new_hostage_state="boarded",
        )
        self.assertEqual(bus.door_state, "closing")

        bus = update_bus_ai(bus, 0.31, mission_phase="escort_to_lz", tech_on_bus=True)
        self.assertEqual(bus.door_state, "closed")

        apply_airport_bus_door_transitions(
            bus_state=bus,
            audio=audio,
            prev_hostage_state="boarded",
            new_hostage_state="rescued",
        )
        self.assertEqual(bus.door_state, "opening")

    def test_no_transition_no_door_change(self) -> None:
        bus = BusState(x=600.0, y=400.0)
        audio = SimpleNamespace(play_bus_door=lambda: None)

        apply_airport_bus_door_transitions(
            bus_state=bus,
            audio=audio,
            prev_hostage_state="transferring_to_bus",
            new_hostage_state="transferring_to_bus",
        )
        self.assertEqual(bus.door_state, "closed")


if __name__ == "__main__":
    unittest.main()
