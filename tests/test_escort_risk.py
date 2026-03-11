from __future__ import annotations

from types import SimpleNamespace
import unittest

from src.choplifter.app.escort_risk import (
    POST_RESPAWN_ESCORT_RISK_SECONDS,
    POST_RESPAWN_ESCORT_DAMAGE_MULTIPLIER,
    activate_post_respawn_escort_risk,
    airport_escort_damage_multiplier,
    tick_post_respawn_escort_risk,
)


class EscortRiskTests(unittest.TestCase):
    def test_activate_sets_timer_for_airport_mission(self) -> None:
        mission = SimpleNamespace(mission_id="airport", post_respawn_escort_risk_seconds=0.0)

        activate_post_respawn_escort_risk(mission)

        self.assertEqual(mission.post_respawn_escort_risk_seconds, POST_RESPAWN_ESCORT_RISK_SECONDS)

    def test_activate_ignored_for_non_airport(self) -> None:
        mission = SimpleNamespace(mission_id="city", post_respawn_escort_risk_seconds=0.0)

        activate_post_respawn_escort_risk(mission)

        self.assertEqual(mission.post_respawn_escort_risk_seconds, 0.0)

    def test_tick_clamps_timer_to_zero(self) -> None:
        mission = SimpleNamespace(post_respawn_escort_risk_seconds=0.4)

        tick_post_respawn_escort_risk(mission, 1.0)

        self.assertEqual(mission.post_respawn_escort_risk_seconds, 0.0)

    def test_multiplier_only_when_timer_active_during_boarded_escort(self) -> None:
        mission = SimpleNamespace(
            mission_id="airport",
            post_respawn_escort_risk_seconds=2.0,
            airport_hostage_state=SimpleNamespace(state="boarded"),
        )

        self.assertEqual(airport_escort_damage_multiplier(mission), POST_RESPAWN_ESCORT_DAMAGE_MULTIPLIER)

        mission.airport_hostage_state.state = "rescued"
        self.assertEqual(airport_escort_damage_multiplier(mission), 1.0)

        mission.airport_hostage_state.state = "boarded"
        mission.post_respawn_escort_risk_seconds = 0.0
        self.assertEqual(airport_escort_damage_multiplier(mission), 1.0)


if __name__ == "__main__":
    unittest.main()
