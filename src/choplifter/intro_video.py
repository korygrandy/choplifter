from __future__ import annotations

from dataclasses import dataclass
from concurrent.futures import Future, ThreadPoolExecutor
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any

import pygame


_VIDEO_IO_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="intro-video-io")


def _extract_audio_track_to_temp(video_path: Path) -> Path | None:
    try:
        import imageio_ffmpeg  # type: ignore

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None

    try:
        tmp = tempfile.NamedTemporaryFile(prefix="choplifter-intro-", suffix=".ogg", delete=False)
        tmp_path = Path(tmp.name)
        tmp.close()

        args = [
            str(ffmpeg_exe),
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-acodec",
            "libvorbis",
            "-ar",
            "44100",
            "-ac",
            "2",
            str(tmp_path),
        ]

        creationflags = 0
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

        result = subprocess.run(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
            check=False,
        )
        if result.returncode != 0 or not tmp_path.exists() or tmp_path.stat().st_size <= 0:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
            return None

        return tmp_path
    except Exception:
        return None


@dataclass
class IntroVideoPlayer:
    """Minimal video player for the launch intro.

    Uses `imageio` (ffmpeg backend) to decode frames and blit them with
    letterboxing.

    If the container has an audio track, it is extracted to a temporary OGG
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
    _audio_path: Path | None = None
    _audio_started: bool = False
    _audio_failed: bool = False
    _audio_extract_future: Future[Path | None] | None = None
    _audio_wait_s: float = 0.0
    _audio_wait_timeout_s: float = 3.5
    _loading_font: pygame.font.Font | None = None
    done: bool = False

    _last_error: str | None = None

    @staticmethod
    def last_error() -> str | None:
        return IntroVideoPlayer._last_error

    @staticmethod
    def try_create(path: Path) -> "IntroVideoPlayer | None":
        IntroVideoPlayer._last_error = None
        try:
            if not path.exists():
                IntroVideoPlayer._last_error = f"missing video asset: {path}"
                return None

            # Import lazily so the game still runs without video deps.
            # Force `imageio` to use the bundled ffmpeg exe when available.
            try:
                import imageio_ffmpeg  # type: ignore

                os.environ.setdefault("IMAGEIO_FFMPEG_EXE", imageio_ffmpeg.get_ffmpeg_exe())
            except Exception:
                pass

            import imageio.v2 as imageio  # type: ignore

            reader = imageio.get_reader(str(path), format="ffmpeg")
            meta = reader.get_meta_data() if hasattr(reader, "get_meta_data") else {}
            fps = float(meta.get("fps") or 30.0)
            duration_s = float(meta.get("duration") or 0.0)
            it = reader.iter_data()
            player = IntroVideoPlayer(path=path, fps=fps, duration_s=duration_s, _reader=reader, _iter=it)
            # Start audio extraction in background to avoid frame hitch on cutscene start.
            player._audio_extract_future = _VIDEO_IO_EXECUTOR.submit(_extract_audio_track_to_temp, path)
            return player
        except Exception:
            try:
                import traceback

                IntroVideoPlayer._last_error = traceback.format_exc(limit=1).strip().splitlines()[-1]
            except Exception:
                IntroVideoPlayer._last_error = "failed to initialize intro video"
            return None

    def close(self, *, immediate: bool = False) -> None:
        self._stop_audio(immediate=immediate)
        if self._audio_extract_future is not None and self._audio_path is None and self._audio_extract_future.done():
            try:
                pending_path = self._audio_extract_future.result()
            except Exception:
                pending_path = None
            if pending_path is not None:
                try:
                    pending_path.unlink(missing_ok=True)
                except Exception:
                    pass
        self._audio_extract_future = None

        if self._audio_path is not None:
            try:
                self._audio_path.unlink(missing_ok=True)
            except Exception:
                pass
            self._audio_path = None

        try:
            self._reader.close()
        except Exception:
            pass

    def is_audio_loading(self) -> bool:
        """Return True while optional cutscene audio is still warming up.

        Playback remains valid while this is True; it only indicates that
        extracted audio is not yet ready to start.
        """
        if self._audio_started or self._audio_failed:
            return False
        if self._audio_extract_future is None:
            return True
        return not self._audio_extract_future.done()

    def _stop_audio(self, *, immediate: bool) -> None:
        try:
            if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                if not immediate:
                    pygame.mixer.music.fadeout(200)
                pygame.mixer.music.stop()
        except Exception:
            pass

    def _ensure_audio_started(self) -> None:
        if self._audio_started or self._audio_failed:
            return

        # Ensure mixer is available.
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except Exception:
            self._audio_failed = True
            return

        if self._audio_extract_future is None:
            self._audio_extract_future = _VIDEO_IO_EXECUTOR.submit(_extract_audio_track_to_temp, self.path)
            return
        if not self._audio_extract_future.done():
            return

        try:
            self._audio_path = self._audio_extract_future.result()
        except Exception:
            self._audio_path = None
        finally:
            self._audio_extract_future = None

        if self._audio_path is None:
            self._audio_failed = True
            return

        try:
            pygame.mixer.music.load(str(self._audio_path))
            pygame.mixer.music.set_volume(1.0)
            try:
                pygame.mixer.music.play(start=max(0.0, float(self._t)))
            except Exception:
                pygame.mixer.music.play()
            self._audio_started = True
        except Exception:
            self._audio_failed = True
            return

    def _is_waiting_on_audio(self) -> bool:
        return (
            not self._audio_started
            and not self._audio_failed
            and self._audio_extract_future is not None
            and not self._audio_extract_future.done()
            and self._t <= 0.05
            and self._audio_wait_s < self._audio_wait_timeout_s
        )

    def _draw_terminal_loading_prompt(self, screen: pygame.Surface) -> None:
        if self._loading_font is None:
            self._loading_font = pygame.font.SysFont("consolas", 28, bold=True)

        text_full = "Loading..."
        chars_per_second = 11.0
        typed_count = max(0, min(len(text_full), int(self._audio_wait_s * chars_per_second)))
        typed = text_full[:typed_count]
        cursor = "_" if int(self._audio_wait_s * 2.8) % 2 == 0 else " "
        terminal_text = f"> {typed}{cursor}"

        glow = self._loading_font.render(terminal_text, True, (36, 120, 46))
        main = self._loading_font.render(terminal_text, True, (74, 248, 102))
        x = 34
        y = screen.get_height() - 72
        screen.blit(glow, (x + 2, y + 2))
        screen.blit(main, (x, y))

    def update(self, dt: float) -> None:
        if self.done:
            return

        self._ensure_audio_started()

        # Keep opening audio intact: while extraction/playback is warming up,
        # hold at t=0 instead of running video ahead and seeking into audio later.
        waiting_for_audio = self._is_waiting_on_audio()
        if waiting_for_audio and self._t <= 0.05:
            self._audio_wait_s += max(0.0, float(dt))
            if self._audio_wait_s < self._audio_wait_timeout_s:
                return
            # Failsafe: avoid indefinite freeze if extraction stalls.
            self._audio_failed = True

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
            if self._is_waiting_on_audio():
                self._draw_terminal_loading_prompt(screen)
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

        if self._is_waiting_on_audio():
            self._draw_terminal_loading_prompt(screen)
