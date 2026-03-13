from __future__ import annotations

from types import SimpleNamespace
import random
import unittest

from src.choplifter.app.airport_session import configure_airport_passenger_distribution


def _compound(*, x: float, y: float, width: float = 90.0) -> SimpleNamespace:
    return SimpleNamespace(
        pos=SimpleNamespace(x=float(x), y=float(y)),
        width=float(width),
        hostage_count=0,
    )


class AirportPassengerDistributionTests(unittest.TestCase):
    def test_three_compounds_always_keep_some_lower_compound_rescues(self) -> None:
        random.seed(7)
        mission = SimpleNamespace(
            compounds=[
                _compound(x=1200.0, y=260.0),
                _compound(x=1500.0, y=260.0),
                _compound(x=1800.0, y=320.0),
            ]
        )

        pickup_points, elevated_total, lower_total, _raised_bunker_x = configure_airport_passenger_distribution(
            mission=mission,
            total_passengers=16,
        )

        total = sum(int(getattr(c, "hostage_count", 0)) for c in mission.compounds)
        self.assertEqual(len(pickup_points), 2)
        self.assertGreaterEqual(elevated_total, 1)
        self.assertGreaterEqual(lower_total, 1)
        self.assertEqual(total, 16)

    def test_same_height_compounds_still_reserve_lower_lane(self) -> None:
        random.seed(11)
        mission = SimpleNamespace(
            compounds=[
                _compound(x=1200.0, y=300.0),
                _compound(x=1500.0, y=300.0),
                _compound(x=1800.0, y=300.0),
            ]
        )

        pickup_points, elevated_total, lower_total, _raised_bunker_x = configure_airport_passenger_distribution(
            mission=mission,
            total_passengers=16,
        )

        total = sum(int(getattr(c, "hostage_count", 0)) for c in mission.compounds)
        self.assertEqual(len(pickup_points), 2)
        self.assertGreaterEqual(elevated_total, 1)
        self.assertGreaterEqual(lower_total, 1)
        self.assertEqual(total, 16)


if __name__ == "__main__":
    unittest.main()
