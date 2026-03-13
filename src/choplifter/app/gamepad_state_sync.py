from __future__ import annotations


def sync_gamepad_state(
    *,
    gamepad_buttons: object,
    runtime: object,
    a_down: bool,
    b_down: bool,
    x_down: bool,
    y_down: bool,
    start_down: bool,
    rb_down: bool,
    lb_down: bool,
    back_down: bool,
    menu_dir: int,
    menu_vert: int,
) -> None:
    """Persist current gamepad button and menu-axis state for edge-trigger handling."""
    gamepad_buttons.snapshot(
        a_down=a_down,
        b_down=b_down,
        x_down=x_down,
        y_down=y_down,
        start_down=start_down,
        rb_down=rb_down,
        lb_down=lb_down,
        back_down=back_down,
    )
    runtime.prev_menu_dir = menu_dir
    runtime.prev_menu_vert = menu_vert
