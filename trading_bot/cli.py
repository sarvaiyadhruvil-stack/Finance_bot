"""
Command-line interface for the Binance Futures Trading Bot.

Entry-point: ``python -m trading_bot.cli`` (or the ``trade`` console script).

Usage examples
--------------
MARKET BUY::

    python -m trading_bot.cli --symbol BTCUSDT --side BUY \\
        --type MARKET --quantity 0.001

LIMIT SELL::

    python -m trading_bot.cli --symbol ETHUSDT --side SELL \\
        --type LIMIT --quantity 0.05 --price 3500.00
"""

from __future__ import annotations

import argparse
import sys
import textwrap
from typing import Any

from trading_bot.config import load_settings
from trading_bot.exceptions import (
    BinanceAPIError,
    ConfigurationError,
    NetworkError,
    TradingBotError,
    ValidationError,
)
from trading_bot.logging_config import get_logger, setup_logging
from trading_bot.orders import place_order

# Initialise logging before anything else.
setup_logging()
logger = get_logger("cli")

# ---------------------------------------------------------------------------
# ANSI colour helpers (degrade gracefully on Windows without colorama)
# ---------------------------------------------------------------------------

_RESET = "\033[0m"
_BOLD = "\033[1m"
_GREEN = "\033[92m"
_RED = "\033[91m"
_CYAN = "\033[96m"
_YELLOW = "\033[93m"
_MAGENTA = "\033[95m"
_BLUE = "\033[94m"


def _c(text: str, *codes: str) -> str:
    """Wrap *text* in ANSI codes when stdout is a TTY."""
    if sys.stdout.isatty():
        return "".join(codes) + text + _RESET
    return text


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

_BANNER = r"""
  ____  _                              ____        _
 | __ )(_)_ __   __ _ _ __   ___ ___|  _ \  ___ | |_
 |  _ \| | '_ \ / _` | '_ \ / __/ _ \ |_) |/ _ \| __|
 | |_) | | | | | (_| | | | | (_|  __/  _ < (_) | |_
 |____/|_|_| |_|\__,_|_| |_|\___\___|_| \_\___/ \__|

          Binance Futures Testnet — Trading CLI
"""


def _print_banner() -> None:
    print(_c(_BANNER, _CYAN, _BOLD))


def _separator(char: str = "─", width: int = 60) -> str:
    return _c(char * width, _BLUE)


def _print_order_summary(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: float | None,
) -> None:
    """Print a formatted pre-submission order summary table."""
    print()
    print(_c("  📋  ORDER SUMMARY", _BOLD, _CYAN))
    print(_separator())
    rows = [
        ("Symbol", symbol),
        ("Side", _c(side, _GREEN if side == "BUY" else _RED, _BOLD)),
        ("Type", order_type),
        ("Quantity", f"{quantity:,.8g}"),
        (
            "Price",
            f"{price:,.8g}" if price is not None else _c("N/A (MARKET)", _YELLOW),
        ),
    ]
    for label, value in rows:
        print(f"  {_c(label + ':', _BOLD):<30} {value}")
    print(_separator())


def _print_order_result(result: dict[str, Any]) -> None:
    """Print a formatted post-submission order result table."""
    side = result.get("side", "N/A")
    status = result.get("status", "UNKNOWN")

    status_colour = _GREEN if status in ("FILLED", "NEW") else _YELLOW

    print()
    print(_c("  ✅  ORDER RESULT", _BOLD, _GREEN))
    print(_separator())
    rows = [
        ("Order ID", str(result.get("order_id", "N/A"))),
        ("Status", _c(status, status_colour, _BOLD)),
        ("Symbol", result.get("symbol", "N/A")),
        ("Side", _c(side, _GREEN if side == "BUY" else _RED, _BOLD)),
        ("Type", result.get("type", "N/A")),
        ("Original Qty", str(result.get("orig_qty", "N/A"))),
        ("Executed Qty", str(result.get("executed_qty", "0"))),
        (
            "Average Price",
            f"{result['avg_price']:,.8g}" if result.get("avg_price") else "N/A",
        ),
        (
            "Limit Price",
            f"{result['price']:,.8g}" if result.get("price") else "N/A (MARKET)",
        ),
        ("Time-in-Force", result.get("time_in_force", "N/A")),
        ("Timestamp (UTC)", result.get("timestamp", "N/A")),
    ]
    for label, value in rows:
        print(f"  {_c(label + ':', _BOLD):<30} {value}")
    print(_separator())
    print()


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Construct and return the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="trade",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(
            """\
            Binance Futures Testnet — Trading Bot CLI
            -----------------------------------------
            Place MARKET or LIMIT orders on the Binance Futures Testnet.
            Credentials are read from environment variables / .env file.
            """
        ),
        epilog=textwrap.dedent(
            """\
            Examples:
              MARKET BUY  0.001 BTC:
                trade --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

              LIMIT SELL  0.05 ETH at $3 500:
                trade --symbol ETHUSDT --side SELL --type LIMIT \\
                      --quantity 0.05 --price 3500.00
            """
        ),
    )

    parser.add_argument(
        "--symbol",
        required=True,
        metavar="SYMBOL",
        help="Trading pair symbol, e.g. BTCUSDT (case-insensitive).",
    )
    parser.add_argument(
        "--side",
        required=True,
        choices=["BUY", "SELL", "buy", "sell"],
        metavar="SIDE",
        help="Order side: BUY or SELL.",
    )
    parser.add_argument(
        "--type",
        dest="order_type",
        required=True,
        choices=["MARKET", "LIMIT", "market", "limit"],
        metavar="TYPE",
        help="Order type: MARKET or LIMIT.",
    )
    parser.add_argument(
        "--quantity",
        required=True,
        type=float,
        metavar="QTY",
        help="Order quantity (positive number).",
    )
    parser.add_argument(
        "--price",
        required=False,
        type=float,
        default=None,
        metavar="PRICE",
        help="Limit price (required for LIMIT orders, ignored for MARKET).",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        default=False,
        help="Skip confirmation prompt and submit order immediately.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0",
    )

    return parser


