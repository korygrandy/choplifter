from __future__ import annotations

from types import SimpleNamespace
import unittest

from src.choplifter.boarding_telemetry import (
    BOARDING_FAIL_DOORS_CLOSED,
    BOARDING_FAIL_FULL,
    BOARDING_FAIL_NOT_GROUNDED,
    record_boarding_failure,
)


class BoardingTelemetryTests(unittest.TestCase):
    def test_records_reason_counter(self) -> None:
        mission = SimpleNamespace(elapsed_seconds=1.0)

        record_boarding_failure(mission, BOARDING_FAIL_NOT_GROUNDED)

        self.assertEqual(mission.boarding_failure_counts[BOARDING_FAIL_NOT_GROUNDED], 1)

    def test_debounces_same_reason_within_cooldown(self) -> None:
        mission = SimpleNamespace(elapsed_seconds=2.0)

        record_boarding_failure(mission, BOARDING_FAIL_DOORS_CLOSED, cooldown_s=0.65)
        mission.elapsed_seconds = 2.3
        record_boarding_failure(mission, BOARDING_FAIL_DOORS_CLOSED, cooldown_s=0.65)
        mission.elapsed_seconds = 2.8
        record_boarding_failure(mission, BOARDING_FAIL_DOORS_CLOSED, cooldown_s=0.65)

        self.assertEqual(mission.boarding_failure_counts[BOARDING_FAIL_DOORS_CLOSED], 2)

    def test_reasons_are_counted_independently(self) -> None:
        mission = SimpleNamespace(elapsed_seconds=3.0)

        record_boarding_failure(mission, BOARDING_FAIL_NOT_GROUNDED)
        record_boarding_failure(mission, BOARDING_FAIL_FULL)

        self.assertEqual(mission.boarding_failure_counts[BOARDING_FAIL_NOT_GROUNDED], 1)
        self.assertEqual(mission.boarding_failure_counts[BOARDING_FAIL_FULL], 1)


if __name__ == "__main__":
    unittest.main()
