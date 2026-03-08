from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING

import pygame

from ..app.boarding_status import compute_boarding_ux_status
from ..game_types import HostageState
from ..helicopter import Helicopter

if TYPE_CHECKING:
    from ..mission_state import MissionState


_HUD_FONT: pygame.font.Font | None = None
_HUD_SMALL_FONT: pygame.font.Font | None = None
_TOAST_FONT: pygame.font.Font | None = None
_HUD_ICON_CACHE: dict[tuple[str, int], pygame.Surface | None] = {}
_LIFE_ICON_CACHE: dict[tuple[str, int, bool], pygame.Surface | None] = {}


def _assets_ui_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "assets" / "ui"


def _load_hud_icon(name: str, size: int) -> pygame.Surface | None:
    key = (name, size)
    if key in _HUD_ICON_CACHE:
        return _HUD_ICON_CACHE[key]

    icon_path = _assets_ui_dir() / f"{name}.png"
    if icon_path.exists():
        try:
            surf = pygame.image.load(str(icon_path)).convert_alpha()
            surf = pygame.transform.smoothscale(surf, (size, size))
            _HUD_ICON_CACHE[key] = surf
            return surf
        except Exception:
            pass

    _HUD_ICON_CACHE[key] = None
    return None


def _draw_fallback_icon(target: pygame.Surface, kind: str, x: int, y: int, size: int) -> None:
    cx = x + size // 2
    cy = y + size // 2
    if kind == "fuel":
        pygame.draw.rect(target, (220, 180, 70), (x + 2, y + 3, size - 4, size - 6), border_radius=3)
        pygame.draw.rect(target, (36, 36, 36), (x + size - 5, y + 7, 3, size - 14), border_radius=1)
    elif kind == "health":
        pygame.draw.rect(target, (220, 60, 60), (cx - 3, y + 3, 6, size - 6), border_radius=2)
        pygame.draw.rect(target, (220, 60, 60), (x + 3, cy - 3, size - 6, 6), border_radius=2)
    elif kind == "crash":
        pygame.draw.polygon(target, (240, 210, 100), [(x + 2, y + 2), (x + size - 2, cy), (x + 2, y + size - 2)])
    elif kind == "sentiment":
        pygame.draw.circle(target, (80, 200, 120), (cx, cy), max(3, size // 2 - 3), 2)
        pygame.draw.arc(target, (80, 200, 120), (x + 3, y + 4, size - 6, size - 6), 0.2, 2.9, 2)
    elif kind == "saved":
        pygame.draw.circle(target, (120, 180, 255), (cx, cy), max(3, size // 2 - 3), 2)
        pygame.draw.circle(target, (120, 180, 255), (cx, cy - 2), max(2, size // 5))
    elif kind == "vip":
        pygame.draw.circle(target, (255, 215, 70), (cx, cy), max(3, size // 2 - 4), 2)
        pygame.draw.circle(target, (255, 245, 185), (cx, cy), 2)
    else:
        pygame.draw.circle(target, (220, 220, 220), (cx, cy), max(3, size // 2 - 4), 2)


def _draw_vip_crown_indicator(target: pygame.Surface, *, x: int, y: int, size: int, mission_time: float) -> None:
    cx = x + size // 2
    cy = y + size // 2 + 2

    # Match in-world VIP marker language: purple hostage circle with black outline.
    dot_r = max(4, size // 3)
    pygame.draw.circle(target, (170, 65, 220), (cx, cy), dot_r)
    pygame.draw.circle(target, (25, 25, 25), (cx, cy), dot_r, 1)

    alpha = int(127.5 * (math.sin(float(mission_time) * 5.2) + 1.0))
    alpha = max(36, min(255, alpha))

    crown_w = max(10, int(size * 0.95))
    crown_h = max(7, int(size * 0.62))
    crown = pygame.Surface((crown_w, crown_h), pygame.SRCALPHA)
    points = [
        (1, crown_h - 2),
        (max(2, crown_w // 4), max(1, crown_h // 3)),
        (crown_w // 2 - 1, crown_h - 4),
        (crown_w // 2 + 1, 0),
        (crown_w // 2 + 3, crown_h - 4),
        (crown_w - max(2, crown_w // 4), max(1, crown_h // 3)),
        (crown_w - 1, crown_h - 2),
    ]
    pygame.draw.polygon(crown, (255, 220, 70, alpha), points)
    pygame.draw.polygon(crown, (255, 245, 185, min(255, alpha + 20)), points, 1)
    crown.set_alpha(alpha)

    crown_x = cx - crown_w // 2
    crown_y = cy - dot_r - crown_h + 2
    target.blit(crown, (crown_x, crown_y))


def _draw_stat_chip(
    screen: pygame.Surface,
    *,
    x: int,
    y: int,
    label: str,
    value: str,
    icon_name: str,
    icon_kind: str,
    label_font: pygame.font.Font,
    value_font: pygame.font.Font,
    panel_color: tuple[int, int, int, int] = (0, 0, 0, 152),
    mission_time: float = 0.0,
) -> None:
    chip_w = 198
    chip_h = 34
    icon_size = 18
    panel = pygame.Surface((chip_w, chip_h), pygame.SRCALPHA)
    panel.fill(panel_color)

    ix = 8
    iy = (chip_h - icon_size) // 2
    if icon_kind == "vip":
        _draw_vip_crown_indicator(panel, x=ix, y=iy, size=icon_size, mission_time=mission_time)
    else:
        icon = _load_hud_icon(icon_name, icon_size)
        if icon is not None:
            panel.blit(icon, (ix, iy))
        else:
            _draw_fallback_icon(panel, icon_kind, ix, iy, icon_size)

    label_surf = label_font.render(label, True, (192, 206, 224))
    value_surf = value_font.render(value, True, (245, 245, 245))
    panel.blit(label_surf, (34, 5))
    panel.blit(value_surf, (34, 16))
    screen.blit(panel, (x, y))


def _draw_fuel_gauge_chip(
    screen: pygame.Surface,
    *,
    x: int,
    y: int,
    fuel_value: float,
    label_font: pygame.font.Font,
    value_font: pygame.font.Font,
    panel_color: tuple[int, int, int, int] = (0, 0, 0, 152),
) -> None:
    chip_w = 198
    chip_h = 34
    icon_size = 18

    panel = pygame.Surface((chip_w, chip_h), pygame.SRCALPHA)
    panel.fill(panel_color)

    icon = _load_hud_icon("hud_fuel", icon_size)
    ix = 8
    iy = (chip_h - icon_size) // 2
    if icon is not None:
        panel.blit(icon, (ix, iy))
    else:
        _draw_fallback_icon(panel, "fuel", ix, iy, icon_size)

    fuel = max(0.0, min(100.0, float(fuel_value)))
    ratio = fuel / 100.0

    panel.blit(label_font.render("FUEL", True, (192, 206, 224)), (34, 4))
    pct_surf = value_font.render(f"{int(round(fuel)):3d}%", True, (245, 245, 245))
    panel.blit(pct_surf, (chip_w - pct_surf.get_width() - 8, 2))

    bar_x = 34
    bar_y = 19
    bar_w = chip_w - bar_x - 10
    bar_h = 10
    inner_w = max(1, bar_w - 2)
    fill_w = int(inner_w * ratio)

    pygame.draw.rect(panel, (28, 34, 40), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
    pygame.draw.rect(panel, (115, 128, 142), (bar_x, bar_y, bar_w, bar_h), 1, border_radius=4)

    if ratio >= 0.60:
        fill_color = (78, 190, 116)
    elif ratio >= 0.30:
        fill_color = (232, 186, 72)
    else:
        fill_color = (228, 86, 72)

    if fill_w > 0:
        # Fill starts at the left edge so the visible fuel line retreats left as fuel is consumed.
        pygame.draw.rect(panel, fill_color, (bar_x + 1, bar_y + 1, fill_w, bar_h - 2), border_radius=3)

    screen.blit(panel, (x, y))


def _draw_health_icons_chip(
    screen: pygame.Surface,
    *,
    x: int,
    y: int,
    damage_value: float,
    label_font: pygame.font.Font,
    panel_color: tuple[int, int, int, int] = (0, 0, 0, 152),
) -> None:
    chip_w = 198
    chip_h = 34
    icon_size = 18

    panel = pygame.Surface((chip_w, chip_h), pygame.SRCALPHA)
    panel.fill(panel_color)

    icon = _load_hud_icon("hud_health", icon_size)
    ix = 8
    iy = (chip_h - icon_size) // 2
    if icon is not None:
        panel.blit(icon, (ix, iy))
    else:
        _draw_fallback_icon(panel, "health", ix, iy, icon_size)

    damage = max(0.0, min(100.0, float(damage_value)))
    health_pct = 100.0 - damage
    # 10 pips total, one pip per 10% remaining health.
    # Keep a fractional remainder so values like 95% show a partial final pip.
    active_full = int(health_pct // 10.0)
    active_partial = (health_pct % 10.0) / 10.0

    panel.blit(label_font.render("HEALTH", True, (192, 206, 224)), (34, 4))

    pips = 10
    pip_gap = 3
    pips_x = 34
    pips_y = 18
    pips_w = chip_w - pips_x - 10
    pip_w = max(4, (pips_w - (pips - 1) * pip_gap) // pips)
    pip_h = 9

    for i in range(pips):
        px = pips_x + i * (pip_w + pip_gap)
        if i < active_full:
            if i >= 7:
                fill = (72, 190, 114)
            elif i >= 4:
                fill = (230, 188, 78)
            else:
                fill = (228, 88, 74)
            pygame.draw.rect(panel, fill, (px, pips_y, pip_w, pip_h), border_radius=3)
        elif i == active_full and active_partial > 0.0 and active_full < pips:
            if i >= 7:
                fill = (72, 190, 114)
            elif i >= 4:
                fill = (230, 188, 78)
            else:
                fill = (228, 88, 74)
            fill_w = max(1, min(pip_w, int(round(pip_w * active_partial))))
            pygame.draw.rect(panel, fill, (px, pips_y, fill_w, pip_h), border_radius=3)
            if fill_w < pip_w:
                pygame.draw.rect(panel, (44, 48, 54), (px + fill_w, pips_y, pip_w - fill_w, pip_h), border_radius=3)
        else:
            pygame.draw.rect(panel, (44, 48, 54), (px, pips_y, pip_w, pip_h), border_radius=3)

    screen.blit(panel, (x, y))


def _load_life_icon(asset_name: str, size_w: int, *, lost: bool) -> pygame.Surface | None:
    key = (asset_name, size_w, lost)
    if key in _LIFE_ICON_CACHE:
        return _LIFE_ICON_CACHE[key]

    asset_path = Path(__file__).resolve().parent.parent / "assets" / asset_name
    if not asset_path.exists():
        _LIFE_ICON_CACHE[key] = None
        return None

    try:
        surf = pygame.image.load(str(asset_path)).convert_alpha()
        ow, oh = surf.get_size()
        if ow <= 0 or oh <= 0:
            _LIFE_ICON_CACHE[key] = None
            return None

        scale = float(size_w) / float(ow)
        out_h = max(1, int(oh * scale))
        out = pygame.transform.smoothscale(surf, (size_w, out_h))

        if lost:
            # Grayscale-style dimming for spent lives.
            out = out.copy()
            out.fill((110, 110, 110, 255), special_flags=pygame.BLEND_RGB_MULT)
            out.set_alpha(105)

        _LIFE_ICON_CACHE[key] = out
        return out
    except Exception:
        _LIFE_ICON_CACHE[key] = None
        return None


def _draw_lives_strip(screen: pygame.Surface, mission: MissionState, helicopter: Helicopter, *, x: int, y: int) -> None:
    total_lives = 3
    crashes = max(0, int(getattr(mission, "crashes", 0)))
    remaining = max(0, total_lives - crashes)

    panel_w = 198
    panel_h = 38
    panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 152))

    icon_w = 60
    gap = 8
    total_icons_w = total_lives * icon_w + (total_lives - 1) * gap
    start_x = max(0, (panel_w - total_icons_w) // 2)
    icon_y = 3
    for i in range(total_lives):
        lost = i >= remaining
        icon = _load_life_icon(getattr(helicopter, "skin_asset", "chopper-one.png"), icon_w, lost=lost)
        draw_x = start_x + i * (icon_w + gap)
        if icon is not None:
            draw_y = max(0, (panel_h - icon.get_height()) // 2)
            panel.blit(icon, (draw_x, draw_y))
        else:
            # Fallback life marker if icon load fails.
            color = (120, 200, 120) if not lost else (90, 90, 90)
            pygame.draw.rect(panel, color, (draw_x + 2, icon_y + 10, 28, 14), border_radius=4)
            pygame.draw.rect(panel, (25, 25, 25), (draw_x + 2, icon_y + 10, 28, 14), 1, border_radius=4)

    screen.blit(panel, (x, y))


def draw_hud(screen: pygame.Surface, mission: MissionState, helicopter: Helicopter) -> None:
    global _HUD_FONT, _HUD_SMALL_FONT
    if _HUD_FONT is None:
        pygame.font.init()
        _HUD_FONT = pygame.font.SysFont("consolas", 18)
    if _HUD_SMALL_FONT is None:
        pygame.font.init()
        _HUD_SMALL_FONT = pygame.font.SysFont("consolas", 14)

    font = _HUD_FONT
    small = _HUD_SMALL_FONT

    boarding_ux = compute_boarding_ux_status(mission, helicopter)
    boarded = boarding_ux.boarded
    saved = mission.stats.saved
    doors_state = "OPEN" if helicopter.doors_open else "CLOSED"
    grounded_state = "YES" if helicopter.grounded else "NO"
    rescue_ready = "READY" if helicopter.grounded and helicopter.doors_open else "NOT READY"
    boarding_status = f"{boarding_ux.state.upper()}: {boarding_ux.detail}"

    hud_x = 12
    lives_y = 8
    _draw_lives_strip(screen, mission, helicopter, x=hud_x, y=lives_y)

    # Start stat stack below the lives strip.
    hud_y = lives_y + 48

    _draw_fuel_gauge_chip(
        screen,
        x=hud_x,
        y=hud_y,
        fuel_value=helicopter.fuel,
        label_font=small,
        value_font=font,
    )
    _draw_health_icons_chip(
        screen,
        x=hud_x,
        y=hud_y + 38,
        damage_value=helicopter.damage,
        label_font=small,
    )
    _draw_stat_chip(
        screen,
        x=hud_x,
        y=hud_y + 76,
        label="SENTIMENT",
        value=f"{int(mission.sentiment):3d}",
        icon_name="hud_sentiment",
        icon_kind="sentiment",
        label_font=small,
        value_font=font,
    )
    _draw_stat_chip(
        screen,
        x=hud_x,
        y=hud_y + 114,
        label="SAVED / TARGET",
        value=f"{saved}/20",
        icon_name="hud_saved",
        icon_kind="saved",
        label_font=small,
        value_font=font,
    )

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
        _draw_stat_chip(
            screen,
            x=hud_x,
            y=hud_y + 152,
            label="VIP",
            value=vip_status,
            icon_name="hud_vip",
            icon_kind="vip",
            label_font=small,
            value_font=font,
            panel_color=(36, 14, 52, 172),
            mission_time=float(getattr(mission, "elapsed_seconds", 0.0)),
        )

    if is_city_siege and vip_hostage:
        lines = [
            "Objective: Rescue VIP and save 20 hostages",
            f"Rescue flow: Open compound -> land -> doors (E) -> load {boarded}/16",
            "Unload flow: land at base flag -> doors (E)",
            f"LZ status: {rescue_ready} | Grounded: {grounded_state} | Doors: {doors_state}",
            f"Boarding: {boarding_status}",
        ]
    else:
        lines = [
            f"Objective: Save 20 hostages (saved {saved}/20)",
            f"Rescue flow: Open compound -> land -> doors (E) -> load {boarded}/16",
            "Unload flow: land at base flag -> doors (E)",
            f"LZ status: {rescue_ready} | Grounded: {grounded_state} | Doors: {doors_state}",
            f"Boarding: {boarding_status}",
        ]

    if mission.invuln_seconds > 0.0:
        lines.append(f"INVULN: {mission.invuln_seconds:0.1f}s")

    if float(getattr(mission, "tank_warning_seconds", 0.0)) > 0.0:
        tank_dir = "->" if bool(getattr(mission, "tank_warning_from_right", False)) else "<-"
        lines.append(f"[TANK] LOCK {tank_dir}")

    if float(getattr(mission, "jet_warning_seconds", 0.0)) > 0.0:
        direction = "FROM RIGHT" if bool(getattr(mission, "jet_warning_from_right", False)) else "FROM LEFT"
        lines.append(f"[JET] >>> INBOUND ({direction})")

    if float(getattr(mission, "mine_warning_seconds", 0.0)) > 0.0:
        mine_dist = int(float(getattr(mission, "mine_warning_distance", 0.0)))
        lines.append(f"[MINE] * PROXIMITY ({mine_dist}px)")

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
