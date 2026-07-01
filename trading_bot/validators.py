"""
Input validation for trading order parameters.

Each ``validate_*`` function raises a specific :mod:`exceptions` subclass on
failure, giving the CLI layer clear, user-friendly error messages and letting
the logging layer capture structured context automatically.
"""

from __future__ import annotations

import math
import re

from trading_bot.config import VALID_ORDER_TYPES, VALID_SIDES
from trading_bot.exceptions import (
    InvalidOrderTypeError,
    InvalidPriceError,
    InvalidQuantityError,
    InvalidSideError,
    InvalidSymbolError,
)
from trading_bot.logging_config import get_logger

logger = get_logger("validators")

# Binance symbol pattern: 2-20 uppercase alphanumeric characters.
_SYMBOL_RE = re.compile(r"^[A-Z0-9]{2,20}$")

# Maximum quantity / price to guard against obviously wrong inputs.
_MAX_QUANTITY: float = 1_000_000.0
_MAX_PRICE: float = 10_000_000.0


# ---------------------------------------------------------------------------
# Individual validators
# ---------------------------------------------------------------------------


def validate_symbol(symbol: str) -> str:
    """Validate and normalise a Binance trading symbol.

    Args:
        symbol: Raw symbol string from the CLI (e.g. ``"btcusdt"``).

    Returns:
        Upper-cased, stripped symbol string (e.g. ``"BTCUSDT"``).

    Raises:
        InvalidSymbolError: If the symbol is blank or does not match the
            expected ``^[A-Z0-9]{2,20}$`` pattern.
    """
    cleaned = symbol.strip().upper()

    if not cleaned:
        msg = "Symbol must not be empty."
        logger.warning("Validation failed — %s (raw=%r)", msg, symbol)
        raise InvalidSymbolError(msg, context={"raw_symbol": symbol})

    if not _SYMBOL_RE.match(cleaned):
        msg = (
            f"Symbol '{cleaned}' is invalid. Expected 2–20 uppercase "
            "alphanumeric characters (e.g. BTCUSDT, ETHUSDT)."
        )
        logger.warning("Validation failed — %s", msg)
        raise InvalidSymbolError(msg, context={"symbol": cleaned})

    logger.debug("Symbol validated: %s", cleaned)
    return cleaned


def validate_side(side: str) -> str:
    """Validate the order side.

    Args:
        side: Raw side string from the CLI (e.g. ``"buy"``).

    Returns:
        Upper-cased side string — ``"BUY"`` or ``"SELL"``.

    Raises:
        InvalidSideError: If the value is not ``BUY`` or ``SELL``.
    """
    cleaned = side.strip().upper()

    if cleaned not in VALID_SIDES:
        msg = (
            f"Order side '{cleaned}' is invalid. "
            f"Accepted values: {sorted(VALID_SIDES)}."
        )
        logger.warning("Validation failed — %s", msg)
        raise InvalidSideError(msg, context={"side": cleaned})

    logger.debug("Side validated: %s", cleaned)
    return cleaned


def validate_order_type(order_type: str) -> str:
    """Validate the order type.

    Args:
        order_type: Raw order-type string from the CLI (e.g. ``"limit"``).

    Returns:
        Upper-cased order type — ``"MARKET"`` or ``"LIMIT"``.

    Raises:
        InvalidOrderTypeError: If the value is not ``MARKET`` or ``LIMIT``.
    """
    cleaned = order_type.strip().upper()

    if cleaned not in VALID_ORDER_TYPES:
        msg = (
            f"Order type '{cleaned}' is invalid. "
            f"Accepted values: {sorted(VALID_ORDER_TYPES)}."
        )
        logger.warning("Validation failed — %s", msg)
        raise InvalidOrderTypeError(msg, context={"order_type": cleaned})

    logger.debug("Order type validated: %s", cleaned)
    return cleaned


