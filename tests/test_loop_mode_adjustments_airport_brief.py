from __future__ import annotations

from types import SimpleNamespace
import unittest

from src.choplifter.app.loop_mode_adjustments import apply_post_input_mode_adjustments


class LoopModeAdjustmentsAirportBriefTests(unittest.TestCase):
    def test_city_mission_start_sets_pending_satellite_sfx_during_cutscene(self) -> None:
        runtime = SimpleNamespace(
            prev_loop_mode="select_chopper",
            city_satellite_sfx_pending=False,
            airport_ai_mission_brief_pending=False,
        )
        calls = {"city": 0, "airport": 0}

        out = apply_post_input_mode_adjustments(
            mode="cutscene",
            selected_mission_id="city",
            runtime=runtime,
            cutscene_video=None,
            start_mission_intro_or_playing_fn=lambda _mission_id: "cutscene",
            play_satellite_reallocating_fn=lambda: calls.__setitem__("city", calls["city"] + 1),
            play_airport_ai_mission_brief_fn=lambda: calls.__setitem__("airport", calls["airport"] + 1),
        )

        self.assertEqual(out.mode, "cutscene")
        self.assertTrue(runtime.city_satellite_sfx_pending)
        self.assertEqual(calls["city"], 0)

    def test_pending_city_satellite_sfx_plays_once_when_entering_playing(self) -> None:
        runtime = SimpleNamespace(
            prev_loop_mode="cutscene",
            city_satellite_sfx_pending=True,
            airport_ai_mission_brief_pending=False,
        )
        calls = {"city": 0, "airport": 0}

        out = apply_post_input_mode_adjustments(
            mode="playing",
            selected_mission_id="city",
            runtime=runtime,
            cutscene_video=None,
            start_mission_intro_or_playing_fn=lambda _mission_id: "playing",
            play_satellite_reallocating_fn=lambda: calls.__setitem__("city", calls["city"] + 1),
            play_airport_ai_mission_brief_fn=lambda: calls.__setitem__("airport", calls["airport"] + 1),
        )

        self.assertEqual(out.mode, "playing")
        self.assertFalse(runtime.city_satellite_sfx_pending)
        self.assertEqual(calls["city"], 1)

    def test_worship_mission_start_sets_pending_satellite_sfx_during_cutscene(self) -> None:
        runtime = SimpleNamespace(
            prev_loop_mode="select_chopper",
            city_satellite_sfx_pending=False,
            airport_ai_mission_brief_pending=False,
        )
        calls = {"city": 0, "airport": 0}

        out = apply_post_input_mode_adjustments(
            mode="cutscene",
            selected_mission_id="worship",
            runtime=runtime,
            cutscene_video=None,
            start_mission_intro_or_playing_fn=lambda _mission_id: "cutscene",
            play_satellite_reallocating_fn=lambda: calls.__setitem__("city", calls["city"] + 1),
            play_airport_ai_mission_brief_fn=lambda: calls.__setitem__("airport", calls["airport"] + 1),
        )

        self.assertEqual(out.mode, "cutscene")
        self.assertTrue(runtime.city_satellite_sfx_pending)
        self.assertEqual(calls["city"], 0)

    def test_pending_worship_satellite_sfx_plays_once_when_entering_playing(self) -> None:
        runtime = SimpleNamespace(
            prev_loop_mode="cutscene",
            city_satellite_sfx_pending=True,
            airport_ai_mission_brief_pending=False,
        )
        calls = {"city": 0, "airport": 0}

        out = apply_post_input_mode_adjustments(
            mode="playing",
            selected_mission_id="worship",
            runtime=runtime,
            cutscene_video=None,
            start_mission_intro_or_playing_fn=lambda _mission_id: "playing",
            play_satellite_reallocating_fn=lambda: calls.__setitem__("city", calls["city"] + 1),
            play_airport_ai_mission_brief_fn=lambda: calls.__setitem__("airport", calls["airport"] + 1),
        )

        self.assertEqual(out.mode, "playing")
        self.assertFalse(runtime.city_satellite_sfx_pending)
        self.assertEqual(calls["city"], 1)

    def test_airport_mission_start_sets_pending_brief_during_cutscene(self) -> None:
        runtime = SimpleNamespace(
            prev_loop_mode="select_chopper",
            city_satellite_sfx_pending=False,
            airport_ai_mission_brief_pending=False,
        )
        calls = {"city": 0, "airport": 0}

        out = apply_post_input_mode_adjustments(
            mode="cutscene",
            selected_mission_id="airport",
            runtime=runtime,
            cutscene_video=None,
            start_mission_intro_or_playing_fn=lambda _mission_id: "cutscene",
            play_satellite_reallocating_fn=lambda: calls.__setitem__("city", calls["city"] + 1),
            play_airport_ai_mission_brief_fn=lambda: calls.__setitem__("airport", calls["airport"] + 1),
        )

        self.assertEqual(out.mode, "cutscene")
        self.assertTrue(runtime.airport_ai_mission_brief_pending)
        self.assertEqual(calls["airport"], 0)

    def test_pending_airport_brief_plays_once_when_entering_playing(self) -> None:
        runtime = SimpleNamespace(
            prev_loop_mode="cutscene",
            city_satellite_sfx_pending=False,
            airport_ai_mission_brief_pending=True,
        )
        calls = {"city": 0, "airport": 0}

        out = apply_post_input_mode_adjustments(
            mode="playing",
            selected_mission_id="airport",
            runtime=runtime,
            cutscene_video=None,
            start_mission_intro_or_playing_fn=lambda _mission_id: "playing",
            play_satellite_reallocating_fn=lambda: calls.__setitem__("city", calls["city"] + 1),
            play_airport_ai_mission_brief_fn=lambda: calls.__setitem__("airport", calls["airport"] + 1),
        )

        self.assertEqual(out.mode, "playing")
        self.assertFalse(runtime.airport_ai_mission_brief_pending)
        self.assertEqual(calls["airport"], 1)


if __name__ == "__main__":
    unittest.main()
