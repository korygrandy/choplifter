from __future__ import annotations

from pathlib import Path
import math
import pygame

from .helicopter import Facing, Helicopter
from .mission import EnemyKind, HostageState, MissionState, ProjectileKind


_HUD_FONT: pygame.font.Font | None = None
_TOAST_FONT: pygame.font.Font | None = None

_MISSION1_BG_ORIG: pygame.Surface | None = None
_MISSION1_BG_LOAD_FAILED: bool = False
_MISSION1_BG_SCALED: dict[tuple[int, int], pygame.Surface] = {}

_CHOPPER_ORIG: dict[str, pygame.Surface] = {}
_CHOPPER_LOAD_FAILED: set[str] = set()
_CHOPPER_SCALED: dict[tuple[str, int], pygame.Surface] = {}

_BURN_SPRITE_CACHE: dict[tuple[str, int], pygame.Surface] = {}


def draw_sky(screen: pygame.Surface, horizon_y: float) -> None:
    """Draws the mission sky background above the horizon line.

    Falls back to a solid sky color if the background image is missing/unloadable.
    """

    width = screen.get_width()
    height = screen.get_height()
    horizon_h = max(0, min(int(horizon_y), height))
    if horizon_h <= 0:
        return

    bg = _get_mission1_bg_scaled(width, horizon_h)
    if bg is None:
        screen.fill((135, 190, 235), pygame.Rect(0, 0, width, horizon_h))
        return

    screen.blit(bg, (0, 0))


def _get_mission1_bg_scaled(width: int, height: int) -> pygame.Surface | None:
    global _MISSION1_BG_ORIG, _MISSION1_BG_LOAD_FAILED

    if _MISSION1_BG_LOAD_FAILED:
        return None

    if _MISSION1_BG_ORIG is None:
        module_dir = Path(__file__).resolve().parent
        repo_root = module_dir.parents[1]
        candidate_paths = (
            module_dir / "assets" / "mission1-bg.jpg",
            repo_root / "asset" / "mission1-bg.jpg",
        )
        path = next((p for p in candidate_paths if p.exists()), candidate_paths[0])
        try:
            _MISSION1_BG_ORIG = pygame.image.load(str(path)).convert()
        except Exception:
            _MISSION1_BG_LOAD_FAILED = True
            return None

    key = (width, height)
    cached = _MISSION1_BG_SCALED.get(key)
    if cached is not None:
        return cached

    scaled = pygame.transform.smoothscale(_MISSION1_BG_ORIG, (width, height))
    _MISSION1_BG_SCALED[key] = scaled
    return scaled


def draw_ground(screen: pygame.Surface, ground_y: float) -> None:
    pygame.draw.rect(screen, (40, 40, 40), pygame.Rect(0, int(ground_y), screen.get_width(), screen.get_height() - int(ground_y)))
    pygame.draw.line(screen, (90, 90, 90), (0, int(ground_y)), (screen.get_width(), int(ground_y)), 2)


