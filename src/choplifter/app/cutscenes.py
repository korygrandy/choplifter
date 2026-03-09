from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pygame

from ..intro_video import IntroVideoPlayer
from ..rendering import draw_intro_cutscene, draw_skip_overlay
from .state import IntroCutsceneState, MissionCutsceneState

if TYPE_CHECKING:
    from logging import Logger


def init_intro_cutscene(state: IntroCutsceneState, *, assets_dir: Path, logger: Logger) -> None:
    """Initialize the launch intro cutscene.

    Behavior matches the legacy inline logic in `main.py`:
    - Prefer `game-intro.avi`, then `city-seige-intro.avi`, then legacy `intro.mpg`.
    - If no video player is available, use an in-engine title card.
    """

    # Prefer the game intro AVI, then fall back to prior intro assets.
    intro_candidates = (
        assets_dir / "game-intro.avi",
        assets_dir / "city-seige-intro.avi",
        assets_dir / "intro.mpg",
    )
    intro_video_path = next((p for p in intro_candidates if p.exists()), intro_candidates[0])
    state.video_path = intro_video_path

    state.video = IntroVideoPlayer.try_create(intro_video_path)
    if state.video is None:
        logger.info(
            "INTRO_VIDEO: disabled path=%s exists=%s reason=%s",
            intro_video_path.as_posix(),
            intro_video_path.exists(),
            IntroVideoPlayer.last_error(),
        )
        state.seconds = 4.25
    else:
        logger.info(
            "INTRO_VIDEO: enabled path=%s fps=%0.1f duration_s=%0.2f",
            intro_video_path.as_posix(),
            float(state.video.fps),
            float(state.video.duration_s),
        )
        state.seconds = float(state.video.duration_s) if (state.video.duration_s > 0.5) else 4.25


def close_intro(state: IntroCutsceneState, *, immediate: bool = False) -> None:
    if state.video is not None:
        state.video.close(immediate=immediate)
        state.video = None


def skip_intro(state: IntroCutsceneState) -> None:
    state.t = 0.0
    close_intro(state, immediate=True)


def update_intro(state: IntroCutsceneState, dt: float) -> bool:
    """Advance intro playback. Returns True if the intro is finished."""
    state.t += float(dt)

    if state.video is not None:
        state.video.update(dt)
        if state.video.done:
            state.t = 0.0
            close_intro(state)
            return True

    if state.t >= float(state.seconds):
        state.t = 0.0
        close_intro(state)
        return True

    return False


def draw_intro(state: IntroCutsceneState, target: pygame.Surface, *, skip_hint: str) -> None:
    if state.video is not None:
        state.video.draw(target)
        draw_skip_overlay(target, text=skip_hint)
    else:
        draw_intro_cutscene(target, state.t, show_skip=True, skip_text=skip_hint)


def start_mission_cutscene(
    state: MissionCutsceneState,
    *,
    cutscene_path: Path,
    logger: Logger,
    event_id: str,
    mission_id: str,
) -> bool:
    """Attempt to start a mission cutscene.

    Returns True if cutscene playback started (caller should enter cutscene mode).
    """

    cutscene_video = IntroVideoPlayer.try_create(cutscene_path)
    if cutscene_video is None:
        logger.info(
            "MISSION_CUTSCENE: skipped id=%s mission_id=%s path=%s exists=%s reason=%s",
            event_id,
            mission_id,
            cutscene_path.as_posix(),
            cutscene_path.exists(),
            IntroVideoPlayer.last_error(),
        )
        return False

    logger.info(
        "MISSION_CUTSCENE: start id=%s mission_id=%s path=%s fps=%0.1f duration_s=%0.2f",
        event_id,
        mission_id,
        cutscene_path.as_posix(),
        float(cutscene_video.fps),
        float(cutscene_video.duration_s),
    )

    state.video = cutscene_video
    state.t = 0.0
    state.seconds = float(cutscene_video.duration_s) if float(cutscene_video.duration_s) > 0.5 else 6.0
    return True


def close_mission_cutscene(state: MissionCutsceneState, *, immediate: bool = False) -> None:
    if state.video is not None:
        state.video.close(immediate=immediate)
        state.video = None


def skip_mission_cutscene(state: MissionCutsceneState) -> None:
    state.t = 0.0
    close_mission_cutscene(state, immediate=True)


def update_mission_cutscene(state: MissionCutsceneState, dt: float) -> bool:
    """Advance mission cutscene playback. Returns True if the cutscene is finished."""
    state.t += float(dt)

    if state.video is not None:
        state.video.update(dt)
        if state.video.done:
            state.t = 0.0
            close_mission_cutscene(state)
            return True

    if state.t >= float(state.seconds):
        state.t = 0.0
        close_mission_cutscene(state)
        return True

    return False


def draw_mission_cutscene(state: MissionCutsceneState, target: pygame.Surface, *, skip_hint: str) -> None:
    if state.video is not None:
        state.video.draw(target)
        draw_skip_overlay(target, text=skip_hint)
    else:
        target.fill((0, 0, 0))
        draw_skip_overlay(target, text=skip_hint)
