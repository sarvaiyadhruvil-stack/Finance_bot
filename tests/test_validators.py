"""
Unit tests for trading_bot.validators
"""

from __future__ import annotations

import pytest

from trading_bot.exceptions import (
    InvalidOrderTypeError,
    InvalidPriceError,
    InvalidQuantityError,
    InvalidSideError,
    InvalidSymbolError,
)
from trading_bot.validators import (
    validate_order_params,
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_symbol,
)


# ─────────────────────────────────────────────────────────────────────────────
# validate_symbol
# ─────────────────────────────────────────────────────────────────────────────


class TestValidateSymbol:
    def test_valid_uppercase(self):
        assert validate_symbol("BTCUSDT") == "BTCUSDT"

    def test_valid_lowercase_normalised(self):
        assert validate_symbol("btcusdt") == "BTCUSDT"

    def test_valid_strips_whitespace(self):
        assert validate_symbol("  ETHUSDT  ") == "ETHUSDT"

    def test_empty_string_raises(self):
        with pytest.raises(InvalidSymbolError, match="must not be empty"):
            validate_symbol("")

    def test_whitespace_only_raises(self):
        with pytest.raises(InvalidSymbolError, match="must not be empty"):
            validate_symbol("   ")

    def test_too_short_raises(self):
        with pytest.raises(InvalidSymbolError):
            validate_symbol("B")

    def test_special_characters_raise(self):
        with pytest.raises(InvalidSymbolError):
            validate_symbol("BTC/USDT")

    def test_hyphen_raises(self):
        with pytest.raises(InvalidSymbolError):
            validate_symbol("BTC-USDT")

    def test_long_valid_symbol(self):
        assert validate_symbol("BTCUSDT1234567890AB") == "BTCUSDT1234567890AB"

    def test_too_long_raises(self):
        with pytest.raises(InvalidSymbolError):
            validate_symbol("A" * 21)


# ─────────────────────────────────────────────────────────────────────────────
# validate_side
# ─────────────────────────────────────────────────────────────────────────────


class TestValidateSide:
    def test_buy_uppercase(self):
        assert validate_side("BUY") == "BUY"

    def test_sell_uppercase(self):
        assert validate_side("SELL") == "SELL"

    def test_buy_lowercase(self):
        assert validate_side("buy") == "BUY"

    def test_sell_mixed_case(self):
        assert validate_side("Sell") == "SELL"

    def test_invalid_raises(self):
        with pytest.raises(InvalidSideError, match="invalid"):
            validate_side("LONG")

    def test_empty_raises(self):
        with pytest.raises(InvalidSideError):
            validate_side("")


# ─────────────────────────────────────────────────────────────────────────────
# validate_order_type
# ─────────────────────────────────────────────────────────────────────────────


class TestValidateOrderType:
    def test_market(self):
        assert validate_order_type("MARKET") == "MARKET"

    def test_limit(self):
        assert validate_order_type("LIMIT") == "LIMIT"

    def test_lowercase_normalised(self):
        assert validate_order_type("market") == "MARKET"

    def test_invalid_raises(self):
        with pytest.raises(InvalidOrderTypeError):
            validate_order_type("STOP_LIMIT")

    def test_empty_raises(self):
        with pytest.raises(InvalidOrderTypeError):
            validate_order_type("")


# ─────────────────────────────────────────────────────────────────────────────
# validate_quantity
# ─────────────────────────────────────────────────────────────────────────────


class TestValidateQuantity:
    def test_valid_float(self):
        assert validate_quantity(0.001) == pytest.approx(0.001)

    def test_valid_string(self):
        assert validate_quantity("0.5") == pytest.approx(0.5)

    def test_large_valid(self):
        assert validate_quantity(999_999) == pytest.approx(999_999)

    def test_zero_raises(self):
        with pytest.raises(InvalidQuantityError, match="positive"):
            validate_quantity(0)

    def test_negative_raises(self):
        with pytest.raises(InvalidQuantityError, match="positive"):
            validate_quantity(-1.0)

    def test_non_numeric_string_raises(self):
        with pytest.raises(InvalidQuantityError, match="valid number"):
            validate_quantity("abc")

    def test_infinity_raises(self):
        with pytest.raises(InvalidQuantityError, match="finite"):
            validate_quantity(float("inf"))

    def test_nan_raises(self):
        with pytest.raises(InvalidQuantityError, match="finite"):
            validate_quantity(float("nan"))

    def test_exceeds_max_raises(self):
        with pytest.raises(InvalidQuantityError, match="maximum"):
            validate_quantity(2_000_000)


# ─────────────────────────────────────────────────────────────────────────────
# validate_price
# ─────────────────────────────────────────────────────────────────────────────


class TestValidatePrice:
    def test_market_returns_none(self):
        assert validate_price(None, order_type="MARKET") is None

    def test_market_ignores_supplied_price(self):
        assert validate_price(50000.0, order_type="MARKET") is None

    def test_limit_valid(self):
        assert validate_price(35000.0, order_type="LIMIT") == pytest.approx(35000.0)

    def test_limit_missing_raises(self):
        with pytest.raises(InvalidPriceError, match="required for LIMIT"):
            validate_price(None, order_type="LIMIT")

    def test_limit_zero_raises(self):
        with pytest.raises(InvalidPriceError, match="positive"):
            validate_price(0, order_type="LIMIT")

    def test_limit_negative_raises(self):
        with pytest.raises(InvalidPriceError, match="positive"):
            validate_price(-100.0, order_type="LIMIT")

    def test_limit_non_numeric_raises(self):
        with pytest.raises(InvalidPriceError, match="valid number"):
            validate_price("abc", order_type="LIMIT")

    def test_limit_infinity_raises(self):
        with pytest.raises(InvalidPriceError, match="finite"):
            validate_price(float("inf"), order_type="LIMIT")


# ─────────────────────────────────────────────────────────────────────────────
# validate_order_params (composite)
# ─────────────────────────────────────────────────────────────────────────────


class TestValidateOrderParams:
    def test_market_buy_valid(self):
        result = validate_order_params(
            symbol="BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quantity=0.001,
        )
        assert result["symbol"] == "BTCUSDT"
        assert result["side"] == "BUY"
        assert result["order_type"] == "MARKET"
        assert result["price"] is None

    def test_limit_sell_valid(self):
        result = validate_order_params(
            symbol="ethusdt",
            side="sell",
            order_type="limit",
            quantity="0.05",
            price="3500.00",
        )
        assert result["symbol"] == "ETHUSDT"
        assert result["side"] == "SELL"
        assert result["order_type"] == "LIMIT"
        assert result["price"] == pytest.approx(3500.0)

    def test_limit_missing_price_raises(self):
        with pytest.raises(InvalidPriceError):
            validate_order_params(
                symbol="BTCUSDT",
                side="BUY",
                order_type="LIMIT",
                quantity=0.001,
                price=None,
            )

    def test_invalid_symbol_raises(self):
        with pytest.raises(InvalidSymbolError):
            validate_order_params(
                symbol="BTC/USDT",
                side="BUY",
                order_type="MARKET",
                quantity=0.001,
            )
