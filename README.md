# 🤖 Binance Futures Testnet — Trading Bot CLI

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

A **production-quality, interview-ready** command-line trading bot that places
MARKET and LIMIT orders on the **Binance Futures Testnet (USDT-M)**.  
Built with clean modular architecture, structured rotating logs, comprehensive
input validation, typed custom exceptions, and HMAC-SHA256 signed REST calls —
all following PEP 8 and SOLID principles.

---

## 📑 Table of Contents

1. [Project Overview](#project-overview)  
2. [Architecture](#architecture)  
3. [Prerequisites](#prerequisites)  
4. [Setup Instructions](#setup-instructions)  
   - [Clone & Virtual Environment](#1-clone--virtual-environment)  
   - [Install Dependencies](#2-install-dependencies)  
   - [Environment Variables](#3-environment-variables)  
   - [Generate Binance Testnet API Keys](#4-generate-binance-testnet-api-keys)  
5. [Usage](#usage)  
   - [MARKET Order](#market-order)  
   - [LIMIT Order](#limit-order)  
   - [Skip Confirmation](#skip-confirmation)  
   - [All CLI Flags](#all-cli-flags)  
6. [Expected Output](#expected-output)  
   - [Order Summary](#order-summary-pre-submission)  
   - [Order Result](#order-result-post-submission)  
7. [Logging](#logging)  
8. [Running Tests](#running-tests)  
9. [Project Structure](#project-structure)  
10. [Module Descriptions](#module-descriptions)  
11. [Error Handling](#error-handling)  
12. [Assumptions](#assumptions)  
13. [Future Improvements](#future-improvements)  

---

## Project Overview

This application provides a **simplified but production-grade** interface for
submitting futures orders against the Binance Testnet REST API
(`https://testnet.binancefuture.com`).

**Key capabilities:**

| Feature | Detail |
|---|---|
| Order types | `MARKET`, `LIMIT` |
| Order sides | `BUY`, `SELL` |
| Input validation | Symbol, side, type, quantity, price |
| Authentication | HMAC-SHA256 signed requests |
| Logging | Rotating file + coloured console |
| Error handling | Typed custom exception hierarchy |
| Configuration | `.env` / environment variables |
| Testing | pytest + `responses` HTTP mocking |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                          CLI  (cli.py)                           │
│  argparse → validation summary → confirm → call orders layer     │
└──────────────────────┬───────────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────────────┐
│                     Orders  (orders.py)                          │
│  validate_order_params() → BinanceClient → _parse_order_response │
└──────────┬──────────────────────┬────────────────────────────────┘
           │                      │
┌──────────▼──────────┐  ┌────────▼────────────────────────────────┐
│  Validators          │  │  BinanceClient  (client.py)             │
│  (validators.py)     │  │  HMAC signing, retry, error mapping     │
└──────────────────────┘  └─────────────────────────────────────────┘
           │                      │
┌──────────▼──────────────────────▼──────────────────────────────┐
│  Config (config.py)     Exceptions (exceptions.py)              │
│  Settings dataclass     Typed exception hierarchy               │
│  .env via dotenv                                                │
└─────────────────────────────────────────────────────────────────┘
           │
┌──────────▼──────────────────────────────────────────────────────┐
│  Logging Config (logging_config.py)                             │
│  RotatingFileHandler → logs/trading_bot.log                     │
│  StreamHandler → stdout (coloured)                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

- **Python 3.11+** (uses `dict | None` union syntax, `match` statement
  compatible)
- **pip** (comes with Python)
- A [Binance Futures Testnet](https://testnet.binancefuture.com/) account
- Internet access to reach `testnet.binancefuture.com`

---

## Setup Instructions

### 1. Clone & Virtual Environment

```bash
# Clone the repository
git clone https://github.com/<your-username>/binance-futures-trading-bot.git
cd binance-futures-trading-bot

# Create a virtual environment
python -m venv .venv

# Activate it
# macOS / Linux:
source .venv/bin/activate
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Windows CMD:
.venv\Scripts\activate.bat
```

### 2. Install Dependencies

```bash
# Install all runtime + dev dependencies
pip install -r requirements.txt

# Install the package in editable mode (registers the `trade` console script)
pip install -e .
```

### 3. Environment Variables

```bash
# Copy the example file
cp .env.example .env   # Windows: copy .env.example .env

# Edit .env with your real testnet API credentials
# (see next section for how to generate them)
```

Your `.env` file should look like:

```ini
BINANCE_API_KEY=your_actual_testnet_api_key
BINANCE_API_SECRET=your_actual_testnet_api_secret
BINANCE_BASE_URL=https://testnet.binancefuture.com
REQUEST_TIMEOUT=10
RECV_WINDOW=5000
LOG_LEVEL=DEBUG
```

> **⚠️ Security:** The `.gitignore` excludes `.env` from version control.
> **Never** commit real credentials.

### 4. Generate Binance Testnet API Keys

1. Visit [https://testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Click **"Log In with GitHub"** (GitHub OAuth required).
3. Navigate to **Account → API Key**.
4. Click **"Generate"** — copy both the API Key and Secret immediately
   (the secret is shown only once).
5. Paste them into your `.env` file.

> The Testnet resets periodically and provides pre-funded USDT balances for
> free trading practice.

---

## Usage

### MARKET Order

Place a MARKET BUY for `0.001 BTC` (BTCUSDT perpetual):

```bash
python -m trading_bot.cli \
    --symbol BTCUSDT \
    --side BUY \
    --type MARKET \
    --quantity 0.001
```

Or using the installed console script:

```bash
trade --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

### LIMIT Order

Place a LIMIT SELL for `0.05 ETH` at `$3,500`:

```bash
python -m trading_bot.cli \
    --symbol ETHUSDT \
    --side SELL \
    --type LIMIT \
    --quantity 0.05 \
    --price 3500.00
```

### Skip Confirmation

Add `--yes` (or `-y`) to bypass the interactive confirmation prompt
(useful for scripting / CI pipelines):

```bash
trade --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001 --yes
```

### All CLI Flags

```
usage: trade [-h] --symbol SYMBOL --side SIDE --type TYPE --quantity QTY
             [--price PRICE] [--yes] [--version]

options:
  -h, --help            Show this help message and exit
  --symbol SYMBOL       Trading pair symbol, e.g. BTCUSDT (case-insensitive)
  --side SIDE           Order side: BUY or SELL
  --type TYPE           Order type: MARKET or LIMIT
  --quantity QTY        Order quantity (positive number)
  --price PRICE         Limit price (required for LIMIT orders)
  --yes, -y             Skip confirmation prompt
  --version             Show program's version number and exit
```

---

## Expected Output

### Order Summary (pre-submission)

```
  ____  _
 | __ )(_)_ __   __ _ _ __   ___ ___  ____   ___  _
 ...
          Binance Futures Testnet — Trading CLI

  📋  ORDER SUMMARY
────────────────────────────────────────────────────────────
  Symbol:                        BTCUSDT
  Side:                          BUY
  Type:                          MARKET
  Quantity:                      0.001
  Price:                         N/A (MARKET)
────────────────────────────────────────────────────────────

  ⚠️  Submit this order? [yes/no]:
```

### Order Result (post-submission)

```
  ✅  ORDER RESULT
────────────────────────────────────────────────────────────
  Order ID:                      4611685020
  Status:                        FILLED
  Symbol:                        BTCUSDT
  Side:                          BUY
  Type:                          MARKET
  Original Qty:                  0.001
  Executed Qty:                  0.001
  Average Price:                 42185.3
  Limit Price:                   N/A (MARKET)
  Time-in-Force:                 GTC
  Timestamp (UTC):               2024-01-15T09:00:01 UTC
────────────────────────────────────────────────────────────

  🎉  Order submitted successfully! Order ID: 4611685020
```

**LIMIT order result (status NEW — resting in order book):**

```
  ✅  ORDER RESULT
────────────────────────────────────────────────────────────
  Order ID:                      4611688100
  Status:                        NEW
  Symbol:                        ETHUSDT
  Side:                          SELL
  Type:                          LIMIT
  Original Qty:                  0.05
  Executed Qty:                  0
  Average Price:                 N/A
  Limit Price:                   3500
  Time-in-Force:                 GTC
  Timestamp (UTC):               2024-01-15T10:30:01 UTC
────────────────────────────────────────────────────────────
```

### Validation Error Example

```
  ❌  Validation error: Price must be a positive number, got -500.0.
```

### Configuration Error Example

```
  ❌  Configuration error: Missing required environment variable(s):
      BINANCE_API_KEY, BINANCE_API_SECRET. Create a .env file from
      .env.example and populate it with your Binance Futures Testnet
      credentials.
```

---

## Logging

All log records are written to **`logs/trading_bot.log`** (created
automatically) using a `RotatingFileHandler` (5 MB per file, 5 backups).
A shorter summary is printed to stdout.

### Log Format

```
2024-01-15T09:00:01 | INFO     | trading_bot.client:client.py:195 | Order placed successfully — orderId=4611685020 status=FILLED
```

**Fields:**

| Field | Description |
|---|---|
| Timestamp | ISO-8601 local time |
| Level | `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL` |
| Logger | `trading_bot.<module>:<file>:<line>` |
| Message | Human-readable log message with key=value context |

### What Gets Logged

| Event | Level |
|---|---|
| Application start, config load | `INFO` |
| Validation steps (each field) | `DEBUG` |
| Validation failures | `WARNING` |
| API request parameters (no secrets) | `DEBUG` |
| Full API response body (truncated at 2 000 chars) | `DEBUG` |
| Successful order placement | `INFO` |
| API errors with Binance code + message | `ERROR` |
| Network / timeout errors | `ERROR` |
| Unexpected exceptions with full stack trace | `CRITICAL` |

> **Sample log files** are provided in `logs/` for reference:
> - `logs/sample_market_order.log` — successful MARKET BUY
> - `logs/sample_limit_order.log` — successful LIMIT SELL
> - `logs/sample_failed_order.log` — three failure scenarios

---

## Running Tests

```bash
# Run all tests with coverage
pytest tests/ -v --cov=trading_bot --cov-report=term-missing

# Run only validator tests
pytest tests/test_validators.py -v

# Run only client tests
pytest tests/test_client.py -v
```

Expected output:

```
tests/test_validators.py::TestValidateSymbol::test_valid_uppercase PASSED
tests/test_validators.py::TestValidateSymbol::test_valid_lowercase_normalised PASSED
...
tests/test_client.py::test_place_market_order_success PASSED
tests/test_client.py::test_rate_limit_raises PASSED
...
---------- coverage: 94% ----------
```

---

## Project Structure

```
binance-futures-trading-bot/
│
├── trading_bot/                 # Main package
│   ├── __init__.py              # Package metadata
│   ├── cli.py                   # argparse CLI entry-point
│   ├── client.py                # Binance REST client (HMAC signed)
│   ├── orders.py                # Order orchestration layer
│   ├── validators.py            # Input validation functions
│   ├── config.py                # Settings dataclass + .env loader
│   ├── exceptions.py            # Custom exception hierarchy
│   └── logging_config.py        # Dual-handler rotating logger
│
├── tests/                       # Pytest test suite
│   ├── __init__.py
│   ├── test_validators.py       # 30+ validator unit tests
│   └── test_client.py           # BinanceClient integration tests (mocked)
│
├── logs/                        # Auto-created at runtime
│   ├── sample_market_order.log  # Sample: successful MARKET order
│   ├── sample_limit_order.log   # Sample: successful LIMIT order
│   └── sample_failed_order.log  # Sample: failed order scenarios
│
├── .env.example                 # Credential template (safe to commit)
├── .env                         # Real credentials (git-ignored)
├── .gitignore                   # Python + IDE ignore rules
├── requirements.txt             # Runtime + dev dependencies
├── setup.py                     # Package config + console script
└── README.md                    # This file
```

---

## Module Descriptions

### `exceptions.py`
Defines a typed exception hierarchy rooted at `TradingBotError`.
Every exception carries an optional `context: dict` for structured logging.

```
TradingBotError
├── ValidationError
│   ├── InvalidSymbolError
│   ├── InvalidSideError
│   ├── InvalidOrderTypeError
│   ├── InvalidQuantityError
│   └── InvalidPriceError
├── ConfigurationError
├── BinanceAPIError
│   ├── AuthenticationError
│   ├── RateLimitError
│   └── OrderPlacementError
└── NetworkError
    └── TimeoutError
```

### `logging_config.py`
`setup_logging()` attaches two handlers to `trading_bot` logger:  
- **RotatingFileHandler** → `logs/trading_bot.log` (DEBUG level, 5 MB × 5 files)  
- **StreamHandler** → stdout (INFO level)

`get_logger(name)` returns `logging.getLogger(f"trading_bot.{name}")`.

### `config.py`
`load_settings()` reads all env vars via `python-dotenv`, validates mandatory
keys (`BINANCE_API_KEY`, `BINANCE_API_SECRET`), and returns a frozen
`Settings` dataclass. All other modules receive `Settings` by dependency
injection — no global state.

### `validators.py`
Pure functions, each raising a specific exception subclass on failure:

| Function | Validates |
|---|---|
| `validate_symbol` | 2–20 uppercase alphanumeric, normalises case |
| `validate_side` | `BUY` or `SELL` only |
| `validate_order_type` | `MARKET` or `LIMIT` only |
| `validate_quantity` | positive, finite, ≤ 1 000 000 |
| `validate_price` | required + positive for LIMIT; ignored for MARKET |
| `validate_order_params` | composite — calls all the above |

### `client.py`
`BinanceClient` wraps `requests.Session` with:
- `HTTPAdapter` retry strategy (3 retries, 500–504 back-off)
- HMAC-SHA256 request signing (`_sign`)
- Typed error mapping (`_handle_response`) for auth, rate-limit, order errors
- Context-manager support (`with BinanceClient(...) as c:`)

### `orders.py`
`place_order()` orchestrates: validate → open client → call API → parse
response. `_parse_order_response()` converts raw Binance JSON to a clean dict
with a human-readable ISO-8601 timestamp.

### `cli.py`
`main()`:
1. Prints ASCII banner
2. Parses args with `argparse`
3. Loads settings
4. Prints coloured order summary table
5. Prompts for confirmation (skippable with `--yes`)
6. Calls `orders.place_order()`
7. Prints coloured result table
8. Handles all exception types with user-friendly messages

---

## Error Handling

The application never crashes unexpectedly. Every exception type produces a
distinct, actionable message:

| Scenario | Exception | User Message |
|---|---|---|
| Missing `--price` for LIMIT | `InvalidPriceError` | "Price is required for LIMIT orders" |
| Negative quantity | `InvalidQuantityError` | "Quantity must be a positive number" |
| Invalid symbol format | `InvalidSymbolError` | "Symbol 'X' is invalid. Expected 2–20 alphanumeric…" |
| Missing `.env` credentials | `ConfigurationError` | "Missing required environment variable(s): BINANCE_API_KEY…" |
| Bad API key / secret | `AuthenticationError` | "Authentication failed. Verify your API key and secret." |
| Insufficient balance | `OrderPlacementError` | "Binance API error -2010: Account has insufficient balance…" |
| Rate limit hit | `RateLimitError` | "Rate limit exceeded (HTTP 429). Retry after: 60s." |
| No internet | `NetworkError` | "Connection error reaching testnet.binancefuture.com" |
| Request timeout | `TimeoutError` | "Request to /fapi/v1/order timed out after 10s." |
| Unexpected Python error | `Exception` | "An unexpected error occurred. Check logs/trading_bot.log" |

Full stack traces for all ERROR/CRITICAL events are written to the log file.

---

## Assumptions

1. **Testnet only** — the `BINANCE_BASE_URL` defaults to
   `https://testnet.binancefuture.com`. Switching to production requires only
   changing this environment variable (and real keys).
2. **One-way margin** — the bot submits orders in one-sided BOTH position mode
   (Binance Futures default). Hedge mode is not supported.
3. **GTC time-in-force** — all LIMIT orders use Good-Till-Cancelled. This is
   configurable via the `LIMIT_TIME_IN_FORCE` constant in `config.py`.
4. **Synchronous execution** — the application is intentionally single-threaded
   for simplicity. An async version using `aiohttp` is listed as a future
   improvement.
5. **Symbol validation is format-only** — the bot validates the symbol matches
   `^[A-Z0-9]{2,20}$` but does not call `exchangeInfo` to confirm the symbol
   is live. Binance will return a clear error if the symbol is unknown.
6. **Python 3.11+** required — the code uses `dict | None` union syntax
   (PEP 604) and `from __future__ import annotations`.

---

## Future Improvements

| Area | Improvement |
|---|---|
| **Async** | Rewrite `BinanceClient` with `aiohttp` / `httpx[async]` for concurrent order streams |
| **Order types** | Support `STOP_MARKET`, `STOP_LIMIT`, `TRAILING_STOP_MARKET` |
| **Symbol validation** | Pre-fetch `exchangeInfo` to validate symbol against live exchange data |
| **Position management** | Add `--close-position` flag and `/fapi/v1/positionRisk` integration |
| **WebSocket** | Stream live prices and order book via Binance WebSocket to auto-fill LIMIT prices |
| **Strategy layer** | Pluggable trading strategy interface (e.g. VWAP, momentum) |
| **Config file** | Support TOML / YAML config for multi-account setups |
| **Docker** | Containerise with a `Dockerfile` + `docker-compose.yml` |
| **CI/CD** | GitHub Actions workflow for lint + test on every push |
| **Retry budget** | Exponential back-off with jitter for rate-limit `429` responses |
| **Paper-trade mode** | Local order simulation without any API calls |

---

## License

MIT — see [LICENSE](LICENSE) for details.
"# Finance_bot" 
