"""Logging setup: every pipeline step logs to logs/<step>_<timestamp>.log and to the console."""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

from bowpilot.config import REPO_ROOT


def setup_logging(step: str, log_dir: Path | None = None, level: int = logging.INFO) -> Path:
    """Configure the root logger for one step and return the log file path."""
    log_dir = log_dir or (REPO_ROOT / "logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / f"{step}_{datetime.now():%Y%m%d_%H%M%S}.log"
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    fh = logging.FileHandler(path)
    fh.setFormatter(fmt)
    ch = logging.StreamHandler(sys.stderr)
    ch.setFormatter(fmt)
    root.addHandler(fh)
    root.addHandler(ch)
    root.setLevel(level)
    for noisy in ("urllib3", "rasterio", "botocore", "fiona", "pyogrio", "matplotlib", "PIL", "googleapiclient"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    return path
