"""
Logging configuration for the Binance Futures Trading Bot.

Sets up a dual-handler logger that writes structured records both to
``logs/trading_bot.log`` (rotating file) and to the console (stdout).
Call ``setup_logging()`` once at application start-up before importing
any other module that logs.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "trading_bot.log"

# 5 MB per file, keep 5 back-ups → up to 25 MB of history.
MAX_BYTES: int = 5 * 1024 * 1024
BACKUP_COUNT: int = 5

# Detailed format used for the rotating file handler.
FILE_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"
)

# Slightly shorter format for the console handler.
CONSOLE_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"

DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def setup_logging(
    *,
    log_level: int = logging.DEBUG,
    console_level: int = logging.INFO,
) -> logging.Logger:
    """Create and configure the root logger for the trading bot.

    This function is idempotent – calling it more than once returns the same
    logger without adding duplicate handlers.

    Args:
        log_level:     Minimum level written to the rotating log file.
        console_level: Minimum level written to stdout.

    Returns:
        The configured ``trading_bot`` logger.
    """
    logger = logging.getLogger("trading_bot")

    # Guard against duplicate handler registration on repeated calls.
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)  # let handlers decide their own thresholds

    # ------------------------------------------------------------------
    # File handler (rotating)
    # ------------------------------------------------------------------
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    file_handler = logging.handlers.RotatingFileHandler(
        filename=LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(
        logging.Formatter(fmt=FILE_FORMAT, datefmt=DATE_FORMAT)
    )

    # ------------------------------------------------------------------
    # Console handler (stdout)
    # ------------------------------------------------------------------
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(
        logging.Formatter(fmt=CONSOLE_FORMAT, datefmt=DATE_FORMAT)
    )

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info("Logging initialised — file: %s", LOG_FILE.resolve())
    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a child logger scoped under the ``trading_bot`` namespace.

    Args:
        name: Sub-logger name (e.g. ``"client"``, ``"orders"``).

    Returns:
        A ``logging.Logger`` instance named ``trading_bot.<name>``.
    """
    return logging.getLogger(f"trading_bot.{name}")