def draw_helicopter(screen: pygame.Surface, helicopter: Helicopter, *, camera_x: float = 0.0) -> None:
    x = int(helicopter.pos.x - camera_x)
    y = int(helicopter.pos.y)

    skin = getattr(helicopter, "skin_asset", "chopper-one.png")
    sprite = _get_chopper_scaled(skin, width_px=120)
    if sprite is not None:
        s = sprite
        # The base sprite is authored facing LEFT; flip for RIGHT-facing.
        if helicopter.facing is Facing.RIGHT:
            s = pygame.transform.flip(s, True, False)

        rotated = pygame.transform.rotate(s, -helicopter.tilt_deg)
        rect = rotated.get_rect(center=(x, y))
        screen.blit(rotated, rect)
        return

    # Fallback: minimal placeholder (kept for robustness if asset missing).
    body_w, body_h = 70, 22
    body = pygame.Surface((body_w, body_h), pygame.SRCALPHA)
    body.fill((0, 0, 0, 0))
    pygame.draw.rect(body, (60, 190, 80), pygame.Rect(0, 0, body_w, body_h), border_radius=6)

    if helicopter.facing is Facing.LEFT:
        pygame.draw.circle(body, (220, 220, 220), (8, body_h // 2), 4)
    elif helicopter.facing is Facing.RIGHT:
        pygame.draw.circle(body, (220, 220, 220), (body_w - 8, body_h // 2), 4)
    else:
        pygame.draw.circle(body, (220, 220, 220), (body_w // 2, body_h // 2), 4)

    rotated = pygame.transform.rotate(body, -helicopter.tilt_deg)
    rect = rotated.get_rect(center=(x, y))
    screen.blit(rotated, rect)

    rotor_len = 90
    rotor_offset = 18
    angle_rad = math.radians(-helicopter.tilt_deg)
    cx, cy = rect.centerx, rect.centery - rotor_offset
    dx = math.cos(angle_rad) * (rotor_len / 2)
    dy = math.sin(angle_rad) * (rotor_len / 2)
    pygame.draw.line(screen, (30, 30, 30), (cx - dx, cy - dy), (cx + dx, cy + dy), 4)


def _get_chopper_scaled(asset_filename: str, *, width_px: int) -> pygame.Surface | None:
    if asset_filename in _CHOPPER_LOAD_FAILED:
        return None

    width_px = max(1, int(width_px))
    cache_key = (asset_filename, width_px)
    cached = _CHOPPER_SCALED.get(cache_key)
    if cached is not None:
        return cached

    orig = _CHOPPER_ORIG.get(asset_filename)
    if orig is None:
        module_dir = Path(__file__).resolve().parent
        path = module_dir / "assets" / asset_filename
        try:
            loaded = pygame.image.load(str(path))
            if pygame.display.get_surface() is not None:
                loaded = loaded.convert_alpha()

            # If the sprite has no transparency, treat top-left as background key.
            w = loaded.get_width()
            h = loaded.get_height()
            if w > 0 and h > 0:
                corners = ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1))
                if all(loaded.get_at(p).a == 255 for p in corners):
                    key = loaded.get_at((0, 0))
                    loaded.set_colorkey((key.r, key.g, key.b), pygame.RLEACCEL)

            _CHOPPER_ORIG[asset_filename] = loaded
            orig = loaded
        except Exception:
            _CHOPPER_LOAD_FAILED.add(asset_filename)
            return None

    ow, oh = orig.get_width(), orig.get_height()
    if ow <= 0 or oh <= 0:
        _CHOPPER_LOAD_FAILED.add(asset_filename)
        return None

    scale = width_px / float(ow)
    out_h = max(1, int(oh * scale))
    scaled = pygame.transform.smoothscale(orig, (width_px, out_h))

    key = orig.get_colorkey()
    if key is not None:
        scaled.set_colorkey(key, pygame.RLEACCEL)

    _CHOPPER_SCALED[cache_key] = scaled
    return scaled


def draw_chopper_select_overlay(
    screen: pygame.Surface,
    choices: list[tuple[str, str]],
    selected_index: int,
    *,
    title: str = "Select a Chopper",
    hint: str = "Left/Right (or D-pad) to choose • Enter/A to start",
    show_restart: bool = False,
    restart_selected: bool = False,
) -> None:
    """Draw a simple chopper selection overlay.

    choices: list of (asset_filename, display_name)
    """

    global _TOAST_FONT
    if _TOAST_FONT is None:
        pygame.font.init()
        _TOAST_FONT = pygame.font.SysFont("consolas", 26)
    title_font = _TOAST_FONT

    w = screen.get_width()
    h = screen.get_height()

    # Dim the game view.
    dim = pygame.Surface((w, h), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 160))
    screen.blit(dim, (0, 0))

    title_surf = title_font.render(title, True, (240, 240, 240))
    screen.blit(title_surf, (w // 2 - title_surf.get_width() // 2, 44))

    hint_font = pygame.font.SysFont("consolas", 18)
    hint_surf = hint_font.render(hint, True, (220, 220, 220))
    screen.blit(hint_surf, (w // 2 - hint_surf.get_width() // 2, 80))

    n = max(1, len(choices))
    selected_index = max(0, min(int(selected_index), n - 1))

    margin_x = 26
    gap = 14
    box_top = 130
    box_h = min(210, h - box_top - 40)
    available_w = w - margin_x * 2
    box_w = int((available_w - gap * (n - 1)) / float(n))
    box_w = max(90, box_w)

    # Center row if boxes don't exactly fill due to min-width clamping.
    row_w = box_w * n + gap * (n - 1)
    start_x = max(margin_x, (w - row_w) // 2)

    for i, (asset, name) in enumerate(choices):
        x = start_x + i * (box_w + gap)
        rect = pygame.Rect(x, box_top, box_w, box_h)

        is_selected = i == selected_index
        border = 4 if is_selected else 2
        bg = (20, 20, 20, 200) if is_selected else (10, 10, 10, 180)

        panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        panel.fill(bg)
        screen.blit(panel, rect.topleft)

        pygame.draw.rect(screen, (240, 240, 240) if is_selected else (160, 160, 160), rect, border)

        # Thumbnail.
        thumb_w = min(110, rect.width - 18)
        thumb = _get_chopper_scaled(asset, width_px=thumb_w)
        if thumb is not None:
            tx = rect.centerx - thumb.get_width() // 2
            ty = rect.y + 18
            screen.blit(thumb, (tx, ty))

        # Name.
        label = hint_font.render(name, True, (240, 240, 240) if is_selected else (200, 200, 200))
        lx = rect.centerx - label.get_width() // 2
        ly = rect.bottom - label.get_height() - 14
        screen.blit(label, (lx, ly))

    if show_restart:
        btn_w = min(320, w - 80)
        btn_h = 52
        btn_x = w // 2 - btn_w // 2
        btn_y = box_top + box_h + 22
        btn = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

        panel = pygame.Surface((btn.width, btn.height), pygame.SRCALPHA)
        panel.fill((20, 20, 20, 200) if restart_selected else (10, 10, 10, 180))
        screen.blit(panel, btn.topleft)
        pygame.draw.rect(screen, (240, 240, 240) if restart_selected else (160, 160, 160), btn, 4 if restart_selected else 2)

        text = hint_font.render("Restart Mission", True, (240, 240, 240) if restart_selected else (200, 200, 200))
        screen.blit(text, (btn.centerx - text.get_width() // 2, btn.centery - text.get_height() // 2))


def draw_mission(screen: pygame.Surface, mission: MissionState, *, camera_x: float = 0.0) -> None:
    _draw_base(screen, mission, camera_x=camera_x)
    _draw_compounds(screen, mission, camera_x=camera_x)
    _draw_hostages(screen, mission, camera_x=camera_x)
    _draw_enemies(screen, mission, camera_x=camera_x)
    _draw_burning_particles(screen, mission, camera_x=camera_x)
    _draw_projectiles(screen, mission, camera_x=camera_x)

    if mission.ended and mission.end_text:
        boarded = sum(1 for h in mission.hostages if h.state is HostageState.BOARDED)
        _draw_end(
            screen,
            mission.end_text,
            mission.end_reason,
            mission.stats.saved,
            boarded,
            mission.stats.kia_by_player,
            mission.stats.kia_by_enemy,
            mission.stats.lost_in_transit,
            mission.stats.enemies_destroyed,
            mission.crashes,
            mission.sentiment,
        )


def draw_hud(screen: pygame.Surface, mission: MissionState, helicopter: Helicopter) -> None:
    global _HUD_FONT
    if _HUD_FONT is None:
        pygame.font.init()
        _HUD_FONT = pygame.font.SysFont("consolas", 18)

    font = _HUD_FONT

    boarded = sum(1 for h in mission.hostages if h.state is HostageState.BOARDED)
    saved = mission.stats.saved

    # Minimal always-on guidance so the rescue loop is discoverable.
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
        surf = font.render(line, True, (10, 10, 10))
        # Shadow for readability.
        shadow = font.render(line, True, (255, 255, 255))
        screen.blit(shadow, (x + 1, y + i * 20 + 1))
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


def _draw_base(screen: pygame.Surface, mission: MissionState, *, camera_x: float) -> None:
    r = pygame.Rect(
        int(mission.base.pos.x - camera_x),
        int(mission.base.pos.y),
        int(mission.base.width),
        int(mission.base.height),
    )
    pygame.draw.rect(screen, (60, 60, 75), r, border_radius=8)
    pygame.draw.rect(screen, (210, 210, 210), r, 2, border_radius=8)

    # Simple flag pole marker.
    pole_x = r.right - 26
    pygame.draw.line(screen, (230, 230, 230), (pole_x, r.top + 10), (pole_x, r.bottom - 10), 3)
    pygame.draw.polygon(
        screen,
        (200, 40, 40),
        [(pole_x, r.top + 14), (pole_x + 22, r.top + 22), (pole_x, r.top + 30)],
    )


def _draw_compounds(screen: pygame.Surface, mission: MissionState, *, camera_x: float) -> None:
    for c in mission.compounds:
        r = pygame.Rect(int(c.pos.x - camera_x), int(c.pos.y), int(c.width), int(c.height))
        color = (160, 120, 70) if not c.is_open else (120, 95, 60)
        pygame.draw.rect(screen, color, r)
        pygame.draw.rect(screen, (30, 30, 30), r, 2)
        if c.is_open:
            gap = pygame.Rect(r.centerx - 10, r.bottom - 14, 20, 14)
            pygame.draw.rect(screen, (35, 35, 35), gap)


def _draw_hostages(screen: pygame.Surface, mission: MissionState, *, camera_x: float) -> None:
    for h in mission.hostages:
        if h.state in (HostageState.IDLE, HostageState.BOARDED, HostageState.SAVED):
            continue

        if h.state is HostageState.KIA:
            pygame.draw.circle(screen, (120, 10, 10), (int(h.pos.x - camera_x), int(h.pos.y)), 4)
            continue

        pygame.draw.circle(screen, (245, 235, 210), (int(h.pos.x - camera_x), int(h.pos.y)), 5)
        pygame.draw.circle(screen, (25, 25, 25), (int(h.pos.x - camera_x), int(h.pos.y)), 5, 1)


def _draw_projectiles(screen: pygame.Surface, mission: MissionState, *, camera_x: float) -> None:
    for p in mission.projectiles:
        x = int(p.pos.x - camera_x)
        y = int(p.pos.y)
        if p.kind is ProjectileKind.BULLET:
            pygame.draw.circle(screen, (240, 240, 240), (x, y), 2)
        elif p.kind is ProjectileKind.ENEMY_BULLET:
            pygame.draw.circle(screen, (200, 40, 40), (x, y), 2)
        else:
            pygame.draw.circle(screen, (35, 35, 35), (x, y), 4)


def _draw_enemies(screen: pygame.Surface, mission: MissionState, *, camera_x: float) -> None:
    ground_y = mission.base.pos.y + mission.base.height

    for e in mission.enemies:
        if e.kind is EnemyKind.TANK:
            # Simple tank block near ground.
            w, h = 44, 18
            r = pygame.Rect(int(e.pos.x - camera_x - w / 2), int(ground_y - h), w, h)
            pygame.draw.rect(screen, (70, 70, 70), r)
            pygame.draw.rect(screen, (25, 25, 25), r, 2)
            # Turret marker.
            pygame.draw.line(screen, (25, 25, 25), (r.centerx, r.top + 3), (r.centerx + 10, r.top - 6), 3)

        elif e.kind is EnemyKind.JET:
            x = int(e.pos.x - camera_x)
            y = int(e.pos.y)
            direction = 1 if e.vel.x >= 0 else -1
            pygame.draw.polygon(
                screen,
                (35, 35, 35),
                [(x, y), (x - 20 * direction, y - 8), (x - 20 * direction, y + 8)],
            )

        elif e.kind is EnemyKind.AIR_MINE:
            pygame.draw.circle(screen, (200, 40, 40), (int(e.pos.x - camera_x), int(e.pos.y)), 9)
            pygame.draw.circle(screen, (25, 25, 25), (int(e.pos.x - camera_x), int(e.pos.y)), 9, 2)


def _draw_burning_particles(screen: pygame.Surface, mission: MissionState, *, camera_x: float) -> None:
    # Particles are in world-space; apply camera offset.
    for p in getattr(mission, "burning").particles:
        x = int(p.pos.x - camera_x)
        y = int(p.pos.y)

        t = p.age / max(0.001, p.ttl)
        if p.kind == "ember":
            alpha = int(220 * (1.0 - t))
            radius = int(max(1.0, p.radius))
            sprite = _get_burn_sprite("ember", radius)
        else:
            # Smoke: fades slower and expands a little.
            alpha = int(160 * (1.0 - t) * (1.0 - t))
            radius = int(max(1.0, p.radius * (1.0 + 0.35 * t)))
            sprite = _get_burn_sprite("smoke", radius)

        if alpha <= 0:
            continue

        sprite.set_alpha(alpha)
        screen.blit(sprite, (x - sprite.get_width() // 2, y - sprite.get_height() // 2))


def _get_burn_sprite(kind: str, radius: int) -> pygame.Surface:
    radius = max(1, int(radius))
    key = (kind, radius)
    cached = _BURN_SPRITE_CACHE.get(key)
    if cached is not None:
        return cached

    size = radius * 2 + 6
    s = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = size // 2
    cy = size // 2

    if kind == "ember":
        # Small hot spark with bright core.
        pygame.draw.circle(s, (255, 210, 80, 220), (cx, cy), radius)
        pygame.draw.circle(s, (255, 245, 220, 235), (cx, cy), max(1, radius // 2))
    else:
        # Soft smoke puff.
        pygame.draw.circle(s, (55, 55, 55, 46), (cx, cy), radius)
        pygame.draw.circle(s, (75, 75, 75, 62), (cx - max(1, radius // 5), cy), max(1, int(radius * 0.75)))
        pygame.draw.circle(s, (35, 35, 35, 40), (cx + max(1, radius // 6), cy + max(1, radius // 8)), max(1, int(radius * 0.60)))

    _BURN_SPRITE_CACHE[key] = s
    return s


def _draw_end(
    screen: pygame.Surface,
    text: str,
    reason: str,
    saved: int,
    boarded: int,
    kia_player: int,
    kia_enemy: int,
    lost_in_transit: int,
    enemies_destroyed: int,
    crashes: int,
    sentiment: float,
) -> None:
    panel = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 120))
    screen.blit(panel, (0, 0))

    pygame.font.init()
    font = pygame.font.SysFont("consolas", 72, bold=True)
    surf = font.render(text, True, (255, 255, 255))
    rect = surf.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
    screen.blit(surf, rect)

    small = pygame.font.SysFont("consolas", 22)
    lines = [
        f"Result: {reason}",
        f"Saved: {saved}",
        f"Boarded (not yet unloaded): {boarded}",
        f"KIA (player): {kia_player}",
        f"KIA (by enemy): {kia_enemy}",
        f"Lost in transit: {lost_in_transit}",
        f"Enemies destroyed: {enemies_destroyed}",
        f"Crashes: {crashes}",
        f"Sentiment: {int(sentiment)}",
        "Press Enter (or Start) to restart",
    ]
    y = rect.bottom + 18
    for line in lines:
        s = small.render(line, True, (235, 235, 235))
        r = s.get_rect(center=(screen.get_width() // 2, y))
        screen.blit(s, r)
        y += 28
