"""
Binance Futures Testnet REST client wrapper.

Wraps ``python-binance``'s ``AsyncClient`` / ``Client`` for synchronous use and
falls back to direct ``requests`` calls when needed.  All public methods log
the outgoing request and the raw response (or error) so that the rotating log
file captures a full audit trail.
"""

from __future__ import annotations

import hashlib
import hmac
import time
import urllib.parse
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from trading_bot.config import Settings
from trading_bot.exceptions import (
    AuthenticationError,
    BinanceAPIError,
    NetworkError,
    OrderPlacementError,
    RateLimitError,
    TimeoutError,
)
from trading_bot.logging_config import get_logger

logger = get_logger("client")

# ---------------------------------------------------------------------------
# HTTP session factory
# ---------------------------------------------------------------------------

_RETRY_STRATEGY = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[500, 502, 503, 504],
    allowed_methods=["GET", "POST", "DELETE"],
    raise_on_status=False,
)


def _build_session(timeout: int) -> requests.Session:
    """Create a ``requests.Session`` with retry logic and a default timeout."""
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=_RETRY_STRATEGY)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    # Store timeout as a session-level attribute for convenience.
    session._default_timeout = timeout  # type: ignore[attr-defined]
    return session


# ---------------------------------------------------------------------------
# BinanceClient
# ---------------------------------------------------------------------------


