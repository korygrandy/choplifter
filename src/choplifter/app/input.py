from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

import pygame


def get_active_joystick(joysticks: Mapping[int, pygame.joystick.Joystick]) -> pygame.joystick.Joystick | None:
    if not joysticks:
        return None
    # Prefer a stable order to avoid flipping between devices.
    instance_id = sorted(joysticks.keys())[0]
    return joysticks.get(instance_id)


def _axis_value(js: pygame.joystick.Joystick, axis_index: int) -> float:
    if axis_index < 0 or axis_index >= js.get_numaxes():
        return 0.0
    return float(js.get_axis(axis_index))


def _trigger_pressed(raw: float, threshold01: float) -> bool:
    # Triggers are inconsistent across drivers:
    # - Some report in [-1..1] (rest=-1, pressed=1)
    # - Some report in [0..1] (rest=0, pressed=1)
    if raw < -0.1:
        value01 = (raw + 1.0) * 0.5
    else:
        value01 = raw
    return value01 >= threshold01


@dataclass(frozen=True)
class GamepadReadout:
    tilt_left: bool
    tilt_right: bool
    lift_up: bool
    lift_down: bool
    menu_dir: int
    menu_vert: int

    a_down: bool
    b_down: bool
    x_down: bool
    y_down: bool
    start_down: bool
    rb_down: bool
    lb_down: bool
    back_down: bool


def read_gamepad(
    js: pygame.joystick.Joystick,
    *,
    deadzone: float,
    trigger_threshold01: float,
) -> GamepadReadout:
    x_axis = _axis_value(js, 0)
    tilt_left = x_axis <= -deadzone
    tilt_right = x_axis >= deadzone

    menu_dir = -1 if tilt_left else (1 if tilt_right else 0)
    menu_vert = 0

    lift_up = False
    lift_down = False

    if js.get_numhats() > 0:
        hat_x, hat_y = js.get_hat(0)
        tilt_left = tilt_left or hat_x <= -1
        tilt_right = tilt_right or hat_x >= 1
        lift_up = lift_up or hat_y >= 1
        lift_down = lift_down or hat_y <= -1
        if hat_x <= -1:
            menu_dir = -1
        elif hat_x >= 1:
            menu_dir = 1
        if hat_y >= 1:
            menu_vert = -1
        elif hat_y <= -1:
            menu_vert = 1
    else:
        # Fallback: use left stick Y for menu up/down.
        y_axis = _axis_value(js, 1)
        if y_axis <= -deadzone:
            menu_vert = -1
        elif y_axis >= deadzone:
            menu_vert = 1

    axes = js.get_numaxes()
    if axes >= 6:
        lift_down = _trigger_pressed(_axis_value(js, 4), threshold01=trigger_threshold01)
        lift_up = _trigger_pressed(_axis_value(js, 5), threshold01=trigger_threshold01)
    elif axes >= 3:
        # Common fallback: a combined trigger axis.
        trig = _axis_value(js, 2)
        lift_down = trig <= -0.35
        lift_up = trig >= 0.35

    a_down = bool(js.get_numbuttons() > 0 and js.get_button(0))
    b_down = bool(js.get_numbuttons() > 1 and js.get_button(1))
    x_down = bool(js.get_numbuttons() > 2 and js.get_button(2))
    y_down = bool(js.get_numbuttons() > 3 and js.get_button(3))
    start_down = bool(js.get_numbuttons() > 7 and js.get_button(7))
    rb_down = bool(js.get_numbuttons() > 5 and js.get_button(5))
    lb_down = bool(js.get_numbuttons() > 4 and js.get_button(4))
    back_down = bool(js.get_numbuttons() > 6 and js.get_button(6))

    return GamepadReadout(
        tilt_left=tilt_left,
        tilt_right=tilt_right,
        lift_up=lift_up,
        lift_down=lift_down,
        menu_dir=menu_dir,
        menu_vert=menu_vert,
        a_down=a_down,
        b_down=b_down,
        x_down=x_down,
        y_down=y_down,
        start_down=start_down,
        rb_down=rb_down,
        lb_down=lb_down,
        back_down=back_down,
    )
