from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import tempfile
from typing import Any

import pygame


@dataclass
class IntroVideoPlayer:
    """Minimal video player for the launch intro.

    Uses `imageio` (ffmpeg backend) to decode frames and blit them with
    letterboxing.

    If the container has an audio track, it is extracted to a temporary WAV
    (via `imageio-ffmpeg`'s bundled ffmpeg) and played with
    `pygame.mixer.music`.
    """

    path: Path
    fps: float
    duration_s: float

    _reader: Any
    _iter: Any
    _t: float = 0.0
    _frame_index: int = -1
    _frame: pygame.Surface | None = None
    _frame_size: tuple[int, int] | None = None
    _scaled: pygame.Surface | None = None
    _scaled_size: tuple[int, int] | None = None
    _scaled_screen: tuple[int, int] | None = None
    _audio_wav: Path | None = None
    _audio_started: bool = False
    _audio_failed: bool = False
    done: bool = False

    @staticmethod
    def try_create(path: Path) -> "IntroVideoPlayer | None":
        try:
            if not path.exists():
                return None

            # Import lazily so the game still runs without video deps.
            import imageio.v2 as imageio  # type: ignore

            reader = imageio.get_reader(str(path), format="ffmpeg")
            meta = reader.get_meta_data() if hasattr(reader, "get_meta_data") else {}
            fps = float(meta.get("fps") or 30.0)
            duration_s = float(meta.get("duration") or 0.0)
            it = reader.iter_data()
            return IntroVideoPlayer(path=path, fps=fps, duration_s=duration_s, _reader=reader, _iter=it)
        except Exception:
            return None

    def close(self) -> None:
        self._stop_audio()
        if self._audio_wav is not None:
            try:
                self._audio_wav.unlink(missing_ok=True)
            except Exception:
                pass
            self._audio_wav = None

        try:
            self._reader.close()
        except Exception:
            pass

    def _stop_audio(self) -> None:
        try:
            if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                pygame.mixer.music.fadeout(200)
                pygame.mixer.music.stop()
        except Exception:
            pass

    def _ensure_audio_started(self) -> None:
        if self._audio_started or self._audio_failed:
            return

        # Lazy import so the game still runs without video deps.
        try:
            import imageio_ffmpeg  # type: ignore
        except Exception:
            self._audio_failed = True
            return

        # Ensure mixer is available.
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except Exception:
            self._audio_failed = True
            return

        # Extract audio to temp WAV (Windows: keep file path, don't rely on delete-on-close semantics).
        try:
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            tmp = tempfile.NamedTemporaryFile(prefix="choplifter-intro-", suffix=".wav", delete=False)
            tmp_path = Path(tmp.name)
            tmp.close()

            args = [
                str(ffmpeg_exe),
                "-y",
                "-i",
                str(self.path),
                "-vn",
                "-acodec",
                "pcm_s16le",
                "-ar",
                "44100",
                "-ac",
                "2",
                str(tmp_path),
            ]

            creationflags = 0
            if hasattr(subprocess, "CREATE_NO_WINDOW"):
                creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

            r = subprocess.run(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
                check=False,
            )
            if r.returncode != 0 or not tmp_path.exists() or tmp_path.stat().st_size <= 0:
                try:
                    tmp_path.unlink(missing_ok=True)
                except Exception:
                    pass
                self._audio_failed = True
                return

            self._audio_wav = tmp_path
        except Exception:
            self._audio_failed = True
            return

        try:
            pygame.mixer.music.load(str(self._audio_wav))
            pygame.mixer.music.play()
            self._audio_started = True
        except Exception:
            self._audio_failed = True
            return

    def update(self, dt: float) -> None:
        if self.done:
            return

        self._ensure_audio_started()

        self._t += max(0.0, float(dt))
        target_index = int(self._t * max(1e-6, self.fps))

        # Decode frames sequentially up to target.
        while self._frame_index < target_index and not self.done:
            try:
                frame = next(self._iter)
            except StopIteration:
                self.done = True
                return
            except Exception:
                self.done = True
                return

            try:
                # `frame` is typically a numpy array HxWx(3|4).
                if getattr(frame, "ndim", 0) == 3 and frame.shape[2] >= 3:
                    rgb = frame[:, :, :3]
                else:
                    # Unsupported format.
                    self.done = True
                    return

                # Pygame expects array with shape (w,h,3) for make_surface.
                surf = pygame.surfarray.make_surface(rgb.swapaxes(0, 1))
                self._frame = surf.convert()
                self._frame_size = self._frame.get_size()
                self._scaled = None
                self._scaled_size = None
                self._scaled_screen = None
                self._frame_index += 1
            except Exception:
                self.done = True
                return

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill((0, 0, 0))
        if self._frame is None:
            return

        sw, sh = screen.get_size()
        fw, fh = self._frame_size or self._frame.get_size()
        if fw <= 0 or fh <= 0:
            return

        scale = min(sw / float(fw), sh / float(fh))
        dw = max(1, int(fw * scale))
        dh = max(1, int(fh * scale))
        size = (dw, dh)

        if self._scaled is None or self._scaled_size != size or self._scaled_screen != (sw, sh):
            if size == (fw, fh):
                self._scaled = self._frame
            else:
                self._scaled = pygame.transform.smoothscale(self._frame, size)
            self._scaled_size = size
            self._scaled_screen = (sw, sh)

        x = (sw - dw) // 2
        y = (sh - dh) // 2
        screen.blit(self._scaled, (x, y))
