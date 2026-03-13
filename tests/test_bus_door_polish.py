from __future__ import annotations

import unittest
import pytest

from src.choplifter.bus_ai import (
    BusState,
    _bus_door_open_blend,
    close_bus_doors,
    open_bus_doors,
    update_bus_ai,
)


pytestmark = pytest.mark.airport_smoke


class BusDoorPolishTests(unittest.TestCase):
    def test_opening_and_closing_blend_weights(self) -> None:
        bus = BusState(x=800.0, y=400.0)

        open_bus_doors(bus)
        self.assertEqual(bus.door_state, "opening")
        self.assertAlmostEqual(_bus_door_open_blend(bus), 0.0, places=3)

        bus = update_bus_ai(bus, 0.15, mission_phase="waiting_for_tech_deploy", tech_on_bus=False)
        self.assertEqual(bus.door_state, "opening")
        self.assertGreater(_bus_door_open_blend(bus), 0.0)
        self.assertLess(_bus_door_open_blend(bus), 1.0)

        bus = update_bus_ai(bus, 0.20, mission_phase="waiting_for_tech_deploy", tech_on_bus=False)
        self.assertEqual(bus.door_state, "open")
        self.assertAlmostEqual(_bus_door_open_blend(bus), 1.0, places=3)

        close_bus_doors(bus)
        self.assertEqual(bus.door_state, "closing")
        self.assertAlmostEqual(_bus_door_open_blend(bus), 1.0, places=3)

        bus = update_bus_ai(bus, 0.30, mission_phase="waiting_for_tech_deploy", tech_on_bus=False)
        self.assertEqual(bus.door_state, "closed")
        self.assertAlmostEqual(_bus_door_open_blend(bus), 0.0, places=3)

    def test_open_with_auto_close_delay_recloses(self) -> None:
        bus = BusState(x=800.0, y=400.0)

        open_bus_doors(bus, auto_close_delay_s=0.2)
        bus = update_bus_ai(bus, 0.31, mission_phase="waiting_for_tech_deploy", tech_on_bus=False)
        self.assertEqual(bus.door_state, "open")

        bus = update_bus_ai(bus, 0.21, mission_phase="waiting_for_tech_deploy", tech_on_bus=False)
        self.assertEqual(bus.door_state, "closing")

        bus = update_bus_ai(bus, 0.31, mission_phase="waiting_for_tech_deploy", tech_on_bus=False)
        self.assertEqual(bus.door_state, "closed")


if __name__ == "__main__":
    unittest.main()
