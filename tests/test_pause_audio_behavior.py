from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch
from unittest.mock import Mock

import pygame

from src.choplifter.app.event_loop import (
    apply_pause_transition,
    handle_gamepad_pause_button,
    handle_mission_end_gamepad_navigation,
    handle_mission_end_keyboard_navigation,
    handle_pause_quit_confirm_gamepad,
)
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
            bus_accelerate=None,
            bus_brakes=None,
            bus_door=None,
            hang_on_yall=None,
            carjacked_mealtruck=None,
            barak_explosion=None,
        )

    def test_pause_menu_mutes_gameplay_buses_but_keeps_ui(self) -> None:
        mixer = _RecordingMixer()
        bank = self._make_bank(mixer)

        bank.set_pause_menu_active(True)

        self.assertEqual(
            mixer.calls[-3:],
            [("sfx", 0.0), ("ui", 1.0), ("music", 0.0)],
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

    def test_select_chopper_escape_takes_back_over_quit_binding(self) -> None:
        controls = SimpleNamespace(
            quit=[pygame.K_ESCAPE],
            restart=[],
            toggle_debug=[],
            cycle_facing=[],
            reverse_flip=[],
            doors=[],
            flare=[],
            fire=[],
            tilt_left=[],
            tilt_right=[],
        )
        audio = _RecordingAudio()
        mission = SimpleNamespace(ended=False, crash_active=False)
        helicopter = SimpleNamespace(skin_asset="chopper-one.png")

        out = handle_keyboard_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE),
            mode="select_chopper",
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

        self.assertEqual(out[0], "select_mission")
        self.assertFalse(out[2])

    def test_mission_end_pause_keys_open_pause_menu(self) -> None:
        handled, mode = handle_mission_end_keyboard_navigation(
            key=pygame.K_ESCAPE,
            mode="mission_end",
            mission_ended=True,
            set_toast=lambda _msg: None,
        )
        self.assertEqual((handled, mode), (True, "paused"))

        handled, mode = handle_mission_end_keyboard_navigation(
            key=pygame.K_PAUSE,
            mode="mission_end",
            mission_ended=True,
            set_toast=lambda _msg: None,
        )
        self.assertEqual((handled, mode), (True, "paused"))

    def test_mission_end_gamepad_start_opens_pause_menu(self) -> None:
        handled, mode = handle_mission_end_gamepad_navigation(
            button=7,
            mode="mission_end",
            set_toast=lambda _msg: None,
        )
        self.assertEqual((handled, mode), (True, "paused"))

    def test_gamepad_start_pauses_from_mission_end_mode(self) -> None:
        mode, just_paused, toggled, clear_quit = handle_gamepad_pause_button(
            mode="mission_end",
            start_down=True,
            prev_btn_start_down=False,
            b_down=False,
            prev_btn_b_down=False,
            just_paused_with_start=False,
        )
        self.assertEqual((mode, just_paused, toggled, clear_quit), ("paused", True, True, False))

    def test_pause_transition_applies_audio_and_focus(self) -> None:
        audio = _RecordingAudio()

        entered = apply_pause_transition(
            prev_mode="playing",
            next_mode="paused",
            pause_focus="quit",
            audio=audio,
        )
        resumed = apply_pause_transition(
            prev_mode="paused",
            next_mode="playing",
            pause_focus=entered.pause_focus,
            audio=audio,
        )

        self.assertEqual(entered.pause_focus, "choppers")
        self.assertTrue(entered.entered_pause)
        self.assertFalse(entered.resumed_playing)
        self.assertFalse(resumed.entered_pause)
        self.assertTrue(resumed.resumed_playing)
        self.assertEqual(audio.pause_active_calls, [True, False])
        self.assertEqual(audio.pause_toggle_calls, 2)

    def test_pause_quit_confirm_gamepad_edges(self) -> None:
        handled, keep_running, quit_confirm = handle_pause_quit_confirm_gamepad(
            quit_confirm=True,
            a_down=True,
            prev_btn_a_down=False,
            b_down=False,
            prev_btn_b_down=False,
        )
        self.assertEqual((handled, keep_running, quit_confirm), (True, False, True))

        handled, keep_running, quit_confirm = handle_pause_quit_confirm_gamepad(
            quit_confirm=True,
            a_down=False,
            prev_btn_a_down=False,
            b_down=True,
            prev_btn_b_down=False,
        )
        self.assertEqual((handled, keep_running, quit_confirm), (True, True, False))

    def test_keyboard_fire_blocked_when_weapon_locked(self) -> None:
        controls = SimpleNamespace(
            quit=[],
            restart=[],
            toggle_debug=[],
            cycle_facing=[],
            reverse_flip=[],
            doors=[],
            flare=[],
            fire=[pygame.K_SPACE],
            tilt_left=[],
            tilt_right=[],
        )
        audio = _RecordingAudio()
        mission = SimpleNamespace(ended=False, crash_active=False)
        helicopter = SimpleNamespace(skin_asset="chopper-one.png", facing="forward")
        spawn_fire = Mock()

        handle_keyboard_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE),
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
            spawn_projectile_from_helicopter_logged=spawn_fire,
            try_start_flare_salvo=lambda *_args, **_kwargs: None,
            toggle_doors_with_logging=lambda *_args, **_kwargs: None,
            Facing=SimpleNamespace(FORWARD="forward"),
            DebugSettings=lambda **kwargs: SimpleNamespace(**kwargs),
            boarded_count=lambda *_args, **_kwargs: 0,
            flares=SimpleNamespace(),
            selected_mission_index=0,
            selected_mission_id="airport",
            selected_chopper_index=0,
            selected_chopper_asset="chopper-one.png",
            debug=SimpleNamespace(show_overlay=False),
            quit_confirm=False,
            helicopter_weapon_locked=True,
        )

        spawn_fire.assert_not_called()

    def test_keyboard_flare_blocked_when_weapon_locked(self) -> None:
        controls = SimpleNamespace(
            quit=[],
            restart=[],
            toggle_debug=[],
            cycle_facing=[],
            reverse_flip=[],
            doors=[],
            flare=[pygame.K_f],
            fire=[],
            tilt_left=[],
            tilt_right=[],
        )
        audio = _RecordingAudio()
        mission = SimpleNamespace(ended=False, crash_active=False)
        helicopter = SimpleNamespace(skin_asset="chopper-one.png", facing="forward")
        start_flare = Mock()

        handle_keyboard_event(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_f),
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
            try_start_flare_salvo=start_flare,
            toggle_doors_with_logging=lambda *_args, **_kwargs: None,
            Facing=SimpleNamespace(FORWARD="forward"),
            DebugSettings=lambda **kwargs: SimpleNamespace(**kwargs),
            boarded_count=lambda *_args, **_kwargs: 0,
            flares=SimpleNamespace(),
            selected_mission_index=0,
            selected_mission_id="airport",
            selected_chopper_index=0,
            selected_chopper_asset="chopper-one.png",
            debug=SimpleNamespace(show_overlay=False),
            quit_confirm=False,
            helicopter_weapon_locked=True,
        )

        start_flare.assert_not_called()


if __name__ == "__main__":
    unittest.main()