class BinanceClient:
    """Thin wrapper around the Binance Futures Testnet REST API.

    Uses HMAC-SHA256 request signing as required by Binance's ``/fapi/v1``
    endpoints.  Every outgoing request and incoming response is logged at
    DEBUG level; errors are logged at ERROR level with full context.

    Args:
        settings: Application :class:`~trading_bot.config.Settings` instance.
    """

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.api_key
        self._api_secret = settings.api_secret
        self._base_url = settings.base_url.rstrip("/")
        self._timeout = settings.timeout
        self._recv_window = settings.recv_window
        self._session = _build_session(settings.timeout)
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self._api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        logger.info(
            "BinanceClient initialised — base_url=%s", self._base_url
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _sign(self, params: dict[str, Any]) -> dict[str, Any]:
        """Add HMAC-SHA256 ``signature`` field to *params* in-place.

        Args:
            params: Query / body parameters dict (must already include
                ``timestamp`` and ``recvWindow``).

        Returns:
            The same dict with a ``signature`` key added.
        """
        query_string = urllib.parse.urlencode(params)
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _timestamp(self) -> int:
        """Return the current UTC timestamp in milliseconds."""
        return int(time.time() * 1000)

    def _handle_response(
        self, response: requests.Response, *, endpoint: str
    ) -> dict[str, Any]:
        """Parse a Binance REST response and raise typed exceptions on errors.

        Args:
            response: The raw :class:`requests.Response` object.
            endpoint: URL path used (for logging context).

        Returns:
            Parsed JSON payload as a dictionary.

        Raises:
            AuthenticationError: On HTTP 401 / Binance code -2014 / -2015.
            RateLimitError:      On HTTP 429 or 418.
            OrderPlacementError: On order-specific Binance error codes.
            BinanceAPIError:     For all other API-level errors.
        """
        logger.debug(
            "Response — endpoint=%s status=%d body=%s",
            endpoint,
            response.status_code,
            response.text[:2000],  # truncate huge bodies
        )

        # HTTP-level rate limiting
        if response.status_code in (429, 418):
            retry_after = response.headers.get("Retry-After", "unknown")
            msg = (
                f"Rate limit exceeded (HTTP {response.status_code}). "
                f"Retry after: {retry_after}s."
            )
            logger.error(msg)
            raise RateLimitError(
                msg,
                http_status=response.status_code,
                context={"retry_after": retry_after},
            )

        # Authentication failure at HTTP level
        if response.status_code == 401:
            msg = "Authentication failed. Verify your API key and secret."
            logger.error(msg)
            raise AuthenticationError(
                msg, http_status=401, context={"endpoint": endpoint}
            )

        try:
            payload: dict = response.json()
        except ValueError:
            msg = (
                f"Unexpected non-JSON response (HTTP {response.status_code}) "
                f"from {endpoint}: {response.text[:500]}"
            )
            logger.error(msg)
            raise BinanceAPIError(msg, http_status=response.status_code)

        # Binance encodes errors as {"code": <negative int>, "msg": "..."}
        if isinstance(payload, dict) and "code" in payload and payload["code"] < 0:
            error_code: int = payload["code"]
            error_msg: str = payload.get("msg", "Unknown Binance error")
            full_msg = f"Binance API error {error_code}: {error_msg}"
            logger.error(
                "API error — endpoint=%s code=%d msg=%s",
                endpoint,
                error_code,
                error_msg,
            )

            # Map specific Binance codes to typed exceptions.
            if error_code in (-2014, -2015):
                raise AuthenticationError(
                    full_msg, error_code=error_code, http_status=response.status_code
                )
            if error_code in (-2010, -2011, -1111, -1100, -1013):
                raise OrderPlacementError(
                    full_msg, error_code=error_code, http_status=response.status_code
                )

            raise BinanceAPIError(
                full_msg,
                error_code=error_code,
                http_status=response.status_code,
            )

        return payload

    # ------------------------------------------------------------------
    # Public API surface
    # ------------------------------------------------------------------

    def get_server_time(self) -> dict[str, Any]:
        """Fetch Binance server time (useful for connectivity checks).

        Returns:
            JSON payload: ``{"serverTime": <epoch_ms>}``.

        Raises:
            NetworkError: On connection / timeout issues.
            BinanceAPIError: On API-level failures.
        """
        endpoint = "/fapi/v1/time"
        url = f"{self._base_url}{endpoint}"
        logger.debug("GET %s", url)
        try:
            resp = self._session.get(url, timeout=self._timeout)
        except requests.exceptions.Timeout as exc:
            raise TimeoutError(
                f"Request to {endpoint} timed out after {self._timeout}s."
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise NetworkError(
                f"Connection error reaching {self._base_url}: {exc}"
            ) from exc
        return self._handle_response(resp, endpoint=endpoint)

    def get_exchange_info(self) -> dict[str, Any]:
        """Fetch exchange info including all tradeable symbols.

        Returns:
            Full exchange info payload from ``/fapi/v1/exchangeInfo``.

        Raises:
            NetworkError: On connection / timeout issues.
        """
        endpoint = "/fapi/v1/exchangeInfo"
        url = f"{self._base_url}{endpoint}"
        logger.debug("GET %s", url)
        try:
            resp = self._session.get(url, timeout=self._timeout)
        except requests.exceptions.Timeout as exc:
            raise TimeoutError(
                f"Request to {endpoint} timed out after {self._timeout}s."
            ) from exc
        except requests.exceptions.ConnectionError as exc:
            raise NetworkError(
                f"Connection error reaching {self._base_url}: {exc}"
            ) from exc
        return self._handle_response(resp, endpoint=endpoint)

    def place_order(
        self,
        *,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: float | None = None,
        time_in_force: str = "GTC",
    ) -> dict[str, Any]:
        """Submit a new futures order to Binance.

        Args:
            symbol:        Trading pair (e.g. ``"BTCUSDT"``).
            side:          ``"BUY"`` or ``"SELL"``.
            order_type:    ``"MARKET"`` or ``"LIMIT"``.
            quantity:      Contract quantity.
            price:         Limit price (required when *order_type* is ``"LIMIT"``).
            time_in_force: Time-in-force for LIMIT orders (default ``"GTC"``).

        Returns:
            Binance order response dict containing order ID, status, fills, etc.

        Raises:
            OrderPlacementError: If Binance rejects the order.
            AuthenticationError: On invalid API credentials.
            RateLimitError:      On API rate-limit breach.
            NetworkError:        On connectivity failures.
            TimeoutError:        When the request times out.
        """
        endpoint = "/fapi/v1/order"
        url = f"{self._base_url}{endpoint}"

        params: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
            "timestamp": self._timestamp(),
            "recvWindow": self._recv_window,
        }

        if order_type == "LIMIT":
            if price is None:
                raise OrderPlacementError(
                    "price is required for LIMIT orders but was not supplied."
                )
            params["price"] = price
            params["timeInForce"] = time_in_force

        signed_params = self._sign(params)

        logger.info(
            "Placing order — symbol=%s side=%s type=%s qty=%s price=%s",
            symbol,
            side,
            order_type,
            quantity,
            price,
        )
        logger.debug("POST %s params=%s", url, {k: v for k, v in signed_params.items() if k != "signature"})

        try:
            resp = self._session.post(
                url, data=signed_params, timeout=self._timeout
            )
        except requests.exceptions.Timeout as exc:
            msg = f"Order request to {endpoint} timed out after {self._timeout}s."
            logger.error(msg)
            raise TimeoutError(msg) from exc
        except requests.exceptions.ConnectionError as exc:
            msg = f"Connection error when placing order: {exc}"
            logger.error(msg)
            raise NetworkError(msg) from exc

        result = self._handle_response(resp, endpoint=endpoint)
        logger.info(
            "Order placed successfully — orderId=%s status=%s",
            result.get("orderId"),
            result.get("status"),
        )
        return result

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._session.close()
        logger.debug("HTTP session closed.")

    # Context-manager support
    def __enter__(self) -> "BinanceClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
