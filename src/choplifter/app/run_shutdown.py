from __future__ import annotations

import pygame


def finalize_run_shutdown(*, audio: object) -> None:
    """Stop persistent audio and shut down pygame subsystems for app exit."""
    try:
        if audio is not None and hasattr(audio, "stop_persistent_channels"):
            audio.stop_persistent_channels()
        if pygame.mixer.get_init():
            pygame.mixer.stop()
            pygame.mixer.music.stop()
            pygame.mixer.quit()
    except Exception:
        pass

    pygame.quit()