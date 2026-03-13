from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import random
from typing import Callable

import pygame

from .. import haptics
from ..accessibility import load_accessibility
from ..audio import AudioBank
from ..debug_overlay import DebugOverlay
from ..game_logging import create_session_logger
from ..controls import load_controls
from ..fx.dust_storm import DustStormSystem
from ..fx.fog import FogSystem
from ..fx.lightning import LightningSystem
from ..fx.rain import RainSystem
from ..fx.storm_clouds import StormCloudSystem
from ..sky_smoke import SkySmokeSystem
from .cutscenes import init_intro_cutscene
from .feedback import ScreenShakeState
from .gamepad_button_state import GamepadButtonState
from .gamepads import init_connected_joysticks
from .runtime_state import GameRuntimeState
from .state import CutsceneState, IntroCutsceneState, MissionCutsceneState
from .toast import ToastState
from .flares import FlareState


@dataclass
class RunBootstrapState:
    logger: object
    controls: object
    accessibility: object
    audio: object
    joysticks: dict[int, pygame.joystick.Joystick]
    screenshake: object
    toast: object
    gamepad_buttons: object
    set_toast: Callable[[str], None]
    particles_enabled: bool
    flashes_enabled: bool
    screenshake_enabled: bool
    screen: pygame.Surface
    assets_dir: Path
    cutscenes: object
    clock: object
    overlay: object
    sky_smoke: object
    rain: object
    fog: object
    dust: object
    lightning: object
    storm_clouds: object
    mission_choices: list[tuple[str, str]]
    selected_mission_index: int
    selected_mission_id: str
    chopper_choices: list[tuple[str, str]]
    selected_chopper_index: int
    selected_chopper_asset: str
    mode: str
    runtime: object
    flares: object


def _set_window_icon(logger: object) -> None:
    # Window icon (taskbar/alt-tab). This does not change the .exe file icon.
    try:
        module_dir = Path(__file__).resolve().parent.parent
        icon_path = module_dir / "assets" / "chopper-one.png"
        icon = pygame.image.load(str(icon_path))
        try:
            icon = pygame.transform.smoothscale(icon, (32, 32))
        except Exception:
            pass
        pygame.display.set_icon(icon)
        logger.info("WINDOW_ICON: %s", icon_path.as_posix())
    except Exception as e:
        logger.info("WINDOW_ICON: failed (%s)", type(e).__name__)


def initialize_run_bootstrap(*, window: object, debug_weather_modes: list[str]) -> RunBootstrapState:
    """Initialize startup systems and initial menu/runtime state for the main run loop."""
    pygame.init()
    logger = create_session_logger()
    _set_window_icon(logger)

    controls = load_controls(logger=logger)
    accessibility = load_accessibility(logger=logger)
    haptics.set_enabled(accessibility.rumble_enabled)
    audio = AudioBank.try_create()
    logger.info("Controls: SPACE fire | F flare | E doors (grounded) | TAB facing | R reverse | F1 debug")
    logger.info("Rescue: open compound, land near hostages, E doors to load; land at base and E to unload")
    logger.info("Gamepad: Left stick tilt | Triggers lift | A doors | X fire | Y reverse | B flare | Back facing | D-pad optional")

    pygame.joystick.init()
    screenshake = ScreenShakeState()
    toast = ToastState()
    gamepad_buttons = GamepadButtonState()

    def set_toast(message: str) -> None:
        toast.set(message)

    joysticks = init_connected_joysticks(logger=logger, set_toast=set_toast)

    particles_enabled = accessibility.particles_enabled
    flashes_enabled = accessibility.flashes_enabled
    screenshake_enabled = accessibility.screenshake_enabled

    flags = 0
    if getattr(window, "vsync", False):
        # VSYNC is honored on some platforms/drivers.
        flags |= pygame.SCALED

    screen = pygame.display.set_mode((window.width, window.height), flags)
    pygame.display.set_caption(window.title)

    module_dir = Path(__file__).resolve().parent.parent
    assets_dir = module_dir / "assets"
    cutscenes = CutsceneState(intro=IntroCutsceneState(), mission=MissionCutsceneState())
    init_intro_cutscene(cutscenes.intro, assets_dir=assets_dir, logger=logger)

    clock = pygame.time.Clock()
    overlay = DebugOverlay()

    sky_smoke = SkySmokeSystem()
    rain = RainSystem()
    fog = FogSystem()
    dust = DustStormSystem()
    lightning = LightningSystem(area_width=window.width, area_height=window.height)
    storm_clouds = StormCloudSystem(window.width, window.height)

    mission_choices: list[tuple[str, str]] = [
        ("city", "City Center Seige"),
        ("airport", "Airport Special Ops"),
        ("worship", "Worship Center Warfare"),
    ]
    selected_mission_index = 0
    selected_mission_id = mission_choices[selected_mission_index][0]

    chopper_choices: list[tuple[str, str]] = [
        ("chopper-one.png", "Classic"),
        ("chopper-two-orange.png", "Orange"),
        ("chopper-three-green.png", "Green"),
        ("chopper-four-blue.png", "Blue"),
        ("chopper-five-desert.png", "Desert"),
    ]
    selected_chopper_index = 0
    selected_chopper_asset = chopper_choices[selected_chopper_index][0]

    mode = "intro"
    runtime = GameRuntimeState()
    runtime.prev_loop_mode = mode
    runtime.weather_mode = random.choice(debug_weather_modes)
    runtime.weather_duration = random.uniform(18, 40)

    flares = FlareState()

    return RunBootstrapState(
        logger=logger,
        controls=controls,
        accessibility=accessibility,
        audio=audio,
        joysticks=joysticks,
        screenshake=screenshake,
        toast=toast,
        gamepad_buttons=gamepad_buttons,
        set_toast=set_toast,
        particles_enabled=particles_enabled,
        flashes_enabled=flashes_enabled,
        screenshake_enabled=screenshake_enabled,
        screen=screen,
        assets_dir=assets_dir,
        cutscenes=cutscenes,
        clock=clock,
        overlay=overlay,
        sky_smoke=sky_smoke,
        rain=rain,
        fog=fog,
        dust=dust,
        lightning=lightning,
        storm_clouds=storm_clouds,
        mission_choices=mission_choices,
        selected_mission_index=selected_mission_index,
        selected_mission_id=selected_mission_id,
        chopper_choices=chopper_choices,
        selected_chopper_index=selected_chopper_index,
        selected_chopper_asset=selected_chopper_asset,
        mode=mode,
        runtime=runtime,
        flares=flares,
    )
