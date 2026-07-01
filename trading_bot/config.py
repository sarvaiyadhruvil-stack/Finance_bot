"""
Configuration management for the Binance Futures Trading Bot.

Reads API credentials and runtime settings from environment variables
(populated by ``.env`` via python-dotenv) and exposes them through the
immutable :class:`Settings` dataclass.  All secrets stay out of source code.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from trading_bot.exceptions import ConfigurationError
from trading_bot.logging_config import get_logger

logger = get_logger("config")

# Load .env from the project root (parent of this file's package directory).
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_FILE, override=False)


# ---------------------------------------------------------------------------
# Constants shared across the application
# ---------------------------------------------------------------------------

#: Supported order sides.
VALID_SIDES: frozenset[str] = frozenset({"BUY", "SELL"})

#: Supported order types.
VALID_ORDER_TYPES: frozenset[str] = frozenset({"MARKET", "LIMIT"})

#: Binance Futures Testnet base REST URL.
TESTNET_BASE_URL: str = "https://testnet.binancefuture.com"

#: Default request timeout in seconds.
DEFAULT_TIMEOUT: int = 10

#: Time-in-force for LIMIT orders.
LIMIT_TIME_IN_FORCE: str = "GTC"  # Good Till Cancelled


# ---------------------------------------------------------------------------
# Settings dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Settings:
    """Immutable application configuration loaded from environment variables.

    Attributes:
        api_key:      Binance Testnet API key.
        api_secret:   Binance Testnet API secret.
        base_url:     REST base URL (defaults to testnet).
        timeout:      HTTP request timeout in seconds.
        recv_window:  ``recvWindow`` parameter sent with signed requests (ms).
        log_level:    Minimum file-log level string (``"DEBUG"`` / ``"INFO"`` …).
    """

    api_key: str
    api_secret: str
    base_url: str = field(default=TESTNET_BASE_URL)
    timeout: int = field(default=DEFAULT_TIMEOUT)
    recv_window: int = field(default=5000)
    log_level: str = field(default="DEBUG")


def load_settings() -> Settings:
    """Read environment variables and return a validated :class:`Settings` object.

    Raises:
        ConfigurationError: If ``BINANCE_API_KEY`` or ``BINANCE_API_SECRET``
            are absent or empty.

    Returns:
        A fully populated :class:`Settings` instance.
    """
    api_key = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()

    missing: list[str] = []
    if not api_key:
        missing.append("BINANCE_API_KEY")
    if not api_secret:
        missing.append("BINANCE_API_SECRET")

    if missing:
        msg = (
            f"Missing required environment variable(s): {', '.join(missing)}. "
            "Create a .env file from .env.example and populate it with your "
            "Binance Futures Testnet credentials."
        )
        logger.error(msg)
        raise ConfigurationError(msg)

    timeout_raw = os.getenv("REQUEST_TIMEOUT", str(DEFAULT_TIMEOUT))
    try:
        timeout = int(timeout_raw)
        if timeout <= 0:
            raise ValueError("timeout must be positive")
    except ValueError:
        logger.warning(
            "Invalid REQUEST_TIMEOUT=%r — falling back to %d s",
            timeout_raw,
            DEFAULT_TIMEOUT,
        )
        timeout = DEFAULT_TIMEOUT

    recv_window_raw = os.getenv("RECV_WINDOW", "5000")
    try:
        recv_window = int(recv_window_raw)
    except ValueError:
        logger.warning(
            "Invalid RECV_WINDOW=%r — falling back to 5000 ms", recv_window_raw
        )
        recv_window = 5000

    settings = Settings(
        api_key=api_key,
        api_secret=api_secret,
        base_url=os.getenv("BINANCE_BASE_URL", TESTNET_BASE_URL).rstrip("/"),
        timeout=timeout,
        recv_window=recv_window,
        log_level=os.getenv("LOG_LEVEL", "DEBUG").upper(),
    )

    logger.info(
        "Configuration loaded — base_url=%s, timeout=%ds, recv_window=%dms",
        settings.base_url,
        settings.timeout,
        settings.recv_window,
    )
    return settings
