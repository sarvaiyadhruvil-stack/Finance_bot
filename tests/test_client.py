"""
Unit tests for trading_bot.client (BinanceClient)
"""

from __future__ import annotations

import json
import time

import pytest
import responses as resp_mock

from trading_bot.client import BinanceClient
from trading_bot.config import Settings
from trading_bot.exceptions import (
    AuthenticationError,
    BinanceAPIError,
    OrderPlacementError,
    RateLimitError,
)

TESTNET_URL = "https://testnet.binancefuture.com"

SETTINGS = Settings(
    api_key="test_api_key",
    api_secret="test_api_secret",
    base_url=TESTNET_URL,
    timeout=5,
    recv_window=5000,
)


def _make_order_response(**overrides) -> dict:
    base = {
        "orderId": 123456789,
        "symbol": "BTCUSDT",
        "status": "NEW",
        "clientOrderId": "testOrder001",
        "price": "0",
        "avgPrice": "0",
        "origQty": "0.001",
        "executedQty": "0",
        "type": "MARKET",
        "side": "BUY",
        "updateTime": int(time.time() * 1000),
        "timeInForce": "GTC",
    }
    base.update(overrides)
    return base


# ─────────────────────────────────────────────────────────────────────────────
# get_server_time
# ─────────────────────────────────────────────────────────────────────────────


@resp_mock.activate
def test_get_server_time_success():
    resp_mock.add(
        resp_mock.GET,
        f"{TESTNET_URL}/fapi/v1/time",
        json={"serverTime": 1700000000000},
        status=200,
    )
    with BinanceClient(SETTINGS) as client:
        result = client.get_server_time()
    assert result["serverTime"] == 1700000000000


# ─────────────────────────────────────────────────────────────────────────────
# place_order — success paths
# ─────────────────────────────────────────────────────────────────────────────


@resp_mock.activate
def test_place_market_order_success():
    expected = _make_order_response(status="NEW", type="MARKET")
    resp_mock.add(
        resp_mock.POST,
        f"{TESTNET_URL}/fapi/v1/order",
        json=expected,
        status=200,
    )
    with BinanceClient(SETTINGS) as client:
        result = client.place_order(
            symbol="BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quantity=0.001,
        )
    assert result["orderId"] == 123456789
    assert result["status"] == "NEW"


@resp_mock.activate
def test_place_limit_order_success():
    expected = _make_order_response(
        status="NEW",
        type="LIMIT",
        price="35000.00",
        timeInForce="GTC",
    )
    resp_mock.add(
        resp_mock.POST,
        f"{TESTNET_URL}/fapi/v1/order",
        json=expected,
        status=200,
    )
    with BinanceClient(SETTINGS) as client:
        result = client.place_order(
            symbol="BTCUSDT",
            side="SELL",
            order_type="LIMIT",
            quantity=0.001,
            price=35000.0,
        )
    assert result["price"] == "35000.00"


# ─────────────────────────────────────────────────────────────────────────────
# place_order — error paths
# ─────────────────────────────────────────────────────────────────────────────


@resp_mock.activate
def test_rate_limit_raises():
    resp_mock.add(
        resp_mock.POST,
        f"{TESTNET_URL}/fapi/v1/order",
        json={},
        status=429,
        headers={"Retry-After": "60"},
    )
    with BinanceClient(SETTINGS) as client:
        with pytest.raises(RateLimitError):
            client.place_order(
                symbol="BTCUSDT",
                side="BUY",
                order_type="MARKET",
                quantity=0.001,
            )


@resp_mock.activate
def test_auth_error_raises():
    resp_mock.add(
        resp_mock.POST,
        f"{TESTNET_URL}/fapi/v1/order",
        json={"code": -2015, "msg": "Invalid API-key, IP, or permissions for action."},
        status=200,
    )
    with BinanceClient(SETTINGS) as client:
        with pytest.raises(AuthenticationError):
            client.place_order(
                symbol="BTCUSDT",
                side="BUY",
                order_type="MARKET",
                quantity=0.001,
            )


@resp_mock.activate
def test_order_placement_error_raises():
    resp_mock.add(
        resp_mock.POST,
        f"{TESTNET_URL}/fapi/v1/order",
        json={"code": -2010, "msg": "Account has insufficient balance for requested action."},
        status=200,
    )
    with BinanceClient(SETTINGS) as client:
        with pytest.raises(OrderPlacementError, match="insufficient balance"):
            client.place_order(
                symbol="BTCUSDT",
                side="BUY",
                order_type="MARKET",
                quantity=0.001,
            )


@resp_mock.activate
def test_generic_api_error_raises():
    resp_mock.add(
        resp_mock.POST,
        f"{TESTNET_URL}/fapi/v1/order",
        json={"code": -1121, "msg": "Invalid symbol."},
        status=200,
    )
    with BinanceClient(SETTINGS) as client:
        with pytest.raises(BinanceAPIError, match="Invalid symbol"):
            client.place_order(
                symbol="INVALID",
                side="BUY",
                order_type="MARKET",
                quantity=0.001,
            )


@resp_mock.activate
def test_http_401_raises_auth_error():
    resp_mock.add(
        resp_mock.POST,
        f"{TESTNET_URL}/fapi/v1/order",
        json={},
        status=401,
    )
    with BinanceClient(SETTINGS) as client:
        with pytest.raises(AuthenticationError):
            client.place_order(
                symbol="BTCUSDT",
                side="BUY",
                order_type="MARKET",
                quantity=0.001,
            )
