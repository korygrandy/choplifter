from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..intro_video import IntroVideoPlayer


@dataclass(slots=True)
class IntroCutsceneState:
    t: float = 0.0
    seconds: float = 4.25
    video: IntroVideoPlayer | None = None
    video_path: Path | None = None


@dataclass(slots=True)
class MissionCutsceneState:
    t: float = 0.0
    seconds: float = 0.0
    video: IntroVideoPlayer | None = None


@dataclass(slots=True)
class CutsceneState:
    intro: IntroCutsceneState
    mission: MissionCutsceneState
