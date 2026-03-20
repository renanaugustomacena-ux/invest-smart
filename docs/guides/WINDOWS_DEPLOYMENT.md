# MONEYMAKER — Windows Deployment Guide

Deploy the MONEYMAKER trading system on Windows for live MT5 trading.

## Architecture Overview

The recommended deployment is **hybrid**: Linux (Docker) hosts the data pipeline and algo-engine, while Windows runs the MT5 bridge natively alongside the MetaTrader 5 terminal.

```
┌─────────────── Linux / Docker ───────────────┐     ┌──────── Windows ────────┐
│  data-ingestion ──ZMQ──► algo-engine         │     │  mt5-bridge (native)    │
│       │                      │               │     │       │                 │
│  PostgreSQL  Redis  Prometheus  Grafana      │     │  MetaTrader 5 Terminal  │
│                          gRPC :50057 ────────┼─────┼──► gRPC :50055         │
└──────────────────────────────────────────────┘     └─────────────────────────┘
```

**Alternative**: Run everything on Windows using Docker Desktop + native mt5-bridge.

---

## Prerequisites

| Component | Version | Notes |
|-----------|---------|-------|
| Python | >= 3.11 | [python.org](https://python.org) — check "Add to PATH" during install |
| Git | Latest | [git-scm.com](https://git-scm.com) |
| MetaTrader 5 | Latest | From your broker, or [metatrader5.com](https://www.metatrader5.com) |
| Docker Desktop | Latest | Only for hybrid/full-Docker deployment |

Verify installations:

```powershell
python --version    # Python 3.11.x or 3.12.x
git --version       # git version 2.x
```

---

## Step 1: Clone the Repository

```powershell
git clone https://github.com/renanaugustomacena-ux/invest-smart.git
cd invest-smart
```

---

## Step 2: Set Up Python Virtual Environment

Use the included PowerShell script:

```powershell
# Allow script execution (one-time)
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# Run setup
.\setup-venv.ps1
```

This script:
1. Verifies Python 3.11+
2. Creates `.venv` virtual environment
3. Installs all dependencies
4. Installs local packages in editable mode (moneymaker-common, moneymaker-proto, algo-engine, mt5-bridge, console, dashboard)
5. Verifies MetaTrader 5 is installed
6. Creates `.env` from `.env.example`

**Manual alternative:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -e program\shared\python-common
pip install -e program\shared\proto
pip install -e program\services\mt5-bridge
pip install -e program\services\console
```

---

## Step 3: Configure Environment

```powershell
Copy-Item program\.env.example program\.env
notepad program\.env
```

**Required variables for live trading:**

| Variable | Description | Example |
|----------|-------------|---------|
| `MONEYMAKER_DB_PASSWORD` | PostgreSQL password | `openssl rand -base64 24` |
| `MONEYMAKER_REDIS_PASSWORD` | Redis password | `openssl rand -base64 24` |
| `MT5_ACCOUNT` | MT5 account number | `12345678` |
| `MT5_PASSWORD` | MT5 account password | Your broker password |
| `MT5_SERVER` | MT5 server name | `ICMarkets-Demo` |
| `POLYGON_API_KEY` | Required for Forex | From [polygon.io](https://polygon.io) |

**For crypto (Binance), `POLYGON_API_KEY` is not required.** Set `MONEYMAKER_DATA_CONNECTOR=binance`.

---

## Step 4: Configure MetaTrader 5

1. **Open MetaTrader 5** and log in to your account
2. **Enable Algo Trading**: Tools → Options → Expert Advisors → check "Allow algorithmic trading"
3. **Allow DLL imports**: Same page → check "Allow DLL imports"
4. **Keep MT5 running** — the mt5-bridge connects to the running terminal

Verify the connection:

```powershell
.\.venv\Scripts\Activate.ps1
python -c "import MetaTrader5 as mt5; mt5.initialize(); print(mt5.terminal_info()); mt5.shutdown()"
```

---

## Step 5: Start the Pipeline

### Option A: Hybrid Deployment (Recommended)

**Linux/Docker side** — start infrastructure + data pipeline:

```bash
cd program/infra/docker
docker compose up -d postgres redis data-ingestion algo-engine prometheus grafana alertmanager
```

**Windows side** — start mt5-bridge natively:

```powershell
.\.venv\Scripts\Activate.ps1
cd program\services\mt5-bridge
python -m mt5_bridge.main
```

### Option B: Full Windows (Docker Desktop)

```powershell
cd program\infra\docker
docker compose up -d postgres redis data-ingestion algo-engine prometheus grafana alertmanager

# MT5 bridge must still run natively (needs MT5 terminal access)
.\.venv\Scripts\Activate.ps1
cd program\services\mt5-bridge
python -m mt5_bridge.main
```

---

## Network Configuration

### Port Reference

| Service | Port | Protocol | Direction |
|---------|------|----------|-----------|
| PostgreSQL | 5432 | TCP | Internal |
| Redis | 6379 | TCP | Internal |
| ZeroMQ (data feed) | 5555 | TCP | data-ingestion → algo-engine |
| gRPC (algo → mt5) | 50055 | TCP | algo-engine → mt5-bridge |
| gRPC (algo API) | 50057 | TCP | Internal |
| Dashboard | 8888 | HTTP | Browser |
| Grafana | 3000 | HTTP | Browser |
| Prometheus | 9091 | HTTP | Internal |

### Cross-Machine Configuration

If algo-engine runs on Linux and mt5-bridge on Windows:

1. **Linux**: Ensure gRPC port 50057 is accessible from Windows (check firewall)
2. **Windows .env**: Set `ALGO_GRPC_HOST=<linux-ip-address>`
3. **Windows firewall**: Allow inbound on port 50055 (mt5-bridge gRPC server)

```powershell
# Allow mt5-bridge gRPC through Windows Firewall
New-NetFirewallRule -DisplayName "MONEYMAKER mt5-bridge gRPC" -Direction Inbound -LocalPort 50055 -Protocol TCP -Action Allow
```

---

## Using the Console

The MONEYMAKER console provides a unified command center:

```powershell
.\.venv\Scripts\Activate.ps1
moneymaker
```

Available commands: service status, alert testing, health checks, diagnostics.

---

## Troubleshooting

### Execution Policy Error

```
File .\setup-venv.ps1 cannot be loaded because running scripts is disabled
```

**Fix:**
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### MetaTrader 5 Not Found

```
MetaTrader5 package not installed or MT5 terminal not found
```

**Fix:**
1. Ensure MT5 is installed and has been opened at least once
2. Install the Python package: `pip install MetaTrader5`
3. MT5 must be the 64-bit version matching your Python architecture

### MT5 Connection Timeout

```
MT5 initialize() failed — timeout
```

**Fix:**
1. Ensure MetaTrader 5 terminal is **running and logged in**
2. Check `MT5_TIMEOUT_MS` in `.env` (default: 10000ms, increase if slow)
3. Verify account credentials: `MT5_ACCOUNT`, `MT5_PASSWORD`, `MT5_SERVER`

### gRPC Connection Refused

```
algo-engine cannot reach mt5-bridge on port 50055
```

**Fix:**
1. Verify mt5-bridge is running: check console output for "gRPC server listening on :50055"
2. Check Windows Firewall allows port 50055
3. If cross-machine: verify network reachability with `Test-NetConnection <ip> -Port 50055`

### Docker Desktop Issues

```
Cannot connect to the Docker daemon
```

**Fix:**
1. Start Docker Desktop application
2. Wait for "Docker Desktop is running" status
3. In Docker Desktop settings: enable WSL 2 backend for best performance

### Database Connection from Windows

If running PostgreSQL in Docker on Linux:

```powershell
# Test connectivity
Test-NetConnection <linux-ip> -Port 5432
```

Ensure Docker exposes port 5432 on the host network (check `docker-compose.yml` ports section).

---

## Health Verification

After starting all services, verify the pipeline:

```powershell
# Check mt5-bridge health
curl http://localhost:9094/metrics

# Check dashboard
Start-Process http://localhost:8888

# Check Grafana
Start-Process http://localhost:3000
```

From the console:

```powershell
moneymaker
# Then use: status, health, diagnostics commands
```

---

## Updating

```powershell
git pull origin main
.\.venv\Scripts\Activate.ps1
pip install -e program\shared\python-common
pip install -e program\shared\proto
pip install -e program\services\mt5-bridge
pip install -e program\services\console
```

If Docker services were updated:

```bash
cd program/infra/docker
docker compose pull
docker compose up -d --build
```
