# MONEYMAKER Console (TUI/CLI)

The **MONEYMAKER Console** is the centralized control station for the entire trading ecosystem. It provides both an interactive TUI (Text User Interface) for manual management and a direct CLI (Command Line Interface) for scripting and automation.

---

## 🏗️ How It Works: The Control Hub

The Console communicates with all MONEYMAKER services via standard protocols:
- **Redis**: For real-time state, health checks, and global kill-switches.
- **SQL (Postgres)**: For querying historical data, signals, and audits.
- **ZMQ/gRPC**: For sending direct control commands to the Brain or Data Ingestion services.

---

## 📂 Command Structure

The Console is organized into 15 logical categories, covering every aspect of the MONEYMAKER operation:

### 🎮 Primary Controls
- `brain`: Start/stop the Algo Engine, pause signal generation, or view model confidence.
- `data`: Manage the market data feed, add symbols, or trigger backfills.
- `mt5`: Direct connection to MetaTrader 5, position management, and historical logs.
- `svc`: High-level lifecycle management for Docker-based services.

### 🛡️ Risk & Security
- `risk`: Monitor real-time drawdown, manage position limits, and toggle the **Global Kill-Switch**.
- `audit`: Review system security audits and integrity checks.

### 📊 Analysis & Monitoring
- `market`: Real-time view of market regimes, economic calendars, and spreads.
- `signal`: Review the latest generated signals and their validation reasoning.
- `sys`: Comprehensive system overview (CPU, RAM, DB connectivity).

### 🔧 Maintenance & Build
- `maint`: Database maintenance (VACUUM, Reindex, Cache Pruning).
- `build`: Build individual or all Docker containers.
- `test`: Execute the full test suite (E2E, Unit, and Brain Verification).

---

## 🚀 Operational Guide

### 1. Launching the Console
The console requires a Python environment with the `python-common` shared library installed.

```bash
# Interactive TUI Mode
python moneymaker_console.py

# Direct CLI Command
python moneymaker_console.py brain status
python moneymaker_console.py mt5 close-all
```

### 2. Common Workflows
- **Daily Check**: `sys status` -> `brain status` -> `mt5 positions`.
- **Emergency Stop**: `risk kill-switch`.
- **Symbol Expansion**: `data add XAU/USD` -> `data status`.
- **System Maintenance**: `maint prune-old` -> `maint reindex`.

---

## 🛠️ Troubleshooting

### 🔴 Problem: "Console cannot connect to Redis"
- **Cause**: Redis container is down or `REDIS_URL` in `.env` is incorrect.
- **Solution**: 
  1. Verify Redis is running: `docker ps`.
  2. Check connectivity: `redis-cli ping`.
  3. Ensure `.env` is correctly loaded.

### 🔴 Problem: "Brain commands have no effect"
- **Cause**: The `algo-engine` service is either not running or the control socket is blocked.
- **Solution**: 
  1. Run `svc status` to verify all services are UP.
  2. Restart the brain: `svc restart brain`.
  3. Check `algo-engine` logs for control command receipt.

### 🔴 Problem: "MT5 Positions differ from Broker"
- **Cause**: Position tracking sync lag or manual trades were made directly in the MT5 terminal.
- **Solution**: 
  1. Use `mt5 sync` (if available) or restart the `mt5-bridge`.
  2. Avoid manual trades outside of the MONEYMAKER pipeline to ensure ledger integrity.

---

## ⚙️ Configuration & Environment

The Console relies on the global `.env` file in the project root. Ensure the following are set for full functionality:
- `MONEYMAKER_DB_URL`: Postgres connection string.
- `REDIS_URL`: Redis connection string.
- `MONEYMAKER_ENV`: Set to `production` or `development`.
- `GRAFANA_URL`: (Optional) For deep links to dashboards.
