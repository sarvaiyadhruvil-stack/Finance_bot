"""
Custom exception hierarchy for the Binance Futures Trading Bot.

All application-specific exceptions inherit from TradingBotError,
which allows callers to catch any trading-bot exception with a single clause.
"""


class TradingBotError(Exception):
    """Base exception for all trading-bot errors."""

    def __init__(self, message: str, *, context: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        # Optional structured context for richer log records.
        self.context: dict = context or {}

    def __str__(self) -> str:  # pragma: no cover
        return self.message


# ---------------------------------------------------------------------------
# Validation exceptions
# ---------------------------------------------------------------------------


class ValidationError(TradingBotError):
    """Raised when user-supplied CLI arguments fail validation."""


class InvalidSymbolError(ValidationError):
    """Raised when the trading symbol is empty, malformed, or unknown."""


class InvalidSideError(ValidationError):
    """Raised when the order side is not BUY or SELL."""


class InvalidOrderTypeError(ValidationError):
    """Raised when the order type is not MARKET or LIMIT."""


class InvalidQuantityError(ValidationError):
    """Raised when the quantity is not a positive finite number."""


class InvalidPriceError(ValidationError):
    """Raised when the price is missing for a LIMIT order or is not positive."""


# ---------------------------------------------------------------------------
# Configuration exceptions
# ---------------------------------------------------------------------------


class ConfigurationError(TradingBotError):
    """Raised when required environment variables or config values are missing."""


# ---------------------------------------------------------------------------
# API / network exceptions
# ---------------------------------------------------------------------------


class BinanceAPIError(TradingBotError):
    """Raised when the Binance REST API returns an error payload."""

    def __init__(
        self,
        message: str,
        *,
        error_code: int | None = None,
        http_status: int | None = None,
        context: dict | None = None,
    ) -> None:
        super().__init__(message, context=context)
        self.error_code = error_code
        self.http_status = http_status


class AuthenticationError(BinanceAPIError):
    """Raised on API key / signature rejection (HTTP 401 / code -2014 etc.)."""


class RateLimitError(BinanceAPIError):
    """Raised when Binance returns HTTP 429 or 418 (IP ban)."""


class OrderPlacementError(BinanceAPIError):
    """Raised when an order submission fails at the exchange level."""


class NetworkError(TradingBotError):
    """Raised on connection failures, timeouts, or DNS errors."""


class TimeoutError(NetworkError):  # noqa: A001 – intentional shadow of built-in
    """Raised when an API request times out."""
