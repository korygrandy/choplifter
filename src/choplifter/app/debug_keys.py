from __future__ import annotations

from typing import Sequence

import pygame


def handle_debug_weather_keydown(
    *,
    key: int,
    debug_mode: bool,
    debug_weather_index: int,
    debug_weather_modes: Sequence[str],
) -> tuple[bool, bool, int, str | None, str | None]:
    """Handle F3/F5/F6 debug-weather key events.

    Returns: (handled, next_debug_mode, next_weather_index, toast_message, selected_weather_mode)
    """
    if key == pygame.K_F3:
        next_debug_mode = not debug_mode
        return True, next_debug_mode, debug_weather_index, f"Debug mode: {'ON' if next_debug_mode else 'OFF'} (F3)", None

    if debug_mode and key == pygame.K_F5:
        next_index = (debug_weather_index + 1) % max(1, len(debug_weather_modes))
        selected_mode = debug_weather_modes[next_index]
        return True, debug_mode, next_index, f"Weather: {selected_mode}", selected_mode

    if debug_mode and key == pygame.K_F6:
        next_index = (debug_weather_index - 1) % max(1, len(debug_weather_modes))
        selected_mode = debug_weather_modes[next_index]
        return True, debug_mode, next_index, f"Weather: {selected_mode}", selected_mode

    return False, debug_mode, debug_weather_index, None, None