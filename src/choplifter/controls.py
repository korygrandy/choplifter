from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from pathlib import Path

import pygame


def _try_key_code(name: str, *, logger: logging.Logger | None) -> int | None:
    try:
        return int(pygame.key.key_code(name))
    except Exception:
        if logger is not None:
            logger.info("CONTROLS: invalid key name ignored: %s", name)
        return None


def _coerce_key_list(value: object, *, logger: logging.Logger | None) -> list[int]:
    if value is None:
        return []
    if isinstance(value, int):
        return [value]
    if isinstance(value, str):
        code = _try_key_code(value, logger=logger)
        return [code] if code is not None else []
    if isinstance(value, list):
        out: list[int] = []
        for item in value:
            if isinstance(item, int):
                out.append(item)
            elif isinstance(item, str):
                code = _try_key_code(item, logger=logger)
                if code is not None:
                    out.append(code)
        return out
    return []


@dataclass(frozen=True)
class Controls:
    # Continuous axes (polling via pygame.key.get_pressed).
    tilt_left: tuple[int, ...]
    tilt_right: tuple[int, ...]
    lift_up: tuple[int, ...]
    lift_down: tuple[int, ...]
    brake: tuple[int, ...]

    # Discrete actions (event.key in KEYDOWN).
    quit: tuple[int, ...]
    restart: tuple[int, ...]
    toggle_debug: tuple[int, ...]
    cycle_facing: tuple[int, ...]
    reverse_flip: tuple[int, ...]
    doors: tuple[int, ...]
    fire: tuple[int, ...]

    @staticmethod
    def defaults() -> "Controls":
        return Controls(
            tilt_left=(pygame.K_LEFT, pygame.K_a),
            tilt_right=(pygame.K_RIGHT, pygame.K_d),
            lift_up=(pygame.K_UP, pygame.K_w),
            lift_down=(pygame.K_DOWN, pygame.K_s),
            brake=(pygame.K_LSHIFT, pygame.K_RSHIFT),
            quit=(pygame.K_ESCAPE,),
            restart=(pygame.K_RETURN,),
            toggle_debug=(pygame.K_F1,),
            cycle_facing=(pygame.K_TAB,),
            reverse_flip=(pygame.K_r,),
            doors=(pygame.K_e,),
            fire=(pygame.K_SPACE,),
        )


def load_controls(*, logger: logging.Logger | None = None) -> Controls:
    """Loads optional key rebinding from `controls.json` at the repo root.

    If the file doesn't exist or can't be parsed, defaults are used.

    Format example:
    {
      "tilt_left": ["left", "a"],
      "fire": ["space"],
      "doors": ["e"]
    }
    """

    controls = Controls.defaults()

    module_dir = Path(__file__).resolve().parent
    repo_root = module_dir.parents[1]
    path = repo_root / "controls.json"
    if not path.exists():
        return controls

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        if logger is not None:
            logger.info("CONTROLS: failed to load controls.json; using defaults")
        return controls

    if not isinstance(data, dict):
        if logger is not None:
            logger.info("CONTROLS: controls.json must be an object; using defaults")
        return controls

    def override(field: str, existing: tuple[int, ...]) -> tuple[int, ...]:
        raw = data.get(field)
        codes = _coerce_key_list(raw, logger=logger)
        return tuple(codes) if codes else existing

    return Controls(
        tilt_left=override("tilt_left", controls.tilt_left),
        tilt_right=override("tilt_right", controls.tilt_right),
        lift_up=override("lift_up", controls.lift_up),
        lift_down=override("lift_down", controls.lift_down),
        brake=override("brake", controls.brake),
        quit=override("quit", controls.quit),
        restart=override("restart", controls.restart),
        toggle_debug=override("toggle_debug", controls.toggle_debug),
        cycle_facing=override("cycle_facing", controls.cycle_facing),
        reverse_flip=override("reverse_flip", controls.reverse_flip),
        doors=override("doors", controls.doors),
        fire=override("fire", controls.fire),
    )


def pressed(keys: pygame.key.ScancodeWrapper, codes: tuple[int, ...]) -> bool:
    return any(keys[c] for c in codes)


def matches_key(key: int, codes: tuple[int, ...]) -> bool:
    return key in codes
