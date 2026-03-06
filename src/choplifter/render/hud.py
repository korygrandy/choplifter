from __future__ import annotations

from typing import TYPE_CHECKING
import pygame

from ..game_types import HostageState
from ..helicopter import Helicopter

if TYPE_CHECKING:
    from ..mission_state import MissionState


_HUD_FONT: pygame.font.Font | None = None
_TOAST_FONT: pygame.font.Font | None = None


def draw_hud(screen: pygame.Surface, mission: MissionState, helicopter: Helicopter) -> None:
    global _HUD_FONT
    if _HUD_FONT is None:
        pygame.font.init()
        _HUD_FONT = pygame.font.SysFont("consolas", 18)

    font = _HUD_FONT

    boarded = sum(1 for h in mission.hostages if h.state is HostageState.BOARDED)
    saved = mission.stats.saved

    # Minimal always-on guidance so the rescue loop is discoverable.
    # --- VIP Mission HUD for City Siege ---
    vip_hostage = next((h for h in mission.hostages if getattr(h, "is_vip", False)), None)
    vip_status = "UNKNOWN"
    if vip_hostage:
        if vip_hostage.state.name == "SAVED":
            vip_status = "RESCUED"
        elif vip_hostage.state.name == "BOARDED":
            vip_status = "ONBOARD"
        elif vip_hostage.state.name == "EXITING":
            vip_status = "EXITING"
        elif vip_hostage.state.name == "KIA":
            vip_status = "KIA"
        else:
            vip_status = vip_hostage.state.name
    is_city_siege = getattr(mission, "mission_id", "").lower() in ("city", "city_center", "citycenter", "mission1", "m1")
    if is_city_siege and vip_hostage:
        lines = [
            f"Fuel {int(helicopter.fuel):3d}   Damage {int(helicopter.damage):3d}   Crashes {mission.crashes}/3   Sentiment {int(mission.sentiment):3d}",
            f"Objective: Rescue VIP (Purple) + Save 20 Hostages",
            f"VIP Status: {vip_status}",
            f"Hostages Saved: {saved}/20",
            f"Rescue: shoot compound (Space) → land near hostages → press E to open doors → load {boarded}/16",
            "Unload: land in base zone (flag) → press E to open doors",
        ]
    else:
        lines = [
            f"Fuel {int(helicopter.fuel):3d}   Damage {int(helicopter.damage):3d}   Crashes {mission.crashes}/3   Sentiment {int(mission.sentiment):3d}",
            f"Objective: save 20 (saved {saved}/20)",
            f"Rescue: shoot compound (Space) → land near hostages → press E to open doors → load {boarded}/16",
            "Unload: land in base zone (flag) → press E to open doors",
        ]

    if mission.invuln_seconds > 0.0:
        lines.append(f"INVULN: {mission.invuln_seconds:0.1f}s")

    x = 12
    y = screen.get_height() - 12 - len(lines) * 20
    for i, line in enumerate(lines):
        surf = font.render(line, True, (240, 240, 240))
        screen.blit(surf, (x, y + i * 20))


def draw_toast(screen: pygame.Surface, message: str) -> None:
    if not message:
        return

    global _TOAST_FONT
    if _TOAST_FONT is None:
        pygame.font.init()
        _TOAST_FONT = pygame.font.SysFont("consolas", 20)

    font = _TOAST_FONT

    text = font.render(message, True, (240, 240, 240))
    padding_x = 10
    padding_y = 8
    w = text.get_width() + padding_x * 2
    h = text.get_height() + padding_y * 2

    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 160))
    panel.blit(text, (padding_x, padding_y))

    x = screen.get_width() - w - 12
    y = 12
    screen.blit(panel, (x, y))
