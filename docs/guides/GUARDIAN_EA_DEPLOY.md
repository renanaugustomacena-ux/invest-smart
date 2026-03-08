# MoneyMakerGuardian EA — Deployment & Usage Guide

## Overview

The MoneyMakerGuardian EA is an MQL5 Expert Advisor that runs **natively inside MetaTrader 5** as an independent safety net for MONEYMAKER positions. It does **not** place trades — it only monitors and protects existing positions when the Python bridge (mt5-bridge service) is offline or crashes.

---

## Architecture

```
Algo Engine → gRPC → MT5 Bridge (Python) → mt5.order_send() → MT5 Terminal
                                                                ↑
                                                    MoneyMakerGuardian EA (MQL5)
                                                    - Reads MONEYMAKER_HEARTBEAT
                                                    - Emergency trailing stops
                                                    - Drawdown / daily loss kill
                                                    - Friday session close
```

The Python bridge writes a heartbeat timestamp to MT5's `GlobalVariable` every 5 seconds. The Guardian EA reads it. If the heartbeat goes stale (>30 seconds), the EA enters **defensive mode** and takes over position management.

---

## Prerequisites

- MetaTrader 5 terminal installed and running
- MetaEditor (bundled with MT5) for compiling the EA
- "Allow Algo Trading" enabled in MT5 (Tools → Options → Expert Advisors)

---

## Installation

### Step 1: Locate the MQL5 Experts folder

In MetaTrader 5:
1. Open MetaEditor (press F4 or click the IDE icon)
2. In the Navigator panel, right-click on **Expert Advisors**
3. Select **Open Folder** — this opens `MQL5/Experts/`

Alternatively, navigate manually:
- **Windows**: `C:\Users\<username>\AppData\Roaming\MetaQuotes\Terminal\<instance_id>\MQL5\Experts\`
- **Wine/Linux**: `~/.wine/drive_c/users/<username>/AppData/Roaming/MetaQuotes/Terminal/<instance_id>/MQL5/Experts/`

### Step 2: Copy the EA source file

Copy `MoneyMakerGuardian.mq5` from this repository:

```
program/mql5/MoneyMakerGuardian.mq5
```

into the `MQL5/Experts/` folder.

### Step 3: Compile

Option A — **MetaEditor**:
1. Open MetaEditor (F4 from MT5)
2. Open `MoneyMakerGuardian.mq5`
3. Press F7 (Compile)
4. Verify "0 errors" in the output panel

Option B — **Command line** (Wine/Linux):
```bash
wine "C:/Program Files/MetaTrader 5/metaeditor64.exe" /compile:"MQL5/Experts/MoneyMakerGuardian.mq5"
```

### Step 4: Attach to a chart

1. In MT5, open the **Navigator** panel (Ctrl+N)
2. Expand **Expert Advisors**
3. Drag **MoneyMakerGuardian** onto any chart (e.g., EURUSD M1)
4. In the dialog that appears:
   - **Common tab**: Check "Allow Algo Trading"
   - **Inputs tab**: Review and adjust parameters (see below)
5. Click OK

The EA will display a status box on the chart showing its current mode.

---

## Input Parameters

| Parameter | Default | Description |
|---|---|---|
| `InpHeartbeatTimeoutSec` | 30 | Seconds without heartbeat before entering defensive mode |
| `InpHeartbeatGlobalVar` | `MONEYMAKER_HEARTBEAT` | MT5 GlobalVariable name (must match Python bridge) |
| `InpMagicNumber` | 123456 | MONEYMAKER magic number — only manages positions with this magic |
| `InpEmergencyTrailEnabled` | true | Enable emergency trailing stop when bridge is offline |
| `InpTrailActivationPips` | 30.0 | Pips in profit before trailing activates |
| `InpTrailDistancePips` | 50.0 | Trailing stop distance from current price |
| `InpDrawdownKillEnabled` | true | Enable hard drawdown kill (independent of Redis/Python) |
| `InpMaxDrawdownPct` | 10.0 | Max drawdown % from peak equity → close ALL positions |
| `InpMaxDailyLossPct` | 2.0 | Max daily loss % from session start → close ALL positions |
| `InpFridayCloseEnabled` | true | Auto-close all positions before weekend |
| `InpFridayCloseHour` | 21 | Hour (server time) to close on Friday |
| `InpFridayCloseMinute` | 0 | Minute to close on Friday |
| `InpCheckIntervalSec` | 3 | How often the EA checks (seconds) |
| `InpLogFileName` | `MoneyMakerGuardian.log` | Log file name (in MT5's Files directory) |

> **Important**: The trailing stop parameters (30/50 pips) match the Python bridge defaults in `position_tracker.py`. If you change them in the bridge config, update the EA inputs to match.

---

## Operating Modes

### MONITORING (normal)
- Bridge heartbeat is fresh (<30 seconds old)
- EA watches but does **not** intervene with trailing stops
- Drawdown kill and Friday close are **always active** regardless of mode

### DEFENSIVE (bridge offline)
- Heartbeat is stale (>30 seconds) or GlobalVariable not found
- EA takes over trailing stop management for all MONEYMAKER positions
- Displayed as `!! DEFENSIVE !!` on the chart

### KILL FIRED (emergency)
- Drawdown or daily loss limit was breached
- All MONEYMAKER positions have been closed
- All pending MONEYMAKER orders have been cancelled
- EA remains in this state for the rest of the session

---

## Chart Display

When attached, the EA shows a live status box on the chart:

```
╔══════════════════════════════════╗
║     MONEYMAKER GUARDIAN EA v1.00     ║
╠══════════════════════════════════╣
║ Mode:        MONITORING           ║
║ Heartbeat:   3s ago               ║
║ Positions:   2                    ║
║ Equity:      10250.00             ║
║ Peak Equity: 10300.00             ║
║ Drawdown:    0.49%                ║
║ Day PnL:     -50.00               ║
╚══════════════════════════════════╝
```

---

## Logging

All defensive actions are logged to two locations:

1. **MT5 Experts tab** — visible in MT5 under View → Toolbox → Experts
2. **Log file** — `MoneyMakerGuardian.log` in MT5's `MQL5/Files/` directory

Log entries include timestamps and full details:
```
2026.03.08 14:23:15 | DEFENSIVE MODE ON: heartbeat stale by 45 seconds (threshold: 30)
2026.03.08 14:23:18 | EMERGENCY TRAIL BUY: EURUSD ticket 12345678 SL 1.08500 → 1.08650 (price: 1.09150)
2026.03.08 14:23:21 | DRAWDOWN KILL: equity 9050.00, peak 10300.00, drawdown 12.14% >= 10.00%
2026.03.08 14:23:21 | CLOSED EURUSD ticket 12345678 | BUY 0.10 lots | PnL: -150.00 | Reason: DRAWDOWN_KILL
```

---

## How the Heartbeat Works

The Python bridge (`mt5_bridge/connector.py`) calls `send_heartbeat()` every 5 seconds:

```python
mt5.global_variable_set("MONEYMAKER_HEARTBEAT", float(int(time.time())))
```

The Guardian EA reads it:

```mql5
double heartbeatTimestamp = GlobalVariableGet("MONEYMAKER_HEARTBEAT");
int ageSec = (int)(TimeCurrent() - (datetime)heartbeatTimestamp);
if(ageSec > InpHeartbeatTimeoutSec)
    // Enter defensive mode
