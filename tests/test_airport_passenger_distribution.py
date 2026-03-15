from __future__ import annotations

from types import SimpleNamespace
import random
import unittest

from src.choplifter.app.airport_session import configure_airport_passenger_distribution
from src.choplifter.app.airport_session import initialize_airport_runtime


def _compound(*, x: float, y: float, width: float = 90.0) -> SimpleNamespace:
    return SimpleNamespace(
        pos=SimpleNamespace(x=float(x), y=float(y)),
        width=float(width),
        hostage_count=0,
    )


class AirportPassengerDistributionTests(unittest.TestCase):
    def test_initialize_airport_runtime_combined_total_is_16(self) -> None:
        random.seed(101)
        mission = SimpleNamespace(
            compounds=[
                _compound(x=1200.0, y=260.0),
                _compound(x=1500.0, y=260.0),
                _compound(x=1200.0, y=320.0),
                _compound(x=1500.0, y=320.0),
                _compound(x=1800.0, y=320.0),
            ],
            hostages=[],
        )

        runtime = initialize_airport_runtime(mission=mission, ground_y=340.0)

        elevated_remaining = sum(int(v) for v in (getattr(runtime.hostage_state, "terminal_remaining", []) or []))
        lower_remaining = sum(int(getattr(c, "hostage_count", 0)) for c in (mission.compounds or []))
        self.assertEqual(elevated_remaining + lower_remaining, 16)

        # Enforce authored per-area minima: 2 elevated + 3 lower areas must each have >= 1.
        elevated_counts = list(getattr(runtime.hostage_state, "terminal_remaining", []) or [])
        self.assertEqual(len(elevated_counts), 2)
        self.assertTrue(all(int(v) >= 1 for v in elevated_counts))

        lower_counts = [int(getattr(c, "hostage_count", 0)) for c in mission.compounds]
        active_lower = [c for c in lower_counts if c > 0]
        self.assertEqual(len(active_lower), 3)
        self.assertTrue(all(c >= 1 for c in active_lower))

        # Elevated compounds must not also spawn standard mission hostages.
        sorted_by_height = sorted(
            range(len(mission.compounds)),
            key=lambda i: (float(mission.compounds[i].pos.y), float(mission.compounds[i].pos.x)),
        )
        elevated_indices = sorted_by_height[:2]
        for idx in elevated_indices:
            self.assertEqual(int(getattr(mission.compounds[idx], "hostage_count", 0)), 0)

    def test_total_passengers_is_always_authored_16(self) -> None:
        random.seed(3)
        mission = SimpleNamespace(
            compounds=[
                _compound(x=1200.0, y=260.0),
                _compound(x=1500.0, y=260.0),
                _compound(x=1200.0, y=320.0),
                _compound(x=1500.0, y=320.0),
                _compound(x=1800.0, y=320.0),
            ]
        )

        _pickup_points, elevated_counts, lower_total, _raised_bunker_x = configure_airport_passenger_distribution(
            mission=mission,
            total_passengers=99,
        )

        self.assertEqual(sum(int(v) for v in elevated_counts) + int(lower_total), 16)

    def test_five_compounds_distribute_across_five_areas(self) -> None:
        random.seed(23)
        mission = SimpleNamespace(
            compounds=[
                _compound(x=1200.0, y=260.0),
                _compound(x=1500.0, y=260.0),
                _compound(x=1200.0, y=320.0),
                _compound(x=1500.0, y=320.0),
                _compound(x=1800.0, y=320.0),
            ]
        )

        pickup_points, elevated_counts, lower_total, _raised_bunker_x = configure_airport_passenger_distribution(
            mission=mission,
            total_passengers=16,
        )

        self.assertEqual(len(pickup_points), 2)
        self.assertEqual(len(elevated_counts), 2)
        self.assertEqual(sum(int(v) for v in elevated_counts) + int(lower_total), 16)
        self.assertTrue(all(int(v) >= 1 for v in elevated_counts))

        lower_counts = [int(getattr(c, "hostage_count", 0)) for c in mission.compounds]
        active_lower = [c for c in lower_counts if c > 0]
        self.assertEqual(len(active_lower), 3)
        self.assertTrue(all(c >= 1 for c in active_lower))

    def test_three_compounds_enforce_mandatory_airport_baseline_split(self) -> None:
        random.seed(7)
        mission = SimpleNamespace(
            compounds=[
                _compound(x=1200.0, y=260.0),
                _compound(x=1500.0, y=260.0),
                _compound(x=1800.0, y=320.0),
            ]
        )

        pickup_points, elevated_counts, lower_total, _raised_bunker_x = configure_airport_passenger_distribution(
            mission=mission,
            total_passengers=16,
        )

        elevated_total = sum(int(v) for v in elevated_counts)
        total = elevated_total + int(lower_total)
        lower_compound_count = int(getattr(mission.compounds[2], "hostage_count", 0))
        self.assertEqual(len(pickup_points), 2)
        self.assertGreaterEqual(elevated_total, 2)
        self.assertGreaterEqual(lower_total, 4)
        self.assertGreaterEqual(lower_compound_count, 4)
        self.assertEqual(total, 16)

    def test_same_height_compounds_still_enforce_mandatory_baseline_split(self) -> None:
        random.seed(11)
        mission = SimpleNamespace(
            compounds=[
                _compound(x=1200.0, y=300.0),
                _compound(x=1500.0, y=300.0),
                _compound(x=1800.0, y=300.0),
            ]
        )

        pickup_points, elevated_counts, lower_total, _raised_bunker_x = configure_airport_passenger_distribution(
            mission=mission,
            total_passengers=16,
        )

        elevated_total = sum(int(v) for v in elevated_counts)
        total = elevated_total + int(lower_total)
        lower_compound_count = int(getattr(mission.compounds[2], "hostage_count", 0))
        self.assertEqual(len(pickup_points), 2)
        self.assertGreaterEqual(elevated_total, 2)
        self.assertGreaterEqual(lower_total, 4)
        self.assertGreaterEqual(lower_compound_count, 4)
        self.assertEqual(total, 16)


if __name__ == "__main__":
    unittest.main()
