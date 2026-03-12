from __future__ import annotations

from types import SimpleNamespace
import unittest

from src.choplifter.app.game_update import process_playing_progression
from src.choplifter.app.stats_snapshot import MissionStatsSnapshot


class _AudioProbe:
    def __init__(self) -> None:
        self.stop_warning_calls = 0

    def stop_chopper_warning_beeps(self) -> None:
        self.stop_warning_calls += 1

    def __getattr__(self, _name: str):
        # Allow process_playing_progression to call other optional audio hooks.
        return lambda *args, **kwargs: None


def _make_prev_stats() -> MissionStatsSnapshot:
    return MissionStatsSnapshot(
        crashes=0,
        lost_in_transit=0,
        saved=0,
        boarded=0,
        open_compounds=0,
        tanks_destroyed=0,
        artillery_fired=0,
        artillery_hits=0,
        jets_entered=0,
        mines_detonated=0,
    )


def _make_mission() -> SimpleNamespace:
    return SimpleNamespace(
        ended=False,
        sentiment=0.0,
        stats=SimpleNamespace(
            saved=0,
            lost_in_transit=0,
            tanks_destroyed=0,
            artillery_fired=0,
            artillery_hits=0,
            jets_entered=0,
            mines_detonated=0,
        ),
        compounds=[],
        crashes=0,
        end_reason="",
        invuln_seconds=0.0,
        feedback_shake_impulse=0.0,
        feedback_duck_strength=0.0,
    )


class ChopperWarningBeepRecoveryTests(unittest.TestCase):
    def test_stops_warning_beeps_when_damage_recovers_below_threshold(self) -> None:
        mission = _make_mission()
        helicopter = SimpleNamespace(damage=0.0, damage_flash_seconds=0.0)
        audio = _AudioProbe()

        process_playing_progression(
            mission=mission,
            helicopter=helicopter,
            tick_dt=1 / 60,
            mission_end_delay_s=3.0,
            prev_stats=_make_prev_stats(),
            boarded_count=lambda _mission: 0,
            audio=audio,
            set_toast=lambda _msg: None,
            screenshake=SimpleNamespace(),
            screenshake_enabled=True,
        )

        self.assertEqual(audio.stop_warning_calls, 1)

    def test_does_not_stop_warning_beeps_when_still_above_threshold(self) -> None:
        mission = _make_mission()
        helicopter = SimpleNamespace(damage=85.0, damage_flash_seconds=0.0)
        audio = _AudioProbe()

        process_playing_progression(
            mission=mission,
            helicopter=helicopter,
            tick_dt=1 / 60,
            mission_end_delay_s=3.0,
            prev_stats=_make_prev_stats(),
            boarded_count=lambda _mission: 0,
            audio=audio,
            set_toast=lambda _msg: None,
            screenshake=SimpleNamespace(),
            screenshake_enabled=True,
        )

        self.assertEqual(audio.stop_warning_calls, 0)


if __name__ == "__main__":
    unittest.main()
