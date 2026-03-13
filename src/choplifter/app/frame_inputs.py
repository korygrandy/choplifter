from __future__ import annotations

from dataclasses import dataclass

import pygame

from .. import haptics
from ..controls import pressed
from .input import read_active_gamepad_snapshot


@dataclass
class FrameInputSnapshot:
    kb_tilt_left: bool
    kb_tilt_right: bool
    kb_lift_up: bool
    kb_lift_down: bool
    kb_brake: bool
    active_gamepad: object | None


def read_frame_input_snapshot(
    *,
    controls: object,
    joysticks: dict[int, pygame.joystick.Joystick],
    gamepad_buttons: object,
    gamepad_deadzone: float,
    trigger_threshold: float,
) -> FrameInputSnapshot:
    """Read keyboard/gamepad inputs for the current frame and sync active haptics joystick."""
    keys = pygame.key.get_pressed()
    kb_tilt_left = bool(pressed(keys, controls.tilt_left))
    kb_tilt_right = bool(pressed(keys, controls.tilt_right))
    kb_lift_up = bool(pressed(keys, controls.lift_up))
    kb_lift_down = bool(pressed(keys, controls.lift_down))
    kb_brake = bool(pressed(keys, controls.brake))

    active_gamepad = read_active_gamepad_snapshot(
        joysticks,
        button_state=gamepad_buttons,
        deadzone=float(gamepad_deadzone),
        trigger_threshold01=float(trigger_threshold),
    )
    active_js = active_gamepad.joystick if active_gamepad is not None else None
    haptics.set_active_joystick(active_js)

    return FrameInputSnapshot(
        kb_tilt_left=kb_tilt_left,
        kb_tilt_right=kb_tilt_right,
        kb_lift_up=kb_lift_up,
        kb_lift_down=kb_lift_down,
        kb_brake=kb_brake,
        active_gamepad=active_gamepad,
    )