# ---------------------------------------------------------------------------
# User confirmation
# ---------------------------------------------------------------------------


def _confirm(auto_confirm: bool) -> bool:
    """Ask the user to confirm the order submission.

    Args:
        auto_confirm: If ``True``, skip the prompt and return ``True``.

    Returns:
        ``True`` if the user confirms, ``False`` otherwise.
    """
    if auto_confirm:
        logger.info("Auto-confirmation flag set — skipping prompt.")
        return True

    prompt = _c("\n  ⚠️  Submit this order? [yes/no]: ", _YELLOW, _BOLD)
    try:
        answer = input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        logger.info("Order cancelled by user (keyboard interrupt / EOF).")
        return False

    confirmed = answer in ("yes", "y")
    if not confirmed:
        logger.info("Order cancelled by user (answered '%s').", answer)
    return confirmed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI entry-point.

    Args:
        argv: Argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Exit code — ``0`` on success, ``1`` on error.
    """
    _print_banner()

    parser = _build_parser()
    args = parser.parse_args(argv)

    logger.info(
        "CLI invoked — symbol=%s side=%s type=%s qty=%s price=%s",
        args.symbol,
        args.side,
        args.order_type,
        args.quantity,
        args.price,
    )

    # ------------------------------------------------------------------
    # Load configuration
    # ------------------------------------------------------------------
    try:
        settings = load_settings()
    except ConfigurationError as exc:
        print(_c(f"\n  ❌  Configuration error: {exc}\n", _RED, _BOLD))
        logger.error("Configuration error: %s", exc, exc_info=True)
        return 1

    # ------------------------------------------------------------------
    # Display order summary and ask for confirmation
    # ------------------------------------------------------------------
    _print_order_summary(
        symbol=args.symbol.upper(),
        side=args.side.upper(),
        order_type=args.order_type.upper(),
        quantity=args.quantity,
        price=args.price,
    )

    if not _confirm(args.yes):
        print(_c("\n  🚫  Order cancelled.\n", _YELLOW))
        return 0

    print(_c("\n  ⏳  Submitting order…\n", _CYAN))

    # ------------------------------------------------------------------
    # Place the order
    # ------------------------------------------------------------------
    try:
        result = place_order(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
            settings=settings,
        )

    except ValidationError as exc:
        print(_c(f"\n  ❌  Validation error: {exc}\n", _RED, _BOLD))
        logger.error("Validation error: %s | context=%s", exc, exc.context)
        return 1

    except ConfigurationError as exc:
        print(_c(f"\n  ❌  Configuration error: {exc}\n", _RED, _BOLD))
        logger.error("Configuration error: %s", exc, exc_info=True)
        return 1

    except NetworkError as exc:
        print(
            _c(
                f"\n  ❌  Network error: {exc}\n"
                "  Check your internet connection and try again.\n",
                _RED,
                _BOLD,
            )
        )
        logger.error("Network error: %s", exc, exc_info=True)
        return 1

    except BinanceAPIError as exc:
        detail = f"(code {exc.error_code})" if exc.error_code else ""
        print(
            _c(
                f"\n  ❌  Binance API error {detail}: {exc}\n",
                _RED,
                _BOLD,
            )
        )
        logger.error(
            "Binance API error — code=%s http=%s msg=%s",
            exc.error_code,
            exc.http_status,
            exc,
            exc_info=True,
        )
        return 1

    except TradingBotError as exc:
        print(_c(f"\n  ❌  Trading bot error: {exc}\n", _RED, _BOLD))
        logger.error("TradingBotError: %s", exc, exc_info=True)
        return 1

    except Exception as exc:  # noqa: BLE001
        print(
            _c(
                "\n  ❌  An unexpected error occurred. "
                "Please check logs/trading_bot.log for details.\n",
                _RED,
                _BOLD,
            )
        )
        logger.critical(
            "Unexpected exception in CLI main: %s", exc, exc_info=True
        )
        return 1

    # ------------------------------------------------------------------
    # Display result
    # ------------------------------------------------------------------
    _print_order_result(result)
    print(
        _c(
            f"  🎉  Order submitted successfully! "
            f"Order ID: {result['order_id']}\n",
            _GREEN,
            _BOLD,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
