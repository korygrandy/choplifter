from __future__ import annotations

from types import SimpleNamespace
import unittest
import pytest

from src.choplifter.game_types import HostageState
from src.choplifter.helicopter import Facing
from src.choplifter.mission_hostages import _handle_unload, _update_hostages
from src.choplifter.settings import HelicopterSettings


pytestmark = pytest.mark.airport_smoke


def _hostage(*, x: float, y: float) -> SimpleNamespace:
    return SimpleNamespace(
        state=HostageState.WAITING,
        pos=SimpleNamespace(x=x, y=y),
        move_speed=0.0,
        saved_slot=-1,
    )


def _boarded_hostage(*, x: float, y: float) -> SimpleNamespace:
    return SimpleNamespace(
        state=HostageState.BOARDED,
        pos=SimpleNamespace(x=x, y=y),
        move_speed=0.0,
        saved_slot=-1,
    )


def _mission(*, mission_id: str, tech_state_name: str) -> SimpleNamespace:
    return SimpleNamespace(
        mission_id=mission_id,
        mission_tech=SimpleNamespace(state=tech_state_name),
        hostages=[_hostage(x=10.0, y=200.0)],
        elapsed_seconds=0.0,
        doors_open_maxvel_timer=0.0,
        next_fall_time=9999.0,
        tuning=SimpleNamespace(
            hostage_boarding_radius=58.0,
            hostage_controlled_move_speed=65.0,
            hostage_controlled_max_moving_to_lz=4,
            hostage_chaotic_move_speed=90.0,
            hostage_chaotic_max_moving_to_lz=8,
            hostage_chaos_probability=0.0,
            hostage_chaotic_start_radius=320.0,
            hostage_controlled_start_radius=240.0,
        ),
        stats=SimpleNamespace(lost_in_transit=0, saved=0),
        base=SimpleNamespace(pos=SimpleNamespace(x=0.0, y=0.0), width=200.0),
    )


