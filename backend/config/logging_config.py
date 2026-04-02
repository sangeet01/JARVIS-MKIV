"""
JARVIS-MKIII — config/logging_config.py
Centralised logging setup. Call setup_logging() once at application startup.

Output:
  - File  : logs/jarvis.log  (DEBUG+, rotating 5 MB × 3 backups)
  - Console: stdout          (INFO+)

Format: "2026-04-03 14:00:00,123 | INFO     | module.name | message"
"""
from __future__ import annotations
import logging
import logging.handlers
import sys
from pathlib import Path

LOG_DIR  = Path(__file__).parent.parent.parent / "logs"
LOG_FILE = LOG_DIR / "jarvis.log"
FMT      = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FMT = "%Y-%m-%d %H:%M:%S"


def setup_logging() -> None:
    """Configure root logger with rotating file handler + console handler."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    if root.handlers:
        # Already configured (e.g. called twice during hot-reload) — skip
        return

    root.setLevel(logging.DEBUG)

    fmt = logging.Formatter(FMT, datefmt=DATE_FMT)

    # ── File handler: DEBUG and above, 5 MB max, 3 backups ─────────────────
    fh = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    # ── Console handler: INFO and above ────────────────────────────────────
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    root.addHandler(fh)
    root.addHandler(ch)

    # Quiet noisy third-party loggers
    for noisy in ("httpx", "httpcore", "chromadb", "sentence_transformers",
                  "uvicorn.access", "apscheduler"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger(__name__).info("[LOGGING] Structured logging initialised → %s", LOG_FILE)