def validate_quantity(quantity: float | str) -> float:
    """Validate the order quantity.

    Args:
        quantity: Quantity value (may arrive as a string from argparse).

    Returns:
        Validated positive float quantity.

    Raises:
        InvalidQuantityError: If the value cannot be parsed, is not finite,
            is not positive, or exceeds the sanity cap.
    """
    try:
        qty = float(quantity)
    except (TypeError, ValueError):
        msg = f"Quantity '{quantity}' is not a valid number."
        logger.warning("Validation failed — %s", msg)
        raise InvalidQuantityError(msg, context={"quantity": quantity})

    if math.isnan(qty) or math.isinf(qty):
        msg = f"Quantity must be a finite number, got '{quantity}'."
        logger.warning("Validation failed — %s", msg)
        raise InvalidQuantityError(msg, context={"quantity": quantity})

    if qty <= 0:
        msg = f"Quantity must be a positive number, got {qty}."
        logger.warning("Validation failed — %s", msg)
        raise InvalidQuantityError(msg, context={"quantity": qty})

    if qty > _MAX_QUANTITY:
        msg = (
            f"Quantity {qty} exceeds the maximum allowed value of "
            f"{_MAX_QUANTITY:,.0f}. Please double-check your input."
        )
        logger.warning("Validation failed — %s", msg)
        raise InvalidQuantityError(msg, context={"quantity": qty})

    logger.debug("Quantity validated: %s", qty)
    return qty


def validate_price(
    price: float | str | None,
    *,
    order_type: str,
) -> float | None:
    """Validate the order price.

    For MARKET orders the price is ignored (returns ``None``).
    For LIMIT orders the price must be a positive finite number.

    Args:
        price:      Price value from CLI (may be ``None`` if not supplied).
        order_type: Validated order type (``"MARKET"`` or ``"LIMIT"``).

    Returns:
        ``None`` for MARKET orders, or the validated positive float price.

    Raises:
        InvalidPriceError: For LIMIT orders when price is absent, non-numeric,
            non-finite, not positive, or exceeds the sanity cap.
    """
    if order_type == "MARKET":
        if price is not None:
            logger.debug(
                "Price %r supplied for MARKET order — it will be ignored.", price
            )
        return None

    # LIMIT order — price is mandatory.
    if price is None:
        msg = "Price is required for LIMIT orders. Supply --price <value>."
        logger.warning("Validation failed — %s", msg)
        raise InvalidPriceError(msg, context={"order_type": order_type})

    try:
        p = float(price)
    except (TypeError, ValueError):
        msg = f"Price '{price}' is not a valid number."
        logger.warning("Validation failed — %s", msg)
        raise InvalidPriceError(msg, context={"price": price})

    if math.isnan(p) or math.isinf(p):
        msg = f"Price must be a finite number, got '{price}'."
        logger.warning("Validation failed — %s", msg)
        raise InvalidPriceError(msg, context={"price": price})

    if p <= 0:
        msg = f"Price must be a positive number, got {p}."
        logger.warning("Validation failed — %s", msg)
        raise InvalidPriceError(msg, context={"price": p})

    if p > _MAX_PRICE:
        msg = (
            f"Price {p} exceeds the maximum allowed value of "
            f"{_MAX_PRICE:,.0f}. Please double-check your input."
        )
        logger.warning("Validation failed — %s", msg)
        raise InvalidPriceError(msg, context={"price": p})

    logger.debug("Price validated: %s", p)
    return p


# ---------------------------------------------------------------------------
# Composite validator
# ---------------------------------------------------------------------------


def validate_order_params(
    *,
    symbol: str,
    side: str,
    order_type: str,
    quantity: float | str,
    price: float | str | None = None,
) -> dict:
    """Run all validators in sequence and return a clean parameter dict.

    This is the primary entry-point used by :mod:`orders`.

    Args:
        symbol:     Trading pair symbol.
        side:       Order side.
        order_type: Order type.
        quantity:   Order quantity.
        price:      Order price (optional; required for LIMIT).

    Returns:
        Dictionary with validated keys:
        ``symbol``, ``side``, ``order_type``, ``quantity``, ``price``.

    Raises:
        Any :mod:`exceptions` subclass on the first validation failure.
    """
    logger.info(
        "Validating order params — symbol=%s side=%s type=%s qty=%s price=%s",
        symbol,
        side,
        order_type,
        quantity,
        price,
    )

    clean_symbol = validate_symbol(symbol)
    clean_side = validate_side(side)
    clean_type = validate_order_type(order_type)
    clean_qty = validate_quantity(quantity)
    clean_price = validate_price(price, order_type=clean_type)

    validated = {
        "symbol": clean_symbol,
        "side": clean_side,
        "order_type": clean_type,
        "quantity": clean_qty,
        "price": clean_price,
    }

    logger.info("All order params validated successfully: %s", validated)
    return validated
