from __future__ import annotations

from types import SimpleNamespace
import unittest
import pytest

from src.choplifter.game_types import HostageState
from src.choplifter.render.world import _compound_has_awaiting_passengers


pytestmark = pytest.mark.airport_smoke
class AirportLowerCompoundWindowLightingTests(unittest.TestCase):
    def test_detects_waiting_passengers_as_awaiting(self) -> None:
        mission = SimpleNamespace(hostages=[SimpleNamespace(state=HostageState.IDLE), SimpleNamespace(state=HostageState.SAVED)])
        compound = SimpleNamespace(hostage_start=0, hostage_count=2)

        self.assertTrue(_compound_has_awaiting_passengers(mission, compound))

    def test_detects_no_awaiting_passengers_when_all_saved_or_kia(self) -> None:
        mission = SimpleNamespace(hostages=[SimpleNamespace(state=HostageState.SAVED), SimpleNamespace(state=HostageState.KIA)])
        compound = SimpleNamespace(hostage_start=0, hostage_count=2)

        self.assertFalse(_compound_has_awaiting_passengers(mission, compound))

    def test_boarded_or_exiting_passengers_no_longer_keep_lower_compound_lit(self) -> None:
        mission = SimpleNamespace(
            hostages=[
                SimpleNamespace(state=HostageState.BOARDED),
                SimpleNamespace(state=HostageState.EXITING),
                SimpleNamespace(state=HostageState.SAVED),
            ]
        )
        compound = SimpleNamespace(hostage_start=0, hostage_count=3)

        self.assertFalse(_compound_has_awaiting_passengers(mission, compound))


if __name__ == "__main__":
    unittest.main()