class AirportTechBoardingGateTests(unittest.TestCase):
    def test_airport_blocks_lower_boarding_when_tech_not_on_chopper(self) -> None:
        mission = _mission(mission_id="airport", tech_state_name="waiting_at_lz")
        helicopter = SimpleNamespace(pos=SimpleNamespace(x=0.0, y=0.0), grounded=True, doors_open=True)

        _update_hostages(
            mission,
            helicopter,
            0.016,
            HelicopterSettings(),
            boarded_count_fn=lambda m: 0,
        )

        self.assertEqual(mission.hostages[0].state, HostageState.WAITING)

    def test_airport_allows_lower_boarding_when_tech_on_chopper(self) -> None:
        mission = _mission(mission_id="airport", tech_state_name="on_chopper")
        helicopter = SimpleNamespace(pos=SimpleNamespace(x=0.0, y=0.0), grounded=True, doors_open=True)

        _update_hostages(
            mission,
            helicopter,
            0.016,
            HelicopterSettings(),
            boarded_count_fn=lambda m: 0,
        )

        self.assertEqual(mission.hostages[0].state, HostageState.MOVING_TO_LZ)

    def test_non_airport_mission_ignores_tech_gate(self) -> None:
        mission = _mission(mission_id="city", tech_state_name="waiting_at_lz")
        helicopter = SimpleNamespace(pos=SimpleNamespace(x=0.0, y=0.0), grounded=True, doors_open=True)

        _update_hostages(
            mission,
            helicopter,
            0.016,
            HelicopterSettings(),
            boarded_count_fn=lambda m: 0,
        )

        self.assertEqual(mission.hostages[0].state, HostageState.MOVING_TO_LZ)

    def test_airport_gate_records_tech_not_on_chopper_failure_reason(self) -> None:
        mission = _mission(mission_id="airport", tech_state_name="waiting_at_lz")
        helicopter = SimpleNamespace(pos=SimpleNamespace(x=0.0, y=0.0), grounded=True, doors_open=True)

        _update_hostages(
            mission,
            helicopter,
            0.016,
            HelicopterSettings(),
            boarded_count_fn=lambda m: 0,
        )

        counters = getattr(mission, "boarding_failure_counts", {})
        self.assertGreaterEqual(int(counters.get("tech_not_on_chopper", 0)), 1)

    def test_hostages_do_not_fall_before_two_to_three_second_grace(self) -> None:
        mission = _mission(mission_id="city", tech_state_name="on_chopper")
        mission.hostages = [_boarded_hostage(x=10.0, y=200.0)]
        mission._prev_fall_eligible = True
        mission._hostage_fall_delay_s = 2.8
        mission.doors_open_maxvel_timer = 2.4
        mission.next_fall_time = 0.0
        helicopter = SimpleNamespace(pos=SimpleNamespace(x=0.0, y=120.0), grounded=False, doors_open=True)

        mission.elapsed_seconds = 2.5
        _update_hostages(
            mission,
            helicopter,
            0.1,
            HelicopterSettings(),
            boarded_count_fn=lambda m: 1,
        )

        self.assertEqual(mission.hostages[0].state, HostageState.BOARDED)
        self.assertEqual(mission.stats.lost_in_transit, 0)

    def test_hostages_fall_after_grace_window_expires(self) -> None:
        mission = _mission(mission_id="city", tech_state_name="on_chopper")
        mission.hostages = [_boarded_hostage(x=10.0, y=200.0)]
        mission._prev_fall_eligible = True
        mission._hostage_fall_delay_s = 2.1
        mission.doors_open_maxvel_timer = 2.1
        mission.next_fall_time = 0.0
        helicopter = SimpleNamespace(pos=SimpleNamespace(x=0.0, y=120.0), grounded=False, doors_open=True)

        mission.elapsed_seconds = 2.2
        _update_hostages(
            mission,
            helicopter,
            0.05,
            HelicopterSettings(),
            boarded_count_fn=lambda m: 1,
        )

        self.assertEqual(mission.hostages[0].state, HostageState.FALLING)
        self.assertEqual(mission.stats.lost_in_transit, 1)

    def test_airport_blocks_lower_rescue_completion_when_upper_compounds_still_have_passengers(self) -> None:
        mission = _mission(mission_id="airport", tech_state_name="on_chopper")
        mission.hostages = [_boarded_hostage(x=10.0, y=200.0)]
        mission.airport_hostage_state = SimpleNamespace(terminal_remaining=[2, 0])
        mission.airport_bus_state = SimpleNamespace(stop_x=500.0)
        mission.base = SimpleNamespace(pos=SimpleNamespace(x=0.0, y=0.0), width=200.0, contains_point=lambda _p: False)
        mission.unload_release_seconds = 0.0
        mission.next_saved_slot = 0
        helicopter = SimpleNamespace(
            pos=SimpleNamespace(x=450.0, y=0.0),
            grounded=True,
            doors_open=True,
            facing=Facing.RIGHT,
        )

        _handle_unload(mission, helicopter, HelicopterSettings(), 0.25)

        self.assertEqual(mission.hostages[0].state, HostageState.BOARDED)
        self.assertEqual(mission.stats.saved, 0)

    def test_airport_blocks_lower_rescue_completion_when_tech_not_on_chopper(self) -> None:
        mission = _mission(mission_id="airport", tech_state_name="waiting_at_lz")
        mission.hostages = [_boarded_hostage(x=10.0, y=200.0)]
        mission.airport_hostage_state = SimpleNamespace(terminal_remaining=[0, 0])
        mission.airport_bus_state = SimpleNamespace(stop_x=500.0)
        mission.base = SimpleNamespace(pos=SimpleNamespace(x=0.0, y=0.0), width=200.0, contains_point=lambda _p: False)
        mission.unload_release_seconds = 0.0
        mission.next_saved_slot = 0
        helicopter = SimpleNamespace(
            pos=SimpleNamespace(x=450.0, y=0.0),
            grounded=True,
            doors_open=True,
            facing=Facing.RIGHT,
        )

        _handle_unload(mission, helicopter, HelicopterSettings(), 0.25)

        self.assertEqual(mission.hostages[0].state, HostageState.BOARDED)
        self.assertEqual(mission.stats.saved, 0)

    def test_airport_allows_lower_rescue_completion_when_upper_empty_and_tech_on_chopper(self) -> None:
        mission = _mission(mission_id="airport", tech_state_name="on_chopper")
        mission.hostages = [_boarded_hostage(x=10.0, y=200.0)]
        mission.airport_hostage_state = SimpleNamespace(terminal_remaining=[0, 0])
        mission.airport_bus_state = SimpleNamespace(stop_x=500.0)
        mission.base = SimpleNamespace(pos=SimpleNamespace(x=0.0, y=0.0), width=200.0, contains_point=lambda _p: False)
        mission.unload_release_seconds = 0.0
        mission.next_saved_slot = 0
        helicopter = SimpleNamespace(
            pos=SimpleNamespace(x=450.0, y=0.0),
            grounded=True,
            doors_open=True,
            facing=Facing.RIGHT,
        )

        _handle_unload(mission, helicopter, HelicopterSettings(), 0.25)

        self.assertEqual(mission.hostages[0].state, HostageState.EXITING)


if __name__ == "__main__":
    unittest.main()
