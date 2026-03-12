from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GamepadButtonState:
    a_down: bool = False
    b_down: bool = False
    x_down: bool = False
    y_down: bool = False
    start_down: bool = False
    rb_down: bool = False
    lb_down: bool = False
    back_down: bool = False

    def reset(self) -> None:
        self.a_down = False
        self.b_down = False
        self.x_down = False
        self.y_down = False
        self.start_down = False
        self.rb_down = False
        self.lb_down = False
        self.back_down = False

    def clear_on_disconnect(self) -> None:
        self.a_down = False
        self.b_down = False
        self.x_down = False
        self.y_down = False
        self.back_down = False

    def snapshot(
        self,
        *,
        a_down: bool,
        b_down: bool,
        x_down: bool,
        y_down: bool,
        start_down: bool,
        rb_down: bool,
        lb_down: bool,
        back_down: bool,
    ) -> None:
        self.a_down = a_down
        self.b_down = b_down
        self.x_down = x_down
        self.y_down = y_down
        self.start_down = start_down
        self.rb_down = rb_down
        self.lb_down = lb_down
        self.back_down = back_down