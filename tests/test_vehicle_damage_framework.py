from __future__ import annotations

from types import SimpleNamespace
import unittest

from src.choplifter.vehicle_damage import apply_vehicle_damage, is_airport_bus_vulnerable, update_vehicle_damage_state


class VehicleDamageFrameworkTests(unittest.TestCase):
    def test_apply_vehicle_damage_updates_health_and_state(self) -> None:
        bus = SimpleNamespace(max_health=100.0, health=100.0)

        result = apply_vehicle_damage(bus, 35.0, default_max_health=100.0, source="test")

        self.assertAlmostEqual(result.applied_damage, 35.0)
        self.assertAlmostEqual(bus.health, 65.0)
        self.assertEqual(getattr(bus, "damage_state", ""), "damaged")

    def test_apply_vehicle_damage_honors_immunity(self) -> None:
        bus = SimpleNamespace(max_health=100.0, health=100.0)

        result = apply_vehicle_damage(bus, 35.0, default_max_health=100.0, allow_damage=False, source="immune")

        self.assertAlmostEqual(result.applied_damage, 0.0)
        self.assertAlmostEqual(bus.health, 100.0)

    def test_update_vehicle_damage_state_marks_destroyed(self) -> None:
        truck = SimpleNamespace(max_health=120.0, health=0.0)

        state = update_vehicle_damage_state(truck, default_max_health=120.0)

        self.assertEqual(state, "destroyed")
        self.assertTrue(bool(getattr(truck, "destroyed", False)))

    def test_airport_bus_vulnerability_starts_at_escort_phase(self) -> None:
        mission = SimpleNamespace(
            mission_id="airport",
            airport_hostage_state=SimpleNamespace(state="waiting"),
            airport_objective_state=SimpleNamespace(mission_phase="waiting_for_tech_deploy"),
        )
        self.assertFalse(is_airport_bus_vulnerable(mission))

        mission.airport_hostage_state.state = "boarded"
        self.assertTrue(is_airport_bus_vulnerable(mission))


if __name__ == "__main__":
    unittest.main()
