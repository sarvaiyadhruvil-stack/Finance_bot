"""
Unit tests for trading_bot.cli (main entry-point)

Uses pytest's capsys + monkeypatch to test argument parsing, user confirmation
flow, and all exception-handling branches without touching the network.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from trading_bot.cli import main
from trading_bot.exceptions import (
    AuthenticationError,
    BinanceAPIError,
    ConfigurationError,
    InvalidPriceError,
    InvalidSymbolError,
    NetworkError,
    OrderPlacementError,
    RateLimitError,
    ValidationError,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_GOOD_MARKET_ARGS = [
    "--symbol", "BTCUSDT",
    "--side", "BUY",
    "--type", "MARKET",
    "--quantity", "0.001",
    "--yes",
]

_GOOD_LIMIT_ARGS = [
    "--symbol", "ETHUSDT",
    "--side", "SELL",
    "--type", "LIMIT",
    "--quantity", "0.05",
    "--price", "3500.00",
    "--yes",
]

_GOOD_RESULT = {
    "order_id": 123456789,
    "status": "FILLED",
    "symbol": "BTCUSDT",
    "side": "BUY",
    "type": "MARKET",
    "orig_qty": "0.001",
    "executed_qty": "0.001",
    "avg_price": 42000.0,
    "price": None,
    "time_in_force": "GTC",
    "timestamp": "2024-01-15T09:00:01 UTC",
}

_GOOD_LIMIT_RESULT = {
    "order_id": 987654321,
    "status": "NEW",
    "symbol": "ETHUSDT",
    "side": "SELL",
    "type": "LIMIT",
    "orig_qty": "0.05",
    "executed_qty": "0",
    "avg_price": None,
    "price": 3500.0,
    "time_in_force": "GTC",
    "timestamp": "2024-01-15T10:30:01 UTC",
}


# ---------------------------------------------------------------------------
# Success paths
# ---------------------------------------------------------------------------


class TestMainSuccessPaths:
    @patch("trading_bot.cli.load_settings")
    @patch("trading_bot.cli.place_order", return_value=_GOOD_RESULT)
    def test_market_order_exits_zero(self, _mock_order, _mock_cfg, capsys):
        exit_code = main(_GOOD_MARKET_ARGS)
        assert exit_code == 0

    @patch("trading_bot.cli.load_settings")
    @patch("trading_bot.cli.place_order", return_value=_GOOD_RESULT)
    def test_market_order_prints_order_id(self, _mock_order, _mock_cfg, capsys):
        main(_GOOD_MARKET_ARGS)
        captured = capsys.readouterr()
        assert "123456789" in captured.out

    @patch("trading_bot.cli.load_settings")
    @patch("trading_bot.cli.place_order", return_value=_GOOD_LIMIT_RESULT)
    def test_limit_order_exits_zero(self, _mock_order, _mock_cfg, capsys):
        exit_code = main(_GOOD_LIMIT_ARGS)
        assert exit_code == 0

    @patch("trading_bot.cli.load_settings")
    @patch("trading_bot.cli.place_order", return_value=_GOOD_LIMIT_RESULT)
    def test_limit_order_prints_price(self, _mock_order, _mock_cfg, capsys):
        main(_GOOD_LIMIT_ARGS)
        captured = capsys.readouterr()
        # CLI formats 3500.0 with thousands separator → "3,500"
        assert "3,500" in captured.out or "3500" in captured.out

    @patch("trading_bot.cli.load_settings")
    @patch("trading_bot.cli.place_order", return_value=_GOOD_RESULT)
    def test_order_summary_shows_symbol(self, _mock_order, _mock_cfg, capsys):
        main(_GOOD_MARKET_ARGS)
        captured = capsys.readouterr()
        assert "BTCUSDT" in captured.out

    @patch("trading_bot.cli.load_settings")
    @patch("trading_bot.cli.place_order", return_value=_GOOD_RESULT)
    def test_success_message_in_output(self, _mock_order, _mock_cfg, capsys):
        main(_GOOD_MARKET_ARGS)
        captured = capsys.readouterr()
        assert "successfully" in captured.out.lower()


# ---------------------------------------------------------------------------
# User cancellation
# ---------------------------------------------------------------------------


class TestUserCancellation:
    @patch("trading_bot.cli.load_settings")
    @patch("trading_bot.cli.place_order")
    @patch("builtins.input", return_value="no")
    def test_cancel_on_no_exits_zero(self, _mock_input, mock_order, _mock_cfg):
        args = [a for a in _GOOD_MARKET_ARGS if a != "--yes"]
        exit_code = main(args)
        assert exit_code == 0
        mock_order.assert_not_called()

    @patch("trading_bot.cli.load_settings")
    @patch("trading_bot.cli.place_order")
    @patch("builtins.input", side_effect=KeyboardInterrupt)
    def test_keyboard_interrupt_exits_zero(self, _mock_input, mock_order, _mock_cfg):
        args = [a for a in _GOOD_MARKET_ARGS if a != "--yes"]
        exit_code = main(args)
        assert exit_code == 0
        mock_order.assert_not_called()

    @patch("trading_bot.cli.load_settings")
    @patch("trading_bot.cli.place_order")
    @patch("builtins.input", return_value="yes")
    def test_confirm_on_yes_calls_place_order(self, _mock_input, mock_order, _mock_cfg):
        mock_order.return_value = _GOOD_RESULT
        args = [a for a in _GOOD_MARKET_ARGS if a != "--yes"]
        main(args)
        mock_order.assert_called_once()


# ---------------------------------------------------------------------------
# Error-handling branches
# ---------------------------------------------------------------------------


class TestErrorHandling:
    @patch(
        "trading_bot.cli.load_settings",
        side_effect=ConfigurationError("Missing BINANCE_API_KEY"),
    )
    def test_config_error_exits_one(self, _mock_cfg, capsys):
        exit_code = main(_GOOD_MARKET_ARGS)
        assert exit_code == 1
        assert "Configuration error" in capsys.readouterr().out

    @patch("trading_bot.cli.load_settings")
    @patch(
        "trading_bot.cli.place_order",
        side_effect=InvalidPriceError("Price required for LIMIT"),
    )
    def test_validation_error_exits_one(self, _mock_order, _mock_cfg, capsys):
        exit_code = main(_GOOD_MARKET_ARGS)
        assert exit_code == 1
        assert "Validation error" in capsys.readouterr().out

    @patch("trading_bot.cli.load_settings")
    @patch(
        "trading_bot.cli.place_order",
        side_effect=NetworkError("Connection refused"),
    )
    def test_network_error_exits_one(self, _mock_order, _mock_cfg, capsys):
        exit_code = main(_GOOD_MARKET_ARGS)
        assert exit_code == 1
        assert "Network error" in capsys.readouterr().out

    @patch("trading_bot.cli.load_settings")
    @patch(
        "trading_bot.cli.place_order",
        side_effect=AuthenticationError(
            "Invalid API key", error_code=-2015, http_status=200
        ),
    )
    def test_auth_error_exits_one(self, _mock_order, _mock_cfg, capsys):
        exit_code = main(_GOOD_MARKET_ARGS)
        assert exit_code == 1
        out = capsys.readouterr().out
        assert "Binance API error" in out or "error" in out.lower()

    @patch("trading_bot.cli.load_settings")
    @patch(
        "trading_bot.cli.place_order",
        side_effect=RateLimitError("Rate limit exceeded", http_status=429),
    )
    def test_rate_limit_exits_one(self, _mock_order, _mock_cfg, capsys):
        exit_code = main(_GOOD_MARKET_ARGS)
        assert exit_code == 1

    @patch("trading_bot.cli.load_settings")
    @patch(
        "trading_bot.cli.place_order",
        side_effect=OrderPlacementError(
            "Insufficient balance", error_code=-2010, http_status=200
        ),
    )
    def test_order_placement_error_exits_one(self, _mock_order, _mock_cfg, capsys):
        exit_code = main(_GOOD_MARKET_ARGS)
        assert exit_code == 1

    @patch("trading_bot.cli.load_settings")
    @patch(
        "trading_bot.cli.place_order",
        side_effect=RuntimeError("Something exploded"),
    )
    def test_unexpected_exception_exits_one(self, _mock_order, _mock_cfg, capsys):
        exit_code = main(_GOOD_MARKET_ARGS)
        assert exit_code == 1
        assert "unexpected error" in capsys.readouterr().out.lower()


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


class TestArgParsing:
    def test_missing_symbol_exits_nonzero(self):
        with pytest.raises(SystemExit) as exc_info:
            main(["--side", "BUY", "--type", "MARKET", "--quantity", "0.001"])
        assert exc_info.value.code != 0

    def test_missing_quantity_exits_nonzero(self):
        with pytest.raises(SystemExit) as exc_info:
            main(["--symbol", "BTCUSDT", "--side", "BUY", "--type", "MARKET"])
        assert exc_info.value.code != 0

    def test_invalid_side_choice_exits_nonzero(self):
        with pytest.raises(SystemExit) as exc_info:
            main([
                "--symbol", "BTCUSDT",
                "--side", "LONG",
                "--type", "MARKET",
                "--quantity", "0.001",
            ])
        assert exc_info.value.code != 0

    def test_version_flag_exits(self):
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0