```

MT5 GlobalVariables are shared memory within the terminal — no network, no files, no external dependencies.

---

## Position Close Comments

When the Guardian EA closes a position, it sets the order comment to:
- `GUARDIAN:DRAWDOWN_KILL` — closed due to drawdown limit
- `GUARDIAN:DAILY_LOSS_KILL` — closed due to daily loss limit
- `GUARDIAN:FRIDAY_CLOSE` — closed before weekend

These comments are visible in MT5's trade history and can be queried by the Python bridge's `TradeRecorder` for the ML feedback loop.

---

## Safety Design Principles

1. **Never opens trades** — the EA is purely defensive
2. **Magic number filter** — only touches MONEYMAKER positions (magic=123456), never manual trades
3. **Trailing stop direction** — only moves SL in the profitable direction, never against
4. **Wide slippage on emergency close** — uses 50 points deviation to ensure fills
5. **Independent of infrastructure** — works even if Docker, Redis, PostgreSQL, and the Python bridge are all down
6. **Fail-safe defaults** — if heartbeat variable doesn't exist, assumes bridge is offline

---

## Troubleshooting

### EA shows "!! DEFENSIVE !!" but bridge is running
- Verify the Python bridge's position monitor loop is running (check mt5-bridge logs)
- Check that `MONEYMAKER_HEARTBEAT` GlobalVariable exists: in MT5, go to View → GlobalVariables (F3)
- Ensure the heartbeat timestamp is updating every ~5 seconds

### EA doesn't appear in Navigator
- Verify the `.mq5` file is in the correct `MQL5/Experts/` folder
- Compile the file in MetaEditor (F7) and check for errors
- Restart MT5 if needed

### EA is attached but not running
- Check that "Allow Algo Trading" is enabled (button in the toolbar, and in Tools → Options → Expert Advisors)
- Look for errors in the Experts tab (View → Toolbox → Experts)

### Positions not being managed
- Verify the magic number matches (default: 123456)
- Check that positions were opened by the Python bridge (not manually)
- Look at the chart comment — does it show the correct position count?

---

## Updating

When updating the EA:
1. Pull the latest `MoneyMakerGuardian.mq5` from the repository
2. Copy it to `MQL5/Experts/` (overwrite the old file)
3. Recompile in MetaEditor (F7)
4. The running EA will automatically use the new version on next chart reload

> **Tip**: Keep the `.mq5` source in version control (`program/mql5/`) and only copy the compiled version to MT5. This way the source of truth stays in the Git repository.
