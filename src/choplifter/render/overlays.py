from __future__ import annotations

import pygame


_TOAST_FONT: pygame.font.Font | None = None

_INTRO_TITLE_FONT: pygame.font.Font | None = None
_INTRO_SUB_FONT: pygame.font.Font | None = None
_INTRO_SKIP_FONT: pygame.font.Font | None = None
_SCRATCH_SURFACES: dict[tuple[int, int], pygame.Surface] = {}


def _scratch_surface(width: int, height: int) -> pygame.Surface:
    key = (max(1, int(width)), max(1, int(height)))
    surf = _SCRATCH_SURFACES.get(key)
    if surf is not None:
        return surf

    surf = pygame.Surface(key, pygame.SRCALPHA)
    _SCRATCH_SURFACES[key] = surf
    if len(_SCRATCH_SURFACES) > 48:
        _SCRATCH_SURFACES.clear()
        _SCRATCH_SURFACES[key] = surf
    return surf


def draw_chopper_select_overlay(
    screen: pygame.Surface,
    choices: list[tuple[str, str]],
    selected_index: int,
    *,
    title: str = "Select a Chopper",
    hint: str = "Left/Right (or D-pad) to choose • Enter/Numpad Enter/A to start",
    show_restart: bool = False,
    restart_selected: bool = False,
    show_restart_game: bool = False,
    restart_game_selected: bool = False,
    show_mute: bool = False,
    mute_selected: bool = False,
    muted: bool = False,
    show_quit: bool = False,
    quit_selected: bool = False,
    quit_confirm: bool = False,
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
    dim = _scratch_surface(w, h)
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

    from .helicopter import _get_chopper_scaled

    for i, (asset, name) in enumerate(choices):
        x = start_x + i * (box_w + gap)
        rect = pygame.Rect(x, box_top, box_w, box_h)

        is_selected = i == selected_index
        border = 4 if is_selected else 2
        bg = (20, 20, 20, 200) if is_selected else (10, 10, 10, 180)

        panel = _scratch_surface(rect.width, rect.height)
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

        panel = _scratch_surface(btn.width, btn.height)
        panel.fill((20, 20, 20, 200) if restart_selected else (10, 10, 10, 180))
        screen.blit(panel, btn.topleft)
        pygame.draw.rect(screen, (240, 240, 240) if restart_selected else (160, 160, 160), btn, 4 if restart_selected else 2)

        text = hint_font.render("Restart Mission", True, (240, 240, 240) if restart_selected else (200, 200, 200))
        screen.blit(text, (btn.centerx - text.get_width() // 2, btn.centery - text.get_height() // 2))

    if show_restart_game:
        btn_w = min(320, w - 80)
        btn_h = 52
        btn_x = w // 2 - btn_w // 2

        base_y = box_top + box_h + 22
        if show_restart:
            base_y += btn_h + 12

        btn_y = base_y
        btn = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

        panel = _scratch_surface(btn.width, btn.height)
        panel.fill((20, 20, 20, 200) if restart_game_selected else (10, 10, 10, 180))
        screen.blit(panel, btn.topleft)
        pygame.draw.rect(
            screen,
            (240, 240, 240) if restart_game_selected else (160, 160, 160),
            btn,
            4 if restart_game_selected else 2,
        )

        text = hint_font.render(
            "Restart Game", True, (240, 240, 240) if restart_game_selected else (200, 200, 200)
        )
        screen.blit(text, (btn.centerx - text.get_width() // 2, btn.centery - text.get_height() // 2))

    if show_mute:
        btn_w = min(320, w - 80)
        btn_h = 52
        btn_x = w // 2 - btn_w // 2

        base_y = box_top + box_h + 22
        if show_restart:
            base_y += btn_h + 12
        if show_restart_game:
            base_y += btn_h + 12

        btn_y = base_y
        btn = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

        panel = _scratch_surface(btn.width, btn.height)
        panel.fill((20, 20, 20, 200) if mute_selected else (10, 10, 10, 180))
        screen.blit(panel, btn.topleft)
        pygame.draw.rect(screen, (240, 240, 240) if mute_selected else (160, 160, 160), btn, 4 if mute_selected else 2)

        label = f"Mute: {'ON' if muted else 'OFF'}"
        text = hint_font.render(label, True, (240, 240, 240) if mute_selected else (200, 200, 200))
        screen.blit(text, (btn.centerx - text.get_width() // 2, btn.centery - text.get_height() // 2))

    if show_quit:
        btn_w = min(320, w - 80)
        btn_h = 52
        btn_x = w // 2 - btn_w // 2

        base_y = box_top + box_h + 22
        if show_restart:
            base_y += btn_h + 12
        if show_restart_game:
            base_y += btn_h + 12
        if show_mute:
            base_y += btn_h + 12

        btn_y = base_y
        btn = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

        panel = _scratch_surface(btn.width, btn.height)
        panel.fill((220, 40, 40, 220) if quit_selected else (80, 10, 10, 180))
        screen.blit(panel, btn.topleft)
        pygame.draw.rect(screen, (255, 80, 80) if quit_selected else (160, 80, 80), btn, 4 if quit_selected else 2)

        label = "Quit Game"
        text = hint_font.render(label, True, (255, 255, 255) if quit_selected else (220, 180, 180))
        screen.blit(text, (btn.centerx - text.get_width() // 2, btn.centery - text.get_height() // 2))

        # Confirmation overlay
        if quit_selected and quit_confirm:
            confirm_w = min(340, w - 100)
            confirm_h = 70
            confirm_x = w // 2 - confirm_w // 2
            confirm_y = btn_y + btn_h + 16
            confirm_rect = pygame.Rect(confirm_x, confirm_y, confirm_w, confirm_h)
            confirm_panel = _scratch_surface(confirm_w, confirm_h)
            confirm_panel.fill((40, 40, 40, 240))
            screen.blit(confirm_panel, (confirm_x, confirm_y))
            pygame.draw.rect(screen, (255, 80, 80), confirm_rect, 3)
            confirm_text = hint_font.render("Press A again to confirm quit", True, (255, 255, 255))
            screen.blit(confirm_text, (confirm_x + confirm_w // 2 - confirm_text.get_width() // 2, confirm_y + confirm_h // 2 - confirm_text.get_height() // 2))


def draw_mission_select_overlay(
    screen: pygame.Surface,
    choices: list[tuple[str, str]],
    selected_index: int,
    *,
    title: str = "Select a Mission",
    hint: str = "Left/Right (or D-pad) to choose • Enter/Numpad Enter/A to continue",
) -> None:
    """Draw a simple mission selection overlay.

    choices: list of (mission_id, display_name)
    """

    global _TOAST_FONT
    if _TOAST_FONT is None:
        pygame.font.init()
        _TOAST_FONT = pygame.font.SysFont("consolas", 26)
    title_font = _TOAST_FONT

    w = screen.get_width()
    h = screen.get_height()

    # Dim the game view.
    dim = _scratch_surface(w, h)
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
    box_top = 150
    box_h = min(190, h - box_top - 40)
    available_w = w - margin_x * 2
    box_w = int((available_w - gap * (n - 1)) / float(n))
    box_w = max(160, box_w)

    row_w = box_w * n + gap * (n - 1)
    start_x = max(margin_x, (w - row_w) // 2)

    for i, (_mission_id, name) in enumerate(choices):
        x = start_x + i * (box_w + gap)
        rect = pygame.Rect(x, box_top, box_w, box_h)

        is_selected = i == selected_index
        border = 4 if is_selected else 2
        bg = (20, 20, 20, 200) if is_selected else (10, 10, 10, 180)

        panel = _scratch_surface(rect.width, rect.height)
        panel.fill(bg)
        screen.blit(panel, rect.topleft)

        pygame.draw.rect(screen, (240, 240, 240) if is_selected else (160, 160, 160), rect, border)

        # Name (centered).
        label = title_font.render(name, True, (240, 240, 240) if is_selected else (200, 200, 200))
        lx = rect.centerx - label.get_width() // 2
        ly = rect.centery - label.get_height() // 2
        screen.blit(label, (lx, ly))


def draw_intro_cutscene(
    screen: pygame.Surface,
    t: float,
    *,
    title: str = "CHOPLIFTER",
    subtitle: str = "Mission: Middle East Rescue",
    show_skip: bool = True,
    skip_text: str | None = None,
) -> None:
    """Draw a lightweight intro title card.

    Plays as an in-engine, resolution-independent sequence (no video assets).
    """

    global _INTRO_TITLE_FONT, _INTRO_SUB_FONT, _INTRO_SKIP_FONT
    if _INTRO_TITLE_FONT is None or _INTRO_SUB_FONT is None or _INTRO_SKIP_FONT is None:
        pygame.font.init()
        _INTRO_TITLE_FONT = pygame.font.SysFont("consolas", 72, bold=True)
        _INTRO_SUB_FONT = pygame.font.SysFont("consolas", 26)
        _INTRO_SKIP_FONT = pygame.font.SysFont("consolas", 18)

    w = screen.get_width()
    h = screen.get_height()

    # Black background.
    screen.fill((0, 0, 0))

    # Timeline:
    # - Title fades in early and holds.
    # - Subtitle fades in slightly later.
    t = max(0.0, float(t))
    title_in_start = 0.55
    title_in_end = 1.55
    sub_in_start = 1.25
    sub_in_end = 2.15

    def _fade01(x: float, a: float, b: float) -> float:
        if b <= a:
            return 1.0
        if x <= a:
            return 0.0
        if x >= b:
            return 1.0
        return (x - a) / (b - a)

    title_a01 = _fade01(t, title_in_start, title_in_end)
    sub_a01 = _fade01(t, sub_in_start, sub_in_end)

    title_surf = _INTRO_TITLE_FONT.render(title, True, (255, 255, 255))
    sub_surf = _INTRO_SUB_FONT.render(subtitle, True, (235, 235, 235))

    title_surf.set_alpha(int(255 * title_a01))
    sub_surf.set_alpha(int(255 * sub_a01))

    cx = w // 2
    cy = h // 2

    title_rect = title_surf.get_rect(center=(cx, cy - 18))
    sub_rect = sub_surf.get_rect(center=(cx, title_rect.bottom + 24))
    screen.blit(title_surf, title_rect)
    screen.blit(sub_surf, sub_rect)

    if show_skip:
        draw_skip_overlay(screen, text=skip_text)


def draw_skip_overlay(screen: pygame.Surface, *, text: str | None = None) -> None:
    """Draw the subtle "Skip" overlay used by the intro."""

    global _INTRO_SKIP_FONT
    if _INTRO_SKIP_FONT is None:
        pygame.font.init()
        _INTRO_SKIP_FONT = pygame.font.SysFont("consolas", 18)

    w = screen.get_width()
    pad = 16
    label = text or "Enter/Space: Skip"
    skip_surf = _INTRO_SKIP_FONT.render(label, True, (235, 235, 235))
    skip_surf.set_alpha(110)
    screen.blit(skip_surf, (w - skip_surf.get_width() - pad, pad))
