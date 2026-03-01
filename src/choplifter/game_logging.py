from __future__ import annotations

import logging
import os
from pathlib import Path
import time


_LOGGER_NAME = "choplifter"


def create_session_logger(logs_dir: str | os.PathLike = "logs") -> logging.Logger:
    """Create (or return) a process-wide logger that writes a session log.

    The log is intended for gameplay/debug tracing (boarding/unload, compound open, win).
    """

    logger = logging.getLogger(_LOGGER_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    logs_path = Path(logs_dir)
    logs_path.mkdir(parents=True, exist_ok=True)

    stamp = time.strftime("%Y%m%d-%H%M%S")
    file_path = logs_path / f"session-{stamp}.log"

    formatter = logging.Formatter("%(asctime)s.%(msecs)03d %(levelname)s %(message)s", datefmt="%H:%M:%S")

    fh = logging.FileHandler(file_path, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)

    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(sh)
    logger.propagate = False

    logger.info("Session start: %s", file_path.as_posix())
    return logger
