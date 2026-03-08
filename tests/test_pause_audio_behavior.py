from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

import pygame

from src.choplifter.app.event_loop import handle_gamepad_pause_button
from src.choplifter.app.keyboard_events import handle_keyboard_event
from src.choplifter.audio import AudioBank


class _RecordingMixer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, float]] = []

    def set_bus_volume(self, bus: str, volume: float) -> None:
        self.calls.append((bus, float(volume)))


class _RecordingAudio:
    def __init__(self) -> None:
        self.pause_toggle_calls = 0
        self.pause_active_calls: list[bool] = []
        self.muted_calls: list[bool] = []
        self.menu_select_calls = 0

    def play_pause_toggle(self) -> None:
        self.pause_toggle_calls += 1

    def set_pause_menu_active(self, active: bool) -> None:
        self.pause_active_calls.append(bool(active))

    def set_muted(self, muted: bool) -> None:
        self.muted_calls.append(bool(muted))

    def play_menu_select(self) -> None:
        self.menu_select_calls += 1


class PauseAudioBehaviorTests(unittest.TestCase):
    def _make_bank(self, mixer: _RecordingMixer) -> AudioBank:
        return AudioBank(
            mixer=mixer,
            shoot=None,
            bomb=None,
            explosion=None,
            explosion_small=None,
            explosion_big=None,
            mine_explosion=None,
            flare_defense=None,
            artillery_shot=None,
            artillery_impact_a=None,
            artillery_impact_b=None,
            jet_flyby=None,
            midair_collision=None,
            chopper_warning_beeps=None,
            doors_open=None,
            doors_close=None,
            board=None,
            rescue=None,
            crash=None,
            chopper_crash=None,
            flying_loop=None,
            menu_select=None,
            pause=None,
            barak_mrad_deploy=None,
            barak_mrad_launch=None,
        )

    def test_pause_menu_hard_mutes_all_buses(self) -> None:
        mixer = _RecordingMixer()
        bank = self._make_bank(mixer)

        bank.set_pause_menu_active(True)

        self.assertEqual(
            mixer.calls[-3:],
            [("sfx", 0.0), ("ui", 0.0), ("music", 0.0)],
        )

    def test_unpause_respects_user_mute(self) -> None:
        mixer = _RecordingMixer()
        bank = self._make_bank(mixer)

        bank.set_muted(True)
        bank.set_pause_menu_active(True)
        bank.set_pause_menu_active(False)

        self.assertEqual(
            mixer.calls[-3:],
            [("sfx", 0.0), ("ui", 0.0), ("music", 0.0)],
        )

    def test_pause_mutes_and_unpause_restores_flying_loop_channel(self) -> None:
        mixer = _RecordingMixer()
        bank = self._make_bank(mixer)

        class _Channel:
            def __init__(self, idx: int) -> None:
                self.idx = idx

            def set_volume(self, volume: float) -> None:
                dedicated_calls.append((self.idx, float(volume)))

        dedicated_calls: list[tuple[int, float]] = []
        with patch("src.choplifter.audio.pygame.mixer.Channel", side_effect=lambda idx: _Channel(idx)):
            bank.set_pause_menu_active(True)
            bank.set_pause_menu_active(False)

        # Dedicated flying-loop channel (14) should be muted on pause, then restored.
        loop_calls = [v for idx, v in dedicated_calls if idx == 14]
        self.assertGreaterEqual(len(loop_calls), 2)
        self.assertEqual(loop_calls[0], 0.0)
        self.assertEqual(loop_calls[-1], 1.0)

    def test_keyboard_escape_toggles_pause_audio_state(self) -> None:
        controls = SimpleNamespace(quit=[], restart=[], toggle_debug=[], cycle_facing=[], reverse_flip=[], doors=[], flare=[], fire=[])
        audio = _RecordingAudio()
        mission = SimpleNamespace(ended=False, crash_active=False)
        helicopter = SimpleNamespace(skin_asset="chopper-one.png")

        # Enter pause from playing.
        pause_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        out = handle_keyboard_event(
            pause_event,
            mode="playing",
            controls=controls,
            mission=mission,
            helicopter=helicopter,
            audio=audio,
            logger=None,
            chopper_choices=[("chopper-one.png", "Classic")],
            mission_choices=[("city", "City")],
            pause_focus="choppers",
            muted=False,
            set_toast=lambda _msg: None,
            reset_game=lambda: None,
            apply_mission_preview=lambda: None,
            skip_intro=lambda: None,
            skip_mission_cutscene=lambda: None,
            toggle_particles_wrapper=lambda: None,
            toggle_flashes_wrapper=lambda: None,
            toggle_screenshake_wrapper=lambda: None,
            spawn_projectile_from_helicopter_logged=lambda *_args, **_kwargs: None,
            try_start_flare_salvo=lambda *_args, **_kwargs: None,
            toggle_doors_with_logging=lambda *_args, **_kwargs: None,
            Facing=SimpleNamespace(FORWARD="forward"),
            DebugSettings=lambda **kwargs: SimpleNamespace(**kwargs),
            boarded_count=lambda *_args, **_kwargs: 0,
            flares=SimpleNamespace(),
            selected_mission_index=0,
            selected_mission_id="city",
            selected_chopper_index=0,
            selected_chopper_asset="chopper-one.png",
            debug=SimpleNamespace(show_overlay=False),
            quit_confirm=False,
        )
        self.assertEqual(out[0], "paused")

        # Exit pause to playing.
        out = handle_keyboard_event(
            pause_event,
            mode="paused",
            controls=controls,
            mission=mission,
            helicopter=helicopter,
            audio=audio,
            logger=None,
            chopper_choices=[("chopper-one.png", "Classic")],
            mission_choices=[("city", "City")],
            pause_focus="choppers",
            muted=False,
            set_toast=lambda _msg: None,
            reset_game=lambda: None,
            apply_mission_preview=lambda: None,
            skip_intro=lambda: None,
            skip_mission_cutscene=lambda: None,
            toggle_particles_wrapper=lambda: None,
            toggle_flashes_wrapper=lambda: None,
            toggle_screenshake_wrapper=lambda: None,
            spawn_projectile_from_helicopter_logged=lambda *_args, **_kwargs: None,
            try_start_flare_salvo=lambda *_args, **_kwargs: None,
            toggle_doors_with_logging=lambda *_args, **_kwargs: None,
            Facing=SimpleNamespace(FORWARD="forward"),
            DebugSettings=lambda **kwargs: SimpleNamespace(**kwargs),
            boarded_count=lambda *_args, **_kwargs: 0,
            flares=SimpleNamespace(),
            selected_mission_index=0,
            selected_mission_id="city",
            selected_chopper_index=0,
            selected_chopper_asset="chopper-one.png",
            debug=SimpleNamespace(show_overlay=False),
            quit_confirm=False,
        )
        self.assertEqual(out[0], "playing")

        self.assertEqual(audio.pause_active_calls, [True, False])
        self.assertEqual(audio.pause_toggle_calls, 2)

    def test_gamepad_pause_handler_edges(self) -> None:
        mode, just_paused, toggled, clear_quit = handle_gamepad_pause_button(
            mode="playing",
            start_down=True,
            prev_btn_start_down=False,
            b_down=False,
            prev_btn_b_down=False,
            just_paused_with_start=False,
        )
        self.assertEqual((mode, just_paused, toggled, clear_quit), ("paused", True, True, False))

        # Releasing start clears the just-paused guard.
        mode, just_paused, toggled, clear_quit = handle_gamepad_pause_button(
            mode="paused",
            start_down=False,
            prev_btn_start_down=True,
            b_down=False,
            prev_btn_b_down=False,
            just_paused_with_start=True,
        )
        self.assertEqual((mode, just_paused, toggled, clear_quit), ("paused", False, False, False))

        # Next start edge resumes and clears quit confirm.
        mode, just_paused, toggled, clear_quit = handle_gamepad_pause_button(
            mode="paused",
            start_down=True,
            prev_btn_start_down=False,
            b_down=False,
            prev_btn_b_down=False,
            just_paused_with_start=False,
        )
        self.assertEqual((mode, just_paused, toggled, clear_quit), ("playing", False, True, True))


if __name__ == "__main__":
    unittest.main()
