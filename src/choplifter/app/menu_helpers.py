from __future__ import annotations


def cycle_index(index: int, direction: int, length: int) -> int:
    if length <= 0:
        return 0
    if direction == 0:
        return int(index) % length
    return (int(index) + int(direction)) % length


def move_pause_focus(current: str, direction: int) -> str:
    # Order matches main.py behavior.
    order = ["choppers", "restart_mission", "restart_game", "mute", "quit"]
    if current not in order:
        current = "choppers"
    if direction == 0:
        return current

    i = order.index(current)
    if direction < 0:
        i = (i - 1) % len(order)
    else:
        i = (i + 1) % len(order)
    return order[i]
