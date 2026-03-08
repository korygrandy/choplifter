from __future__ import annotations

from types import SimpleNamespace
import unittest

from src.choplifter.app.boarding_status import compute_boarding_ux_status
from src.choplifter.game_types import HostageState


def _hostage(*, state: HostageState, x: float, y: float) -> object:
    return SimpleNamespace(state=state, pos=SimpleNamespace(x=x, y=y))


class BoardingUxStatusTests(unittest.TestCase):
    def test_blocked_when_not_grounded_and_no_nearby_hostages(self) -> None:
        mission = SimpleNamespace(hostages=[])
        helicopter = SimpleNamespace(pos=SimpleNamespace(x=0.0, y=0.0), grounded=False, doors_open=True)

        status = compute_boarding_ux_status(mission, helicopter)

        self.assertEqual(status.state, "blocked")
        self.assertEqual(status.detail, "LAND")

    def test_approaching_when_hostages_near_but_not_ready_to_board(self) -> None:
        mission = SimpleNamespace(
            hostages=[
                _hostage(state=HostageState.WAITING, x=25.0, y=20.0),
            ]
        )
        helicopter = SimpleNamespace(pos=SimpleNamespace(x=0.0, y=0.0), grounded=False, doors_open=False)

        status = compute_boarding_ux_status(mission, helicopter)

        self.assertEqual(status.state, "approaching")
        self.assertEqual(status.detail, "HOSTAGES IN RANGE")

    def test_boarding_when_grounded_doors_open_and_hostages_near(self) -> None:
        mission = SimpleNamespace(
            hostages=[
                _hostage(state=HostageState.WAITING, x=20.0, y=15.0),
            ]
        )
        helicopter = SimpleNamespace(pos=SimpleNamespace(x=0.0, y=0.0), grounded=True, doors_open=True)

        status = compute_boarding_ux_status(mission, helicopter)

        self.assertEqual(status.state, "boarding")
        self.assertEqual(status.detail, "READY")

    def test_boarded_when_passengers_onboard_and_not_actively_boarding(self) -> None:
        mission = SimpleNamespace(
            hostages=[
                _hostage(state=HostageState.BOARDED, x=-9999.0, y=-9999.0),
            ]
        )
        helicopter = SimpleNamespace(pos=SimpleNamespace(x=0.0, y=0.0), grounded=False, doors_open=False)

        status = compute_boarding_ux_status(mission, helicopter)

        self.assertEqual(status.state, "boarded")
        self.assertEqual(status.detail, "PASSENGERS ONBOARD")

    def test_blocked_full_overrides_other_states(self) -> None:
        mission = SimpleNamespace(
            hostages=[
                _hostage(state=HostageState.BOARDED, x=-9999.0, y=-9999.0)
                for _ in range(16)
            ]
        )
        helicopter = SimpleNamespace(pos=SimpleNamespace(x=0.0, y=0.0), grounded=True, doors_open=True)

        status = compute_boarding_ux_status(mission, helicopter)

        self.assertEqual(status.state, "blocked")
        self.assertEqual(status.detail, "FULL")


if __name__ == "__main__":
    unittest.main()
