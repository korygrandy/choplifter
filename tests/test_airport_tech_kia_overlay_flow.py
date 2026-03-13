from __future__ import annotations

from types import SimpleNamespace
import unittest
import pytest

from src.choplifter.app.frame_update import update_vip_overlay_state


pytestmark = pytest.mark.airport_smoke


class AirportTechKiaOverlayFlowTests(unittest.TestCase):
    def test_starts_tech_kia_overlay_once_when_tech_is_kia(self) -> None:
        mission = SimpleNamespace(
            mission_id="airport",
            hostages=[],
            mission_tech=SimpleNamespace(state="kia"),
            airport_hostage_state=SimpleNamespace(terminal_remaining=[0, 0]),
        )

        state = update_vip_overlay_state(
            mission=mission,
            vip_kia_overlay_timer=0.0,
            vip_kia_overlay_shown=False,
            tech_kia_overlay_timer=0.0,
            tech_kia_overlay_shown=False,
        )

        self.assertEqual(state.tech_kia_overlay_timer, 3.0)
        self.assertTrue(state.tech_kia_overlay_shown)

    def test_starts_tech_kia_overlay_for_airport_alias_mission_ids(self) -> None:
        mission = SimpleNamespace(
            mission_id="mission2",
            hostages=[],
            mission_tech=SimpleNamespace(state="kia"),
            airport_hostage_state=SimpleNamespace(terminal_remaining=[0, 0]),
        )

        state = update_vip_overlay_state(
            mission=mission,
            vip_kia_overlay_timer=0.0,
            vip_kia_overlay_shown=False,
            tech_kia_overlay_timer=0.0,
            tech_kia_overlay_shown=False,
        )

        self.assertEqual(state.tech_kia_overlay_timer, 3.0)
        self.assertTrue(state.tech_kia_overlay_shown)

    def test_does_not_restart_tech_kia_overlay_after_first_show(self) -> None:
        mission = SimpleNamespace(
            mission_id="airport",
            hostages=[],
            mission_tech=SimpleNamespace(state="kia"),
            airport_hostage_state=SimpleNamespace(terminal_remaining=[2, 0]),
        )

        state = update_vip_overlay_state(
            mission=mission,
            vip_kia_overlay_timer=0.0,
            vip_kia_overlay_shown=False,
            tech_kia_overlay_timer=0.0,
            tech_kia_overlay_shown=True,
        )

        self.assertEqual(state.tech_kia_overlay_timer, 0.0)
        self.assertTrue(state.tech_kia_overlay_shown)

    def test_resets_tech_kia_overlay_flag_when_failure_condition_clears(self) -> None:
        mission = SimpleNamespace(
            mission_id="airport",
            hostages=[],
            mission_tech=SimpleNamespace(state="waiting_at_lz"),
            airport_hostage_state=SimpleNamespace(terminal_remaining=[0, 0]),
        )

        state = update_vip_overlay_state(
            mission=mission,
            vip_kia_overlay_timer=0.0,
            vip_kia_overlay_shown=False,
            tech_kia_overlay_timer=0.0,
            tech_kia_overlay_shown=True,
        )

        self.assertFalse(state.tech_kia_overlay_shown)


if __name__ == "__main__":
    unittest.main()
