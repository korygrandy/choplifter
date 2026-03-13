from pathlib import Path
import pygame

def play_satellite_reallocating():
    """Play the satellite-reallocating.ogg SFX immediately if available."""
    try:
        module_dir = Path(__file__).resolve().parent
        asset_dir = module_dir / "assets"
        sfx_path = asset_dir / "satellite-reallocating.ogg"
        if sfx_path.exists():
            sound = pygame.mixer.Sound(str(sfx_path))
            sound.set_volume(0.7)
            sound.play()
    except Exception:
        pass
