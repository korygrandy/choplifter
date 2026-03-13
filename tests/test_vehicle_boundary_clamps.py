from __future__ import annotations

from types import SimpleNamespace
import unittest

from src.choplifter.app.airport_tick import _apply_vehicle_boundary_clamps


class VehicleBoundaryClampTests(unittest.TestCase):
    def test_meal_truck_clamped_always(self) -> None:
        """Meal truck should always clamp to [0, world_width]."""
        meal_truck = SimpleNamespace(x=2900.0)
        bus = None
        
        _apply_vehicle_boundary_clamps(
            meal_truck_state=meal_truck,
            bus_state=bus,
            world_width=2800.0,
            bus_driver_mode=False
        )
        
        self.assertEqual(meal_truck.x, 2800.0)

    def test_meal_truck_negative_clamped(self) -> None:
        """Meal truck should be clamped at 0."""
        meal_truck = SimpleNamespace(x=-100.0)
        bus = None
        
        _apply_vehicle_boundary_clamps(
            meal_truck_state=meal_truck,
            bus_state=bus,
            world_width=2800.0,
            bus_driver_mode=False
        )
        
        self.assertEqual(meal_truck.x, 0.0)

    def test_bus_player_driving_strict_boundary(self) -> None:
        """Bus with player driving should clamp strictly to [0, world_width]."""
        bus = SimpleNamespace(x=2900.0)
        meal_truck = None
        
        _apply_vehicle_boundary_clamps(
            meal_truck_state=meal_truck,
            bus_state=bus,
            world_width=2800.0,
            bus_driver_mode=True  # player driving
        )
        
        self.assertEqual(bus.x, 2800.0)

    def test_bus_ai_controlled_allows_slight_overage(self) -> None:
        """Bus with AI controlling should allow overage up to world_width + 200."""
        bus = SimpleNamespace(x=2900.0)
        meal_truck = None
        
        _apply_vehicle_boundary_clamps(
            meal_truck_state=meal_truck,
            bus_state=bus,
            world_width=2800.0,
            bus_driver_mode=False  # AI driving
        )
        
        # 2900 is within 2800+200, so should not be clamped
        self.assertEqual(bus.x, 2900.0)

    def test_bus_ai_controlled_clamps_at_max_overage(self) -> None:
        """Bus with AI controlling should clamp at world_width + 200."""
        bus = SimpleNamespace(x=3100.0)
        meal_truck = None
        
        _apply_vehicle_boundary_clamps(
            meal_truck_state=meal_truck,
            bus_state=bus,
            world_width=2800.0,
            bus_driver_mode=False  # AI driving
        )
        
        # 3100 exceeds 2800+200, so should be clamped to 3000
        self.assertEqual(bus.x, 3000.0)


if __name__ == "__main__":
    unittest.main()
