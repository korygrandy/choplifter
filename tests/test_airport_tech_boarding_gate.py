from __future__ import annotations

from types import SimpleNamespace
import unittest
import pytest

from src.choplifter.game_types import HostageState
from src.choplifter.mission_hostages import _update_hostages
from src.choplifter.settings import HelicopterSettings


pytestmark = pytest.mark.airport_smoke


def _hostage(*, x: float, y: float) -> SimpleNamespace:
    return SimpleNamespace(
        state=HostageState.WAITING,
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


if __name__ == "__main__":
    unittest.main()
