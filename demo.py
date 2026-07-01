"""
demo.py -- Dry-run demonstration of the Binance Futures Trading Bot CLI.

Patches:
  • os.environ  → injects fake API credentials so config loads successfully
  • place_order → returns realistic mock responses (no network calls)

Three scenarios are shown:
  1. Successful MARKET BUY
  2. Successful LIMIT SELL
  3. Validation failure  (negative price)
  4. API rejection       (insufficient balance)
"""

import io
import os
import sys

# Force UTF-8 on Windows so box-drawing / emoji print correctly.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Inject fake credentials before any trading_bot module is imported ─────
os.environ.setdefault("BINANCE_API_KEY",    "DEMO_API_KEY_TESTNET_123456")
os.environ.setdefault("BINANCE_API_SECRET", "DEMO_SECRET_TESTNET_ABCDEF")
os.environ.setdefault("BINANCE_BASE_URL",   "https://testnet.binancefuture.com")
os.environ.setdefault("LOG_LEVEL",          "DEBUG")

from unittest.mock import patch                    # noqa: E402

from trading_bot.cli import main                   # noqa: E402
from trading_bot.exceptions import OrderPlacementError  # noqa: E402

# ── Realistic mock responses ──────────────────────────────────────────────

MARKET_BUY_RESULT = {
    "order_id":     4_611_685_020,
    "status":       "FILLED",
    "symbol":       "BTCUSDT",
    "side":         "BUY",
    "type":         "MARKET",
    "orig_qty":     "0.001",
    "executed_qty": "0.001",
    "avg_price":    42_185.3,
    "price":        None,
    "time_in_force": "GTC",
    "timestamp":    "2026-07-01T06:10:01 UTC",
}

LIMIT_SELL_RESULT = {
    "order_id":     4_611_688_100,
    "status":       "NEW",
    "symbol":       "ETHUSDT",
    "side":         "SELL",
    "type":         "LIMIT",
    "orig_qty":     "0.05",
    "executed_qty": "0",
    "avg_price":    None,
    "price":        3_500.0,
    "time_in_force": "GTC",
    "timestamp":    "2026-07-01T06:10:05 UTC",
}

# ─────────────────────────────────────────────────────────────────────────────

DIVIDER = "\n" + "=" * 70 + "\n"


def run_scenario(title: str, args: list[str], *, mock_result=None, mock_exc=None):
    print(DIVIDER)
    print(f"  >> SCENARIO: {title}")
    print(DIVIDER)

    if mock_exc:
        with patch("trading_bot.cli.place_order", side_effect=mock_exc), \
             patch("trading_bot.cli.load_settings"):
            code = main(args)
    elif mock_result:
        with patch("trading_bot.cli.place_order", return_value=mock_result), \
             patch("trading_bot.cli.load_settings"):
            code = main(args)
    else:
        # No patch — let validators surface the error naturally
        with patch("trading_bot.cli.load_settings"):
            code = main(args)

    print(f"\n  [exit code: {code}]")


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    # ── 1. Successful MARKET BUY ──────────────────────────────────────────
    run_scenario(
        "MARKET BUY 0.001 BTCUSDT  →  FILLED",
        [
            "--symbol", "BTCUSDT",
            "--side",   "BUY",
            "--type",   "MARKET",
            "--quantity", "0.001",
            "--yes",          # skip confirmation prompt in demo
        ],
        mock_result=MARKET_BUY_RESULT,
    )

    # ── 2. Successful LIMIT SELL ──────────────────────────────────────────
    run_scenario(
        "LIMIT SELL 0.05 ETHUSDT @ $3,500  →  NEW (resting in book)",
        [
            "--symbol",   "ETHUSDT",
            "--side",     "SELL",
            "--type",     "LIMIT",
            "--quantity", "0.05",
            "--price",    "3500.00",
            "--yes",
        ],
        mock_result=LIMIT_SELL_RESULT,
    )

    # ── 3. Validation failure — negative price ────────────────────────────
    run_scenario(
        "LIMIT BUY with NEGATIVE PRICE  →  Validation error",
        [
            "--symbol",   "BTCUSDT",
            "--side",     "BUY",
            "--type",     "LIMIT",
            "--quantity", "0.001",
            "--price",    "-500",
            "--yes",
        ],
        # No mock — validators run before place_order is ever called
    )

    # ── 4. API rejection — insufficient balance ───────────────────────────
    run_scenario(
        "MARKET BUY huge qty  →  Binance rejects (insufficient balance)",
        [
            "--symbol",   "BTCUSDT",
            "--side",     "BUY",
            "--type",     "MARKET",
            "--quantity", "999999",
            "--yes",
        ],
        mock_exc=OrderPlacementError(
            "Binance API error -2010: "
            "Account has insufficient balance for requested action.",
            error_code=-2010,
            http_status=200,
        ),
    )

    print(DIVIDER)
    print("  [OK] Demo complete -- all scenarios executed.")
    print(DIVIDER)
