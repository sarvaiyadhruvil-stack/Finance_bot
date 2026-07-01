"""
Unit tests for trading_bot.orders (orchestration layer)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from trading_bot.config import Settings
from trading_bot.exceptions import (
    InvalidPriceError,
    InvalidSymbolError,
    OrderPlacementError,
)
from trading_bot.orders import _parse_order_response, place_order

SETTINGS = Settings(
    api_key="test_key",
    api_secret="test_secret",
    base_url="https://testnet.binancefuture.com",
)

_RAW_MARKET_FILLED = {
    "orderId": 111222333,
    "symbol": "BTCUSDT",
    "status": "FILLED",
    "side": "BUY",
    "type": "MARKET",
    "origQty": "0.001",
    "executedQty": "0.001",
    "avgPrice": "42000.50",
    "price": "0",
    "timeInForce": "GTC",
    "updateTime": 1705309200000,
}

_RAW_LIMIT_NEW = {
    "orderId": 444555666,
    "symbol": "ETHUSDT",
    "status": "NEW",
    "side": "SELL",
    "type": "LIMIT",
    "origQty": "0.05",
    "executedQty": "0",
    "avgPrice": "0",
    "price": "3500.00",
    "timeInForce": "GTC",
    "updateTime": 1705313400000,
}


# ---------------------------------------------------------------------------
# _parse_order_response
# ---------------------------------------------------------------------------


class TestParseOrderResponse:
    def test_market_filled_parses_correctly(self):
        result = _parse_order_response(_RAW_MARKET_FILLED)
        assert result["order_id"] == 111222333
        assert result["status"] == "FILLED"
        assert result["symbol"] == "BTCUSDT"
        assert result["side"] == "BUY"
        assert result["avg_price"] == pytest.approx(42000.50)
        assert result["price"] is None  # zero price → None for MARKET
        assert result["executed_qty"] == "0.001"
        assert "UTC" in result["timestamp"]

    def test_limit_new_parses_correctly(self):
        result = _parse_order_response(_RAW_LIMIT_NEW)
        assert result["order_id"] == 444555666
        assert result["status"] == "NEW"
        assert result["avg_price"] is None  # zero avgPrice → None
        assert result["price"] == pytest.approx(3500.0)

    def test_missing_update_time_gives_na(self):
        raw = dict(_RAW_MARKET_FILLED)
        del raw["updateTime"]
        result = _parse_order_response(raw)
        assert result["timestamp"] == "N/A"

    def test_missing_fields_give_defaults(self):
        result = _parse_order_response({})
        assert result["order_id"] == "N/A"
        assert result["status"] == "UNKNOWN"


# ---------------------------------------------------------------------------
# place_order
# ---------------------------------------------------------------------------


class TestPlaceOrder:
    @patch("trading_bot.orders.BinanceClient")
    def test_market_buy_calls_client_correctly(self, MockClient):
        mock_instance = MagicMock()
        mock_instance.__enter__ = MagicMock(return_value=mock_instance)
        mock_instance.__exit__ = MagicMock(return_value=False)
        mock_instance.place_order.return_value = _RAW_MARKET_FILLED
        MockClient.return_value = mock_instance

        result = place_order(
            symbol="BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quantity=0.001,
            settings=SETTINGS,
        )

        mock_instance.place_order.assert_called_once()
        call_kwargs = mock_instance.place_order.call_args.kwargs
        assert call_kwargs["symbol"] == "BTCUSDT"
        assert call_kwargs["side"] == "BUY"
        assert call_kwargs["order_type"] == "MARKET"
        assert result["order_id"] == 111222333

    @patch("trading_bot.orders.BinanceClient")
    def test_limit_sell_passes_price(self, MockClient):
        mock_instance = MagicMock()
        mock_instance.__enter__ = MagicMock(return_value=mock_instance)
        mock_instance.__exit__ = MagicMock(return_value=False)
        mock_instance.place_order.return_value = _RAW_LIMIT_NEW
        MockClient.return_value = mock_instance

        result = place_order(
            symbol="ETHUSDT",
            side="SELL",
            order_type="LIMIT",
            quantity=0.05,
            price=3500.0,
            settings=SETTINGS,
        )

        call_kwargs = mock_instance.place_order.call_args.kwargs
        assert call_kwargs["price"] == pytest.approx(3500.0)
        assert result["status"] == "NEW"

    def test_invalid_symbol_raises_before_api_call(self):
        with pytest.raises(InvalidSymbolError):
            place_order(
                symbol="BAD/SYMBOL",
                side="BUY",
                order_type="MARKET",
                quantity=0.001,
                settings=SETTINGS,
            )

    def test_limit_without_price_raises(self):
        with pytest.raises(InvalidPriceError):
            place_order(
                symbol="BTCUSDT",
                side="BUY",
                order_type="LIMIT",
                quantity=0.001,
                price=None,
                settings=SETTINGS,
            )

    @patch("trading_bot.orders.BinanceClient")
    def test_api_exception_propagates(self, MockClient):
        mock_instance = MagicMock()
        mock_instance.__enter__ = MagicMock(return_value=mock_instance)
        mock_instance.__exit__ = MagicMock(return_value=False)
        mock_instance.place_order.side_effect = OrderPlacementError(
            "Insufficient balance", error_code=-2010
        )
        MockClient.return_value = mock_instance

        with pytest.raises(OrderPlacementError, match="Insufficient balance"):
            place_order(
                symbol="BTCUSDT",
                side="BUY",
                order_type="MARKET",
                quantity=0.001,
                settings=SETTINGS,
            )
