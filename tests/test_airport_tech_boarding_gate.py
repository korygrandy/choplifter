from __future__ import annotations

from types import SimpleNamespace
import unittest
import pytest

from src.choplifter.game_types import HostageState
from src.choplifter.helicopter import Facing
from src.choplifter.mission_hostages import _handle_unload, _update_hostages
from src.choplifter.mission_tech import MissionTechState, update_mission_tech
from src.choplifter.settings import HelicopterSettings
from src.choplifter.vehicle_assets import AirportMealTruckState, update_airport_meal_truck


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

    def test_airport_allows_lower_rescue_completion_even_when_upper_compounds_still_have_passengers(self) -> None:
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

        self.assertEqual(mission.hostages[0].state, HostageState.EXITING)

    def test_airport_allows_lower_rescue_completion_when_tech_not_on_chopper(self) -> None:
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

        self.assertEqual(mission.hostages[0].state, HostageState.EXITING)

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

    def test_tower_reboard_sequence_clears_truck_and_reenables_lower_boarding(self) -> None:
        mission = _mission(mission_id="airport", tech_state_name="waiting_at_lz")
        mission.hostages = [_hostage(x=10.0, y=200.0)]

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
        bus_state = SimpleNamespace(door_state="open", door_animation_progress=0.5, x=1100.0, y=210.0)

        updated_tech = update_mission_tech(
            tech_state,
            0.016,
            helicopter=helicopter,
            bus_state=bus_state,
        )
        self.assertEqual(updated_tech.state, "on_chopper")

        truck = AirportMealTruckState(
            x=1400.0,
            y=210.0,
            plane_lz_x=1500.0,
            speed_px_per_s=80.0,
            tech_has_deployed=True,
        )
        updated_truck = update_airport_meal_truck(
            truck,
            1.0,
            tech_state=updated_tech,
            bus_state=bus_state,
        )
        self.assertFalse(updated_truck.tech_has_deployed)
        self.assertEqual(updated_truck.x, 1400.0)

        mission.mission_tech = updated_tech
        lower_lane_helicopter = SimpleNamespace(
            grounded=True,
            doors_open=True,
            pos=SimpleNamespace(x=0.0, y=0.0),
        )
        _update_hostages(
            mission,
            lower_lane_helicopter,
            0.016,
            HelicopterSettings(),
            boarded_count_fn=lambda m: 0,
        )

        self.assertEqual(mission.hostages[0].state, HostageState.MOVING_TO_LZ)

    def test_lower_boarding_is_singleton_not_instant_batch(self) -> None:
        mission = _mission(mission_id="airport", tech_state_name="on_chopper")
        mission.tuning.hostage_boarding_cadence_s = 0.30
        helicopter = SimpleNamespace(pos=SimpleNamespace(x=100.0, y=606.0), grounded=True, doors_open=True)

        mission.hostages = [
            SimpleNamespace(
                state=HostageState.MOVING_TO_LZ,
                pos=SimpleNamespace(x=100.0, y=612.0),
                move_speed=0.0,
                saved_slot=-1,
            ),
            SimpleNamespace(
                state=HostageState.MOVING_TO_LZ,
                pos=SimpleNamespace(x=100.0, y=612.0),
                move_speed=0.0,
                saved_slot=-1,
            ),
            SimpleNamespace(
                state=HostageState.MOVING_TO_LZ,
                pos=SimpleNamespace(x=100.0, y=612.0),
                move_speed=0.0,
                saved_slot=-1,
            ),
        ]

        boarded_count = lambda m: sum(1 for h in m.hostages if h.state is HostageState.BOARDED)

        _update_hostages(mission, helicopter, 0.016, HelicopterSettings(), boarded_count_fn=boarded_count)
        self.assertEqual(boarded_count(mission), 1)

        # Cooldown active, so a second immediate tick should not board another.
        _update_hostages(mission, helicopter, 0.016, HelicopterSettings(), boarded_count_fn=boarded_count)
        self.assertEqual(boarded_count(mission), 1)

        # After cadence interval elapses, next hostage boards.
        _update_hostages(mission, helicopter, 0.35, HelicopterSettings(), boarded_count_fn=boarded_count)
        self.assertEqual(boarded_count(mission), 2)


if __name__ == "__main__":
    unittest.main()
