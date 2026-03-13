from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from .debug_keys import handle_debug_weather_keydown
from .pause_controls import handle_pause_quit_confirm_keydown


@dataclass
class KeydownPreflightResult:
    handled: bool
    running: bool
    mode: str
    pause_focus: str
    quit_confirm: bool
    debug_mode: bool
    debug_weather_index: int
    debug_toast: str | None
    selected_weather_mode: str | None


def handle_keydown_preflight(
    *,
    key: int,
    mode: str,
    mission_ended: bool,
    pause_focus: str,
    quit_confirm: bool,
    debug_mode: bool,
    debug_weather_index: int,
    debug_weather_modes: Sequence[str],
    set_toast: Callable[[str], None],
    audio: object,
    logger: object,
    handle_mission_end_keyboard_navigation_fn: Callable[..., tuple[bool, str]],
    apply_pause_transition_fn: Callable[..., object],
) -> KeydownPreflightResult:
    """Handle KEYDOWN cases that can short-circuit before the main keyboard handler."""
    handled_mission_end, next_mode = handle_mission_end_keyboard_navigation_fn(
        key=key,
        mode=mode,
        mission_ended=mission_ended,
        set_toast=set_toast,
    )
    if handled_mission_end:
        pause_transition = apply_pause_transition_fn(
            prev_mode=mode,
            next_mode=next_mode,
            pause_focus=pause_focus,
            audio=audio,
        )
        return KeydownPreflightResult(
            handled=True,
            running=True,
            mode=next_mode,
            pause_focus=pause_transition.pause_focus,
            quit_confirm=quit_confirm,
            debug_mode=debug_mode,
            debug_weather_index=debug_weather_index,
            debug_toast=None,
            selected_weather_mode=None,
        )

    handled_quit_confirm, keep_running, next_quit_confirm = handle_pause_quit_confirm_keydown(
        mode=mode,
        quit_confirm=quit_confirm,
        key=key,
    )
    if handled_quit_confirm:
        if logger is not None:
            if not keep_running:
                logger.info("PAUSE MENU: Keyboard confirm quit (Enter/Space) on quit_confirm, exiting game")
            else:
                logger.info("PAUSE MENU: Keyboard cancel quit (Escape) on quit_confirm, returning to pause menu")
        return KeydownPreflightResult(
            handled=True,
            running=keep_running,
            mode=mode,
            pause_focus=pause_focus,
            quit_confirm=next_quit_confirm,
            debug_mode=debug_mode,
            debug_weather_index=debug_weather_index,
            debug_toast=None,
            selected_weather_mode=None,
        )

    handled_debug_key, next_debug_mode, next_debug_weather_index, debug_toast, selected_weather_mode = handle_debug_weather_keydown(
        key=key,
        debug_mode=debug_mode,
        debug_weather_index=debug_weather_index,
        debug_weather_modes=debug_weather_modes,
    )
    if handled_debug_key:
        return KeydownPreflightResult(
            handled=True,
            running=True,
            mode=mode,
            pause_focus=pause_focus,
            quit_confirm=quit_confirm,
            debug_mode=next_debug_mode,
            debug_weather_index=next_debug_weather_index,
            debug_toast=debug_toast,
            selected_weather_mode=selected_weather_mode,
        )

    return KeydownPreflightResult(
        handled=False,
        running=True,
        mode=mode,
        pause_focus=pause_focus,
        quit_confirm=quit_confirm,
        debug_mode=debug_mode,
        debug_weather_index=debug_weather_index,
        debug_toast=None,
        selected_weather_mode=None,
    )