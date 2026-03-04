from __future__ import annotations

from pathlib import Path
import pygame


_BG_ORIG: dict[str, pygame.Surface] = {}
_BG_LOAD_FAILED: set[str] = set()
_BG_SCALED: dict[tuple[str, int, int], pygame.Surface] = {}

_SKY_FADE_PREV_ASSET: str | None = None
_SKY_FADE_CUR_ASSET: str | None = None
_SKY_FADE_T: float = 999.0


def draw_sky(
    screen: pygame.Surface,
    horizon_y: float,
    *,
    bg_asset: str = "mission1-bg.jpg",
    dt: float = 0.0,
    enable_fade: bool = False,
    fade_seconds: float = 0.35,
) -> None:
    """Draws the mission sky background above the horizon line.

    Falls back to a solid sky color if the background image is missing/unloadable.
    """

    width = screen.get_width()
    height = screen.get_height()
    horizon_h = max(0, min(int(horizon_y), height))
    if horizon_h <= 0:
        return

    global _SKY_FADE_PREV_ASSET, _SKY_FADE_CUR_ASSET, _SKY_FADE_T

    bg_asset = bg_asset or "mission1-bg.jpg"

    if not enable_fade:
        _SKY_FADE_PREV_ASSET = None
        _SKY_FADE_CUR_ASSET = bg_asset
        _SKY_FADE_T = fade_seconds
    else:
        if _SKY_FADE_CUR_ASSET is None:
            _SKY_FADE_CUR_ASSET = bg_asset
            _SKY_FADE_T = fade_seconds
        elif bg_asset != _SKY_FADE_CUR_ASSET:
            _SKY_FADE_PREV_ASSET = _SKY_FADE_CUR_ASSET
            _SKY_FADE_CUR_ASSET = bg_asset
            _SKY_FADE_T = 0.0

        if dt > 0.0:
            _SKY_FADE_T = min(fade_seconds, _SKY_FADE_T + dt)

    prev_asset = _SKY_FADE_PREV_ASSET
    cur_asset = _SKY_FADE_CUR_ASSET or bg_asset

    # If there's no fade in progress, render the current background directly.
    if not enable_fade or prev_asset is None or fade_seconds <= 0.0 or _SKY_FADE_T >= fade_seconds:
        bg = _get_bg_scaled(cur_asset, width, horizon_h)
        if bg is None:
            screen.fill((135, 190, 235), pygame.Rect(0, 0, width, horizon_h))
        else:
            screen.blit(bg, (0, 0))
        return

    # Cross-fade from prev -> current.
    t01 = max(0.0, min(1.0, _SKY_FADE_T / fade_seconds))
    prev = _get_bg_scaled(prev_asset, width, horizon_h)
    cur = _get_bg_scaled(cur_asset, width, horizon_h)

    if prev is None:
        screen.fill((135, 190, 235), pygame.Rect(0, 0, width, horizon_h))
    else:
        screen.blit(prev, (0, 0))

    cur_alpha = int(255 * t01)
    if cur is None:
        overlay = pygame.Surface((width, horizon_h), pygame.SRCALPHA)
        overlay.fill((135, 190, 235, cur_alpha))
        screen.blit(overlay, (0, 0))
    else:
        old_alpha = cur.get_alpha()
        cur.set_alpha(cur_alpha)
        screen.blit(cur, (0, 0))
        cur.set_alpha(old_alpha)


def draw_ground(screen: pygame.Surface, ground_y: float) -> None:
    pygame.draw.rect(
        screen,
        (40, 40, 40),
        pygame.Rect(0, int(ground_y), screen.get_width(), screen.get_height() - int(ground_y)),
    )
    pygame.draw.line(screen, (90, 90, 90), (0, int(ground_y)), (screen.get_width(), int(ground_y)), 2)


def bg_asset_exists(asset_filename: str) -> bool:
    """Returns True if the background asset can be found on disk."""

    try:
        return _resolve_bg_path(asset_filename).exists()
    except Exception:
        return False


def _resolve_bg_path(asset_filename: str) -> Path:
    package_dir = Path(__file__).resolve().parents[1]
    repo_root = package_dir.parents[1]

    # Be forgiving about a common typo for worship-center.
    alternates: tuple[str, ...] = (asset_filename,)
    if asset_filename == "worship-center-warfare.jpg":
        alternates = (asset_filename, "woship-center-warfare.jpg", "mission3-bg.jpg")
    if asset_filename == "airport-special-ops.jpg":
        alternates = (asset_filename, "mission2-bg.jpg")
    if asset_filename == "mission3-bg.jpg":
        alternates = (asset_filename, "worship-center-warfare.jpg", "woship-center-warfare.jpg")
    if asset_filename == "mission2-bg.jpg":
        alternates = (asset_filename, "airport-special-ops.jpg")

    for name in alternates:
        candidate_paths = (
            package_dir / "assets" / name,
            repo_root / "asset" / name,
        )
        path = next((p for p in candidate_paths if p.exists()), None)
        if path is not None:
            return path

    # Default location (even if missing).
    return package_dir / "assets" / alternates[0]


def _get_bg_scaled(asset_filename: str, width: int, height: int) -> pygame.Surface | None:
    asset_filename = asset_filename or "mission1-bg.jpg"
    if asset_filename in _BG_LOAD_FAILED:
        return None

    orig = _BG_ORIG.get(asset_filename)
    if orig is None:
        path = _resolve_bg_path(asset_filename)
        try:
            orig = pygame.image.load(str(path)).convert()
        except Exception:
            _BG_LOAD_FAILED.add(asset_filename)
            return None
        _BG_ORIG[asset_filename] = orig

    key = (asset_filename, width, height)
    cached = _BG_SCALED.get(key)
    if cached is not None:
        return cached

    scaled = pygame.transform.smoothscale(orig, (width, height))
    _BG_SCALED[key] = scaled
    return scaled
