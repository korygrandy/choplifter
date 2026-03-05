from __future__ import annotations

import logging
import os
from pathlib import Path
import tempfile
import time


_LOGGER_NAME = "choplifter"


def _default_logs_dir() -> Path:
    """Choose a writable logs directory suitable for packaged executables.

    - Prefer per-user LOCALAPPDATA on Windows.
    - Fall back to a local ./logs folder during development.
    - As a last resort, write to the system temp directory.
    """

    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "Choplifter" / "logs"

    # Dev-friendly default.
    return Path("logs")


def create_session_logger(logs_dir: str | os.PathLike | None = None) -> logging.Logger:
    """Create (or return) a process-wide logger that writes a session log.

    The log is intended for gameplay/debug tracing (boarding/unload, compound open, win).
    """

    logger = logging.getLogger(_LOGGER_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    if logs_dir is None:
        candidates = [_default_logs_dir(), Path("logs"), Path(tempfile.gettempdir()) / "Choplifter" / "logs"]
    else:
        candidates = [Path(logs_dir)]

    logs_path: Path | None = None
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            logs_path = candidate
            break
        except Exception:
            continue

    if logs_path is None:
        # If we cannot create a file log, still return a usable console logger.
        logs_path = Path(".")

    stamp = time.strftime("%Y%m%d-%H%M%S")
    file_path = logs_path / f"session-{stamp}.log"

    formatter = logging.Formatter("%(asctime)s.%(msecs)03d %(levelname)s %(message)s", datefmt="%H:%M:%S")


    fh: logging.Handler | None = None
    try:
        fh = logging.FileHandler(file_path, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
    except Exception:
        fh = None


    sh = logging.StreamHandler()
    sh.setLevel(logging.DEBUG)
    sh.setFormatter(formatter)

    if fh is not None:
        logger.addHandler(fh)
    logger.addHandler(sh)
    logger.propagate = False

    if fh is not None:
        logger.info("Session start: %s", file_path.as_posix())
    else:
        logger.info("Session start: (file logging unavailable)")
    return logger
