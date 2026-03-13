from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from src.choplifter.mission_flow import update_mission


class MissionEndPrecedenceTests(unittest.TestCase):
    def _patch_nonessential_flow(self):
        return patch.multiple(
            "src.choplifter.mission_flow",
            tick_post_respawn_escort_risk=lambda mission, dt: None,
            _update_world_particles=lambda mission, helicopter, dt, heli: None,
            _update_enemies=lambda *args, **kwargs: None,
            _update_projectiles=lambda *args, **kwargs: None,
            _update_compounds_and_release=lambda mission, heli, logger: None,
            _update_hostages=lambda mission, helicopter, dt, heli, boarded_count_fn: None,
            _handle_unload=lambda mission, helicopter, heli, dt: None,
            _update_sentiment=lambda mission: None,
            _log_progress_if_changed=lambda mission, logger: None,
        )

    def test_crash_active_state_does_not_get_overridden_by_out_of_fuel(self) -> None:
        mission = SimpleNamespace(
            ended=False,
            elapsed_seconds=0.0,
            invuln_seconds=0.0,
            flare_invuln_seconds=0.0,
            crash_active=True,
            crash_impact_sfx_pending=False,
            stats=SimpleNamespace(saved=0),
            mission_id="city",
            supply_drops=None,
            tuning=SimpleNamespace(),
        )
        helicopter = SimpleNamespace(fuel=30.0, damage=10.0)
        heli = SimpleNamespace(ground_y=0.0, rotor_clearance=0.0)
        ended_reasons: list[str] = []

        def _end_mission(_mission, _end_text, reason, _logger):
            ended_reasons.append(str(reason))
            _mission.ended = True

        with self._patch_nonessential_flow(), patch(
            "src.choplifter.mission_flow._update_fuel",
            side_effect=lambda _mission, _helicopter, _dt, _logger: setattr(_helicopter, "fuel", 0.0),
        ), patch("src.choplifter.mission_flow._handle_crash_and_respawn") as crash_handler:
            update_mission(
                mission,
                helicopter,
                dt=1 / 60,
                heli=heli,
                logger=None,
                end_mission=_end_mission,
            )

        self.assertEqual(ended_reasons, [])
        crash_handler.assert_called_once()

    def test_third_crash_wins_over_out_of_fuel_reason(self) -> None:
        mission = SimpleNamespace(
            ended=False,
            elapsed_seconds=0.0,
            invuln_seconds=0.0,
            flare_invuln_seconds=0.0,
            crash_active=False,
            crashes=2,
            hostages=[],
            stats=SimpleNamespace(saved=0, lost_in_transit=0),
            mission_id="city",
            supply_drops=None,
            tuning=SimpleNamespace(),
            world_width=2000.0,
            crash_seconds=0.0,
            crash_impacted=False,
            crash_impact_seconds=0.0,
            crash_impact_sfx_pending=False,
            crash_origin=SimpleNamespace(x=0.0, y=0.0),
            crash_vel=SimpleNamespace(x=0.0, y=0.0),
            crash_variant=0,
            explosions=SimpleNamespace(emit_explosion=lambda *_args, **_kwargs: None),
            burning=SimpleNamespace(add_site=lambda *_args, **_kwargs: None),
            impact_sparks=SimpleNamespace(emit_hit=lambda *_args, **_kwargs: None),
        )
        helicopter = SimpleNamespace(
            fuel=30.0,
            damage=100.0,
            vel=SimpleNamespace(x=0.0, y=0.0),
            pos=SimpleNamespace(x=100.0, y=100.0),
            crashing=False,
            crash_variant=0,
            crash_seconds=0.0,
            crash_hide=False,
        )
        heli = SimpleNamespace(ground_y=0.0, rotor_clearance=0.0)
        ended_reasons: list[str] = []

        def _end_mission(_mission, _end_text, reason, _logger):
            ended_reasons.append(str(reason))
            _mission.ended = True
            _mission.end_reason = reason

        with self._patch_nonessential_flow(), patch(
            "src.choplifter.mission_flow._update_fuel",
            side_effect=lambda _mission, _helicopter, _dt, _logger: setattr(_helicopter, "fuel", 0.0),
        ):
            update_mission(
                mission,
                helicopter,
                dt=1 / 60,
                heli=heli,
                logger=None,
                end_mission=_end_mission,
            )

        self.assertEqual(ended_reasons, ["CRASHED 3 TIMES"])


if __name__ == "__main__":
    unittest.main()
