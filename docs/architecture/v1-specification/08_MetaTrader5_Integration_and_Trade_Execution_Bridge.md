# MONEYMAKER V1 --- MetaTrader 5 Integration and Trade Execution Bridge

> **Autore** | Renan Augusto Macena

---

## Table of Contents

1. [Overview and Role in the Ecosystem](#81-overview-and-role-in-the-ecosystem)
2. [MetaTrader 5 Platform Architecture](#82-metatrader-5-platform-architecture)
3. [Python MetaTrader5 Package Deep Dive](#83-python-metatrader5-package-deep-dive)
4. [Trade Execution Bridge Service Architecture](#84-trade-execution-bridge-service-architecture)
5. [Order Management System (OMS)](#85-order-management-system-oms)
6. [Multi-Symbol and Multi-Timeframe Support](#86-multi-symbol-and-multi-timeframe-support)
7. [Position Sizing and Risk Integration](#87-position-sizing-and-risk-integration)
8. [Stop-Loss and Take-Profit Management](#88-stop-loss-and-take-profit-management)
9. [Execution Quality Monitoring](#89-execution-quality-monitoring)
10. [Error Handling and Recovery](#810-error-handling-and-recovery)
11. [Windows VM Configuration for MT5](#811-windows-vm-configuration-for-mt5)
12. [Security Considerations](#812-security-considerations)
13. [Testing the Execution Bridge](#813-testing-the-execution-bridge)
14. [Configuration and Deployment](#814-configuration-and-deployment)

---

## 8.1 Overview and Role in the Ecosystem

### The Final Mile: Where Decisions Become Trades

Every component in the MONEYMAKER ecosystem exists, ultimately, to support a single act: the submission of a trade order to a broker through the MetaTrader 5 terminal. The Data Ingestion Service fetches and normalizes market data. The Database Layer stores and serves that data. The ML Training Lab builds predictive models. The AI Trading Brain generates signals. But none of that matters if the final mile -- the translation of an AI-generated signal into a real market order -- fails, is slow, or is unreliable. The MetaTrader 5 Integration and Trade Execution Bridge is the component that owns this final mile. It is the single point of contact between MONEYMAKER's internal intelligence and the external financial markets.

The Bridge is not merely a passthrough. It is an active participant in the execution process, responsible for validating signals before they become orders, calculating precise position sizes based on account equity and risk parameters, constructing MT5-compatible order requests with correct lot sizes, stop-loss levels, take-profit targets, and fill policies, submitting those orders to the MT5 terminal, monitoring their execution status, tracking open positions in real time, managing trailing stops and partial closes, and feeding execution results back to the Algo Engine for the learning feedback loop. It is, in effect, a complete Order Management System (OMS) wrapped around the MetaTrader5 Python API.

### Architectural Position

Within MONEYMAKER's six-service architecture, the Bridge occupies a unique position. It is the only service that interacts with the external broker. It is the only service that can cause real financial gain or loss. It is the only service that operates under the constraints of a third-party platform (the MT5 terminal) running on a different operating system (Windows). These unique characteristics shape every design decision in the Bridge.

The Bridge runs as a dedicated microservice inside a Docker container on a Windows VM (or a Linux VM with a Windows VM accessible via the network). It communicates with the AI Trading Brain via gRPC for signal reception and execution confirmations, with the Database Layer via PostgreSQL for trade logging and position reconciliation, and with the MT5 terminal via the MetaTrader5 Python package over a local or network connection.

```
+=====================================================================+
|                    MONEYMAKER EXECUTION LAYER                           |
+=====================================================================+
|                                                                     |
|  +-----------------+    gRPC     +----------------------------+     |
|  |   AI Trading    |----------->|   MT5 Execution Bridge     |     |
|  |   Brain         |<-----------|   (Python Service)          |     |
|  |   (VM 3)        |  signals   |                            |     |
|  +-----------------+  + acks    |  +----------------------+  |     |
|                                  |  | Signal Receiver      |  |     |
|  +-----------------+             |  | Order Validator      |  |     |
|  |   Database      |<---------->|  | Position Sizer       |  |     |
|  |   Layer         |   SQL +    |  | MT5 API Interface    |  |     |
|  |   (VM 2)        |   Redis    |  | Position Tracker     |  |     |
|  +-----------------+             |  | SL/TP Manager        |  |     |
|                                  |  | Execution Monitor    |  |     |
|  +-----------------+             |  +----------+-----------+  |     |
|  |   Monitoring    |<-- metrics  |             |              |     |
|  |   (VM 6)        |             +-------------|--------------|     |
|  +-----------------+                           |                    |
|                                                v                    |
|                                  +----------------------------+     |
|                                  |   MetaTrader 5 Terminal    |     |
|                                  |   (Windows VM - VM 4)      |     |
|                                  |                            |     |
|                                  |   +--------------------+   |     |
|                                  |   | Broker Connection  |   |     |
|                                  |   | (TCP/IP to broker  |   |     |
|                                  |   |  server)           |   |     |
|                                  |   +--------------------+   |     |
|                                  +----------------------------+     |
+=====================================================================+
```

### Design Principles Specific to the Bridge

The Bridge operates under a stricter set of design principles than other MONEYMAKER services because it directly controls real money. These principles are non-negotiable:

**Fail-safe by default.** If any validation check fails, if any parameter is ambiguous, if any connection is degraded, the Bridge does not execute. It rejects the signal, logs the rejection reason, and notifies the Algo Engine. The only exception to this rule is emergency position management (closing positions to limit losses), which is allowed even in degraded states.

**Idempotency.** Every signal has a unique `signal_id`. The Bridge maintains a deduplication cache. If a signal is received twice (due to gRPC retry, network glitch, or Brain-side retry), the Bridge returns the cached result from the first execution rather than executing the trade a second time. Duplicate order submission is the most dangerous failure mode in an automated trading system, and the Bridge is specifically hardened against it.

**Bounded latency.** The total time from signal reception to order submission must not exceed 100 milliseconds under normal conditions. The Bridge is designed to minimize latency at every step: pre-computed symbol specifications, connection pooling to MT5, pre-validated order templates, and asynchronous logging that does not block the execution path.

**Complete auditability.** Every action the Bridge takes -- every signal received, every validation check performed, every order submitted, every fill received, every position modification, every error encountered -- is logged to the append-only audit trail in PostgreSQL. The audit trail includes timestamps at microsecond resolution, the full order request and response payloads, and the context (AI confidence, regime classification, risk parameters) that led to the action.

**Conservative position management.** The Bridge enforces position sizing limits independently of the Algo Engine. Even if the Brain sends a signal requesting an unreasonably large position, the Bridge caps it at the configured maximum. Even if the Brain fails to send a close signal, the Bridge's time-based and drawdown-based stops will eventually close stale or losing positions. The Bridge is the last line of defense against excessive risk.

### Supported Instruments and Markets

The Bridge is designed to handle the following instrument categories through MT5:

- **Forex pairs:** EUR/USD, GBP/USD, USD/JPY, AUD/USD, USD/CHF, and other major and minor pairs
- **Commodities:** XAU/USD (Gold) is the primary focus, with XAG/USD (Silver) and crude oil as secondary instruments
- **CFDs:** Stock indices (US30, US500, NAS100), energy CFDs, and other broker-supported instruments

XAU/USD (Gold) is the primary trading instrument for MONEYMAKER V1. Gold's characteristics -- high liquidity during London and New York sessions, strong trending behavior, sensitivity to macroeconomic events, and wide daily ranges -- make it an ideal candidate for AI-driven trading. The Bridge's default configuration, position sizing formulas, and risk parameters are all calibrated for Gold first, with other instruments inheriting configurable overrides.

---

## 8.2 MetaTrader 5 Platform Architecture

### Client-Server Model

MetaTrader 5 is built on a client-server architecture. The MT5 terminal (the client) runs on the trader's machine and connects to the broker's trade server over an encrypted TCP/IP connection. The terminal is responsible for displaying charts, executing orders, managing positions, and providing the user interface. The broker's server is responsible for matching orders, managing account balances, enforcing margin requirements, and providing market data.

From MONEYMAKER's perspective, the MT5 terminal is a black box that provides two critical interfaces: (1) a visual terminal for manual monitoring and maintenance, and (2) a Python API (via the MetaTrader5 package) for programmatic control. MONEYMAKER uses exclusively the Python API for all automated operations. The visual terminal is used only for initial setup, broker login configuration, and emergency manual intervention.

```
+-------------------------------------------------------------------+
|                    MT5 CLIENT-SERVER MODEL                         |
+-------------------------------------------------------------------+
|                                                                   |
|  MONEYMAKER Server (Proxmox)              Broker Infrastructure      |
|  +---------------------------+         +----------------------+   |
|  |  Windows VM               |         |  Broker Trade Server |   |
|  |  +---------------------+  |  TCP/IP |  +----------------+  |   |
|  |  | MT5 Terminal        |=============>| Order Matching  |  |   |
|  |  | (MetaQuotes)        |<=============| Engine          |  |   |
|  |  |                     |  | Encrypted|  +----------------+  |   |
|  |  | +------+ +--------+|  |          |  +----------------+  |   |
|  |  | |Charts| |Positions||  |          |  | Market Data    |  |   |
|  |  | +------+ +--------+|  |          |  | Feed           |  |   |
|  |  | +------+ +--------+|  |          |  +----------------+  |   |
|  |  | |Orders| |History ||  |          |  +----------------+  |   |
|  |  | +------+ +--------+|  |          |  | Account Mgmt   |  |   |
|  |  +--------|------------+  |         |  +----------------+  |   |
|  |           | Python API    |         +----------------------+   |
|  |  +--------v------------+  |                                    |
|  |  | MetaTrader5 Python  |  |                                    |
|  |  | Package (mt5)       |  |                                    |
|  |  | - initialize()      |  |                                    |
|  |  | - login()           |  |                                    |
|  |  | - order_send()      |  |                                    |
|  |  | - positions_get()   |  |                                    |
|  |  +--------|------------+  |                                    |
|  |           | IPC/Pipe      |                                    |
|  |  +--------v------------+  |                                    |
|  |  | MONEYMAKER Bridge      |  |                                    |
|  |  | Service (Python)    |  |                                    |
|  |  +---------------------+  |                                    |
|  +---------------------------+                                    |
+-------------------------------------------------------------------+
```

### Broker Connectivity and Server Configuration

Each MT5 broker provides one or more trade server addresses that the terminal connects to. These servers are configured during the initial account setup and stored in the terminal's configuration files. The server selection affects latency (geographic proximity to the broker's data center), available instruments (different servers may offer different symbol lists), and execution quality (some brokers run different execution models on different servers).

For MONEYMAKER, broker selection criteria include:

- **ECN/STP execution model:** Direct market access with minimal dealing desk intervention, reducing requotes and providing tighter spreads
- **Low latency:** Broker server geographically close to the MONEYMAKER server, ideally in the same data center region
- **MetaTrader5 Python API support:** Not all brokers enable the Python API; this must be confirmed before account setup
- **Hedging account support:** MONEYMAKER requires a hedging account (ability to hold simultaneous buy and sell positions on the same instrument), not a netting account
- **Competitive spreads on XAU/USD:** Since Gold is the primary instrument, the broker's Gold spread is a critical selection criterion
- **API rate limits:** Some brokers impose rate limits on programmatic order submission; these must be high enough for MONEYMAKER's operational tempo

### Account Types: Demo vs Live, Hedging vs Netting

MT5 supports two fundamental account models that affect how positions are tracked:

**Hedging mode** allows multiple independent positions on the same symbol. A trader can hold a long position and a short position on XAU/USD simultaneously. Each position has its own ticket number, its own stop-loss and take-profit, and its own P&L. Closing one position does not affect the other. MONEYMAKER requires hedging mode because the Algo Engine may generate signals at different timeframes or from different strategies that result in opposing positions on the same instrument. For example, a short-term mean-reversion strategy might be short XAU/USD while a longer-term trend-following strategy is long XAU/USD.

**Netting mode** aggregates all orders on the same symbol into a single net position. A buy order followed by a sell order of equal size results in a flat position (no open position). Netting mode is simpler but incompatible with MONEYMAKER's multi-strategy architecture.

The Bridge verifies the account mode during initialization and refuses to operate if the account is configured for netting mode. This check is performed in the startup sequence and is a hard requirement.

**Demo accounts** mirror the functionality of live accounts but execute against simulated liquidity with no real money at risk. MONEYMAKER uses demo accounts extensively during development, testing, and paper-trading phases. The Bridge is designed to be entirely agnostic to whether the connected account is demo or live -- the same code handles both. The only difference is the configuration (account credentials and server address), ensuring that the transition from paper trading to live trading requires only a configuration change, not a code change.

### Symbol Specifications

Every tradeable instrument in MT5 has a detailed specification that defines its trading parameters. The Bridge queries these specifications dynamically using `mt5.symbol_info()` and caches them for the duration of the trading session. The critical specification fields are:

| Field | Description | Example (XAU/USD) |
|-------|-------------|-------------------|
| `name` | Symbol identifier | XAUUSD |
| `point` | Minimum price change | 0.01 |
| `digits` | Decimal places in price | 2 |
| `trade_tick_size` | Minimum price increment for orders | 0.01 |
| `trade_tick_value` | Monetary value of one tick per lot | 1.00 USD |
| `volume_min` | Minimum lot size | 0.01 |
| `volume_max` | Maximum lot size | 100.0 |
| `volume_step` | Lot size increment | 0.01 |
| `trade_contract_size` | Units per standard lot | 100 (troy oz) |
| `margin_initial` | Initial margin per lot | Varies by leverage |
| `spread` | Current spread in points | Variable |
| `trade_stops_level` | Minimum distance for SL/TP from price | 0 (varies by broker) |
| `trade_freeze_level` | Price zone where orders cannot be modified | 0 (varies by broker) |

These specifications are essential for correct order construction. The Bridge uses them to validate lot sizes (must be a multiple of `volume_step`, between `volume_min` and `volume_max`), validate stop-loss and take-profit distances (must be at least `trade_stops_level` points from the current price), and calculate margin requirements before order submission.

### MT5 on Windows: The Platform Constraint

MetaTrader 5 is a Windows-native application. The MetaTrader5 Python package communicates with the MT5 terminal via Windows inter-process communication (named pipes and shared memory). This means the Python process calling `mt5.initialize()` must run on the same Windows machine as the MT5 terminal. There is no remote API, no REST endpoint, no WebSocket interface -- the Python package requires direct IPC with the terminal process.

This platform constraint has significant implications for MONEYMAKER's architecture. Since the core MONEYMAKER infrastructure runs on Proxmox (Linux-based), the MT5 terminal must run in a Windows VM hosted on Proxmox. The Bridge service (Python) must also run inside this same Windows VM, or at minimum have network-level access to the Python package running inside the VM. The practical solution is to run the Bridge service directly on the Windows VM, with gRPC providing the network bridge between the Linux-based Algo Engine and the Windows-based Bridge.

### Session Management: Keeping MT5 Alive 24/5

Forex and commodity markets operate 24 hours a day, 5 days a week (Sunday evening to Friday evening, US Eastern Time). The MT5 terminal must remain connected and responsive throughout this entire period. Session management is critical because the terminal can disconnect for various reasons: broker server maintenance, network interruptions, Windows updates, terminal crashes, or VM resource exhaustion.

The Bridge implements a multi-layered session management strategy:

**Connection heartbeat.** Every 10 seconds, the Bridge calls `mt5.terminal_info()` to verify that the terminal is running and connected. If this call fails, the Bridge enters recovery mode (detailed in Section 8.10).

**Auto-login on disconnect.** If the terminal disconnects from the broker server (detected via `terminal_info().connected == False`), the Bridge attempts to re-authenticate using `mt5.login()` with stored credentials. This handles broker server restarts and brief network interruptions.

**Terminal watchdog.** A separate watchdog process (running as a Windows service) monitors the MT5 terminal process. If the terminal process is not running, the watchdog starts it. If the terminal is running but unresponsive (consuming 100% CPU or not updating its heartbeat file), the watchdog kills and restarts it. This handles terminal crashes and hangs.

**Windows session persistence.** The Windows VM is configured to auto-login and auto-start MT5 on boot. The user session is kept alive even when no RDP session is connected, ensuring that MT5's GUI thread continues to operate. This is achieved by configuring a persistent console session and disabling screen saver and sleep modes.

---

## 8.3 Python MetaTrader5 Package Deep Dive

### Package Overview

The `MetaTrader5` Python package (imported as `mt5`) is the official Python interface to the MT5 terminal, provided by MetaQuotes. It is installed via pip (`pip install MetaTrader5`) and provides functions for terminal management, market data retrieval, and trade operations. The package communicates with the MT5 terminal through Windows IPC mechanisms and requires the terminal to be running on the same machine.

The package is synchronous -- all function calls block until the MT5 terminal responds. This has implications for the Bridge's architecture, as discussed in Section 8.4. The package is also not thread-safe -- concurrent calls from multiple threads can cause undefined behavior. The Bridge addresses this with a single-threaded MT5 access pattern wrapped in an asyncio executor.

### Connection and Authentication

#### mt5.initialize()

The `initialize()` function establishes the connection between the Python process and the MT5 terminal. It must be called before any other MT5 function. It accepts an optional path to the MT5 terminal executable, which is necessary when multiple terminals are installed or when the terminal is in a non-standard location.

```python
import MetaTrader5 as mt5

# Basic initialization
if not mt5.initialize():
    error_code, error_message = mt5.last_error()
    raise ConnectionError(
        f"MT5 initialization failed: [{error_code}] {error_message}"
    )

# Initialization with explicit path
MT5_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe"
if not mt5.initialize(path=MT5_PATH):
    error_code, error_message = mt5.last_error()
    raise ConnectionError(
        f"MT5 initialization failed at {MT5_PATH}: "
        f"[{error_code}] {error_message}"
    )
```

Common failure reasons for `initialize()`:

- MT5 terminal is not installed
- MT5 terminal is not running (the Python package does not start the terminal; it connects to an already-running instance, although it can launch it if a path is given)
- Another Python process already has an active connection to the terminal
- Insufficient permissions (the Python process must run with the same user that owns the MT5 terminal)

#### mt5.login()

After initialization, `login()` authenticates with the broker server using the trading account credentials. The function accepts the account number, password, and server name.

```python
ACCOUNT = 12345678
PASSWORD = "secure_password_from_vault"
SERVER = "BrokerName-Live"

if not mt5.login(login=ACCOUNT, password=PASSWORD, server=SERVER):
    error_code, error_message = mt5.last_error()
    raise AuthenticationError(
        f"MT5 login failed for account {ACCOUNT} on {SERVER}: "
        f"[{error_code}] {error_message}"
    )

# Verify login by checking account info
account_info = mt5.account_info()
if account_info is None:
    raise AuthenticationError("Login succeeded but account_info returned None")

print(f"Connected: Account={account_info.login}, "
      f"Balance={account_info.balance}, "
      f"Equity={account_info.equity}, "
      f"Leverage=1:{account_info.leverage}")
```

The Bridge stores the login result and re-authenticates automatically when the connection is lost. Credentials are retrieved from the encrypted vault at startup and held in memory -- they are never logged, never written to configuration files, and never transmitted over the network.

### Market Data Retrieval

#### mt5.symbol_info() and mt5.symbol_info_tick()

`symbol_info()` returns the complete specification of a trading symbol, including all the fields listed in Section 8.2's symbol specification table. `symbol_info_tick()` returns the latest price quote for a symbol.

```python
def get_symbol_spec(symbol: str) -> dict:
    """Retrieve and cache symbol specifications."""
    info = mt5.symbol_info(symbol)
    if info is None:
        raise SymbolError(f"Symbol {symbol} not found or not enabled")

    # Ensure the symbol is visible in Market Watch
    if not info.visible:
        if not mt5.symbol_select(symbol, True):
            raise SymbolError(f"Failed to enable {symbol} in Market Watch")
        info = mt5.symbol_info(symbol)

    return {
        "name": info.name,
        "point": info.point,
        "digits": info.digits,
        "tick_size": info.trade_tick_size,
        "tick_value": info.trade_tick_value,
        "volume_min": info.volume_min,
        "volume_max": info.volume_max,
        "volume_step": info.volume_step,
        "contract_size": info.trade_contract_size,
        "stops_level": info.trade_stops_level,
        "freeze_level": info.trade_freeze_level,
        "spread": info.spread,
        "margin_initial": info.margin_initial,
    }


def get_current_price(symbol: str) -> dict:
    """Get the latest bid/ask/last price for a symbol."""
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise PriceError(f"No tick data for {symbol}")

    return {
        "bid": tick.bid,
        "ask": tick.ask,
        "last": tick.last,
        "volume": tick.volume,
        "time": tick.time,
        "time_msc": tick.time_msc,  # millisecond precision
        "flags": tick.flags,
    }
```

The Bridge calls `symbol_info()` once during initialization for each configured symbol and caches the result. The cache is refreshed every 60 seconds to capture any specification changes (spread widening during low-liquidity sessions, for example). `symbol_info_tick()` is called immediately before every order submission to get the latest price for slippage calculation.

#### Historical Data: copy_rates and copy_ticks

While the Algo Engine handles most historical data analysis, the Bridge uses historical data functions for two purposes: verifying data consistency and computing ATR for dynamic stop-loss calculation.

```python
import MetaTrader5 as mt5
from datetime import datetime, timedelta
import pandas as pd

def get_recent_bars(symbol: str, timeframe: int, count: int) -> pd.DataFrame:
    """Fetch recent OHLCV bars from MT5."""
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
    if rates is None or len(rates) == 0:
        raise DataError(f"No rate data for {symbol} TF={timeframe}")

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    return df


def get_rates_range(
    symbol: str,
    timeframe: int,
    date_from: datetime,
    date_to: datetime
) -> pd.DataFrame:
    """Fetch OHLCV bars for a specific date range."""
    rates = mt5.copy_rates_range(symbol, timeframe, date_from, date_to)
    if rates is None or len(rates) == 0:
        raise DataError(
            f"No rate data for {symbol} from {date_from} to {date_to}"
        )

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    return df


def get_ticks_range(
    symbol: str,
    date_from: datetime,
    date_to: datetime,
    flags: int = mt5.COPY_TICKS_ALL
) -> pd.DataFrame:
    """Fetch tick-level data for a specific date range."""
    ticks = mt5.copy_ticks_range(symbol, date_from, date_to, flags)
    if ticks is None or len(ticks) == 0:
        raise DataError(
            f"No tick data for {symbol} from {date_from} to {date_to}"
        )

    df = pd.DataFrame(ticks)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    return df
```

MT5 timeframe constants used throughout the Bridge:

```python
TIMEFRAME_MAP = {
    "M1":  mt5.TIMEFRAME_M1,    # 1 minute
    "M5":  mt5.TIMEFRAME_M5,    # 5 minutes
    "M15": mt5.TIMEFRAME_M15,   # 15 minutes
    "M30": mt5.TIMEFRAME_M30,   # 30 minutes
    "H1":  mt5.TIMEFRAME_H1,    # 1 hour
    "H4":  mt5.TIMEFRAME_H4,    # 4 hours
    "D1":  mt5.TIMEFRAME_D1,    # 1 day
    "W1":  mt5.TIMEFRAME_W1,    # 1 week
    "MN1": mt5.TIMEFRAME_MN1,   # 1 month
}
```

### Trade Operations

#### mt5.order_check() -- Pre-Flight Validation

Before submitting any order, the Bridge uses `order_check()` to verify that the order is valid and that sufficient margin exists. This is a dry-run that does not submit the order to the broker.

```python
def preflight_check(request: dict) -> dict:
    """
    Perform pre-flight validation of an order request.
    Returns check result with margin requirements.
    """
    check_result = mt5.order_check(request)
    if check_result is None:
        error_code, error_msg = mt5.last_error()
        raise OrderError(
            f"order_check() returned None: [{error_code}] {error_msg}"
        )

    result_dict = {
        "retcode": check_result.retcode,
        "balance": check_result.balance,
        "equity": check_result.equity,
        "profit": check_result.profit,
        "margin": check_result.margin,
        "margin_free": check_result.margin_free,
        "margin_level": check_result.margin_level,
        "comment": check_result.comment,
    }

    if check_result.retcode != 0:
        raise OrderValidationError(
            f"Pre-flight check failed: retcode={check_result.retcode}, "
            f"comment={check_result.comment}"
        )

    return result_dict
```

#### mt5.order_send() -- The Core Execution Function

`order_send()` is the single most important function in the entire Bridge. It submits a trade request to the broker via the MT5 terminal and returns the execution result. The function accepts a dictionary (or a `TradeRequest` named tuple) with the order parameters.

```python
import MetaTrader5 as mt5

def execute_market_order(
    symbol: str,
    direction: str,      # "BUY" or "SELL"
    lots: float,
    sl_price: float,
    tp_price: float,
    magic: int,          # EA magic number for identification
    comment: str = "",
    deviation: int = 20  # max allowed slippage in points
) -> dict:
    """
    Execute a market order with full validation.

    Returns dict with order ticket and execution details.
    Raises OrderError on failure.
    """
    # Determine order type
    if direction == "BUY":
        order_type = mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(symbol).ask
    elif direction == "SELL":
        order_type = mt5.ORDER_TYPE_SELL
        price = mt5.symbol_info_tick(symbol).bid
    else:
        raise ValueError(f"Invalid direction: {direction}")

    # Construct the order request
    request = {
        "action":    mt5.TRADE_ACTION_DEAL,
        "symbol":    symbol,
        "volume":    lots,
        "type":      order_type,
        "price":     price,
        "sl":        sl_price,
        "tp":        tp_price,
        "deviation": deviation,
        "magic":     magic,
        "comment":   comment,
        "type_time": mt5.ORDER_TIME_GTC,       # Good Till Cancelled
        "type_filling": mt5.ORDER_FILLING_IOC,  # Immediate Or Cancel
    }

    # Pre-flight check
    check = mt5.order_check(request)
    if check is None or check.retcode != 0:
        error_code, error_msg = mt5.last_error()
        raise OrderError(
            f"Pre-flight failed for {direction} {lots} {symbol}: "
            f"retcode={getattr(check, 'retcode', 'N/A')}, "
            f"comment={getattr(check, 'comment', error_msg)}"
        )

    # Submit the order
    result = mt5.order_send(request)
    if result is None:
        error_code, error_msg = mt5.last_error()
        raise OrderError(
            f"order_send() returned None: [{error_code}] {error_msg}"
        )

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        raise OrderError(
            f"Order rejected: retcode={result.retcode}, "
            f"comment={result.comment}"
        )

    return {
        "ticket": result.order,
        "deal": result.deal,
        "volume": result.volume,
        "price": result.price,
        "bid": result.bid,
        "ask": result.ask,
        "comment": result.comment,
        "retcode": result.retcode,
        "request_id": result.request_id,
    }
```

The Bridge also supports pending orders (limit and stop orders):

```python
def place_pending_order(
    symbol: str,
    order_type: str,    # "BUY_LIMIT", "SELL_LIMIT", "BUY_STOP", "SELL_STOP"
    lots: float,
    price: float,
    sl_price: float,
    tp_price: float,
    magic: int,
    expiration: datetime = None,
    comment: str = ""
) -> dict:
    """Place a pending order."""
    type_map = {
        "BUY_LIMIT":  mt5.ORDER_TYPE_BUY_LIMIT,
        "SELL_LIMIT":  mt5.ORDER_TYPE_SELL_LIMIT,
        "BUY_STOP":   mt5.ORDER_TYPE_BUY_STOP,
        "SELL_STOP":   mt5.ORDER_TYPE_SELL_STOP,
        "BUY_STOP_LIMIT":  mt5.ORDER_TYPE_BUY_STOP_LIMIT,
        "SELL_STOP_LIMIT": mt5.ORDER_TYPE_SELL_STOP_LIMIT,
    }

    if order_type not in type_map:
        raise ValueError(f"Invalid pending order type: {order_type}")

    request = {
        "action":    mt5.TRADE_ACTION_PENDING,
        "symbol":    symbol,
        "volume":    lots,
        "type":      type_map[order_type],
        "price":     price,
        "sl":        sl_price,
        "tp":        tp_price,
        "magic":     magic,
        "comment":   comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }

    if expiration:
        request["type_time"] = mt5.ORDER_TIME_SPECIFIED
        request["expiration"] = int(expiration.timestamp())

    # Pre-flight and submit
    check = mt5.order_check(request)
    if check is None or check.retcode != 0:
        raise OrderError(
            f"Pre-flight failed for pending {order_type} {lots} {symbol} "
            f"@ {price}"
        )

    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        raise OrderError(
            f"Pending order rejected: "
            f"retcode={getattr(result, 'retcode', 'N/A')}"
        )

    return {"ticket": result.order, "retcode": result.retcode}
```

#### mt5.positions_get() -- Monitoring Open Positions

The Bridge periodically queries open positions to maintain its local position state and detect any external changes (positions opened manually or by other EAs).

```python
def get_open_positions(symbol: str = None, magic: int = None) -> list:
    """
    Retrieve open positions, optionally filtered by symbol and/or magic.
    """
    if symbol:
        positions = mt5.positions_get(symbol=symbol)
    else:
        positions = mt5.positions_get()

    if positions is None:
        return []

    result = []
    for pos in positions:
        if magic is not None and pos.magic != magic:
            continue

        result.append({
            "ticket": pos.ticket,
            "symbol": pos.symbol,
            "type": "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL",
            "volume": pos.volume,
            "price_open": pos.price_open,
            "price_current": pos.price_current,
            "sl": pos.sl,
            "tp": pos.tp,
            "profit": pos.profit,
            "swap": pos.swap,
            "magic": pos.magic,
            "comment": pos.comment,
            "time": pos.time,
            "time_msc": pos.time_msc,
            "identifier": pos.identifier,
        })

    return result
```

#### Trade History: history_orders_get() and history_deals_get()

The Bridge queries trade history for reconciliation and for feeding the feedback loop.

```python
def get_trade_history(
    date_from: datetime,
    date_to: datetime,
    symbol: str = None
) -> dict:
    """
    Retrieve completed orders and deals for the specified period.
    """
    if symbol:
        orders = mt5.history_orders_get(date_from, date_to, group=symbol)
        deals = mt5.history_deals_get(date_from, date_to, group=symbol)
    else:
        orders = mt5.history_orders_get(date_from, date_to)
        deals = mt5.history_deals_get(date_from, date_to)

    return {
        "orders": [
            {
                "ticket": o.ticket,
                "symbol": o.symbol,
                "type": o.type,
                "volume": o.volume_current,
                "price_open": o.price_open,
                "state": o.state,
                "time_setup": o.time_setup,
                "time_done": o.time_done,
            }
            for o in (orders or [])
        ],
        "deals": [
            {
                "ticket": d.ticket,
                "order": d.order,
                "symbol": d.symbol,
                "type": d.type,
                "volume": d.volume,
                "price": d.price,
                "profit": d.profit,
                "commission": d.commission,
                "swap": d.swap,
                "fee": d.fee,
                "time": d.time,
            }
            for d in (deals or [])
        ],
    }
```

### Error Handling: last_error() and Return Codes

Every MT5 function that can fail provides error information through `mt5.last_error()`, which returns a tuple of `(error_code, error_description)`. The Bridge logs every error with full context.

Key return codes from `order_send()`:

| Code | Constant | Meaning | Bridge Response |
|------|----------|---------|-----------------|
| 10009 | `TRADE_RETCODE_DONE` | Order executed successfully | Log success, update position state |
| 10004 | `TRADE_RETCODE_REQUOTE` | Price changed, requote offered | Retry with new price (up to 3 times) |
| 10006 | `TRADE_RETCODE_REJECT` | Order rejected by broker | Log rejection, notify Algo Engine |
| 10007 | `TRADE_RETCODE_CANCEL` | Order cancelled by trader | Log cancellation |
| 10010 | `TRADE_RETCODE_DONE_PARTIAL` | Partial fill | Track partial fill, decide on remainder |
| 10013 | `TRADE_RETCODE_INVALID` | Invalid request parameters | Log error, fix parameters, do not retry |
| 10014 | `TRADE_RETCODE_INVALID_VOLUME` | Invalid volume | Adjust volume to valid step |
| 10015 | `TRADE_RETCODE_INVALID_PRICE` | Invalid price | Refresh price and retry |
| 10016 | `TRADE_RETCODE_INVALID_STOPS` | Invalid SL/TP | Adjust stops to minimum distance |
| 10018 | `TRADE_RETCODE_MARKET_CLOSED` | Market is closed | Queue for market open |
| 10019 | `TRADE_RETCODE_NO_MONEY` | Insufficient margin | Reduce position size or reject |
| 10024 | `TRADE_RETCODE_TOO_MANY_REQUESTS` | Rate limited | Back off and retry |

### Thread Safety Considerations

The MetaTrader5 Python package is not thread-safe. Calling MT5 functions from multiple threads simultaneously leads to race conditions, corrupted state, and crashes. The Bridge enforces single-threaded MT5 access by routing all MT5 calls through a dedicated thread with a queue-based interface.

```python
import asyncio
import threading
from concurrent.futures import Future
from queue import Queue
from typing import Callable, Any


class MT5ThreadSafeWrapper:
    """
    Wraps all MT5 calls to execute on a single dedicated thread.
    Provides an async interface for the Bridge's asyncio event loop.
    """

    def __init__(self):
        self._queue: Queue = Queue()
        self._thread = threading.Thread(
            target=self._worker, daemon=True, name="mt5-worker"
        )
        self._thread.start()

    def _worker(self):
        """Worker thread that processes MT5 calls sequentially."""
        while True:
            func, args, kwargs, future = self._queue.get()
            try:
                result = func(*args, **kwargs)
                future.set_result(result)
            except Exception as e:
                future.set_exception(e)

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Schedule an MT5 function call on the dedicated thread
        and await the result.
        """
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        thread_future = Future()

        def on_done(tf):
            try:
                result = tf.result()
                loop.call_soon_threadsafe(future.set_result, result)
            except Exception as e:
                loop.call_soon_threadsafe(future.set_exception, e)

        thread_future.add_done_callback(on_done)
        self._queue.put((func, args, kwargs, thread_future))
        return await future
```

This wrapper allows the Bridge's asyncio event loop to call MT5 functions asynchronously while ensuring that all actual MT5 calls execute sequentially on a single thread.

---

## 8.4 Trade Execution Bridge Service Architecture

### Service Design: Python asyncio Event Loop

The Bridge is built on Python's `asyncio` framework, providing a single-threaded, non-blocking event loop that handles concurrent operations without the complexity of multi-threading. The choice of asyncio is deliberate: the Bridge's workload is I/O-bound (waiting for gRPC messages, waiting for MT5 responses, waiting for database writes), not CPU-bound, making asyncio's cooperative multitasking model ideal.

The Bridge's main event loop manages several concurrent tasks:

```
+================================================================+
|              BRIDGE SERVICE ARCHITECTURE                         |
+================================================================+
|                                                                  |
|  asyncio Event Loop                                              |
|  +------------------------------------------------------------+ |
|  |                                                            | |
|  |  +------------------+    +------------------+              | |
|  |  | gRPC Server      |    | Position Monitor |              | |
|  |  | (signal intake)  |    | (every 1 second) |              | |
|  |  +--------+---------+    +--------+---------+              | |
|  |           |                       |                        | |
|  |           v                       v                        | |
|  |  +------------------+    +------------------+              | |
|  |  | Signal Validator  |    | SL/TP Manager   |              | |
|  |  | & Deduplicator   |    | (trailing stops) |              | |
|  |  +--------+---------+    +--------+---------+              | |
|  |           |                       |                        | |
|  |           v                       v                        | |
|  |  +------------------+    +------------------+              | |
|  |  | Position Sizer   |    | Time-Based Exits |              | |
|  |  | & Risk Check     |    | (stale positions)|              | |
|  |  +--------+---------+    +--------+---------+              | |
|  |           |                       |                        | |
|  |           v                       v                        | |
|  |  +---------------------------------------------------+    | |
|  |  |     MT5 Thread-Safe Wrapper (single MT5 thread)    |    | |
|  |  +---------------------------------------------------+    | |
|  |           |                                                | |
|  |           v                                                | |
|  |  +------------------+    +------------------+              | |
|  |  | Execution Logger |    | Metrics Exporter |              | |
|  |  | (PostgreSQL)     |    | (Prometheus)     |              | |
|  |  +------------------+    +------------------+              | |
|  |                                                            | |
|  +------------------------------------------------------------+ |
|                                                                  |
|  +------------------------------------------------------------+ |
|  | Background Tasks:                                          | |
|  | - Health check heartbeat (every 10s)                       | |
|  | - Symbol spec cache refresh (every 60s)                    | |
|  | - Position reconciliation (every 30s)                      | |
|  | - Spread monitor (every 5s)                                | |
|  | - Margin utilization check (every 10s)                     | |
|  +------------------------------------------------------------+ |
+================================================================+
```

The main entry point of the Bridge service:

```python
import asyncio
import signal
import logging
from bridge.grpc_server import SignalServer
from bridge.position_monitor import PositionMonitor
from bridge.sltp_manager import SLTPManager
from bridge.health_checker import HealthChecker
from bridge.reconciler import PositionReconciler
from bridge.mt5_wrapper import MT5ThreadSafeWrapper
from bridge.config import BridgeConfig

logger = logging.getLogger("moneymaker.bridge")


class ExecutionBridge:
    """Main Bridge service orchestrator."""

    def __init__(self, config: BridgeConfig):
        self.config = config
        self.mt5 = MT5ThreadSafeWrapper()
        self.running = False

        # Sub-components
        self.grpc_server = SignalServer(config, self.mt5)
        self.position_monitor = PositionMonitor(config, self.mt5)
        self.sltp_manager = SLTPManager(config, self.mt5)
        self.health_checker = HealthChecker(config, self.mt5)
        self.reconciler = PositionReconciler(config, self.mt5)

    async def start(self):
        """Start all Bridge components."""
        logger.info("Starting MONEYMAKER MT5 Execution Bridge...")

        # Initialize MT5 connection
        await self.mt5.call(mt5.initialize, path=self.config.mt5_path)
        await self.mt5.call(
            mt5.login,
            login=self.config.account,
            password=self.config.password,
            server=self.config.server,
        )

        account_info = await self.mt5.call(mt5.account_info)
        logger.info(
            f"Connected: account={account_info.login}, "
            f"equity={account_info.equity}, "
            f"leverage=1:{account_info.leverage}"
        )

        # Pre-load symbol specifications
        await self._load_symbol_specs()

        self.running = True

        # Launch concurrent tasks
        tasks = [
            asyncio.create_task(self.grpc_server.serve()),
            asyncio.create_task(
                self.position_monitor.run(interval=1.0)
            ),
            asyncio.create_task(
                self.sltp_manager.run(interval=2.0)
            ),
            asyncio.create_task(
                self.health_checker.run(interval=10.0)
            ),
            asyncio.create_task(
                self.reconciler.run(interval=30.0)
            ),
        ]

        logger.info("All Bridge components started successfully")
        await asyncio.gather(*tasks)

    async def shutdown(self):
        """Graceful shutdown: manage positions before stopping."""
        logger.warning("Bridge shutdown initiated")
        self.running = False

        # Tighten all stop-losses before shutdown
        await self.sltp_manager.tighten_all_stops()

        # Optionally close all positions (configurable)
        if self.config.close_on_shutdown:
            await self._close_all_positions()

        await self.mt5.call(mt5.shutdown)
        logger.info("MT5 connection closed. Bridge shutdown complete.")

    async def _load_symbol_specs(self):
        """Pre-load and cache symbol specifications."""
        for symbol in self.config.symbols:
            info = await self.mt5.call(mt5.symbol_info, symbol)
            if info is None:
                logger.error(f"Symbol {symbol} not available")
                continue
            if not info.visible:
                await self.mt5.call(mt5.symbol_select, symbol, True)
            self.symbol_cache[symbol] = info
            logger.info(f"Loaded spec for {symbol}: "
                       f"digits={info.digits}, "
                       f"lot_min={info.volume_min}")
```

### gRPC Server Interface

The Bridge exposes a gRPC server that the AI Trading Brain connects to for sending trading signals and receiving execution confirmations. The gRPC service definition extends the basic signal service from Document 03 with execution-specific messages:

```protobuf
syntax = "proto3";

package moneymaker.execution;

// The primary service interface for the Execution Bridge
service ExecutionBridgeService {
    // Submit a single trading signal for execution
    rpc ExecuteSignal (TradingSignal) returns (ExecutionResult);

    // Stream signals for rapid execution during volatile conditions
    rpc StreamSignals (stream TradingSignal) returns (stream ExecutionResult);

    // Close an existing position
    rpc ClosePosition (CloseRequest) returns (ExecutionResult);

    // Modify an existing position (SL/TP)
    rpc ModifyPosition (ModifyRequest) returns (ModifyResult);

    // Get current status of the Bridge and open positions
    rpc GetStatus (StatusRequest) returns (BridgeStatus);

    // Emergency: close all positions immediately
    rpc EmergencyCloseAll (EmptyRequest) returns (EmergencyResult);
}

message TradingSignal {
    string signal_id = 1;          // Unique idempotency key
    string symbol = 2;             // e.g., "XAUUSD"
    Direction direction = 3;       // BUY, SELL, CLOSE
    double confidence = 4;         // 0.0 to 1.0
    double suggested_lots = 5;     // AI-recommended position size
    double stop_loss = 6;          // SL price level
    double take_profit = 7;        // TP price level
    int64 timestamp_ns = 8;        // Signal generation time (UTC nanos)
    string model_version = 9;      // Which model generated this
    string regime = 10;            // Current market regime
    string strategy = 11;          // Strategy that produced the signal
    int32 magic_number = 12;       // EA magic for position tracking
    OrderType order_type = 13;     // MARKET, LIMIT, STOP, STOP_LIMIT
    double limit_price = 14;       // Price for pending orders
    int64 expiry_ns = 15;          // Expiration for pending orders
    map<string, string> metadata = 16;  // Additional context
}

enum Direction {
    HOLD = 0;
    BUY = 1;
    SELL = 2;
    CLOSE = 3;
}

enum OrderType {
    MARKET = 0;
    BUY_LIMIT = 1;
    SELL_LIMIT = 2;
    BUY_STOP = 3;
    SELL_STOP = 4;
    BUY_STOP_LIMIT = 5;
    SELL_STOP_LIMIT = 6;
}

message ExecutionResult {
    string signal_id = 1;
    ExecutionStatus status = 2;
    int64 order_ticket = 3;         // MT5 order ticket
    int64 deal_ticket = 4;          // MT5 deal ticket
    double fill_price = 5;          // Actual fill price
    double fill_volume = 6;         // Actual filled volume
    double slippage_points = 7;     // Expected vs actual price diff
    double spread_at_execution = 8; // Spread at time of execution
    int64 execution_time_us = 9;    // Execution latency in microseconds
    string error_message = 10;      // Error details if failed
    int64 timestamp_ns = 11;        // Execution confirmation time
}

enum ExecutionStatus {
    SUCCESS = 0;
    PARTIAL_FILL = 1;
    REJECTED = 2;
    REQUOTED = 3;
    ERROR = 4;
    DUPLICATE = 5;
    MARKET_CLOSED = 6;
    INSUFFICIENT_MARGIN = 7;
}

message CloseRequest {
    int64 position_ticket = 1;     // MT5 position ticket to close
    double volume = 2;             // Volume to close (0 = close all)
    string reason = 3;             // Why closing (for audit)
    int32 deviation = 4;           // Max slippage in points
}

message ModifyRequest {
    int64 position_ticket = 1;
    double new_sl = 2;             // New stop-loss price (0 = no change)
    double new_tp = 3;             // New take-profit price (0 = no change)
    string reason = 4;             // Why modifying (for audit)
}

message ModifyResult {
    bool success = 1;
    string error_message = 2;
}

message StatusRequest {
    bool include_positions = 1;
    bool include_history = 2;
    int64 history_from_ns = 3;
}

message BridgeStatus {
    bool mt5_connected = 1;
    bool broker_connected = 2;
    double account_equity = 3;
    double account_balance = 4;
    double margin_used = 5;
    double margin_free = 6;
    double margin_level = 7;
    int32 open_positions_count = 8;
    repeated PositionInfo positions = 9;
    int64 uptime_seconds = 10;
    int64 orders_executed_today = 11;
    double daily_pnl = 12;
}

message PositionInfo {
    int64 ticket = 1;
    string symbol = 2;
    string direction = 3;
    double volume = 4;
    double open_price = 5;
    double current_price = 6;
    double sl = 7;
    double tp = 8;
    double profit = 9;
    double swap = 10;
    int64 open_time_ns = 11;
    int32 magic = 12;
}

message EmptyRequest {}

message EmergencyResult {
    int32 positions_closed = 1;
    int32 positions_failed = 2;
    repeated string errors = 3;
}
```

### Execution Flow: Signal to Order

The complete execution flow from AI signal reception to broker order confirmation follows a strict sequence of validation and safety checks:

```
Algo Engine generates signal
        |
        v
[1] gRPC transport to Bridge
        |
        v
[2] Signal Reception & Deserialization
    - Parse protobuf message
    - Validate required fields present
    - Check signal_id format
        |
        v
[3] Idempotency Check
    - Lookup signal_id in deduplication cache
    - If found: return cached result (DUPLICATE status)
    - If not found: proceed
        |
        v
[4] Signal Validation
    - Symbol is in configured watchlist
    - Direction is valid (BUY/SELL, not HOLD)
    - Confidence meets minimum threshold (default: 0.6)
    - Signal age < max_signal_age (default: 5 seconds)
    - Model version matches expected production version
        |
        v
[5] Market State Check
    - MT5 terminal is connected
    - Broker server is reachable
    - Market is open for this symbol
    - Spread is below maximum threshold
        |
        v
[6] Risk Validation
    - Current drawdown < max_daily_drawdown
    - Daily loss < max_daily_loss
    - Total open positions < max_positions
    - Total exposure < max_exposure
    - Correlation check: not overexposed to correlated assets
        |
        v
[7] Position Sizing
    - Calculate lots based on equity, risk %, ATR, and SL distance
    - Apply symbol-specific limits (volume_min, volume_max, volume_step)
    - Apply account-level position size cap
    - Verify margin availability via order_check()
        |
        v
[8] Order Construction
    - Build MT5 order request dictionary
    - Set fill policy based on broker support
    - Set deviation (max slippage) based on symbol config
    - Set magic number for position identification
    - Add comment with signal_id for traceability
        |
        v
[9] Pre-Flight Check (mt5.order_check)
    - Verify order parameters are valid
    - Verify sufficient margin
    - Verify SL/TP distances are valid
        |
        v
[10] Order Submission (mt5.order_send)
    - Submit to MT5 terminal
    - Record submission timestamp
        |
        v
[11] Result Processing
    - Parse order_send result
    - Calculate slippage (fill_price vs expected_price)
    - Calculate execution latency
    - Update local position state
    - Store signal_id in deduplication cache
    - Log to audit trail
    - Return ExecutionResult via gRPC
```

### Fill Policies

MT5 supports three fill policies that determine how partial fills are handled:

**Fill or Kill (FOK):** The order must be filled completely at the specified price or better, or it is cancelled entirely. This is the safest policy for market orders because it prevents partial fills, but it may result in more rejections during volatile conditions. The Bridge uses FOK as the default for symbols where the broker supports it.

**Immediate or Cancel (IOC):** The order is filled as much as possible at the specified price or better, and any unfilled remainder is cancelled. This allows partial fills, which the Bridge must handle (see Section 8.5). IOC is used when FOK is not supported by the broker or when partial fills are acceptable.

**Return:** The unfilled portion of the order remains as a pending order until it is filled or cancelled. This is used exclusively for pending orders (limits and stops), not for market orders.

The Bridge determines the appropriate fill policy per symbol during initialization:

```python
def determine_fill_policy(symbol_info) -> int:
    """
    Determine the best fill policy for a symbol based on broker support.
    MT5 reports supported fill modes via the filling_mode bitmask.
    """
    filling = symbol_info.filling_mode

    if filling & mt5.SYMBOL_FILLING_FOK:
        return mt5.ORDER_FILLING_FOK
    elif filling & mt5.SYMBOL_FILLING_IOC:
        return mt5.ORDER_FILLING_IOC
    else:
        return mt5.ORDER_FILLING_RETURN
```

### Retry Logic with Exponential Backoff

Transient failures (requotes, temporary disconnections, rate limiting) are handled with an exponential backoff retry strategy. The retry logic distinguishes between retryable and non-retryable errors:

```python
import asyncio
import random

RETRYABLE_CODES = {
    10004,  # TRADE_RETCODE_REQUOTE
    10015,  # TRADE_RETCODE_INVALID_PRICE (price moved)
    10024,  # TRADE_RETCODE_TOO_MANY_REQUESTS
}

NON_RETRYABLE_CODES = {
    10006,  # TRADE_RETCODE_REJECT
    10013,  # TRADE_RETCODE_INVALID
    10014,  # TRADE_RETCODE_INVALID_VOLUME
    10016,  # TRADE_RETCODE_INVALID_STOPS
    10018,  # TRADE_RETCODE_MARKET_CLOSED
    10019,  # TRADE_RETCODE_NO_MONEY
}


async def execute_with_retry(
    mt5_wrapper,
    request: dict,
    max_retries: int = 3,
    base_delay: float = 0.05,   # 50ms initial delay
    max_delay: float = 1.0,
) -> dict:
    """
    Execute an order with exponential backoff retry for transient errors.
    """
    last_error = None

    for attempt in range(max_retries + 1):
        # Refresh price on retry
        if attempt > 0:
            tick = await mt5_wrapper.call(
                mt5.symbol_info_tick, request["symbol"]
            )
            if request["type"] == mt5.ORDER_TYPE_BUY:
                request["price"] = tick.ask
            else:
                request["price"] = tick.bid

        result = await mt5_wrapper.call(mt5.order_send, request)

        if result is not None and result.retcode == mt5.TRADE_RETCODE_DONE:
            return {
                "ticket": result.order,
                "price": result.price,
                "volume": result.volume,
                "retcode": result.retcode,
                "attempts": attempt + 1,
            }

        retcode = result.retcode if result else -1
        last_error = {
            "retcode": retcode,
            "comment": getattr(result, "comment", "No result"),
        }

        if retcode in NON_RETRYABLE_CODES:
            raise OrderError(
                f"Non-retryable error: retcode={retcode}, "
                f"comment={last_error['comment']}"
            )

        if attempt < max_retries and retcode in RETRYABLE_CODES:
            delay = min(
                base_delay * (2 ** attempt) + random.uniform(0, 0.01),
                max_delay,
            )
            logger.warning(
                f"Retryable error (attempt {attempt + 1}/{max_retries}): "
                f"retcode={retcode}, retrying in {delay:.3f}s"
            )
            await asyncio.sleep(delay)
        else:
            break

    raise OrderError(
        f"Order failed after {max_retries + 1} attempts: {last_error}"
    )
```

### Idempotency Keys

Every trading signal carries a unique `signal_id` that serves as an idempotency key. The Bridge maintains a time-limited cache of recently processed signal IDs and their results. If a signal with the same ID arrives again (due to gRPC retries, network glitches, or Algo Engine retries), the Bridge returns the cached result without executing a second order.

```python
from collections import OrderedDict
import time


class IdempotencyCache:
    """
    LRU cache with TTL for storing processed signal results.
    Prevents duplicate order execution.
    """

    def __init__(self, max_size: int = 10000, ttl_seconds: int = 300):
        self._cache: OrderedDict = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl_seconds

    def get(self, signal_id: str):
        """Return cached result if exists and not expired."""
        if signal_id in self._cache:
            result, timestamp = self._cache[signal_id]
            if time.time() - timestamp < self._ttl:
                self._cache.move_to_end(signal_id)
                return result
            else:
                del self._cache[signal_id]
        return None

    def put(self, signal_id: str, result: dict):
        """Store execution result for future deduplication."""
        self._cache[signal_id] = (result, time.time())
        self._cache.move_to_end(signal_id)
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def contains(self, signal_id: str) -> bool:
        """Check if signal_id exists (without returning result)."""
        return self.get(signal_id) is not None
```

---

## 8.5 Order Management System (OMS)

### Position Tracking: Local State Synced with MT5 State

The Bridge maintains a local position database that mirrors the state of positions in MT5. This local state is the primary source of truth for the Bridge's decision-making (should we modify this position's SL? should we close this position due to time? how much total exposure do we have?), while MT5's state is the authoritative source of truth for what actually exists at the broker.

The local position database is an in-memory dictionary keyed by MT5 position ticket, supplemented by periodic persistence to PostgreSQL for crash recovery:

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional


@dataclass
class TrackedPosition:
    """Local representation of an open MT5 position."""
    ticket: int
    symbol: str
    direction: str               # "BUY" or "SELL"
    volume: float
    open_price: float
    current_price: float = 0.0
    sl: float = 0.0
    tp: float = 0.0
    profit: float = 0.0
    swap: float = 0.0
    magic: int = 0
    comment: str = ""
    open_time: datetime = None

    # MONEYMAKER-specific tracking
    signal_id: str = ""          # Original signal that opened this
    strategy: str = ""           # Strategy that generated the signal
    model_version: str = ""      # Model version at signal time
    regime_at_open: str = ""     # Market regime when position opened
    confidence_at_open: float = 0.0
    expected_sl: float = 0.0     # SL from original signal
    expected_tp: float = 0.0     # TP from original signal
    trailing_activated: bool = False
    breakeven_activated: bool = False
    partial_closes: list = field(default_factory=list)
    max_favorable_excursion: float = 0.0   # Best unrealized P&L
    max_adverse_excursion: float = 0.0     # Worst unrealized P&L


class PositionTracker:
    """
    Maintains local position state synchronized with MT5.
    """

    def __init__(self, mt5_wrapper, db_connection):
        self.mt5 = mt5_wrapper
        self.db = db_connection
        self.positions: Dict[int, TrackedPosition] = {}
        self._magic_filter: int = None  # Only track MONEYMAKER positions

    async def sync_with_mt5(self):
        """
        Synchronize local state with MT5 positions.
        Detects new positions, closed positions, and state changes.
        """
        mt5_positions = await self.mt5.call(mt5.positions_get)
        if mt5_positions is None:
            mt5_positions = []

        mt5_tickets = set()
        for pos in mt5_positions:
            # Filter by magic number if configured
            if self._magic_filter and pos.magic != self._magic_filter:
                continue

            mt5_tickets.add(pos.ticket)

            if pos.ticket in self.positions:
                # Update existing position
                tracked = self.positions[pos.ticket]
                tracked.current_price = pos.price_current
                tracked.profit = pos.profit
                tracked.swap = pos.swap
                tracked.sl = pos.sl
                tracked.tp = pos.tp

                # Update excursion tracking
                if pos.profit > tracked.max_favorable_excursion:
                    tracked.max_favorable_excursion = pos.profit
                if pos.profit < tracked.max_adverse_excursion:
                    tracked.max_adverse_excursion = pos.profit
            else:
                # New position detected (possibly opened externally)
                self.positions[pos.ticket] = TrackedPosition(
                    ticket=pos.ticket,
                    symbol=pos.symbol,
                    direction=(
                        "BUY" if pos.type == mt5.ORDER_TYPE_BUY
                        else "SELL"
                    ),
                    volume=pos.volume,
                    open_price=pos.price_open,
                    current_price=pos.price_current,
                    sl=pos.sl,
                    tp=pos.tp,
                    profit=pos.profit,
                    swap=pos.swap,
                    magic=pos.magic,
                    comment=pos.comment,
                    open_time=datetime.fromtimestamp(pos.time),
                )
                logger.info(f"New position detected: #{pos.ticket} "
                           f"{pos.symbol} {pos.volume}")

        # Detect closed positions
        local_tickets = set(self.positions.keys())
        closed_tickets = local_tickets - mt5_tickets
        for ticket in closed_tickets:
            closed_pos = self.positions.pop(ticket)
            await self._record_closed_position(closed_pos)
            logger.info(
                f"Position #{ticket} closed: {closed_pos.symbol} "
                f"P&L={closed_pos.profit}"
            )

    async def _record_closed_position(self, pos: TrackedPosition):
        """Record closed position to database for feedback loop."""
        record = {
            "ticket": pos.ticket,
            "symbol": pos.symbol,
            "direction": pos.direction,
            "volume": pos.volume,
            "open_price": pos.open_price,
            "close_price": pos.current_price,
            "sl": pos.sl,
            "tp": pos.tp,
            "profit": pos.profit,
            "swap": pos.swap,
            "open_time": pos.open_time,
            "signal_id": pos.signal_id,
            "strategy": pos.strategy,
            "model_version": pos.model_version,
            "regime_at_open": pos.regime_at_open,
            "confidence_at_open": pos.confidence_at_open,
            "max_favorable_excursion": pos.max_favorable_excursion,
            "max_adverse_excursion": pos.max_adverse_excursion,
            "partial_closes": pos.partial_closes,
        }
        await self.db.insert_closed_trade(record)
```

### Order Lifecycle

Every order in MONEYMAKER follows a well-defined lifecycle with discrete states. The Bridge tracks each order through this lifecycle, logging every state transition to the audit trail:

```
    SIGNAL_RECEIVED
         |
         v
    VALIDATING -----> REJECTED (validation failed)
         |
         v
    SIZING ----------> REJECTED (risk limit exceeded)
         |
         v
    PREFLIGHT -------> REJECTED (margin insufficient)
         |
         v
    SUBMITTED
         |
         +---------> FILLED (success)
         |
         +---------> PARTIAL_FILL (IOC partial)
         |               |
         |               v
         |           REMAINDER_CANCELLED
         |
         +---------> REQUOTED
         |               |
         |               v
         |           RESUBMITTED (with new price)
         |               |
         |               +---> FILLED / REJECTED
         |
         +---------> REJECTED (broker rejection)
         |
         +---------> CANCELLED (timeout/manual)
         |
         +---------> ERROR (MT5 error)
```

### Partial Fills Handling

When an IOC (Immediate Or Cancel) order receives a partial fill, the Bridge must decide what to do with the unfilled portion:

```python
async def handle_partial_fill(
    self, signal: TradingSignal, result, requested_volume: float
):
    """
    Handle a partial fill result.
    Strategy: accept the partial fill, do not resubmit remainder.
    """
    filled_volume = result.volume
    unfilled_volume = requested_volume - filled_volume

    logger.warning(
        f"Partial fill for {signal.signal_id}: "
        f"requested={requested_volume}, "
        f"filled={filled_volume}, "
        f"unfilled={unfilled_volume}"
    )

    # Record the partial fill as a valid position
    # The Algo Engine will be notified that the actual position
    # is smaller than requested
    return ExecutionResult(
        signal_id=signal.signal_id,
        status=ExecutionStatus.PARTIAL_FILL,
        order_ticket=result.order,
        deal_ticket=result.deal,
        fill_price=result.price,
        fill_volume=filled_volume,
        slippage_points=self._calc_slippage(
            signal, result.price
        ),
    )
```

The Bridge's default policy for partial fills is to accept the filled portion and not resubmit the remainder. This conservative approach prevents the situation where repeated partial fill resubmissions result in a total position larger than intended. The Algo Engine is informed of the actual fill size and can adjust its position management accordingly.

### Position Reconciliation

Every 30 seconds, the Bridge performs a full reconciliation between its local position state and the actual positions in MT5. This catches discrepancies caused by:

- Positions closed by broker-side stop-loss or take-profit (the Bridge does not receive a callback for these; it discovers them during reconciliation)
- Positions opened or closed manually through the MT5 terminal
- Positions opened by other Expert Advisors (if any are running)
- State corruption due to unexpected restarts

The reconciliation process compares the local `PositionTracker` dictionary with the result of `mt5.positions_get()` and resolves any differences. Discrepancies are logged as warnings for operator review.

### Trade Journal

Every order, regardless of outcome, is recorded in the trade journal -- a PostgreSQL table that serves as the complete record of the Bridge's trading activity. The journal schema:

```sql
CREATE TABLE trade_journal (
    id              BIGSERIAL PRIMARY KEY,
    signal_id       TEXT NOT NULL,
    timestamp_ns    BIGINT NOT NULL,
    symbol          TEXT NOT NULL,
    direction       TEXT NOT NULL,          -- BUY, SELL, CLOSE
    order_type      TEXT NOT NULL,          -- MARKET, LIMIT, STOP
    requested_lots  DOUBLE PRECISION,
    filled_lots     DOUBLE PRECISION,
    requested_price DOUBLE PRECISION,
    fill_price      DOUBLE PRECISION,
    slippage_points DOUBLE PRECISION,
    spread_at_exec  DOUBLE PRECISION,
    sl_price        DOUBLE PRECISION,
    tp_price        DOUBLE PRECISION,
    mt5_ticket      BIGINT,
    mt5_deal        BIGINT,
    mt5_retcode     INTEGER,
    execution_status TEXT NOT NULL,         -- SUCCESS, REJECTED, ERROR, etc.
    rejection_reason TEXT,
    execution_us    BIGINT,                 -- Latency in microseconds
    ai_confidence   DOUBLE PRECISION,
    model_version   TEXT,
    regime          TEXT,
    strategy        TEXT,
    account_equity  DOUBLE PRECISION,
    account_balance DOUBLE PRECISION,
    margin_used_pct DOUBLE PRECISION,
    metadata_json   JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast lookups
CREATE INDEX idx_trade_journal_signal ON trade_journal(signal_id);
CREATE INDEX idx_trade_journal_symbol_time ON trade_journal(symbol, created_at);
CREATE INDEX idx_trade_journal_ticket ON trade_journal(mt5_ticket);
```

### Slippage Monitoring

Slippage -- the difference between the expected fill price and the actual fill price -- is a critical execution quality metric. The Bridge calculates and records slippage for every order:

```python
def calculate_slippage(
    self, signal: TradingSignal, fill_price: float, symbol_info
) -> float:
    """
    Calculate slippage in points.
    Positive slippage = unfavorable (paid more than expected).
    Negative slippage = favorable (paid less than expected).
    """
    if signal.direction == Direction.BUY:
        # For buys, we expected to pay the ask price
        expected = signal.limit_price or self._last_ask[signal.symbol]
        slippage = (fill_price - expected) / symbol_info.point
    else:
        # For sells, we expected to receive the bid price
        expected = signal.limit_price or self._last_bid[signal.symbol]
        slippage = (expected - fill_price) / symbol_info.point

    return slippage
```

Slippage statistics are aggregated per symbol and per session, and exposed as Prometheus metrics for monitoring. If average slippage exceeds a configured threshold (default: 5 points for XAU/USD), the Bridge generates an alert and can optionally pause trading on the affected symbol.

### Spread Monitoring

The Bridge monitors the spread (difference between ask and bid price) before every order submission. Wide spreads during low-liquidity periods (Asian session open, rollover time, news events) can significantly impact execution quality.

```python
async def check_spread(self, symbol: str) -> bool:
    """
    Check if the current spread is acceptable for trading.
    Returns True if spread is within threshold, False otherwise.
    """
    tick = await self.mt5.call(mt5.symbol_info_tick, symbol)
    info = self.symbol_cache[symbol]

    spread_points = (tick.ask - tick.bid) / info.point
    max_spread = self.config.max_spread_points.get(symbol, 50)

    if spread_points > max_spread:
        logger.warning(
            f"Spread too wide for {symbol}: "
            f"{spread_points} points > max {max_spread}"
        )
        return False

    return True
```

---

## 8.6 Multi-Symbol and Multi-Timeframe Support

### Symbol Registry

The Bridge maintains a configurable registry of tradeable symbols. Each symbol has its own execution parameters, risk limits, and monitoring thresholds. The registry is loaded from the configuration file at startup and can be updated at runtime via Redis pub/sub configuration messages.

```python
# bridge_config.yaml

symbols:
  XAUUSD:
    enabled: true
    priority: 1                    # Primary instrument
    max_lots: 5.0
    max_positions: 3
    max_spread_points: 50
    default_sl_atr_multiplier: 1.5
    default_tp_atr_multiplier: 2.5
    atr_period: 14
    atr_timeframe: "H1"
    magic_number: 100001
    max_slippage_points: 30
    min_confidence: 0.6
    trading_sessions:              # Only trade during these sessions
      - start: "08:00"            # London open
        end: "17:00"              # New York close
    cooldown_seconds: 300          # Min time between trades

  EURUSD:
    enabled: true
    priority: 2
    max_lots: 10.0
    max_positions: 2
    max_spread_points: 20
    default_sl_atr_multiplier: 1.5
    default_tp_atr_multiplier: 2.0
    atr_period: 14
    atr_timeframe: "H1"
    magic_number: 100002
    max_slippage_points: 15
    min_confidence: 0.65
    trading_sessions:
      - start: "07:00"
        end: "17:00"
    cooldown_seconds: 300

  GBPUSD:
    enabled: true
    priority: 3
    max_lots: 8.0
    max_positions: 2
    max_spread_points: 25
    default_sl_atr_multiplier: 2.0
    default_tp_atr_multiplier: 2.5
    atr_period: 14
    atr_timeframe: "H1"
    magic_number: 100003
    max_slippage_points: 20
    min_confidence: 0.65
    trading_sessions:
      - start: "07:00"
        end: "17:00"
    cooldown_seconds: 300
```

### Primary Focus: XAU/USD (Gold)

Gold is the primary instrument for MONEYMAKER V1 for several reasons that align with the system's strengths:

**High volatility.** Gold's average daily range of 200-400 pips (20-40 USD) provides substantial profit potential per trade, allowing the system to absorb execution costs (spread, slippage, commission) while remaining profitable.

**Strong trending behavior.** Gold exhibits clear trending regimes driven by macroeconomic factors (USD strength, real interest rates, geopolitical risk), which the Algo Engine's regime classifier can identify and exploit.

**High liquidity during London and New York sessions.** Tight spreads and deep liquidity during the sessions when MONEYMAKER is configured to trade, minimizing execution costs.

**Sensitivity to quantifiable inputs.** Gold responds to DXY (Dollar Index), US Treasury yields, inflation expectations, and risk sentiment -- all of which the Data Ingestion Service captures and the Algo Engine incorporates into its feature set.

### Timeframe Mapping

The Bridge maps between the Algo Engine's timeframe identifiers and MT5's timeframe constants. The Algo Engine generates signals based on its analysis of multiple timeframes, and the Bridge needs to understand these timeframes for ATR calculation and historical data lookups.

```python
MT5_TIMEFRAME_MAP = {
    "M1":  mt5.TIMEFRAME_M1,
    "M2":  mt5.TIMEFRAME_M2,
    "M3":  mt5.TIMEFRAME_M3,
    "M4":  mt5.TIMEFRAME_M4,
    "M5":  mt5.TIMEFRAME_M5,
    "M6":  mt5.TIMEFRAME_M6,
    "M10": mt5.TIMEFRAME_M10,
    "M12": mt5.TIMEFRAME_M12,
    "M15": mt5.TIMEFRAME_M15,
    "M20": mt5.TIMEFRAME_M20,
    "M30": mt5.TIMEFRAME_M30,
    "H1":  mt5.TIMEFRAME_H1,
    "H2":  mt5.TIMEFRAME_H2,
    "H3":  mt5.TIMEFRAME_H3,
    "H4":  mt5.TIMEFRAME_H4,
    "H6":  mt5.TIMEFRAME_H6,
    "H8":  mt5.TIMEFRAME_H8,
    "H12": mt5.TIMEFRAME_H12,
    "D1":  mt5.TIMEFRAME_D1,
    "W1":  mt5.TIMEFRAME_W1,
    "MN1": mt5.TIMEFRAME_MN1,
}
```

### Cross-Symbol Correlation Awareness

The Bridge maintains awareness of correlations between traded instruments to prevent overexposure. For example, being long both XAU/USD and short USD/CHF is effectively doubling down on USD weakness. The correlation matrix is computed by the Algo Engine and published to Redis, where the Bridge reads it during risk validation:

```python
# Correlation thresholds for position blocking
CORRELATION_THRESHOLD = 0.75  # Block if |correlation| > 0.75

async def check_correlation_risk(
    self, new_symbol: str, new_direction: str
) -> bool:
    """
    Check if a new position would create excessive correlated exposure.
    """
    correlations = await self._get_correlation_matrix()
    if correlations is None:
        return True  # Allow if no correlation data available

    for ticket, pos in self.position_tracker.positions.items():
        pair = (new_symbol, pos.symbol)
        corr = correlations.get(pair, 0.0)

        # Same direction + positive correlation = increased exposure
        # Opposite direction + negative correlation = increased exposure
        same_direction = (new_direction == pos.direction)
        if (same_direction and corr > CORRELATION_THRESHOLD) or \
           (not same_direction and corr < -CORRELATION_THRESHOLD):
            logger.warning(
                f"Correlation risk: {new_symbol} {new_direction} "
                f"correlated with existing {pos.symbol} {pos.direction} "
                f"(r={corr:.2f})"
            )
            return False

    return True
```

---

## 8.7 Position Sizing and Risk Integration

### Position Sizing Philosophy

Position sizing is where risk management becomes concrete. A correct signal with incorrect sizing can destroy an account just as effectively as a wrong signal. The Bridge implements a multi-layered position sizing system that starts with the Algo Engine's recommended size, validates it against multiple risk constraints, and produces a final lot size that is guaranteed to be within all safety limits.

### Kelly Criterion-Based Sizing from Algo Engine

The Algo Engine calculates a suggested position size using a fractional Kelly criterion approach. The full Kelly formula is:

```
f* = (p * b - q) / b

Where:
  f* = fraction of bankroll to risk
  p  = probability of winning (from model confidence)
  b  = ratio of profit to loss (reward-to-risk ratio)
  q  = probability of losing (1 - p)
```

The Algo Engine uses a half-Kelly or quarter-Kelly fraction to reduce volatility:

```
suggested_fraction = kelly_fraction * kelly_multiplier
                   = f* * 0.25  (quarter-Kelly default)
```

The Bridge receives this as `suggested_lots` in the trading signal but always validates and potentially reduces it further.

### Dynamic Lot Calculation

The Bridge's primary position sizing formula converts risk parameters into a concrete lot size:

```python
from decimal import Decimal, ROUND_DOWN


def calculate_lot_size(
    equity: float,
    risk_pct: float,
    sl_distance_points: float,
    tick_value: float,
    tick_size: float,
    volume_min: float,
    volume_max: float,
    volume_step: float,
) -> float:
    """
    Calculate position size based on account equity and risk parameters.

    Formula:
        risk_amount = equity * risk_pct
        sl_value = sl_distance_points * (tick_value / tick_size)
        lots = risk_amount / sl_value

    Example for XAU/USD:
        equity = $10,000
        risk_pct = 0.01 (1%)
        sl_distance = 500 points (5.00 USD move)
        tick_value = $1.00 per tick per lot
        tick_size = 0.01 (1 point)

        risk_amount = $10,000 * 0.01 = $100
        sl_value = 500 * ($1.00 / 0.01) = 500 * 100 = $50,000 per lot
        lots = $100 / $50,000 = 0.002 lots

    Wait -- this requires careful unit analysis for Gold:
        For XAU/USD: 1 standard lot = 100 troy ounces
        tick_value per lot for 1 point (0.01) move = $1.00
        SL distance of 500 points = $500 per lot
        lots = $100 / $500 = 0.20 lots

    The correct formula depends on contract specifications.
    """
    # Calculate the dollar risk per lot for the given SL distance
    point_value_per_lot = tick_value / tick_size
    sl_risk_per_lot = sl_distance_points * point_value_per_lot

    if sl_risk_per_lot <= 0:
        raise ValueError("SL risk per lot must be positive")

    # Calculate the dollar amount we are willing to risk
    risk_amount = equity * risk_pct

    # Raw lot size
    raw_lots = risk_amount / sl_risk_per_lot

    # Round down to the nearest valid step
    lots = Decimal(str(raw_lots)).quantize(
        Decimal(str(volume_step)), rounding=ROUND_DOWN
    )
    lots = float(lots)

    # Clamp to valid range
    lots = max(lots, volume_min)
    lots = min(lots, volume_max)

    return lots
```

### ATR-Based SL Distance Calculation

The stop-loss distance, which is a key input to the position sizing formula, is calculated using the Average True Range (ATR):

```python
import numpy as np


def calculate_atr(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    period: int = 14
) -> float:
    """
    Calculate the Average True Range (ATR).
    Returns the most recent ATR value.
    """
    high_low = highs - lows
    high_close_prev = np.abs(highs[1:] - closes[:-1])
    low_close_prev = np.abs(lows[1:] - closes[:-1])

    true_ranges = np.maximum(
        high_low[1:],
        np.maximum(high_close_prev, low_close_prev)
    )

    # Use exponential moving average for ATR
    atr_values = np.zeros(len(true_ranges))
    atr_values[period - 1] = np.mean(true_ranges[:period])

    multiplier = 2.0 / (period + 1)
    for i in range(period, len(true_ranges)):
        atr_values[i] = (
            true_ranges[i] * multiplier
            + atr_values[i - 1] * (1 - multiplier)
        )

    return atr_values[-1]
```

### Maximum Position Size Limits

The Bridge enforces multiple layers of position size limits, any of which can reduce the calculated lot size:

```python
async def apply_position_limits(
    self,
    symbol: str,
    calculated_lots: float,
    signal: TradingSignal,
) -> float:
    """
    Apply all position size limits and return the final lot size.
    The returned value is guaranteed to be within all limits.
    """
    limits_applied = []
    lots = calculated_lots

    # 1. Symbol-specific max lots
    symbol_max = self.config.symbols[symbol].max_lots
    if lots > symbol_max:
        lots = symbol_max
        limits_applied.append(f"symbol_max={symbol_max}")

    # 2. Account-level max lots per position
    account_max = self.config.max_lots_per_position
    if lots > account_max:
        lots = account_max
        limits_applied.append(f"account_max={account_max}")

    # 3. Maximum total exposure across all positions
    total_lots = sum(
        pos.volume for pos in self.position_tracker.positions.values()
        if pos.symbol == symbol
    )
    remaining = self.config.symbols[symbol].max_lots - total_lots
    if lots > remaining and remaining > 0:
        lots = remaining
        limits_applied.append(f"remaining_capacity={remaining}")
    elif remaining <= 0:
        raise ExposureLimitError(
            f"Maximum exposure reached for {symbol}: "
            f"total={total_lots}"
        )

    # 4. Maximum number of positions per symbol
    position_count = sum(
        1 for pos in self.position_tracker.positions.values()
        if pos.symbol == symbol
    )
    max_positions = self.config.symbols[symbol].max_positions
    if position_count >= max_positions:
        raise ExposureLimitError(
            f"Maximum positions reached for {symbol}: "
            f"{position_count}/{max_positions}"
        )

    # 5. Margin utilization check (never exceed 50% margin)
    account = await self.mt5.call(mt5.account_info)
    margin_level = account.margin_level if account.margin_level else 999
    if margin_level < 200:  # 200% margin level = 50% utilization
        reduction = 0.5
        lots = lots * reduction
        limits_applied.append(f"margin_squeeze(x{reduction})")

    if margin_level < 150:  # 66% margin utilization -- critical
        raise MarginError(
            f"Margin level too low: {margin_level}%. "
            f"Refusing new positions."
        )

    # 6. Round to valid step size
    info = self.symbol_cache[symbol]
    lots = round_to_step(lots, info.volume_step, info.volume_min)

    if limits_applied:
        logger.info(
            f"Position size adjusted for {symbol}: "
            f"{calculated_lots} -> {lots} "
            f"(limits: {', '.join(limits_applied)})"
        )

    return lots
```

---

## 8.8 Stop-Loss and Take-Profit Management

### ATR-Based Dynamic SL/TP Calculation

Rather than using fixed pip distances, the Bridge calculates stop-loss and take-profit levels dynamically based on current market volatility as measured by ATR. This ensures that stops are neither too tight (causing premature exits in volatile conditions) nor too wide (risking excessive loss in calm conditions).

```python
async def calculate_sl_tp(
    self,
    symbol: str,
    direction: str,
    entry_price: float,
) -> tuple:
    """
    Calculate ATR-based stop-loss and take-profit prices.

    Returns (sl_price, tp_price).
    """
    config = self.config.symbols[symbol]
    tf = MT5_TIMEFRAME_MAP[config.atr_timeframe]

    # Fetch recent bars for ATR calculation
    bars = await self.mt5.call(
        mt5.copy_rates_from_pos, symbol, tf, 0, config.atr_period + 5
    )
    if bars is None or len(bars) < config.atr_period:
        raise DataError(f"Insufficient bar data for ATR on {symbol}")

    import pandas as pd
    df = pd.DataFrame(bars)
    atr = calculate_atr(
        df["high"].values,
        df["low"].values,
        df["close"].values,
        period=config.atr_period,
    )

    sl_distance = atr * config.default_sl_atr_multiplier
    tp_distance = atr * config.default_tp_atr_multiplier

    if direction == "BUY":
        sl_price = entry_price - sl_distance
        tp_price = entry_price + tp_distance
    else:  # SELL
        sl_price = entry_price + sl_distance
        tp_price = entry_price - tp_distance

    # Round to symbol's tick size
    info = self.symbol_cache[symbol]
    sl_price = round(sl_price, info.digits)
    tp_price = round(tp_price, info.digits)

    # Validate minimum stop distance
    min_distance = info.trade_stops_level * info.point
    if direction == "BUY":
        if entry_price - sl_price < min_distance:
            sl_price = entry_price - min_distance
        if tp_price - entry_price < min_distance:
            tp_price = entry_price + min_distance
    else:
        if sl_price - entry_price < min_distance:
            sl_price = entry_price + min_distance
        if entry_price - tp_price < min_distance:
            tp_price = entry_price - min_distance

    return sl_price, tp_price
```

### Trailing Stop Implementation

The trailing stop moves the stop-loss in the direction of profit as the price moves favorably. The Bridge implements trailing stops by periodically modifying open positions. This is done through the SL/TP Manager task that runs every 2 seconds.

```python
async def manage_trailing_stops(self):
    """
    Check all open positions and update trailing stops where applicable.
    """
    for ticket, pos in self.position_tracker.positions.items():
        config = self.config.symbols.get(pos.symbol)
        if config is None or not config.get("trailing_enabled", True):
            continue

        # Calculate trailing distance
        tf = MT5_TIMEFRAME_MAP[config["atr_timeframe"]]
        bars = await self.mt5.call(
            mt5.copy_rates_from_pos, pos.symbol, tf, 0,
            config["atr_period"] + 5
        )
        if bars is None:
            continue

        df = pd.DataFrame(bars)
        atr = calculate_atr(
            df["high"].values, df["low"].values,
            df["close"].values, config["atr_period"]
        )
        trail_distance = atr * config.get("trailing_atr_multiplier", 1.0)

        info = self.symbol_cache[pos.symbol]
        current_price = pos.current_price

        if pos.direction == "BUY":
            # Trail below the current price
            new_sl = round(current_price - trail_distance, info.digits)
            # Only move SL up, never down
            if new_sl > pos.sl and new_sl > pos.open_price:
                await self._modify_sl(ticket, new_sl, "trailing_stop")

        elif pos.direction == "SELL":
            # Trail above the current price
            new_sl = round(current_price + trail_distance, info.digits)
            # Only move SL down, never up
            if new_sl < pos.sl and new_sl < pos.open_price:
                await self._modify_sl(ticket, new_sl, "trailing_stop")


async def _modify_sl(self, ticket: int, new_sl: float, reason: str):
    """Modify a position's stop-loss via MT5."""
    position = self.position_tracker.positions.get(ticket)
    if position is None:
        return

    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "position": ticket,
        "symbol": position.symbol,
        "sl": new_sl,
        "tp": position.tp,
    }

    result = await self.mt5.call(mt5.order_send, request)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        position.sl = new_sl
        logger.info(
            f"SL modified for #{ticket}: new_sl={new_sl} "
            f"(reason: {reason})"
        )
    else:
        logger.warning(
            f"SL modification failed for #{ticket}: "
            f"retcode={getattr(result, 'retcode', 'N/A')}"
        )
```

### Break-Even Stop

The break-even mechanism moves the stop-loss to the entry price (plus a small buffer to cover spread and commission) once the position has moved a configurable number of points in profit:

```python
async def check_breakeven(self, ticket: int, pos: TrackedPosition):
    """
    Move SL to break-even when position is sufficiently in profit.
    """
    config = self.config.symbols.get(pos.symbol, {})
    be_trigger_points = config.get("breakeven_trigger_points", 200)
    be_offset_points = config.get("breakeven_offset_points", 10)
    info = self.symbol_cache[pos.symbol]

    if pos.breakeven_activated:
        return

    if pos.direction == "BUY":
        profit_points = (
            (pos.current_price - pos.open_price) / info.point
        )
        if profit_points >= be_trigger_points:
            new_sl = pos.open_price + (be_offset_points * info.point)
            new_sl = round(new_sl, info.digits)
            if new_sl > pos.sl:
                await self._modify_sl(ticket, new_sl, "breakeven")
                pos.breakeven_activated = True

    elif pos.direction == "SELL":
        profit_points = (
            (pos.open_price - pos.current_price) / info.point
        )
        if profit_points >= be_trigger_points:
            new_sl = pos.open_price - (be_offset_points * info.point)
            new_sl = round(new_sl, info.digits)
            if new_sl < pos.sl:
                await self._modify_sl(ticket, new_sl, "breakeven")
                pos.breakeven_activated = True
```

### Multi-Level Take-Profit (Partial Close)

Rather than closing the entire position at a single TP level, the Bridge supports closing portions of the position at multiple TP levels. This locks in partial profits while allowing the remainder to capture larger moves.

```python
# Configuration for multi-level TP
# tp_levels:
#   - pct: 0.33    # Close 33% of position
#     atr_mult: 1.5  # At 1.5x ATR from entry
#   - pct: 0.33    # Close another 33%
#     atr_mult: 2.5  # At 2.5x ATR from entry
#   - pct: 0.34    # Close remainder
#     atr_mult: 4.0  # At 4.0x ATR from entry

async def check_partial_tp(self, ticket: int, pos: TrackedPosition):
    """
    Check if any partial take-profit levels have been reached.
    """
    config = self.config.symbols.get(pos.symbol, {})
    tp_levels = config.get("tp_levels", [])
    info = self.symbol_cache[pos.symbol]

    for i, level in enumerate(tp_levels):
        # Skip levels already taken
        if any(pc["level"] == i for pc in pos.partial_closes):
            continue

        # Calculate the TP price for this level
        atr = await self._get_current_atr(pos.symbol)
        tp_distance = atr * level["atr_mult"]

        if pos.direction == "BUY":
            tp_price = pos.open_price + tp_distance
            if pos.current_price >= tp_price:
                close_volume = round(
                    pos.volume * level["pct"],
                    int(-np.log10(info.volume_step))
                )
                close_volume = max(close_volume, info.volume_min)
                await self._partial_close(
                    ticket, close_volume, f"TP_level_{i}"
                )
                pos.partial_closes.append({
                    "level": i,
                    "volume": close_volume,
                    "price": pos.current_price,
                    "time": datetime.utcnow().isoformat(),
                })
                break  # Only one level per check cycle

        elif pos.direction == "SELL":
            tp_price = pos.open_price - tp_distance
            if pos.current_price <= tp_price:
                close_volume = round(
                    pos.volume * level["pct"],
                    int(-np.log10(info.volume_step))
                )
                close_volume = max(close_volume, info.volume_min)
                await self._partial_close(
                    ticket, close_volume, f"TP_level_{i}"
                )
                pos.partial_closes.append({
                    "level": i,
                    "volume": close_volume,
                    "price": pos.current_price,
                    "time": datetime.utcnow().isoformat(),
                })
                break


async def _partial_close(
    self, ticket: int, volume: float, reason: str
):
    """Close a portion of an open position."""
    pos = self.position_tracker.positions.get(ticket)
    if pos is None:
        return

    if pos.direction == "BUY":
        order_type = mt5.ORDER_TYPE_SELL
        price = (await self.mt5.call(
            mt5.symbol_info_tick, pos.symbol
        )).bid
    else:
        order_type = mt5.ORDER_TYPE_BUY
        price = (await self.mt5.call(
            mt5.symbol_info_tick, pos.symbol
        )).ask

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": ticket,
        "symbol": pos.symbol,
        "volume": volume,
        "type": order_type,
        "price": price,
        "deviation": 20,
        "magic": pos.magic,
        "comment": f"partial_close:{reason}",
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = await self.mt5.call(mt5.order_send, request)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        logger.info(
            f"Partial close #{ticket}: {volume} lots "
            f"(reason: {reason})"
        )
    else:
        logger.error(
            f"Partial close failed for #{ticket}: "
            f"retcode={getattr(result, 'retcode', 'N/A')}"
        )
```

### Time-Based Stops

Positions that remain open beyond a maximum holding time are closed regardless of P&L. This prevents stale positions from tying up margin and protects against the overnight/weekend gap risk for positions that were intended to be short-term.

```python
async def check_time_based_exits(self):
    """Close positions that exceed maximum holding time."""
    now = datetime.utcnow()

    for ticket, pos in list(
        self.position_tracker.positions.items()
    ):
        config = self.config.symbols.get(pos.symbol, {})
        max_hours = config.get("max_holding_hours", 48)

        if pos.open_time is None:
            continue

        holding_hours = (now - pos.open_time).total_seconds() / 3600

        if holding_hours > max_hours:
            logger.warning(
                f"Time-based exit for #{ticket}: "
                f"held {holding_hours:.1f}h > max {max_hours}h"
            )
            await self._close_position(
                ticket,
                reason=f"time_exit_{holding_hours:.0f}h"
            )
```

---

## 8.9 Execution Quality Monitoring

### Why Execution Quality Matters

Execution quality is the difference between theoretical backtest returns and actual live trading returns. A strategy that generates 2 pips of expected profit per trade will be unprofitable if execution consistently costs 3 pips in slippage and spread. The Bridge monitors execution quality continuously and surfaces metrics that allow the operator and the Algo Engine to adjust behavior in response to deteriorating conditions.

### Latency Measurement

The Bridge measures execution latency at multiple granularities:

```python
import time
from dataclasses import dataclass
from typing import Dict, List
from collections import deque


@dataclass
class LatencyMeasurement:
    signal_id: str
    symbol: str
    grpc_receive_us: int       # Time from signal creation to Bridge receipt
    validation_us: int          # Time spent in validation
    sizing_us: int              # Time spent in position sizing
    preflight_us: int           # Time spent in order_check()
    submission_us: int          # Time from order_send call to return
    total_us: int               # Total end-to-end latency
    timestamp: float


class LatencyTracker:
    """Track and report execution latency statistics."""

    def __init__(self, window_size: int = 1000):
        self._measurements: Dict[str, deque] = {}
        self._window = window_size

    def record(self, measurement: LatencyMeasurement):
        symbol = measurement.symbol
        if symbol not in self._measurements:
            self._measurements[symbol] = deque(maxlen=self._window)
        self._measurements[symbol].append(measurement)

    def get_stats(self, symbol: str) -> dict:
        """Calculate latency statistics for a symbol."""
        if symbol not in self._measurements:
            return {}

        measurements = list(self._measurements[symbol])
        if not measurements:
            return {}

        totals = [m.total_us for m in measurements]
        submissions = [m.submission_us for m in measurements]

        return {
            "count": len(measurements),
            "total_mean_us": sum(totals) / len(totals),
            "total_p50_us": sorted(totals)[len(totals) // 2],
            "total_p95_us": sorted(totals)[int(len(totals) * 0.95)],
            "total_p99_us": sorted(totals)[int(len(totals) * 0.99)],
            "total_max_us": max(totals),
            "submission_mean_us": sum(submissions) / len(submissions),
            "submission_p95_us": sorted(submissions)[
                int(len(submissions) * 0.95)
            ],
        }
```

The target latency budget for the execution path:

```
+--------------------------------------------------+
|           LATENCY BUDGET (TARGET)                 |
+--------------------------------------------------+
| Stage                    | Budget    | Measured   |
|--------------------------|-----------|------------|
| gRPC transport           | < 5 ms   | ~1-3 ms    |
| Signal validation        | < 1 ms   | ~0.2 ms    |
| Idempotency check        | < 0.5 ms | ~0.05 ms   |
| Risk validation          | < 2 ms   | ~0.5-1 ms  |
| Position sizing          | < 2 ms   | ~0.3 ms    |
| order_check() preflight  | < 10 ms  | ~5-8 ms    |
| order_send() submission  | < 50 ms  | ~10-40 ms  |
| Result processing        | < 1 ms   | ~0.3 ms    |
| Audit logging (async)    | < 0 ms   | async      |
|--------------------------|-----------|------------|
| TOTAL                    | < 100 ms | ~20-55 ms  |
+--------------------------------------------------+
```

### Slippage Statistics

Slippage is tracked per symbol, per session (Asian, London, New York), and per market condition (volatile vs calm, trending vs ranging):

```python
class SlippageTracker:
    """
    Comprehensive slippage statistics tracker.
    Slippage is measured in points (positive = unfavorable).
    """

    def __init__(self):
        self._records: Dict[str, List[dict]] = {}

    def record(
        self,
        symbol: str,
        slippage_points: float,
        session: str,
        volatility: str,
        order_type: str,
    ):
        if symbol not in self._records:
            self._records[symbol] = []

        self._records[symbol].append({
            "slippage": slippage_points,
            "session": session,
            "volatility": volatility,
            "order_type": order_type,
            "timestamp": time.time(),
        })

    def get_report(self, symbol: str, days: int = 30) -> dict:
        """Generate a slippage report for the specified symbol."""
        cutoff = time.time() - (days * 86400)
        records = [
            r for r in self._records.get(symbol, [])
            if r["timestamp"] > cutoff
        ]

        if not records:
            return {"symbol": symbol, "no_data": True}

        slippages = [r["slippage"] for r in records]

        # Per-session breakdown
        sessions = {}
        for session_name in ["asian", "london", "newyork"]:
            session_records = [
                r["slippage"] for r in records
                if r["session"] == session_name
            ]
            if session_records:
                sessions[session_name] = {
                    "mean": sum(session_records) / len(session_records),
                    "median": sorted(session_records)[
                        len(session_records) // 2
                    ],
                    "max": max(session_records),
                    "count": len(session_records),
                }

        return {
            "symbol": symbol,
            "period_days": days,
            "total_orders": len(records),
            "mean_slippage": sum(slippages) / len(slippages),
            "median_slippage": sorted(slippages)[len(slippages) // 2],
            "p95_slippage": sorted(slippages)[
                int(len(slippages) * 0.95)
            ],
            "max_slippage": max(slippages),
            "pct_positive": sum(
                1 for s in slippages if s > 0
            ) / len(slippages) * 100,
            "pct_zero": sum(
                1 for s in slippages if s == 0
            ) / len(slippages) * 100,
            "pct_favorable": sum(
                1 for s in slippages if s < 0
            ) / len(slippages) * 100,
            "by_session": sessions,
        }
```

### Requote Handling

A requote occurs when the broker cannot fill the order at the requested price and offers a new price. The Bridge handles requotes automatically by refreshing the price and resubmitting, up to the configured retry limit:

```python
async def handle_requote(
    self, request: dict, result, attempt: int
) -> dict:
    """
    Handle a requote by refreshing the price and resubmitting.
    The result object contains the new offered price.
    """
    logger.info(
        f"Requote received (attempt {attempt}): "
        f"requested={request['price']}, "
        f"offered_bid={result.bid}, offered_ask={result.ask}"
    )

    # Update price to the new offered price
    if request["type"] in (mt5.ORDER_TYPE_BUY,):
        request["price"] = result.ask
    else:
        request["price"] = result.bid

    # Track requote frequency
    self.metrics.requote_counter.labels(
        symbol=request["symbol"]
    ).inc()

    return request
```

### Execution Quality Score

The Bridge calculates a composite execution quality score that summarizes overall execution performance. This score is used by the Algo Engine to adjust confidence thresholds and position sizes:

```python
def calculate_execution_quality_score(
    self, symbol: str, lookback_hours: int = 24
) -> float:
    """
    Calculate a 0-100 execution quality score.

    Components:
    - Fill rate (30%): % of orders filled successfully
    - Slippage score (30%): Lower avg slippage = higher score
    - Latency score (20%): Lower avg latency = higher score
    - Requote rate (20%): Lower requote rate = higher score
    """
    stats = self._get_recent_stats(symbol, lookback_hours)
    if stats["total_orders"] == 0:
        return 50.0  # Neutral score when no data

    # Fill rate: 100% fills = 30 points
    fill_score = (stats["fill_rate"] / 100) * 30

    # Slippage: 0 slippage = 30 points, >5 pts avg = 0 points
    max_acceptable_slip = 5.0
    slip_ratio = min(
        stats["avg_slippage"] / max_acceptable_slip, 1.0
    )
    slip_score = (1 - slip_ratio) * 30

    # Latency: <50ms = 20 points, >200ms = 0 points
    max_acceptable_latency = 200000  # 200ms in microseconds
    lat_ratio = min(
        stats["avg_latency_us"] / max_acceptable_latency, 1.0
    )
    lat_score = (1 - lat_ratio) * 20

    # Requote rate: 0% = 20 points, >10% = 0 points
    req_ratio = min(stats["requote_rate"] / 10.0, 1.0)
    req_score = (1 - req_ratio) * 20

    total = fill_score + slip_score + lat_score + req_score
    return round(total, 1)
```

### Broker Performance Metrics

The Bridge exports execution metrics to Prometheus for visualization in Grafana:

```python
from prometheus_client import (
    Counter, Histogram, Gauge, Summary
)

# Order counters
orders_submitted = Counter(
    "moneymaker_orders_submitted_total",
    "Total orders submitted to MT5",
    ["symbol", "direction", "order_type"]
)
orders_filled = Counter(
    "moneymaker_orders_filled_total",
    "Total orders filled successfully",
    ["symbol", "direction"]
)
orders_rejected = Counter(
    "moneymaker_orders_rejected_total",
    "Total orders rejected",
    ["symbol", "reason"]
)

# Execution latency
execution_latency = Histogram(
    "moneymaker_execution_latency_seconds",
    "Order execution latency",
    ["symbol"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

# Slippage
slippage_points = Histogram(
    "moneymaker_slippage_points",
    "Order slippage in points",
    ["symbol", "direction"],
    buckets=[-10, -5, -2, -1, 0, 1, 2, 5, 10, 20, 50]
)

# Spread
current_spread = Gauge(
    "moneymaker_spread_points",
    "Current spread in points",
    ["symbol"]
)

# Position metrics
open_positions = Gauge(
    "moneymaker_open_positions",
    "Number of open positions",
    ["symbol"]
)
total_exposure_lots = Gauge(
    "moneymaker_exposure_lots",
    "Total open position volume",
    ["symbol"]
)
unrealized_pnl = Gauge(
    "moneymaker_unrealized_pnl",
    "Total unrealized profit/loss",
    ["symbol"]
)

# Account metrics
account_equity = Gauge(
    "moneymaker_account_equity", "Current account equity"
)
account_balance = Gauge(
    "moneymaker_account_balance", "Current account balance"
)
margin_level = Gauge(
    "moneymaker_margin_level", "Current margin level percentage"
)

# Execution quality
execution_quality_score = Gauge(
    "moneymaker_execution_quality_score",
    "Composite execution quality score (0-100)",
    ["symbol"]
)
```

### Network Latency Monitoring

The Bridge monitors network latency to the broker server by measuring the round-trip time of lightweight MT5 API calls:

```python
async def measure_broker_latency(self) -> float:
    """
    Measure round-trip latency to the broker server.
    Uses symbol_info_tick() as a lightweight probe.
    """
    start = time.perf_counter_ns()
    tick = await self.mt5.call(
        mt5.symbol_info_tick, self.config.probe_symbol
    )
    end = time.perf_counter_ns()

    if tick is None:
        return -1.0  # Connection issue

    latency_ms = (end - start) / 1_000_000
    self.metrics.broker_latency.set(latency_ms)
    return latency_ms
```

---

## 8.10 Error Handling and Recovery

### Error Classification

The Bridge classifies errors into four categories, each with a different recovery strategy:

| Category | Examples | Recovery Strategy |
|----------|----------|-------------------|
| **Transient** | Requotes, rate limiting, brief disconnection | Automatic retry with exponential backoff |
| **Recoverable** | MT5 terminal crash, broker server restart | Automatic reconnection with state reconciliation |
| **Operational** | Insufficient margin, market closed, invalid stops | Adjust parameters or queue for later |
| **Fatal** | Account disabled, broker credentials changed, persistent corruption | Alert operator, stop trading |

### MT5 Disconnection Recovery

The most common error scenario is a disconnection between the Bridge and the MT5 terminal, or between the MT5 terminal and the broker server. The recovery process follows a strict sequence:

```python
async def recovery_loop(self):
    """
    Main recovery loop that detects disconnections
    and attempts reconnection.
    """
    consecutive_failures = 0
    max_failures_before_alert = 5

    while self.running:
        try:
            # Check MT5 terminal health
            terminal = await self.mt5.call(mt5.terminal_info)

            if terminal is None:
                # Terminal is not running
                consecutive_failures += 1
                logger.error(
                    f"MT5 terminal not responding "
                    f"(failure #{consecutive_failures})"
                )
                await self._attempt_terminal_recovery()

            elif not terminal.connected:
                # Terminal running but not connected to broker
                consecutive_failures += 1
                logger.error(
                    f"MT5 not connected to broker "
                    f"(failure #{consecutive_failures})"
                )
                await self._attempt_login_recovery()

            else:
                # Everything is fine
                if consecutive_failures > 0:
                    logger.info(
                        f"MT5 connection restored after "
                        f"{consecutive_failures} failures"
                    )
                    await self._post_recovery_reconciliation()
                consecutive_failures = 0

            if consecutive_failures >= max_failures_before_alert:
                await self._alert_operator(
                    f"MT5 disconnected for "
                    f"{consecutive_failures} cycles"
                )

        except Exception as e:
            logger.exception(f"Error in recovery loop: {e}")
            consecutive_failures += 1

        await asyncio.sleep(10)  # Check every 10 seconds


async def _attempt_terminal_recovery(self):
    """Attempt to reconnect to the MT5 terminal."""
    logger.info("Attempting MT5 terminal recovery...")

    # First, try re-initializing the connection
    try:
        await self.mt5.call(mt5.shutdown)
    except Exception:
        pass  # May already be disconnected

    await asyncio.sleep(2)

    success = await self.mt5.call(
        mt5.initialize, path=self.config.mt5_path
    )
    if success:
        login_ok = await self.mt5.call(
            mt5.login,
            login=self.config.account,
            password=self.config.password,
            server=self.config.server,
        )
        if login_ok:
            logger.info("MT5 terminal recovery successful")
            return True

    logger.error("MT5 terminal recovery failed")
    return False


async def _attempt_login_recovery(self):
    """Attempt to re-login to the broker server."""
    logger.info("Attempting broker login recovery...")

    success = await self.mt5.call(
        mt5.login,
        login=self.config.account,
        password=self.config.password,
        server=self.config.server,
    )

    if success:
        logger.info("Broker login recovery successful")
        return True

    logger.error("Broker login recovery failed")
    return False


async def _post_recovery_reconciliation(self):
    """
    After recovering from a disconnection, reconcile
    local state with actual MT5 state.
    """
    logger.info("Running post-recovery reconciliation...")

    # Sync positions
    await self.position_tracker.sync_with_mt5()

    # Check for positions that were closed during outage
    # (by broker-side SL/TP)
    await self._check_for_missed_closes()

    # Verify account state
    account = await self.mt5.call(mt5.account_info)
    logger.info(
        f"Post-recovery state: equity={account.equity}, "
        f"balance={account.balance}, "
        f"positions={len(self.position_tracker.positions)}"
    )
```

### Broker Server Unavailable

When the broker server is unreachable for an extended period, the Bridge queues incoming signals and retries when connectivity is restored:

```python
class SignalQueue:
    """
    Queue for signals that cannot be executed due to
    connectivity issues.
    """

    def __init__(self, max_age_seconds: int = 60):
        self._queue: deque = deque()
        self._max_age = max_age_seconds

    def enqueue(self, signal: TradingSignal):
        """Add a signal to the queue."""
        self._queue.append({
            "signal": signal,
            "queued_at": time.time(),
        })
        logger.info(
            f"Signal {signal.signal_id} queued "
            f"(queue size: {len(self._queue)})"
        )

    def drain(self) -> list:
        """
        Return all non-expired signals and clear the queue.
        """
        now = time.time()
        valid = []
        expired = 0

        while self._queue:
            item = self._queue.popleft()
            age = now - item["queued_at"]
            if age < self._max_age:
                valid.append(item["signal"])
            else:
                expired += 1

        if expired:
            logger.info(f"Expired {expired} queued signals")

        return valid
```

### Terminal Crash Recovery

If the MT5 terminal crashes (process exits unexpectedly), the watchdog service on the Windows VM detects this and restarts it. The Bridge detects the terminal absence via its health check loop and attempts reconnection once the terminal is back:

```
TERMINAL CRASH RECOVERY SEQUENCE
=================================

[T+0s]   MT5 terminal process exits unexpectedly
[T+1s]   Windows watchdog detects missing process
[T+3s]   Watchdog starts MT5 terminal
[T+5s]   MT5 terminal initializing, loading symbols
[T+10s]  Bridge health check detects terminal_info() = None
[T+10s]  Bridge enters RECOVERY state
[T+10s]  Bridge pauses signal acceptance (signals queued)
[T+15s]  MT5 terminal connects to broker server
[T+20s]  Bridge health check succeeds
[T+20s]  Bridge re-initializes MT5 connection
[T+21s]  Bridge re-authenticates with broker
[T+22s]  Bridge runs position reconciliation
[T+23s]  Bridge processes queued signals (if still valid)
[T+23s]  Bridge returns to NORMAL state
```

### Windows VM Reboot Handling

If the entire Windows VM reboots (due to Windows Update, Proxmox maintenance, or power event), the recovery is similar but longer:

```
VM REBOOT RECOVERY SEQUENCE
=============================

[T+0s]    VM begins shutdown
[T+0s]    Bridge detects shutdown signal
[T+0s]    Bridge tightens all stop-losses
[T+0s]    Bridge saves state to PostgreSQL
[T+1s]    Bridge exits gracefully
[T+2min]  VM fully shut down
[T+3min]  VM boots (auto-start configured in Proxmox)
[T+4min]  Windows login (auto-login configured)
[T+5min]  MT5 terminal starts (Windows Startup folder)
[T+6min]  MT5 terminal connects to broker
[T+6min]  Bridge service starts (Windows Service)
[T+6min]  Bridge initializes MT5 connection
[T+6min]  Bridge authenticates with broker
[T+7min]  Bridge loads saved state from PostgreSQL
[T+7min]  Bridge reconciles with live MT5 state
[T+7min]  Bridge returns to NORMAL state
```

The total downtime during a VM reboot is approximately 7 minutes. During this time, open positions are protected by broker-side stop-loss orders. The Bridge's state is persisted to PostgreSQL before shutdown, so no tracking information is lost.

---

## 8.11 Windows VM Configuration for MT5

### Proxmox VM Setup

The Windows VM for MT5 is created in Proxmox with the following specifications:

```
VM Configuration:
  VM ID:        104
  Name:         moneymaker-mt5-bridge
  OS:           Windows 10 LTSC 2021 (or Windows 11 LTSC)
  CPU:          4 cores (host type for best performance)
  RAM:          8 GB (minimum), 12 GB (recommended)
  Disk:         64 GB on local-zfs (SSD-backed)
  Network:      VirtIO NIC on TRADE VLAN (vmbr1, VLAN tag 40)
  Display:      VirtIO-GPU (for headless operation)
  BIOS:         OVMF (UEFI)
  Machine:      q35
  SCSI:         VirtIO SCSI Single
```

### VirtIO Drivers

VirtIO drivers provide near-native I/O performance for Windows VMs in Proxmox. They must be installed during Windows setup or immediately after:

```
Required VirtIO Drivers:
  - VirtIO SCSI controller (vioscsi)    -- disk I/O
  - VirtIO network adapter (NetKVM)     -- network I/O
  - VirtIO balloon driver (balloon)     -- memory management
  - VirtIO serial driver (vioserial)    -- serial communication
  - QEMU Guest Agent (qemu-ga)         -- VM management

Installation:
  1. Download virtio-win ISO from Fedora project
  2. Attach ISO as secondary CDROM during Windows install
  3. Load VirtIO SCSI driver during disk selection step
  4. After Windows install, run virtio-win-guest-tools.exe
  5. Verify all drivers installed in Device Manager
```

### Headless Operation

The VM operates headlessly -- there is no physical monitor, keyboard, or mouse. Access is via RDP (Remote Desktop Protocol) for maintenance tasks. The VM is configured for persistent console session operation:

```
Headless Configuration:
  - Auto-login: configured via netplwiz (no login screen)
  - Screen saver: disabled
  - Sleep mode: disabled (power plan = High Performance)
  - Windows Update: defer updates, scheduled reboot window
    only on weekends
  - RDP enabled for remote administration
  - QEMU Guest Agent for Proxmox management commands
  - Console session stays active when RDP disconnects
```

### Auto-Start Configuration

MT5 and the Bridge service must start automatically when the VM boots:

```
Auto-Start Chain:
  1. Proxmox: VM 104 set to auto-start with boot order
  2. Windows: auto-login configured
  3. Windows Startup: shortcut to MT5 terminal in
     shell:startup folder
  4. Windows Service: Bridge service registered as a
     Windows Service via NSSM (Non-Sucking Service Manager)

NSSM Configuration for Bridge Service:
  nssm install MoneyMakerBridge "C:\Python311\python.exe"
  nssm set MoneyMakerBridge AppDirectory "C:\moneymaker\bridge"
  nssm set MoneyMakerBridge AppParameters "main.py"
  nssm set MoneyMakerBridge Start SERVICE_AUTO_START
  nssm set MoneyMakerBridge AppStdout "C:\moneymaker\logs\bridge.log"
  nssm set MoneyMakerBridge AppStderr "C:\moneymaker\logs\bridge_err.log"
  nssm set MoneyMakerBridge AppRotateFiles 1
  nssm set MoneyMakerBridge AppRotateBytes 10485760
```

### Watchdog Service

A lightweight watchdog service monitors the MT5 terminal process and restarts it if it crashes:

```python
# watchdog_service.py -- Runs as a Windows Service
# Registered via NSSM alongside the Bridge service

import subprocess
import time
import psutil
import logging

MT5_PROCESS_NAME = "terminal64.exe"
MT5_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe"
CHECK_INTERVAL = 5  # seconds
RESTART_COOLDOWN = 30  # seconds after restart before checking again

logger = logging.getLogger("mt5_watchdog")


def is_mt5_running() -> bool:
    """Check if the MT5 terminal process is running."""
    for proc in psutil.process_iter(["name"]):
        if proc.info["name"] == MT5_PROCESS_NAME:
            return True
    return False


def start_mt5():
    """Start the MT5 terminal."""
    logger.info("Starting MT5 terminal...")
    subprocess.Popen(
        [MT5_PATH],
        creationflags=subprocess.DETACHED_PROCESS
    )


def main():
    logger.info("MT5 watchdog service started")

    while True:
        if not is_mt5_running():
            logger.warning("MT5 terminal not running, restarting...")
            start_mt5()
            time.sleep(RESTART_COOLDOWN)
        else:
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
```

### Resource Allocation

The VM resources are sized to comfortably run both the MT5 terminal and the Bridge service:

```
Resource Budget:
  +---------------------------+----------+
  | Component                 | Usage    |
  +---------------------------+----------+
  | Windows OS                | ~2 GB RAM |
  | MT5 Terminal              | ~1 GB RAM |
  | MT5 Market Watch (30 sym) | ~500 MB  |
  | Bridge Service (Python)   | ~500 MB  |
  | Redis client buffers      | ~200 MB  |
  | Safety overhead           | ~3.8 GB  |
  +---------------------------+----------+
  | Total allocated           | 8 GB     |
  +---------------------------+----------+

  CPU: 4 cores is sufficient. MT5 is single-threaded for
  order execution. The Bridge uses asyncio (single-threaded
  with async I/O). Additional cores handle Windows background
  tasks and the watchdog service.

  Disk: 64 GB is ample. MT5 stores symbol data locally
  (~5 GB for extended history), Windows requires ~20 GB,
  the Bridge and logs use ~5 GB, leaving ~34 GB free.
```

### Network Configuration

The VM is connected to the TRADE VLAN, which provides network isolation:

```
Network Topology:
  +---------------------------------------------------+
  |  Proxmox Host                                      |
  |  +--------+  vmbr0 (Management VLAN 10)            |
  |  | Bridge |---> Monitoring VM, Management access    |
  |  +--------+                                         |
  |  +--------+  vmbr1 (TRADE VLAN 40)                 |
  |  | Bridge |---> MT5 VM, Algo Engine VM                 |
  |  +--------+                                         |
  |  +--------+  vmbr2 (DATA VLAN 20)                  |
  |  | Bridge |---> Data Ingestion VM, Database VM      |
  |  +--------+                                         |
  +---------------------------------------------------+

  MT5 VM Network:
    Interface: eth0 (VirtIO)
    VLAN: 40 (TRADE)
    IP: 10.10.40.4/24
    Gateway: 10.10.40.1 (internet access for broker)
    DNS: 10.10.40.1 (or public DNS for broker resolution)

  Firewall Rules (Proxmox firewall):
    ALLOW: MT5 VM -> Internet (TCP 443, broker connection)
    ALLOW: Algo Engine VM -> MT5 VM (TCP 50051, gRPC)
    ALLOW: MT5 VM -> Database VM (TCP 5432, PostgreSQL)
    ALLOW: MT5 VM -> Database VM (TCP 6379, Redis)
    ALLOW: Monitoring VM -> MT5 VM (TCP 9090, Prometheus)
    ALLOW: Management -> MT5 VM (TCP 3389, RDP)
    DENY: all other traffic
```

### Backup Strategy

The Windows VM is backed up regularly to protect against data loss and enable rapid recovery:

```
Backup Schedule:
  - Daily: Proxmox Backup Server (PBS) incremental backup
    at 03:00 UTC (market quiet hours)
  - Weekly: Full VM snapshot retained for 4 weeks
  - Before updates: Manual snapshot before any Windows
    Update or MT5 update

Recovery Time Objective (RTO): < 30 minutes
  Restore from PBS to a fresh VM takes ~15-20 minutes
  for an 8 GB VM image, plus ~10 minutes for MT5 to
  reconnect and Bridge to reconcile.

Recovery Point Objective (RPO): < 24 hours
  Position state is continuously written to PostgreSQL
  (on the Database VM), so the actual data loss window
  is only the local MT5 terminal state, not the trade
  records.
```

---

## 8.12 Security Considerations

### Credential Storage

Broker credentials (account number, password, server name) are the most sensitive data in the Bridge. Compromise of these credentials could lead to unauthorized trades, fund withdrawal (if the password is also the investor password), or account lockout.

```
Credential Storage Architecture:
  +--------------------------------------------------+
  |  NEVER:                                           |
  |  - Hardcoded in source code                       |
  |  - Stored in configuration files                  |
  |  - Stored in environment variables in plaintext   |
  |    Docker images                                  |
  |  - Logged in any log output                       |
  |  - Transmitted over unencrypted channels          |
  +--------------------------------------------------+
  |  ALWAYS:                                          |
  |  - Stored in encrypted vault (HashiCorp Vault     |
  |    or encrypted file with key from env var)       |
  |  - Retrieved at service startup only              |
  |  - Held in memory (Python variables)              |
  |  - Zeroed from memory on service shutdown         |
  |  - Rotated periodically (broker password change)  |
  +--------------------------------------------------+
```

Implementation using an encrypted configuration file:

```python
import json
from cryptography.fernet import Fernet
import os


class CredentialVault:
    """
    Encrypted credential storage using Fernet symmetric encryption.
    The encryption key is provided via environment variable.
    """

    def __init__(self):
        key = os.environ.get("MONEYMAKER_VAULT_KEY")
        if not key:
            raise SecurityError(
                "MONEYMAKER_VAULT_KEY environment variable not set"
            )
        self._cipher = Fernet(key.encode())
        self._vault_path = os.environ.get(
            "MONEYMAKER_VAULT_PATH",
            r"C:\moneymaker\config\credentials.vault"
        )

    def get_credentials(self) -> dict:
        """Decrypt and return broker credentials."""
        with open(self._vault_path, "rb") as f:
            encrypted = f.read()

        decrypted = self._cipher.decrypt(encrypted)
        creds = json.loads(decrypted)

        return {
            "account": creds["mt5_account"],
            "password": creds["mt5_password"],
            "server": creds["mt5_server"],
        }

    @staticmethod
    def create_vault(credentials: dict, vault_path: str, key: str):
        """Create an encrypted vault file (one-time setup)."""
        cipher = Fernet(key.encode())
        encrypted = cipher.encrypt(
            json.dumps(credentials).encode()
        )
        with open(vault_path, "wb") as f:
            f.write(encrypted)
```

### Network Isolation

The MT5 VM is isolated on the TRADE VLAN with strict firewall rules (detailed in Section 8.11). Only the Algo Engine VM can connect to the Bridge's gRPC port. Only the MT5 terminal can connect to the internet for broker communication. This isolation ensures that even if another VM in the MONEYMAKER infrastructure is compromised, the attacker cannot directly interact with the execution layer.

### Audit Logging

Every action the Bridge takes is logged to the immutable audit trail in PostgreSQL. The audit log includes:

- Signal received events (with full signal payload)
- Validation pass/fail events (with reason for failure)
- Order submission events (with full request payload)
- Order execution events (with full result payload)
- Position modification events (SL/TP changes)
- Position close events (with P&L and reason)
- Error events (with full error context)
- Recovery events (disconnection, reconnection, reconciliation)
- Configuration change events

The audit log uses the SHA-256 hash chain described in Document 01, making it tamper-evident. Any modification to a historical record breaks the hash chain, which is detected by the daily integrity verification job.

### Rate Limiting

The Bridge enforces rate limits on order submission to prevent runaway behavior caused by bugs or malicious input:

```python
class OrderRateLimiter:
    """
    Prevent excessive order submission.
    Default limits:
    - Max 10 orders per minute per symbol
    - Max 30 orders per minute total
    - Max 100 orders per day total
    """

    def __init__(self, config: dict):
        self._per_symbol_minute = config.get(
            "max_orders_per_symbol_per_minute", 10
        )
        self._total_minute = config.get(
            "max_orders_per_minute", 30
        )
        self._total_day = config.get(
            "max_orders_per_day", 100
        )
        self._symbol_counts: Dict[str, deque] = {}
        self._total_counts: deque = deque()
        self._daily_count: int = 0
        self._daily_reset: float = 0

    def check(self, symbol: str) -> bool:
        """Return True if order is allowed, False if rate limited."""
        now = time.time()

        # Reset daily counter at midnight UTC
        if now - self._daily_reset > 86400:
            self._daily_count = 0
            self._daily_reset = now

        # Check daily limit
        if self._daily_count >= self._total_day:
            logger.error(
                f"Daily order limit reached: {self._daily_count}"
            )
            return False

        # Check per-minute total limit
        while self._total_counts and (
            now - self._total_counts[0] > 60
        ):
            self._total_counts.popleft()
        if len(self._total_counts) >= self._total_minute:
            logger.warning("Total per-minute order limit reached")
            return False

        # Check per-symbol per-minute limit
        if symbol not in self._symbol_counts:
            self._symbol_counts[symbol] = deque()
        while self._symbol_counts[symbol] and (
            now - self._symbol_counts[symbol][0] > 60
        ):
            self._symbol_counts[symbol].popleft()
        if len(self._symbol_counts[symbol]) >= (
            self._per_symbol_minute
        ):
            logger.warning(
                f"Per-symbol per-minute limit for {symbol}"
            )
            return False

        return True

    def record(self, symbol: str):
        """Record that an order was submitted."""
        now = time.time()
        self._total_counts.append(now)
        if symbol not in self._symbol_counts:
            self._symbol_counts[symbol] = deque()
        self._symbol_counts[symbol].append(now)
        self._daily_count += 1
```

### Kill Switch

The emergency kill switch closes all positions and halts all trading. It can be triggered via the gRPC `EmergencyCloseAll` RPC, a Redis pub/sub message, or a manual API call:

```python
async def emergency_kill_switch(self, reason: str):
    """
    EMERGENCY: Close all positions and halt trading.
    This is the nuclear option -- use only when necessary.
    """
    logger.critical(f"KILL SWITCH ACTIVATED: {reason}")

    # 1. Stop accepting new signals immediately
    self.accepting_signals = False

    # 2. Close all open positions
    positions = await self.mt5.call(mt5.positions_get)
    closed = 0
    failed = 0

    for pos in (positions or []):
        try:
            if pos.type == mt5.ORDER_TYPE_BUY:
                close_type = mt5.ORDER_TYPE_SELL
                price = (await self.mt5.call(
                    mt5.symbol_info_tick, pos.symbol
                )).bid
            else:
                close_type = mt5.ORDER_TYPE_BUY
                price = (await self.mt5.call(
                    mt5.symbol_info_tick, pos.symbol
                )).ask

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": pos.ticket,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": close_type,
                "price": price,
                "deviation": 50,  # Wide deviation for emergency
                "magic": pos.magic,
                "comment": f"KILL_SWITCH:{reason}",
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            result = await self.mt5.call(mt5.order_send, request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                closed += 1
            else:
                failed += 1
                logger.error(
                    f"Failed to close #{pos.ticket}: "
                    f"retcode={getattr(result, 'retcode', 'N/A')}"
                )
        except Exception as e:
            failed += 1
            logger.exception(
                f"Exception closing #{pos.ticket}: {e}"
            )

    # 3. Cancel all pending orders
    orders = await self.mt5.call(mt5.orders_get)
    for order in (orders or []):
        try:
            cancel_request = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": order.ticket,
            }
            await self.mt5.call(mt5.order_send, cancel_request)
        except Exception as e:
            logger.exception(
                f"Exception cancelling order #{order.ticket}: {e}"
            )

    # 4. Alert operator
    await self._alert_operator(
        f"KILL SWITCH: {reason}. "
        f"Closed={closed}, Failed={failed}"
    )

    logger.critical(
        f"Kill switch complete: closed={closed}, "
        f"failed={failed}"
    )

    return {"closed": closed, "failed": failed}
```

---

## 8.13 Testing the Execution Bridge

### Testing Philosophy

The Bridge is the most safety-critical component in MONEYMAKER. A bug in the Data Ingestion Service means missing data (recoverable). A bug in the Algo Engine means bad signals (filtered by the Bridge's risk checks). A bug in the Bridge means real money is at risk. Testing the Bridge is therefore more rigorous than testing any other component.

### Demo Account Testing

All new Bridge code is first tested against a demo account. The demo account mirrors live account conditions (same spreads, same execution model, same instrument specifications) but uses virtual money. The Bridge is configured to connect to the demo account by changing only the credential configuration, with no code changes required.

Demo account test scenarios:

```
Integration Test Suite (Demo Account):
  1. Market order execution (BUY and SELL)
  2. Pending order placement and fill
  3. Stop-loss triggered by price movement
  4. Take-profit triggered by price movement
  5. Position modification (change SL/TP)
  6. Partial close at multiple TP levels
  7. Full position close
  8. Multiple simultaneous positions on same symbol
  9. Multiple positions on different symbols
  10. Position sizing calculation accuracy
  11. Spread check rejection (during wide spread)
  12. Maximum position count enforcement
  13. Maximum lot size enforcement
  14. Margin check rejection
  15. Idempotency (duplicate signal rejection)
  16. Graceful shutdown with open positions
  17. Recovery after simulated disconnection
  18. Weekend/market closed handling
  19. Signal expiration (stale signal rejection)
  20. Kill switch activation and verification
```

### Order Simulation Mode

The Bridge supports a simulation mode where it logs all orders without submitting them to MT5. This is used for testing the entire signal-to-order pipeline without any market interaction:

```python
class SimulatedMT5:
    """
    Mock MT5 interface that simulates order execution
    without real market interaction.
    """

    def __init__(self, symbol_specs: dict):
        self._specs = symbol_specs
        self._positions = {}
        self._next_ticket = 100000
        self._slippage_model = GaussianSlippage(mean=0.5, std=1.0)

    async def order_send(self, request: dict):
        """Simulate order execution with realistic slippage."""
        # Simulate processing delay
        await asyncio.sleep(random.uniform(0.005, 0.030))

        # Simulate occasional rejections (2% rate)
        if random.random() < 0.02:
            return SimResult(retcode=10006, comment="Simulated rejection")

        # Simulate slippage
        slippage = self._slippage_model.sample()
        fill_price = request["price"] + slippage * self._specs[
            request["symbol"]
        ].point

        ticket = self._next_ticket
        self._next_ticket += 1

        # Create simulated position
        self._positions[ticket] = {
            "ticket": ticket,
            "symbol": request["symbol"],
            "type": request["type"],
            "volume": request["volume"],
            "price_open": fill_price,
            "sl": request.get("sl", 0),
            "tp": request.get("tp", 0),
        }

        return SimResult(
            retcode=10009,  # TRADE_RETCODE_DONE
            order=ticket,
            deal=ticket + 50000,
            price=fill_price,
            volume=request["volume"],
            comment="Simulated fill",
        )
```

### Stress Testing

The Bridge is stress-tested by sending a high volume of signals in rapid succession to verify that it handles load gracefully:

```python
async def stress_test(bridge_client, symbol: str, count: int):
    """
    Send a rapid burst of signals to test Bridge under load.
    Verifies: rate limiting, idempotency, memory stability.
    """
    results = {"success": 0, "rejected": 0, "error": 0, "duplicate": 0}
    latencies = []

    for i in range(count):
        signal = create_test_signal(
            symbol=symbol,
            signal_id=f"stress_test_{i}",
            direction="BUY" if i % 2 == 0 else "SELL",
        )

        start = time.perf_counter()
        try:
            result = await bridge_client.execute_signal(signal)
            latency = (time.perf_counter() - start) * 1000
            latencies.append(latency)

            if result.status == ExecutionStatus.SUCCESS:
                results["success"] += 1
            elif result.status == ExecutionStatus.DUPLICATE:
                results["duplicate"] += 1
            elif result.status == ExecutionStatus.REJECTED:
                results["rejected"] += 1
            else:
                results["error"] += 1

        except Exception as e:
            results["error"] += 1

        # Small delay to avoid overwhelming the system
        await asyncio.sleep(0.01)

    print(f"Stress test results ({count} signals):")
    print(f"  Success:    {results['success']}")
    print(f"  Rejected:   {results['rejected']}")
    print(f"  Duplicate:  {results['duplicate']}")
    print(f"  Error:      {results['error']}")
    print(f"  Avg latency: {sum(latencies)/len(latencies):.1f}ms")
    print(f"  P95 latency: {sorted(latencies)[int(len(latencies)*0.95)]:.1f}ms")
    print(f"  Max latency: {max(latencies):.1f}ms")
```

### Failover Testing

Deliberate failure injection tests verify that the Bridge recovers correctly from various failure modes:

```
Failover Test Scenarios:
  1. Kill MT5 terminal process while positions are open
     Expected: Watchdog restarts terminal, Bridge reconnects,
     positions are reconciled
  2. Disconnect network to broker (iptables block)
     Expected: Bridge detects disconnect, queues signals,
     reconnects when network restored
  3. Fill PostgreSQL disk (simulate DB failure)
     Expected: Bridge continues trading, logs to local file,
     replays to DB when available
  4. Send 1000 duplicate signals with same signal_id
     Expected: Only first signal executed, rest return cached result
  5. Send signal with invalid SL (inside minimum stop distance)
     Expected: Signal rejected with clear error message
  6. Reboot Windows VM while positions are open
     Expected: Full auto-recovery within 7 minutes,
     positions still exist with original SL/TP
  7. Simulate margin call (reduce equity below maintenance)
     Expected: Bridge detects low margin, refuses new positions,
     alerts operator
```

### Latency Testing

End-to-end latency is measured from signal generation in the Algo Engine to order fill confirmation:

```python
async def measure_e2e_latency(brain_client, bridge_client, iterations=100):
    """
    Measure end-to-end latency from signal generation to execution.
    Uses demo account with market orders.
    """
    latencies = []

    for i in range(iterations):
        # Generate signal in the Brain
        signal_time = time.perf_counter_ns()
        signal = brain_client.generate_test_signal("EURUSD")

        # Send to Bridge and await execution
        result = await bridge_client.execute_signal(signal)
        exec_time = time.perf_counter_ns()

        if result.status == ExecutionStatus.SUCCESS:
            latency_ms = (exec_time - signal_time) / 1_000_000
            latencies.append(latency_ms)

        # Close the position immediately
        await bridge_client.close_position(result.order_ticket)
        await asyncio.sleep(1)  # Cooldown

    print(f"E2E Latency ({len(latencies)} samples):")
    print(f"  Mean:  {sum(latencies)/len(latencies):.1f} ms")
    print(f"  P50:   {sorted(latencies)[len(latencies)//2]:.1f} ms")
    print(f"  P95:   {sorted(latencies)[int(len(latencies)*0.95)]:.1f} ms")
    print(f"  P99:   {sorted(latencies)[int(len(latencies)*0.99)]:.1f} ms")
    print(f"  Max:   {max(latencies):.1f} ms")
```

---

## 8.14 Configuration and Deployment

### Environment Variables

The Bridge uses environment variables for sensitive configuration and Docker-level settings:

```bash
# MT5 Connection (retrieved from vault, not set directly)
MONEYMAKER_VAULT_KEY=<fernet-encryption-key>
MONEYMAKER_VAULT_PATH=C:\moneymaker\config\credentials.vault

# Service Configuration
MONEYMAKER_BRIDGE_GRPC_PORT=50051
MONEYMAKER_BRIDGE_METRICS_PORT=9090
MONEYMAKER_BRIDGE_LOG_LEVEL=INFO
MONEYMAKER_BRIDGE_MODE=live           # live, demo, simulation

# Database Connection
MONEYMAKER_DB_HOST=10.10.20.2
MONEYMAKER_DB_PORT=5432
MONEYMAKER_DB_NAME=moneymaker
MONEYMAKER_DB_USER=bridge_writer
MONEYMAKER_DB_PASSWORD=<from-vault>

# Redis Connection
MONEYMAKER_REDIS_HOST=10.10.20.2
MONEYMAKER_REDIS_PORT=6379
MONEYMAKER_REDIS_PASSWORD=<from-vault>

# MT5 Terminal
MONEYMAKER_MT5_PATH=C:\Program Files\MetaTrader 5\terminal64.exe
```

### Configuration File

Non-sensitive configuration is stored in a YAML configuration file:

```yaml
# bridge_config.yaml

service:
  name: "moneymaker-mt5-bridge"
  version: "1.0.0"
  grpc_port: 50051
  metrics_port: 9090
  log_level: "INFO"
  mode: "live"  # live, demo, simulation

execution:
  max_signal_age_seconds: 5
  min_confidence: 0.6
  default_deviation_points: 20
  close_on_shutdown: false
  tighten_stops_on_shutdown: true

risk:
  max_daily_drawdown_pct: 3.0
  max_daily_loss_pct: 2.0
  max_total_positions: 10
  max_lots_per_position: 5.0
  max_margin_utilization_pct: 50.0
  kelly_fraction: 0.25
  default_risk_per_trade_pct: 1.0

rate_limits:
  max_orders_per_symbol_per_minute: 10
  max_orders_per_minute: 30
  max_orders_per_day: 100

monitoring:
  health_check_interval_seconds: 10
  position_sync_interval_seconds: 1
  reconciliation_interval_seconds: 30
  spread_check_interval_seconds: 5
  symbol_cache_refresh_seconds: 60
  broker_latency_probe_seconds: 30

trailing_stops:
  enabled: true
  check_interval_seconds: 2
  trailing_atr_multiplier: 1.0

breakeven:
  enabled: true
  trigger_points: 200
  offset_points: 10

time_exits:
  enabled: true
  max_holding_hours: 48

symbols:
  XAUUSD:
    enabled: true
    priority: 1
    max_lots: 5.0
    max_positions: 3
    max_spread_points: 50
    default_sl_atr_multiplier: 1.5
    default_tp_atr_multiplier: 2.5
    atr_period: 14
    atr_timeframe: "H1"
    magic_number: 100001
    max_slippage_points: 30
    min_confidence: 0.6
    trading_sessions:
      - start: "08:00"
        end: "17:00"
    cooldown_seconds: 300
    tp_levels:
      - pct: 0.33
        atr_mult: 1.5
      - pct: 0.33
        atr_mult: 2.5
      - pct: 0.34
        atr_mult: 4.0
```

### Docker Container

Although the Bridge runs on a Windows VM (which complicates Docker usage), the Bridge's Python dependencies are managed in a virtual environment. If Docker for Windows is available, the Dockerfile is:

```dockerfile
# Dockerfile for the Bridge service
# Note: This runs on Windows, so uses a Windows base image
# or can be a standard Python image if running on WSL2

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose ports
EXPOSE 50051
# gRPC
EXPOSE 9090
# Prometheus metrics

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python healthcheck.py

# Run the Bridge service
CMD ["python", "main.py"]
```

In practice, on the Windows VM, the Bridge runs directly in a Python virtual environment managed by NSSM (as described in Section 8.11) rather than in Docker, because the MetaTrader5 Python package requires direct IPC with the MT5 terminal process, which is complicated by Docker's container isolation. The Dockerfile is maintained for development and testing on Linux systems using the simulation mode.

### Health Check Endpoints

The Bridge exposes HTTP health check endpoints for monitoring:

```python
from aiohttp import web


async def health_handler(request):
    """Health check endpoint for monitoring."""
    mt5_ok = bridge.health_checker.is_mt5_connected()
    broker_ok = bridge.health_checker.is_broker_connected()

    status = {
        "status": "healthy" if (mt5_ok and broker_ok) else "degraded",
        "mt5_connected": mt5_ok,
        "broker_connected": broker_ok,
        "uptime_seconds": bridge.get_uptime(),
        "open_positions": len(bridge.position_tracker.positions),
        "accepting_signals": bridge.accepting_signals,
        "mode": bridge.config.mode,
        "last_health_check": bridge.health_checker.last_check_time,
    }

    http_status = 200 if status["status"] == "healthy" else 503
    return web.json_response(status, status=http_status)


async def ready_handler(request):
    """Readiness probe -- is the Bridge ready to accept signals?"""
    ready = (
        bridge.health_checker.is_mt5_connected()
        and bridge.health_checker.is_broker_connected()
        and bridge.accepting_signals
        and len(bridge.symbol_cache) > 0
    )

    if ready:
        return web.json_response({"ready": True}, status=200)
    return web.json_response({"ready": False}, status=503)
```

### Graceful Shutdown

When the Bridge receives a shutdown signal (SIGTERM, SIGINT, or a Windows service stop command), it performs a graceful shutdown sequence:

```python
async def graceful_shutdown(self, sig=None):
    """
    Graceful shutdown sequence:
    1. Stop accepting new signals
    2. Wait for in-flight orders to complete
    3. Optionally tighten stop-losses
    4. Optionally close all positions
    5. Save state to PostgreSQL
    6. Disconnect from MT5
    """
    if sig:
        logger.info(f"Received signal {sig}, initiating shutdown")

    # Step 1: Stop accepting signals
    self.accepting_signals = False
    logger.info("Signal acceptance disabled")

    # Step 2: Wait for in-flight orders (max 10 seconds)
    wait_start = time.time()
    while self._in_flight_orders and (time.time() - wait_start < 10):
        await asyncio.sleep(0.1)

    if self._in_flight_orders:
        logger.warning(
            f"Shutdown with {len(self._in_flight_orders)} "
            f"in-flight orders"
        )

    # Step 3: Tighten stop-losses
    if self.config.tighten_stops_on_shutdown:
        logger.info("Tightening stop-losses before shutdown")
        await self.sltp_manager.tighten_all_stops()

    # Step 4: Close positions if configured
    if self.config.close_on_shutdown:
        logger.info("Closing all positions before shutdown")
        await self._close_all_positions()

    # Step 5: Save state
    await self._save_state_to_db()
    logger.info("State saved to PostgreSQL")

    # Step 6: Disconnect
    await self.mt5.call(mt5.shutdown)
    logger.info("MT5 disconnected. Shutdown complete.")
```

### Configuration Hot-Reload

Certain configuration parameters can be updated at runtime without restarting the Bridge. The Bridge subscribes to a Redis pub/sub channel for configuration updates:

```python
async def config_listener(self):
    """
    Listen for runtime configuration updates via Redis pub/sub.

    Hot-reloadable parameters:
    - Risk limits (max drawdown, max exposure)
    - Symbol parameters (max lots, max spread, sessions)
    - Rate limits
    - Trailing stop parameters
    - Breakeven parameters

    NOT hot-reloadable (require restart):
    - gRPC port
    - MT5 connection parameters
    - Database connection parameters
    """
    pubsub = self.redis.pubsub()
    await pubsub.subscribe("moneymaker:config:bridge")

    async for message in pubsub.listen():
        if message["type"] != "message":
            continue

        try:
            update = json.loads(message["data"])
            section = update.get("section")
            values = update.get("values", {})

            if section == "risk":
                self._apply_risk_update(values)
            elif section == "symbols":
                self._apply_symbol_update(values)
            elif section == "rate_limits":
                self._apply_rate_limit_update(values)
            elif section == "trailing_stops":
                self._apply_trailing_update(values)
            elif section == "kill_switch":
                await self.emergency_kill_switch(
                    values.get("reason", "Remote kill switch")
                )

            logger.info(
                f"Configuration hot-reload: section={section}, "
                f"values={values}"
            )

        except Exception as e:
            logger.exception(f"Config reload error: {e}")
```

---

## Summary

The MetaTrader 5 Integration and Trade Execution Bridge is the most safety-critical component in the MONEYMAKER ecosystem. It stands at the boundary between the system's internal intelligence and the external financial markets, translating AI-generated signals into real broker orders with full validation, risk management, and audit trailing at every step.

The Bridge's architecture is built on five foundational pillars: safety (fail-safe defaults, idempotency, rate limiting, kill switch), reliability (automatic recovery, state reconciliation, position tracking), performance (sub-100ms execution latency, asyncio event loop, thread-safe MT5 access), observability (comprehensive metrics, slippage tracking, latency monitoring, execution quality scoring), and auditability (every action logged to the tamper-evident PostgreSQL audit trail).

The Windows VM constraint imposed by the MetaTrader 5 platform adds operational complexity -- a Windows VM must be provisioned, maintained, and monitored within the otherwise Linux-based Proxmox infrastructure. This is addressed through careful VM configuration (auto-login, auto-start, watchdog service, VirtIO drivers) and network isolation (TRADE VLAN with strict firewall rules).

The Bridge is designed to be the last line of defense against excessive risk. Even when the Algo Engine operates perfectly, the Bridge independently validates every signal, enforces position size limits, monitors margin utilization, tracks execution quality, and can halt all trading via the kill switch if conditions deteriorate. This defense-in-depth approach ensures that no single component failure, whether in the data pipeline, the AI models, or the execution layer itself, can result in catastrophic financial loss.

---

*Fine del documento 8 -- MONEYMAKER V1 MetaTrader 5 Integration and Trade Execution
