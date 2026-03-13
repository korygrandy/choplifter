from __future__ import annotations

from types import SimpleNamespace
import unittest
import pytest

from src.choplifter.app.airport_tick import _has_remaining_elevated_passengers, _should_fail_for_tech_kia


pytestmark = pytest.mark.airport_smoke


class AirportTechKiaFailureTests(unittest.TestCase):
    def test_detects_remaining_elevated_passengers(self) -> None:
        hostage_state = SimpleNamespace(terminal_remaining=[0, 2])

        self.assertTrue(_has_remaining_elevated_passengers(hostage_state))

    def test_kia_fails_when_elevated_passengers_remain(self) -> None:
        tech_state = SimpleNamespace(state="kia")
        hostage_state = SimpleNamespace(terminal_remaining=[1, 0])

        self.assertTrue(_should_fail_for_tech_kia(tech_state=tech_state, hostage_state=hostage_state))

    def test_kia_does_not_fail_when_elevated_passengers_cleared(self) -> None:
        tech_state = SimpleNamespace(state="kia")
        hostage_state = SimpleNamespace(terminal_remaining=[0, 0])

        self.assertFalse(_should_fail_for_tech_kia(tech_state=tech_state, hostage_state=hostage_state))


if __name__ == "__main__":
    unittest.main()
