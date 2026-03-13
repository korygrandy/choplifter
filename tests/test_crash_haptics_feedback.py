from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from src.choplifter.app.feedback import ScreenShakeState, consume_mission_feedback


class _AudioProbe:
    def __init__(self) -> None:
        self.duck_calls: list[float] = []
        self.crash_calls = 0

    def trigger_duck(self, *, strength: float) -> None:
        self.duck_calls.append(float(strength))

    def play_chopper_crash(self) -> None:
        self.crash_calls += 1


class CrashHapticsFeedbackTests(unittest.TestCase):
    def test_crash_feedback_triggers_forceful_rumble_and_resets_pending_flag(self) -> None:
        mission = SimpleNamespace(
            feedback_shake_impulse=0.0,
            feedback_duck_strength=0.0,
            crash_impact_sfx_pending=True,
        )
        audio = _AudioProbe()
        shake = ScreenShakeState()

        with patch("src.choplifter.app.feedback.haptics.rumble_chopper_crash") as rumble_crash:
            consume_mission_feedback(
                state=shake,
                mission=mission,
                audio=audio,
                screenshake_enabled=True,
            )

        rumble_crash.assert_called_once_with()
        self.assertEqual(audio.crash_calls, 1)
        self.assertEqual(audio.duck_calls, [1.0])
        self.assertFalse(mission.crash_impact_sfx_pending)


if __name__ == "__main__":
    unittest.main()
