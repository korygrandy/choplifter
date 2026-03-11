from __future__ import annotations

import unittest

from src.choplifter.app.weapon_lock import chopper_weapons_locked


class WeaponLockTests(unittest.TestCase):
    def test_unlocked_in_normal_flight(self) -> None:
        self.assertFalse(
            chopper_weapons_locked(
                meal_truck_driver_mode=False,
                bus_driver_mode=False,
                engineer_remote_control_active=False,
            )
        )

    def test_locked_in_meal_truck_driver_mode(self) -> None:
        self.assertTrue(
            chopper_weapons_locked(
                meal_truck_driver_mode=True,
                bus_driver_mode=False,
                engineer_remote_control_active=False,
            )
        )

    def test_locked_in_bus_driver_mode(self) -> None:
        self.assertTrue(
            chopper_weapons_locked(
                meal_truck_driver_mode=False,
                bus_driver_mode=True,
                engineer_remote_control_active=False,
            )
        )

    def test_locked_when_remote_control_active(self) -> None:
        self.assertTrue(
            chopper_weapons_locked(
                meal_truck_driver_mode=False,
                bus_driver_mode=False,
                engineer_remote_control_active=True,
            )
        )


if __name__ == "__main__":
    unittest.main()
