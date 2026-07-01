"""
Order orchestration layer for the Binance Futures Trading Bot.

:func:`place_order` is the single public entry-point used by the CLI.
It coordinates validation → client API call → response normalisation,
keeping the CLI layer clean of business logic.
"""

from __future__ import annotations

import datetime
from typing import Any

from trading_bot.client import BinanceClient
from trading_bot.config import LIMIT_TIME_IN_FORCE, Settings
from trading_bot.exceptions import TradingBotError
from trading_bot.logging_config import get_logger
from trading_bot.validators import validate_order_params

logger = get_logger("orders")


# ---------------------------------------------------------------------------
# Response normalisation
# ---------------------------------------------------------------------------


def _parse_order_response(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalise the raw Binance order response into a clean summary dict.

    Binance returns many optional fields; this function extracts the ones
    relevant to the CLI display and converts epoch-ms timestamps to ISO-8601.

    Args:
        raw: Raw JSON dict returned by the Binance ``/fapi/v1/order`` endpoint.

    Returns:
        Clean dict with keys: ``order_id``, ``status``, ``symbol``, ``side``,
        ``type``, ``orig_qty``, ``executed_qty``, ``avg_price``, ``price``,
        ``time_in_force``, ``timestamp``.
    """
    # Convert millisecond epoch → ISO-8601 UTC string if present.
    update_time_ms: int | None = raw.get("updateTime") or raw.get("time")
    if update_time_ms:
        ts = datetime.datetime.fromtimestamp(
            update_time_ms / 1000, tz=datetime.timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%S UTC")
    else:
        ts = "N/A"

    avg_price_raw = raw.get("avgPrice", "0")
    try:
        avg_price: float | None = float(avg_price_raw) if avg_price_raw else None
        if avg_price == 0.0:
            avg_price = None
    except (TypeError, ValueError):
        avg_price = None

    price_raw = raw.get("price", "0")
    try:
        order_price: float | None = float(price_raw) if price_raw else None
        if order_price == 0.0:
            order_price = None
    except (TypeError, ValueError):
        order_price = None

    return {
        "order_id": raw.get("orderId", "N/A"),
        "status": raw.get("status", "UNKNOWN"),
        "symbol": raw.get("symbol", "N/A"),
        "side": raw.get("side", "N/A"),
        "type": raw.get("type", "N/A"),
        "orig_qty": raw.get("origQty", raw.get("quantity", "N/A")),
        "executed_qty": raw.get("executedQty", "0"),
        "avg_price": avg_price,
        "price": order_price,
        "time_in_force": raw.get("timeInForce", "N/A"),
        "timestamp": ts,
    }


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------


def place_order(
    *,
    symbol: str,
    side: str,
    order_type: str,
    quantity: float | str,
    price: float | str | None = None,
    settings: Settings,
) -> dict[str, Any]:
    """Validate inputs, call the Binance API, and return a normalised response.

    This function acts as the bridge between the CLI and the low-level
    :class:`~trading_bot.client.BinanceClient`.  It handles validation,
    API communication, and response normalisation in a single call.

    Args:
        symbol:     Trading pair symbol (e.g. ``"BTCUSDT"``).
        side:       Order side — ``"BUY"`` or ``"SELL"``.
        order_type: Order type — ``"MARKET"`` or ``"LIMIT"``.
        quantity:   Order quantity (contracts).
        price:      Limit price (required for ``"LIMIT"`` orders).
        settings:   Application :class:`~trading_bot.config.Settings`.

    Returns:
        Normalised order summary dict (see :func:`_parse_order_response`).

    Raises:
        ValidationError (subclasses): On invalid input parameters.
        BinanceAPIError (subclasses):  On API-level failures.
        NetworkError:                  On connectivity problems.
        TradingBotError:               Any other application error.
    """
    # Step 1 — validate
    validated = validate_order_params(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
    )

    clean_symbol: str = validated["symbol"]
    clean_side: str = validated["side"]
    clean_type: str = validated["order_type"]
    clean_qty: float = validated["quantity"]
    clean_price: float | None = validated["price"]

    logger.info(
        "Submitting order — symbol=%s side=%s type=%s qty=%s price=%s",
        clean_symbol,
        clean_side,
        clean_type,
        clean_qty,
        clean_price,
    )

    # Step 2 — communicate with Binance
    with BinanceClient(settings) as client:
        raw_response = client.place_order(
            symbol=clean_symbol,
            side=clean_side,
            order_type=clean_type,
            quantity=clean_qty,
            price=clean_price,
            time_in_force=LIMIT_TIME_IN_FORCE,
        )

    # Step 3 — normalise
    parsed = _parse_order_response(raw_response)
    logger.info(
        "Order result — orderId=%s status=%s executedQty=%s avgPrice=%s",
        parsed["order_id"],
        parsed["status"],
        parsed["executed_qty"],
        parsed["avg_price"],
    )
    return parsed
