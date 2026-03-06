from __future__ import annotations

from types import SimpleNamespace
import unittest

from src.choplifter.mission_helpers import (
    _update_sentiment,
    sentiment_band_label,
    sentiment_contributions,
    sentiment_progression_pressure_multiplier,
)


def _mission(sentiment: float, *, saved: int = 0, kia_player: int = 0, kia_enemy: int = 0, lost: int = 0):
    stats = SimpleNamespace(saved=saved, kia_by_player=kia_player, kia_by_enemy=kia_enemy, lost_in_transit=lost)
    return SimpleNamespace(
        sentiment=sentiment,
        stats=stats,
        _sentiment_last_saved=0,
        _sentiment_last_kia_player=0,
        _sentiment_last_kia_enemy=0,
        _sentiment_last_lost_in_transit=0,
    )


class SentimentHelpersTests(unittest.TestCase):
    def test_contribution_weights(self) -> None:
        factors = sentiment_contributions(saved=3, kia_player=1, kia_enemy=2, lost_in_transit=1)
        self.assertEqual(factors["saved"], 7.5)
        self.assertEqual(factors["kia_player"], -4.0)
        self.assertEqual(factors["kia_enemy"], -5.0)
        self.assertEqual(factors["lost_in_transit"], -3.5)

    def test_band_thresholds(self) -> None:
        self.assertEqual(sentiment_band_label(80.0), "Excellent")
        self.assertEqual(sentiment_band_label(65.0), "Good")
        self.assertEqual(sentiment_band_label(45.0), "Mixed")
        self.assertEqual(sentiment_band_label(25.0), "Poor")
        self.assertEqual(sentiment_band_label(24.9), "Critical")

    def test_progression_multiplier_matches_band(self) -> None:
        self.assertEqual(sentiment_progression_pressure_multiplier(90.0), 0.88)
        self.assertEqual(sentiment_progression_pressure_multiplier(75.0), 0.94)
        self.assertEqual(sentiment_progression_pressure_multiplier(60.0), 1.00)
        self.assertEqual(sentiment_progression_pressure_multiplier(30.0), 1.10)
        self.assertEqual(sentiment_progression_pressure_multiplier(20.0), 1.18)

    def test_update_sentiment_is_guardrailed_per_tick(self) -> None:
        mission = _mission(50.0, saved=0, kia_player=0, kia_enemy=0, lost=20)
        _update_sentiment(mission)
        # Without guardrail this would drop by 70 in one update.
        self.assertEqual(mission.sentiment, 32.0)

    def test_update_sentiment_clamps_to_bounds(self) -> None:
        mission_low = _mission(1.0, saved=0, kia_player=5, kia_enemy=5, lost=5)
        _update_sentiment(mission_low)
        self.assertEqual(mission_low.sentiment, 0.0)

        mission_high = _mission(98.0, saved=20, kia_player=0, kia_enemy=0, lost=0)
        _update_sentiment(mission_high)
        self.assertEqual(mission_high.sentiment, 100.0)


if __name__ == "__main__":
    unittest.main()
