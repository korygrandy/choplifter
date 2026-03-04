from __future__ import annotations

from collections.abc import Callable

import pygame


def init_connected_joysticks(
    *,
    logger: object,
    set_toast: Callable[[str], None],
) -> dict[int, pygame.joystick.Joystick]:
    joysticks: dict[int, pygame.joystick.Joystick] = {}

    for i in range(pygame.joystick.get_count()):
        js = pygame.joystick.Joystick(i)
        js.init()
        joysticks[js.get_instance_id()] = js
        name = js.get_name() or "Gamepad"
        getattr(logger, "info")("GAMEPAD_CONNECTED: %s", name)
        getattr(logger, "info")(
            "GAMEPAD_INFO: axes=%d buttons=%d hats=%d",
            js.get_numaxes(),
            js.get_numbuttons(),
            js.get_numhats(),
        )
        set_toast(f"Gamepad connected: {name}")

    return joysticks


def handle_joy_device_added(
    device_index: int,
    *,
    joysticks: dict[int, pygame.joystick.Joystick],
    logger: object,
    set_toast: Callable[[str], None],
) -> None:
    js = pygame.joystick.Joystick(device_index)
    js.init()
    joysticks[js.get_instance_id()] = js
    name = js.get_name() or "Gamepad"
    getattr(logger, "info")("GAMEPAD_CONNECTED: %s", name)
    getattr(logger, "info")(
        "GAMEPAD_INFO: axes=%d buttons=%d hats=%d",
        js.get_numaxes(),
        js.get_numbuttons(),
        js.get_numhats(),
    )
    set_toast(f"Gamepad connected: {name}")


def handle_joy_device_removed(
    instance_id: int,
    *,
    joysticks: dict[int, pygame.joystick.Joystick],
    logger: object,
    set_toast: Callable[[str], None],
) -> None:
    removed = joysticks.pop(instance_id, None)
    name = removed.get_name() if removed is not None else "Gamepad"
    getattr(logger, "info")("GAMEPAD_DISCONNECTED: %s", name)
    set_toast(f"Gamepad disconnected: {name}")
