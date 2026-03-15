# MONEYMAKER V1 -- Risk Management and Safety Systems

> **Autore** | Renan Augusto Macena

---

## Table of Contents

1. [Philosophy of Risk Management](#91-philosophy-of-risk-management)
2. [Risk Management Architecture](#92-risk-management-architecture)
3. [Position Sizing Framework](#93-position-sizing-framework)
4. [Stop-Loss and Take-Profit Systems](#94-stop-loss-and-take-profit-systems)
5. [Circuit Breaker System](#95-circuit-breaker-system)
6. [Spiral Protection](#96-spiral-protection)
7. [Drawdown Management](#97-drawdown-management)
8. [Exposure and Correlation Management](#98-exposure-and-correlation-management)
9. [Market Condition Awareness](#99-market-condition-awareness)
10. [The 4-Tier Fallback Decision Engine](#910-the-4-tier-fallback-decision-engine)
11. [Kill Switch System](#911-kill-switch-system)
12. [Margin and Leverage Management](#912-margin-and-leverage-management)
13. [Confidence Gating System](#913-confidence-gating-system)
14. [Audit Trail and Compliance](#914-audit-trail-and-compliance)
15. [Risk Monitoring Dashboard](#915-risk-monitoring-dashboard)
16. [Testing and Validation](#916-testing-and-validation)

---

## 9.1 Philosophy of Risk Management

### Survival First, Profits Second

There is a cardinal rule in the MONEYMAKER ecosystem that supersedes every other design principle, every optimization target, every performance metric, and every profit objective: **survival comes first**. A trading system that generates extraordinary returns for six months and then suffers a catastrophic drawdown that wipes out the account has not succeeded -- it has failed in the most absolute and irreversible way possible. Capital destroyed cannot compound. An account reduced to zero cannot recover. The mathematics of loss are brutally asymmetric: a 50% drawdown requires a 100% return just to break even. A 75% drawdown requires a 300% return. A 90% drawdown requires a 900% return. These are not theoretical abstractions. They are the mathematical reality that shapes every decision in MONEYMAKER's risk management framework.

The first duty of the risk management system is to ensure that MONEYMAKER survives. It must survive bad trades. It must survive losing streaks. It must survive flash crashes, black swan events, liquidity droughts, and broker failures. It must survive bugs in the strategy logic, errors in the data pipeline, and network outages. It must survive the kind of market conditions that have destroyed professional trading firms with teams of quantitative analysts and decades of experience. Survival is not a feature of the risk system -- it is the purpose of the risk system.

Every other objective -- maximizing returns, improving the Sharpe ratio, capturing alpha, outperforming benchmarks -- is subordinate to this prime directive. A risk management system that occasionally allows a large loss in pursuit of higher average returns has failed. A risk management system that can be overridden by the Algo Engine when the model is "confident" has failed. A risk management system that relaxes its constraints during a winning streak has failed. The risk system is the adult in the room: disciplined, conservative, and absolutely unwilling to negotiate on safety.

### Risk Management as the Immune System

Consider the human immune system. It operates continuously, monitoring every cell and every molecule that enters the body. It does not wait for symptoms to appear before acting. It maintains multiple layers of defense -- physical barriers, innate immunity, adaptive immunity -- each with different response speeds and specialization levels. It can escalate from a localized response to a systemic one when the threat level demands it. It has memory: it learns from past infections and responds more quickly to familiar threats. And critically, it operates independently of conscious thought. You do not decide to fight an infection. Your immune system fights it for you, whether you are awake or asleep, whether you are paying attention or not.

MONEYMAKER's risk management system is designed as the immune system of the trading ecosystem. It runs as an independent service, separate from the Algo Engine, separate from the execution bridge, separate from the data pipeline. It monitors every aspect of the system's financial health in real time. It does not wait for a losing trade to trigger a response -- it evaluates risk before the trade is placed, while the trade is open, and after the trade is closed. It maintains multiple layers of defense: position sizing limits, stop-loss systems, circuit breakers, spiral protection, kill switches, and drawdown monitors. Each layer operates independently, so that if one layer fails or is bypassed, the others still protect the account. And it learns: the COPER experience bank records past risk events and their outcomes, allowing the system to respond more quickly and more appropriately to familiar danger patterns.

### Asymmetric Risk-Reward

Profitable trading over the long term does not require a high win rate. It requires an asymmetric distribution of outcomes: losses should be small and frequent, wins should be large and occasional. A system that wins 40% of its trades can be enormously profitable if the average win is three times the size of the average loss. Conversely, a system that wins 80% of its trades can be catastrophically unprofitable if a single loss wipes out the gains from forty wins.

MONEYMAKER's risk management framework is designed to enforce this asymmetry. Stop-losses are set at levels that limit the downside of any individual trade to a small, predetermined fraction of account equity. Take-profit targets are set at multiples of the stop-loss distance, ensuring that winners are given room to run. Trailing stops protect accumulated profits while allowing further upside. The overall portfolio is structured so that even the worst-case loss on any single trade is survivable and psychologically insignificant relative to the total equity.

This philosophy manifests in a concrete mathematical relationship. If we risk 1% of equity per trade, and our average winner is 2.5 times our average loser, then we need only a 35% win rate to break even. At a 45% win rate, we generate a healthy positive expectancy. At a 55% win rate, returns compound powerfully. The risk management system does not attempt to predict winners -- that is the Algo Engine's job. The risk management system ensures that the inevitable losers are contained, controlled, and unable to inflict lasting damage.

### Capital Preservation and the Power of Compounding

The reason capital preservation is paramount is that trading profits compound. A 10% return on a USD 10,000 account yields USD 1,000. A 10% return on a USD 100,000 account yields USD 10,000. The same edge, the same strategy, the same win rate -- but ten times the absolute return, simply because the capital base is larger. Every dollar lost to excessive risk is not just a dollar lost today. It is the future compounding of that dollar, across months and years, that is permanently destroyed.

Consider two hypothetical trading systems, both generating an average of 2% monthly return before risk events. System A has loose risk management and experiences a 40% drawdown once per year. System B has strict risk management and limits its worst annual drawdown to 15%. After five years, System A has compounded to approximately 1.3 times its starting capital. System B has compounded to approximately 2.4 times its starting capital. The difference is not in the gross returns -- they are identical. The difference is entirely in the capital preserved by avoiding large drawdowns. This is why MONEYMAKER's risk management system is not an optional add-on or a nice-to-have feature. It is the single most important determinant of long-term profitability.

### Independence from Trading Decisions

A critical architectural principle: the risk management system must be independent from the trading decisions. This means it runs as a separate service, with its own process, its own configuration, its own database, and its own decision logic. The Algo Engine cannot override the risk system. The Algo Engine cannot modify the risk system's parameters. The Algo Engine cannot bypass the risk system's gates.

This independence is essential because the Algo Engine is optimized for a fundamentally different objective: identifying profitable trading opportunities. When the Algo Engine sees a high-probability setup, it wants to trade. It wants to take the largest position it can justify. It wants to hold the position as long as the signal remains valid. These impulses are correct from a signal-generation perspective, but they are dangerous from a risk-management perspective. The Algo Engine has no concept of portfolio heat, no awareness of correlated exposure, no memory of how many consecutive losses have occurred this week, and no understanding of the margin utilization levels that would make the next trade dangerous.

By running the risk system as an independent service that stands between the Algo Engine and the execution bridge, we create a mandatory checkpoint that every trade must pass through. The Algo Engine proposes. The risk system disposes. This separation of concerns ensures that trading intelligence and risk management can each be optimized for their respective objectives without compromise.

### Defense in Depth

MONEYMAKER's risk management follows the principle of defense in depth: multiple overlapping layers of protection, each designed to catch failures that slip through the layers above. No single risk control is trusted to work perfectly all the time. Instead, the system assumes that any individual control can fail and designs redundancy accordingly.

The layers, from outermost to innermost, are:

```
+------------------------------------------------------------------+
|  Layer 1: Position Sizing (limits exposure before trade opens)    |
|  +------------------------------------------------------------+  |
|  |  Layer 2: Stop-Loss/Take-Profit (limits loss per trade)    |  |
|  |  +------------------------------------------------------+  |  |
|  |  |  Layer 3: Spiral Protection (detects losing streaks) |  |  |
|  |  |  +------------------------------------------------+  |  |  |
|  |  |  |  Layer 4: Circuit Breakers (daily/weekly/monthly)|  |  |  |
|  |  |  |  +------------------------------------------+   |  |  |  |
|  |  |  |  |  Layer 5: Kill Switches (emergency halt)  |   |  |  |  |
|  |  |  |  |  +------------------------------------+   |   |  |  |  |
|  |  |  |  |  |  Layer 6: Margin Monitoring         |   |   |  |  |  |
|  |  |  |  |  |  (broker-level last resort)         |   |   |  |  |  |
|  |  |  |  |  +------------------------------------+   |   |  |  |  |
|  |  |  |  +------------------------------------------+   |  |  |  |
|  |  |  +------------------------------------------------+  |  |  |
|  |  +------------------------------------------------------+  |  |
|  +------------------------------------------------------------+  |
+------------------------------------------------------------------+
```

If position sizing fails to limit exposure, the stop-loss contains the loss on that individual trade. If the stop-loss is somehow not triggered (broker failure, extreme slippage), the spiral protection detects the unusually large loss and reduces future exposure. If the spiral protection is insufficient because the losses are each within normal range but cumulative, the circuit breakers detect the drawdown at the daily, weekly, or monthly level. If the circuit breakers somehow fail to halt trading, the kill switch provides an emergency override. And beneath all of these, the broker's own margin call mechanism provides the absolute last line of defense.

This layered approach means that a single bug, a single misconfiguration, or a single unexpected market event cannot bypass the entire safety system. Multiple independent failures must occur simultaneously for the account to suffer an uncontrolled loss -- a probability that decreases exponentially with each additional layer.

---

## 9.2 Risk Management Architecture

### Standalone Service Design

The Risk Management Service runs as an independent Python service within its own Docker container, hosted on a dedicated VM within the Proxmox infrastructure. It has its own Python environment, its own configuration files, its own logging, its own database tables, and its own health monitoring endpoints. It does not share a process with the Algo Engine. It does not share a process with the execution bridge. It is, by design, the most isolated and independently operated service in the entire MONEYMAKER ecosystem.

The service is designed to be the most reliable component in the system. If the data ingestion service goes down, MONEYMAKER cannot trade but does not lose money. If the Algo Engine crashes, no new signals are generated but existing positions are managed by the risk service. If the execution bridge fails, the risk service detects the disconnection and triggers a kill switch. But if the risk service itself goes down, there is no safety net. For this reason, the risk service has the highest availability requirements of any component:

- **Startup time:** Less than 2 seconds to full operational state
- **Health check interval:** Every 5 seconds
- **Automatic restart on failure:** via Docker's restart policy and systemd watchdog
- **Heartbeat monitoring:** Both the Algo Engine and execution bridge monitor the risk service's heartbeat. If the heartbeat is missed for 15 seconds, both services enter safe mode (no new trades, tighten existing stops)

### Override Authority

The Risk Management Service has absolute override authority over all trading decisions in the MONEYMAKER ecosystem. This authority is not negotiable, not configurable, and not bypassable from within the system. The decision flow is strictly unidirectional:

```
Algo Engine generates signal
        |
        v
+-------------------+
| Risk Gate Service  |  <-- Has VETO authority
|                    |
| Evaluates:         |
| - Position sizing  |
| - Portfolio heat   |
| - Circuit breakers |
| - Spiral status    |
| - Confidence gates |
| - Exposure limits  |
| - Margin status    |
+-------------------+
        |
    [APPROVED] -----> Execution Bridge -----> MT5
        |
    [MODIFIED] -----> Adjust size/stops -----> Execution Bridge -----> MT5
        |
    [REJECTED] -----> Log reason, notify, discard signal
```

The risk gate can take three actions on any incoming trade request:

1. **APPROVE**: The trade passes all risk checks. It is forwarded to the execution bridge unchanged.
2. **MODIFY**: The trade passes some checks but requires adjustment. Typical modifications include reducing position size, tightening stop-loss, widening take-profit targets, or adding mandatory trailing stop parameters. The modified trade is forwarded to the execution bridge.
3. **REJECT**: The trade fails one or more critical risk checks. It is discarded entirely. The reason for rejection is logged, and the Algo Engine is notified so it can update its internal state.

Every decision -- approve, modify, or reject -- is logged with full context: the original trade request, all risk metrics evaluated, the threshold values in effect, the final decision, and the reason for that decision. This audit trail is immutable and serves as the foundation for post-trade analysis and system improvement.

### Communication Protocol

The Risk Management Service communicates with the Algo Engine and the execution bridge via gRPC (Google Remote Procedure Call). gRPC was chosen over REST or ZeroMQ for this specific communication path because of three properties that are critical for a risk gate:

1. **Strong typing**: gRPC uses Protocol Buffers for message definition, which enforces strict type safety. A trade request cannot be malformed -- if it does not conform to the protobuf schema, it is rejected at the serialization layer before it ever reaches the risk evaluation logic. This eliminates an entire class of bugs where a mistyped field name or an incorrect data type could bypass a risk check.

2. **Bidirectional streaming**: gRPC supports bidirectional streaming, which allows the risk service to maintain a persistent connection with the Algo Engine and the execution bridge. The Algo Engine can stream trade requests as they are generated, and the risk service can stream responses back without the overhead of establishing a new connection for each request. This keeps latency minimal -- typically under 5 milliseconds for the risk evaluation round trip.

3. **Deadline propagation**: gRPC supports deadlines, which means the Algo Engine can specify how long it is willing to wait for a risk evaluation. If the risk service does not respond within the deadline (because it is overloaded or has crashed), the Algo Engine knows the request was not evaluated and can handle the timeout appropriately (default: do not trade).

The protobuf schema for the core risk evaluation message:

```protobuf
syntax = "proto3";

package risk;

service RiskGate {
    rpc EvaluateTrade (TradeRequest) returns (RiskDecision);
    rpc GetRiskStatus (StatusRequest) returns (RiskStatus);
    rpc TriggerKillSwitch (KillSwitchRequest) returns (KillSwitchResponse);
    rpc StreamEquityUpdates (stream EquityUpdate) returns (stream RiskAlert);
}

message TradeRequest {
    string request_id = 1;
    string symbol = 2;
    string direction = 3;           // BUY or SELL
    double requested_lots = 4;
    double entry_price = 5;
    double stop_loss = 6;
    double take_profit = 7;
    double model_confidence = 8;    // 0.0 to 1.0
    string strategy_id = 9;
    string tier_source = 10;        // COPER, ML_MODEL, TECHNICAL, CONSERVATIVE
    int64 timestamp = 11;
    map<string, double> indicators = 12;
}

message RiskDecision {
    string request_id = 1;
    string decision = 2;            // APPROVED, MODIFIED, REJECTED
    double approved_lots = 3;
    double approved_stop_loss = 4;
    double approved_take_profit = 5;
    string reason = 6;
    repeated string risk_flags = 7;
    RiskMetrics current_metrics = 8;
    int64 timestamp = 9;
}

message RiskMetrics {
    double account_equity = 1;
    double account_balance = 2;
    double free_margin = 3;
    double margin_utilization = 4;
    double daily_pnl = 5;
    double weekly_pnl = 6;
    double monthly_pnl = 7;
    double current_drawdown = 8;
    double peak_equity = 9;
    int32 open_positions = 10;
    double total_exposure = 11;
    int32 consecutive_losses = 12;
    string circuit_breaker_status = 13;
    double portfolio_heat = 14;
}

message RiskStatus {
    RiskMetrics metrics = 1;
    repeated CircuitBreakerState breakers = 2;
    bool kill_switch_active = 3;
    string kill_switch_reason = 4;
    repeated string active_alerts = 5;
}

message CircuitBreakerState {
    string level = 1;
    string status = 2;              // ARMED, TRIGGERED, COOLING_DOWN, RESET
    double threshold = 3;
    double current_value = 4;
    int64 triggered_at = 5;
    int64 reset_at = 6;
}
```

### Risk Service Database

The Risk Management Service maintains its own PostgreSQL schema, separate from the main market data tables. This schema stores all risk-related state, audit logs, and historical metrics. The separation ensures that the risk service can operate independently even if the main database experiences issues.

```sql
-- Risk audit log: immutable append-only table
CREATE TABLE risk_audit_log (
    id              BIGSERIAL PRIMARY KEY,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    request_id      UUID NOT NULL,
    symbol          VARCHAR(20) NOT NULL,
    direction       VARCHAR(4) NOT NULL,
    requested_lots  DECIMAL(10,4),
    approved_lots   DECIMAL(10,4),
    entry_price     DECIMAL(15,5),
    stop_loss       DECIMAL(15,5),
    take_profit     DECIMAL(15,5),
    model_confidence DECIMAL(5,4),
    decision        VARCHAR(10) NOT NULL,  -- APPROVED, MODIFIED, REJECTED
    reason          TEXT,
    risk_flags      TEXT[],
    account_equity  DECIMAL(15,2),
    drawdown_pct    DECIMAL(5,2),
    margin_util_pct DECIMAL(5,2),
    portfolio_heat  DECIMAL(5,2),
    consecutive_losses INT,
    circuit_breaker_status VARCHAR(20),
    tier_source     VARCHAR(20)
);

-- Circuit breaker events
CREATE TABLE circuit_breaker_events (
    id              BIGSERIAL PRIMARY KEY,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    level           INT NOT NULL,       -- 1, 2, 3, 4
    event_type      VARCHAR(20) NOT NULL, -- TRIGGERED, RESET, COOLING_DOWN
    threshold       DECIMAL(5,2) NOT NULL,
    actual_value    DECIMAL(5,2) NOT NULL,
    action_taken    TEXT NOT NULL,
    positions_closed INT DEFAULT 0,
    equity_at_trigger DECIMAL(15,2)
);

-- Equity snapshots for drawdown tracking
CREATE TABLE equity_snapshots (
    id              BIGSERIAL PRIMARY KEY,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    equity          DECIMAL(15,2) NOT NULL,
    balance         DECIMAL(15,2) NOT NULL,
    free_margin     DECIMAL(15,2) NOT NULL,
    margin_used     DECIMAL(15,2) NOT NULL,
    peak_equity     DECIMAL(15,2) NOT NULL,
    drawdown_abs    DECIMAL(15,2) NOT NULL,
    drawdown_pct    DECIMAL(5,2) NOT NULL,
    open_positions  INT NOT NULL,
    total_exposure  DECIMAL(15,2) NOT NULL
);

-- Spiral tracking
CREATE TABLE spiral_events (
    id              BIGSERIAL PRIMARY KEY,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    scope           VARCHAR(20) NOT NULL,  -- GLOBAL, SYMBOL, STRATEGY
    scope_id        VARCHAR(50),
    consecutive_losses INT NOT NULL,
    action_taken    TEXT NOT NULL,
    size_reduction  DECIMAL(5,2),
    halt_duration   INTERVAL
);

-- Kill switch events
CREATE TABLE kill_switch_events (
    id              BIGSERIAL PRIMARY KEY,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    trigger_type    VARCHAR(30) NOT NULL,
    reason          TEXT NOT NULL,
    positions_closed INT DEFAULT 0,
    orders_cancelled INT DEFAULT 0,
    equity_at_trigger DECIMAL(15,2),
    reset_timestamp  TIMESTAMPTZ,
    reset_by         VARCHAR(50)
);

-- Index for fast audit queries
CREATE INDEX idx_risk_audit_timestamp ON risk_audit_log (timestamp DESC);
CREATE INDEX idx_risk_audit_symbol ON risk_audit_log (symbol, timestamp DESC);
CREATE INDEX idx_risk_audit_decision ON risk_audit_log (decision, timestamp DESC);
CREATE INDEX idx_equity_snapshots_ts ON equity_snapshots (timestamp DESC);
```

### Service Lifecycle and Startup Sequence

When the Risk Management Service starts, it follows a strict initialization sequence:

1. **Load configuration**: Read risk parameters from YAML config file and validate all thresholds.
2. **Connect to database**: Establish connection to the risk-specific PostgreSQL schema. If connection fails, the service will not start.
3. **Load state**: Query the most recent equity snapshot, circuit breaker states, spiral counters, and kill switch status. The service resumes from its last known state, not from a blank slate.
4. **Connect to execution bridge**: Establish gRPC connection to the MT5 bridge to receive real-time position and equity updates. If the bridge is unavailable, the service starts in degraded mode with cached data and will not approve any new trades until the connection is established.
5. **Connect to Algo Engine**: Open gRPC server to receive trade evaluation requests from the Algo Engine.
6. **Start monitoring loops**: Begin the continuous monitoring loops for equity tracking, drawdown calculation, circuit breaker evaluation, and heartbeat emission.
7. **Signal readiness**: Publish a health check endpoint that returns HTTP 200 only after all initialization steps are complete. Upstream services (the Algo Engine) wait for this endpoint before sending trade requests.

---

## 9.3 Position Sizing Framework

### The Kelly Criterion

The Kelly criterion provides the mathematically optimal fraction of capital to risk on each bet in a series of bets with known probabilities and payoffs. It maximizes the expected logarithmic growth of the bankroll over time. The formula is:

```
f* = (b * p - q) / b
```

Where:

- `f*` = optimal fraction of capital to risk
- `b`  = ratio of average win to average loss (win/loss ratio)
- `p`  = probability of winning
- `q`  = probability of losing (q = 1 - p)

For example, if our model has a historical win rate of 55% (p = 0.55, q = 0.45) and an average win-to-loss ratio of 1.8:1 (b = 1.8):

```
f* = (1.8 * 0.55 - 0.45) / 1.8
f* = (0.99 - 0.45) / 1.8
f* = 0.54 / 1.8
f* = 0.30 = 30%
```

Full Kelly says we should risk 30% of capital per trade. This is far too aggressive for real trading. The Kelly criterion assumes perfect knowledge of probabilities and payoffs, which we never have. In practice, our estimates of p and b are derived from historical data that may not represent future conditions. Overestimating either parameter leads to catastrophic over-betting.

### Half-Kelly Implementation

MONEYMAKER uses half-Kelly (f*/2) as its maximum theoretical position size. Half-Kelly achieves approximately 75% of the growth rate of full Kelly while dramatically reducing the variance and maximum drawdown. In the example above, half-Kelly would suggest risking 15% of capital per trade -- still aggressive, but a much safer starting point.

However, half-Kelly is an upper bound, not a target. Several additional constraints further limit position size:

```python
def calculate_kelly_fraction(win_rate: float, win_loss_ratio: float) -> float:
    """
    Calculate half-Kelly position sizing fraction.

    Args:
        win_rate: Historical probability of winning (0.0 to 1.0)
        win_loss_ratio: Average win / average loss

    Returns:
        Half-Kelly fraction, clamped to safety limits
    """
    p = win_rate
    q = 1.0 - p
    b = win_loss_ratio

    # Full Kelly
    full_kelly = (b * p - q) / b

    # Half Kelly for safety
    half_kelly = full_kelly / 2.0

    # Clamp to absolute maximum of 5% per trade
    half_kelly = min(half_kelly, 0.05)

    # Floor at zero (negative Kelly means no edge, do not trade)
    half_kelly = max(half_kelly, 0.0)

    return half_kelly
```

### Maximum Position Size Caps

Regardless of what the Kelly criterion suggests, MONEYMAKER enforces hard caps on position sizing:

| Constraint | Limit | Rationale |
|---|---|---|
| Maximum risk per trade | 2% of equity | Absolute cap, never exceeded |
| Kelly-derived maximum | half-Kelly or 5%, whichever is lower | Kelly upper bound |
| Maximum lots per trade | Configurable per symbol (e.g., 1.0 lot for XAUUSD) | Prevents outsized positions on illiquid instruments |
| Maximum open positions | 5 simultaneous positions | Limits total portfolio complexity |
| Maximum correlated exposure | 3% when correlation > 0.7 | Treats correlated positions as partially the same trade |

### ATR-Based Position Sizing

The primary position sizing method in MONEYMAKER uses the Average True Range (ATR) to dynamically adjust position size based on current market volatility. ATR measures the average range of price movement over a given period, naturally accounting for both normal price movement and volatility expansion.

The formula:

```
lots = (equity * risk_percentage) / (ATR * atr_multiplier * pip_value * lot_size)
```

Where:

- `equity` = current account equity
- `risk_percentage` = risk per trade (from Kelly or fixed, typically 1-2%)
- `ATR` = Average True Range over 14 periods on the trading timeframe
- `atr_multiplier` = multiplier for stop-loss distance (typically 1.5)
- `pip_value` = monetary value of one pip for the given instrument
- `lot_size` = standard lot size for the instrument (100,000 for forex, 100 for gold)

Example calculation for XAUUSD:

- Account equity: USD 10,000
- Risk per trade: 1% = USD 100
- ATR(14) on H1: 5.50 (USD 5.50 price movement)
- ATR multiplier: 1.5 (stop at 1.5 x ATR = USD 8.25 from entry)
- Pip value for 1 lot XAUUSD: USD 1.00 per pip (1 pip = 0.01 for gold)
- Stop distance in pips: 825 pips

```
lots = 100 / (825 * 1.00)
lots = 100 / 825
lots = 0.12 lots
```

Implementation in Python:

```python
def calculate_position_size(
    equity: float,
    risk_pct: float,
    atr_value: float,
    atr_multiplier: float,
    pip_value: float,
    pip_size: float,
    min_lots: float = 0.01,
    max_lots: float = 1.0,
    kelly_fraction: float = None
) -> float:
    """
    Calculate ATR-based position size with Kelly overlay.

    Returns:
        Position size in lots, clamped to min/max constraints.
    """
    # ATR-based stop distance in price units
    stop_distance_price = atr_value * atr_multiplier

    # Convert to pips
    stop_distance_pips = stop_distance_price / pip_size

    # Risk amount in account currency
    if kelly_fraction is not None:
        effective_risk_pct = min(risk_pct, kelly_fraction)
    else:
        effective_risk_pct = risk_pct

    risk_amount = equity * effective_risk_pct

    # Calculate lots
    lots = risk_amount / (stop_distance_pips * pip_value)

    # Clamp to constraints
    lots = max(lots, min_lots)
    lots = min(lots, max_lots)

    # Round to broker's lot step (typically 0.01)
    lots = round(lots, 2)

    return lots
```

### Dynamic Adjustment for Volatility

Position sizes are not static. They automatically adjust to current market conditions:

- **High volatility (ATR > 1.5x 30-day average)**: Reduce risk_pct by 25%. Wider ATR naturally results in smaller positions, but we apply an additional reduction to account for the increased probability of gap risk and slippage during volatile conditions.
- **Very high volatility (ATR > 2.0x 30-day average)**: Reduce risk_pct by 50%. This represents unusual market conditions (news events, geopolitical crises) where the risk of outsized losses is significantly elevated.
- **Extreme volatility (ATR > 3.0x 30-day average)**: Halt new position opening entirely. This represents flash-crash or black-swan territory where the normal risk models cannot be trusted.
- **Low volatility (ATR < 0.5x 30-day average)**: Allow full risk_pct but do not increase it. Low volatility often precedes volatility expansion, and increasing position sizes just before a volatility spike is a common way to get caught in a large adverse move.

```python
def volatility_adjustment(current_atr: float, avg_atr_30d: float) -> float:
    """
    Returns a multiplier for risk_pct based on volatility regime.
    1.0 = normal, <1.0 = reduce, 0.0 = halt trading.
    """
    ratio = current_atr / avg_atr_30d if avg_atr_30d > 0 else 1.0

    if ratio > 3.0:
        return 0.0      # Halt: extreme volatility
    elif ratio > 2.0:
        return 0.50      # Half risk
    elif ratio > 1.5:
        return 0.75      # Three-quarter risk
    else:
        return 1.0       # Normal risk
```

### Correlation-Aware Sizing

When multiple positions are open simultaneously, the total portfolio risk is not simply the sum of individual position risks -- it depends on the correlations between positions. Two uncorrelated positions each risking 1% contribute approximately 1.4% total portfolio risk (sqrt(1^2 + 1^2)). Two perfectly correlated positions each risking 1% contribute 2% total portfolio risk (they move in lockstep). Two negatively correlated positions partially offset each other.

MONEYMAKER maintains a rolling correlation matrix between all traded instruments, updated daily using the most recent 30 days of returns data. When a new trade request arrives, the risk service evaluates how the proposed position correlates with existing open positions:

- **Correlation < 0.3**: Positions treated as independent. Full sizing allowed.
- **Correlation 0.3 to 0.7**: Positions partially correlated. Reduce new position by 25%.
- **Correlation > 0.7**: Positions highly correlated. Reduce new position by 50%, or reject if total correlated exposure would exceed 3%.

```python
def correlation_adjustment(
    new_symbol: str,
    open_positions: list,
    correlation_matrix: dict,
    max_correlated_exposure: float = 0.03
) -> float:
    """
    Returns sizing multiplier based on correlation with open positions.
    """
    max_correlation = 0.0

    for pos in open_positions:
        pair_key = tuple(sorted([new_symbol, pos.symbol]))
        corr = correlation_matrix.get(pair_key, 0.0)
        max_correlation = max(max_correlation, abs(corr))

    if max_correlation > 0.7:
        return 0.50
    elif max_correlation > 0.3:
        return 0.75
    else:
        return 1.0
```

### Account Equity Base

MONEYMAKER uses the current account equity -- not the balance -- as the base for all position sizing calculations. The distinction matters:

- **Balance**: The total of all closed trade profits and losses plus deposits minus withdrawals. It does not reflect the current state of open positions.
- **Equity**: Balance plus unrealized profit/loss from open positions. This reflects the true current value of the account.
- **Free margin**: Equity minus margin currently used by open positions. This represents the capital available to open new positions.

Using equity as the base means that as open positions move against us, our sizing for new trades automatically decreases (because equity decreases). This is a natural self-correcting mechanism: losing positions reduce the capital base, which reduces future position sizes, which reduces future risk. Conversely, winning positions increase equity, which allows slightly larger positions -- but this expansion is gradual and controlled.

---

## 9.4 Stop-Loss and Take-Profit Systems

### ATR-Based Dynamic Stops

Static stop-losses -- "always use a 50-pip stop" -- are one of the most common mistakes in algorithmic trading. A 50-pip stop might be appropriate for EURUSD during a quiet Asian session, but it would be absurdly tight for XAUUSD during a volatile US session. The stop-loss distance must reflect the actual volatility of the instrument on the timeframe being traded.

MONEYMAKER uses the Average True Range (ATR) with a 14-period lookback as the basis for all stop-loss and take-profit calculations:

```
Stop-Loss Distance = ATR(14) * SL_multiplier
Take-Profit Distance = ATR(14) * TP_multiplier
```

Default multipliers:

| Parameter | Value | Rationale |
|---|---|---|
| SL_multiplier | 1.5 | Gives the trade enough room to breathe without allowing catastrophic loss |
| TP_multiplier (Level 1) | 2.0 | Minimum risk-reward of 1.33:1 |
| TP_multiplier (Level 2) | 3.0 | Captures extended moves |
| TP_multiplier (Level 3) | 5.0 | Captures trend continuation |

For a BUY trade on XAUUSD with ATR(14) = 5.50:

- Entry: 2650.00
- Stop-Loss: 2650.00 - (5.50 * 1.5) = 2650.00 - 8.25 = 2641.75
- TP1: 2650.00 + (5.50 * 2.0) = 2650.00 + 11.00 = 2661.00
- TP2: 2650.00 + (5.50 * 3.0) = 2650.00 + 16.50 = 2666.50
- TP3: 2650.00 + (5.50 * 5.0) = 2650.00 + 27.50 = 2677.50

### Trailing Stops

Once a position moves into profit, MONEYMAKER activates trailing stop logic to protect accumulated gains while allowing further upside. The trailing stop is implemented as a soft stop (managed by the risk service) that updates the hard stop (in MT5) at defined intervals:

```python
def calculate_trailing_stop(
    direction: str,
    entry_price: float,
    current_price: float,
    current_stop: float,
    atr_value: float,
    trail_multiplier: float = 1.0
) -> float:
    """
    Calculate new trailing stop level.
    Only moves stop in the direction of profit. Never widens stop.

    Returns:
        New stop-loss price, or current_stop if no adjustment needed.
    """
    trail_distance = atr_value * trail_multiplier

    if direction == "BUY":
        new_stop = current_price - trail_distance
        # Only move stop up (toward profit), never down
        return max(new_stop, current_stop)
    else:  # SELL
        new_stop = current_price + trail_distance
        # Only move stop down (toward profit), never up
        return min(new_stop, current_stop)
```

The trailing stop is evaluated on every new candle close on the trading timeframe. It is not evaluated on every tick, as this would result in excessive MT5 modification requests and could cause issues with broker rate limits.

### Break-Even Stops

When a position reaches 1x ATR in profit, the stop-loss is moved to the break-even level (entry price plus spread and commission). This eliminates the risk of a winning trade turning into a losing trade. The break-even stop is a one-time adjustment that occurs automatically:

```python
def check_breakeven(
    direction: str,
    entry_price: float,
    current_price: float,
    current_stop: float,
    atr_value: float,
    spread: float
) -> float:
    """
    Move stop to breakeven when profit reaches 1x ATR.
    """
    if direction == "BUY":
        profit_distance = current_price - entry_price
        breakeven_level = entry_price + spread  # Cover the spread cost
        if profit_distance >= atr_value and current_stop < breakeven_level:
            return breakeven_level
    else:  # SELL
        profit_distance = entry_price - current_price
        breakeven_level = entry_price - spread
        if profit_distance >= atr_value and current_stop > breakeven_level:
            return breakeven_level

    return current_stop  # No change
```

### Time-Based Stops

Not all risk is measured in price movement. A position that has been open for an extended period without reaching its target is tying up capital and margin while contributing no return. Worse, the longer a position is open, the more exposure it has to overnight gaps, weekend risk, news events, and regime changes that the original signal did not anticipate.

MONEYMAKER enforces maximum holding periods:

| Timeframe | Maximum Holding Period | Action at Expiry |
|---|---|---|
| Scalp (M5-M15) | 4 hours | Close at market regardless of P&L |
| Intraday (H1) | 24 hours | Close at market if not in profit; if in profit, tighten stop to 0.5x ATR |
| Swing (H4-D1) | 5 trading days | Tighten stop to 0.75x ATR, allow further 2 days |
| Position (W1) | 20 trading days | Evaluate weekly; tighten stop progressively |

### Multi-Level Take-Profit

Rather than closing an entire position at a single take-profit level, MONEYMAKER uses a multi-level exit strategy that locks in partial profits while leaving a portion of the position to capture larger moves:

```
Position Split:
  TP1 (2.0x ATR):  Close 50% of position
  TP2 (3.0x ATR):  Close 30% of position
  TP3 (5.0x ATR):  Close remaining 20% of position (or let trailing stop exit)
```

When TP1 is hit:

1. Close 50% of the position at TP1
2. Move stop-loss for remaining position to break-even
3. Continue monitoring for TP2

When TP2 is hit:

1. Close 30% of the original position (60% of remaining) at TP2
2. Move stop-loss for remaining position to TP1 level
3. Activate trailing stop with 1.0x ATR trail distance

When TP3 is hit:

1. Close remaining 20% at TP3

If price reverses before TP3:

1. Trailing stop or locked-in stop at TP1 protects the remaining position
2. Worst case: remaining 20% exits at TP1 level (still profitable)

### The Iron Rule: Never Widen a Stop

There is one absolute, inviolable rule in MONEYMAKER's stop-loss system: **a stop-loss can only be moved in the direction of profit. It can never be moved further from the entry price.** This rule is enforced at the code level with a hard check that cannot be overridden:

```python
def validate_stop_modification(
    direction: str,
    current_stop: float,
    proposed_stop: float
) -> bool:
    """
    Validates that a stop modification does not widen the stop.
    Returns True if the modification is allowed, False if it violates
    the iron rule.
    """
    if direction == "BUY":
        # For longs, stop must move UP (higher), never down
        return proposed_stop >= current_stop
    else:  # SELL
        # For shorts, stop must move DOWN (lower), never up
        return proposed_stop <= current_stop
```

This validation runs in the execution bridge as well as in the risk service -- a redundant check at two layers, because violating this rule is one of the most common ways traders (and trading systems) turn small losses into catastrophic ones.

### Hard Stops vs Soft Stops

MONEYMAKER maintains two layers of stop-loss:

1. **Hard stop**: A real stop-loss order placed in MT5 at the broker level. This stop will execute even if MONEYMAKER is offline, if the risk service crashes, or if network connectivity is lost. The hard stop is always placed at the initial ATR-based level and is only modified when the risk service sends an explicit modification command.

2. **Soft stop**: A virtual stop-loss managed by the risk service in memory. The soft stop is typically tighter than the hard stop and is used for the trailing stop logic, break-even adjustments, and time-based exits. When the soft stop is triggered, the risk service sends a market close command to the execution bridge.

The hard stop is the safety net. The soft stop is the precision tool. Both are always active.

---

## 9.5 Circuit Breaker System

### Overview

Circuit breakers are automatic shutdown mechanisms that halt trading when cumulative losses exceed predefined thresholds within specific time windows. They are named by analogy with electrical circuit breakers, which disconnect a circuit when current flow exceeds a safe level, preventing damage to the system. In MONEYMAKER, the "current" is financial loss, and the "damage" is catastrophic drawdown.

MONEYMAKER implements a four-level circuit breaker system, with each level representing increasing severity and increasingly aggressive protective action.

### Level 1 -- Session Circuit Breaker

```
Trigger:  Daily loss exceeds 2% of starting equity for the session
Scope:    Current trading session (Asian, European, or American)
```

**Detection**: The risk service tracks the equity at the beginning of each trading session. If the current equity drops below 98% of the session's starting equity, the Level 1 breaker triggers.

**Action**:

1. Immediately halt all new trade signals. The risk gate returns REJECTED for all incoming trade requests.
2. Existing positions are NOT closed. Instead, their stops are tightened to 0.75x ATR (if currently wider).
3. Notification sent via Telegram: "Level 1 circuit breaker triggered. Daily loss: X%. New trades suspended for this session."
4. Log the event to the circuit_breaker_events table.

**Reset**: The Level 1 breaker automatically resets at the beginning of the next trading session. If it was triggered during the European session, it resets at the start of the American session (but see below: if it triggers in two consecutive sessions, Level 2 may activate).

**Pseudocode**:

```python
class SessionCircuitBreaker:
    def __init__(self, threshold_pct: float = 0.02):
        self.threshold_pct = threshold_pct
        self.session_start_equity = None
        self.is_triggered = False

    def on_session_start(self, current_equity: float):
        self.session_start_equity = current_equity
        self.is_triggered = False

    def evaluate(self, current_equity: float) -> bool:
        if self.session_start_equity is None:
            return False

        loss_pct = (self.session_start_equity - current_equity) / self.session_start_equity

        if loss_pct >= self.threshold_pct and not self.is_triggered:
            self.is_triggered = True
            self.trigger_actions(loss_pct)
            return True

        return self.is_triggered

    def trigger_actions(self, loss_pct: float):
        log_circuit_breaker_event(level=1, loss_pct=loss_pct)
        send_telegram_alert(f"L1 BREAKER: Daily loss {loss_pct:.2%}")
        tighten_all_stops(multiplier=0.75)
```

### Level 2 -- Weekly Circuit Breaker

```
Trigger:  Weekly loss exceeds 5% of Monday's opening equity
Scope:    Current trading week (Monday 00:00 UTC to Friday 23:59 UTC)
```

**Detection**: The risk service records equity at the start of each trading week (Monday 00:00 UTC). If equity drops below 95% of this level at any point during the week, the Level 2 breaker triggers.

**Action**:

1. Close ALL open positions at market immediately.
2. Cancel ALL pending orders.
3. Halt all trading for 24 hours (configurable).
4. When trading resumes after the 24-hour halt, ALL position sizes are reduced by 50% for the remainder of the week. This reduction is implemented as a multiplier on the position sizing formula that is reset on Monday.
5. Send Telegram alert with full details: positions closed, realized P&L, new restrictions.
6. Log event with all context.

**Reset**: The Level 2 breaker resets at the start of the next trading week, provided the Level 3 breaker has not also been triggered.

### Level 3 -- Monthly Circuit Breaker

```
Trigger:  Monthly loss exceeds 10% of the month's opening equity
Scope:    Current calendar month
```

**Detection**: Equity at the first trading day of each month is recorded. If equity drops below 90% of this level, the Level 3 breaker triggers.

**Action**:

1. Close ALL open positions at market immediately.
2. Cancel ALL pending orders.
3. Halt all trading for 1 full week (7 calendar days).
4. Send Telegram alert marked as CRITICAL: includes equity curve for the month, all circuit breaker events, and the top 5 largest losing trades.
5. Send email alert to the system operator.
6. When trading resumes, require manual confirmation (operator must send a `/resume` command via Telegram or the dashboard).
7. Trading resumes at 25% of normal position sizes for the first week, 50% for the second week, then full if no further breakers trigger.

**Reset**: The Level 3 breaker resets at the start of the next calendar month, but only after manual confirmation.

### Level 4 -- Maximum Drawdown Breaker

```
Trigger:  Total equity drops below 75% of peak equity (all-time high water mark)
Scope:    Lifetime of the account
```

**Detection**: The risk service continuously tracks peak equity (the highest equity ever reached). If current equity drops below 75% of peak, the Level 4 breaker triggers. This is the "account is in serious trouble" breaker.

**Action**:

1. Close ALL positions at market.
2. Cancel ALL pending orders.
3. Disable ALL trading services. The risk service enters lockdown mode where it rejects all trade requests indefinitely.
4. Send EMERGENCY notifications via all channels (Telegram, email, SMS if configured).
5. Full state dump: save all current positions, all recent trades, all risk metrics, model states, and system logs to a dedicated post-mortem directory.
6. Trading cannot resume without manual intervention: the operator must review the post-mortem data, identify the cause of the drawdown, make any necessary configuration changes, and explicitly re-enable trading through a secure command sequence.

**Reset**: Manual only. Requires the operator to execute a specific reset procedure that includes acknowledging the drawdown and confirming the revised risk parameters.

### Hysteresis Prevention

Circuit breakers must not oscillate. If equity is hovering right at a threshold -- dropping below, recovering, dropping below again -- the breaker should not trigger, reset, trigger, reset in rapid succession. MONEYMAKER implements hysteresis by requiring equity to recover beyond a buffer before resetting:

```
Level 1: Triggers at -2%. Resets only when daily loss recovers to -1% or better.
Level 2: Triggers at -5%. Resets only when weekly loss recovers to -3% or better.
Level 3: Triggers at -10%. Requires manual reset after mandatory halt.
Level 4: Triggers at -25% from peak. Requires manual reset.
```

### Circuit Breaker State Machine

Each circuit breaker follows a state machine:

```
                  loss exceeds
    +-------+    threshold     +----------+
    | ARMED | ----------------> | TRIGGERED |
    +-------+                  +----------+
        ^                          |
        |                          | mandatory halt period
        |                          v
        |    recovery         +-----------+
        +<------------------- | COOLING   |
        |  above hysteresis   | DOWN      |
        |  threshold          +-----------+
        |                          |
        |    (L3, L4 only)         | manual review
        |                          v
        |                     +-----------+
        +<------------------- | PENDING   |
           manual reset       | REVIEW    |
                              +-----------+
```

---

## 9.6 Spiral Protection

### The Revenge Trading Problem

One of the most destructive patterns in trading -- for both humans and automated systems -- is the "loss spiral." After a series of losing trades, the natural impulse is to increase position size to recover losses faster. This is revenge trading, and it is the single most common cause of account blowups. An automated system can fall into the same trap if it is designed to "double down" after losses or if the strategy becomes increasingly confident in signals that are not working because market conditions have changed.

MONEYMAKER's spiral protection system detects consecutive losing trades and progressively reduces exposure, exactly opposite to the revenge trading impulse. The logic is simple but powerful: if the system is losing, something is wrong. Either the model is misjudging the market, the data is stale, the strategy is inappropriate for the current regime, or there is a systematic issue. The correct response is to reduce exposure until the problem is identified and resolved, not to increase it.

### Progressive Response Levels

Spiral protection operates on a graduated scale based on the number of consecutive losing trades:

```
Consecutive     Position Size     Additional
Losses          Reduction         Actions
-----------     -------------     ------------------
1-2             None              Normal operation
3               25%               Alert: "Minor losing streak detected"
4               35%               Increase minimum confidence to 65%
5               50%               Increase minimum confidence to 70%
                                  Alert: "Significant losing streak"
6               60%               Review model predictions vs outcomes
7               75%               Halt trading for 4 hours
                                  Mandatory cooling period
8               80%               Halt trading for 8 hours
9               85%               Halt trading for 16 hours
10+             90%               Halt trading for 24 hours
                                  Trigger model review flag
                                  Alert: "CRITICAL: 10+ consecutive losses"
                                  Escalate to manual review
```

### Multi-Scope Spiral Detection

Spiral detection operates at three levels simultaneously:

1. **Global scope**: Counts all consecutive losses across all symbols and strategies. This catches systemic issues affecting the entire portfolio.

2. **Per-symbol scope**: Counts consecutive losses for each symbol independently. If XAUUSD has 5 consecutive losses but EURUSD is profitable, the spiral protection reduces XAUUSD sizing while leaving EURUSD unaffected.

3. **Per-strategy scope**: Counts consecutive losses for each strategy or signal source. If the COPER-based signals are losing but the ML model signals are winning, the spiral protection selectively reduces COPER-sourced trades.

```python
class SpiralProtection:
    def __init__(self):
        self.global_losses = 0
        self.symbol_losses = {}   # symbol -> consecutive loss count
        self.strategy_losses = {} # strategy_id -> consecutive loss count

    def record_trade_result(self, symbol: str, strategy: str, is_win: bool):
        if is_win:
            self.global_losses = 0
            self.symbol_losses[symbol] = 0
            self.strategy_losses[strategy] = 0
        else:
            self.global_losses += 1
            self.symbol_losses[symbol] = self.symbol_losses.get(symbol, 0) + 1
            self.strategy_losses[strategy] = self.strategy_losses.get(strategy, 0) + 1

    def get_size_multiplier(self, symbol: str, strategy: str) -> float:
        """
        Returns the most restrictive multiplier across all scopes.
        """
        global_mult = self._losses_to_multiplier(self.global_losses)
        symbol_mult = self._losses_to_multiplier(
            self.symbol_losses.get(symbol, 0)
        )
        strategy_mult = self._losses_to_multiplier(
            self.strategy_losses.get(strategy, 0)
        )

        return min(global_mult, symbol_mult, strategy_mult)

    def _losses_to_multiplier(self, losses: int) -> float:
        if losses < 3:
            return 1.0
        elif losses == 3:
            return 0.75
        elif losses == 4:
            return 0.65
        elif losses == 5:
            return 0.50
        elif losses == 6:
            return 0.40
        elif losses == 7:
            return 0.25
        elif losses == 8:
            return 0.20
        elif losses == 9:
            return 0.15
        else:  # 10+
            return 0.10

    def should_halt(self, symbol: str, strategy: str) -> tuple:
        """
        Returns (should_halt, halt_duration_hours) based on spiral state.
        """
        max_losses = max(
            self.global_losses,
            self.symbol_losses.get(symbol, 0),
            self.strategy_losses.get(strategy, 0)
        )

        if max_losses >= 10:
            return (True, 24)
        elif max_losses >= 9:
            return (True, 16)
        elif max_losses >= 8:
            return (True, 8)
        elif max_losses >= 7:
            return (True, 4)
        else:
            return (False, 0)
```

### Recovery Protocol

When a losing streak is broken by a winning trade, MONEYMAKER does not immediately restore full position sizing. Instead, it follows a graduated recovery:

1. First win after spiral: Restore 25% of the reduction (e.g., if reduced by 50%, restore to 37.5% reduction).
2. Second consecutive win: Restore another 25%.
3. Third consecutive win: Restore another 25%.
4. Fourth consecutive win: Fully restore normal sizing.

This graduated recovery prevents the system from immediately taking a large position after a single lucky win during an ongoing adverse market condition. The system must demonstrate sustained profitability before it regains full sizing authority.

---

## 9.7 Drawdown Management

### Real-Time Drawdown Calculation

Drawdown is the decline from a peak to a subsequent trough in account equity. It is the most important measure of risk experienced by a trading system because it represents the actual loss of capital relative to the best point achieved. MONEYMAKER tracks multiple types of drawdown simultaneously:

```python
class DrawdownTracker:
    def __init__(self, initial_equity: float):
        self.initial_equity = initial_equity
        self.peak_equity = initial_equity
        self.daily_start_equity = initial_equity
        self.weekly_start_equity = initial_equity
        self.monthly_start_equity = initial_equity

    def update(self, current_equity: float) -> dict:
        # Update peak
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

        return {
            'absolute_drawdown': self.initial_equity - current_equity,
            'absolute_drawdown_pct': (self.initial_equity - current_equity)
                                      / self.initial_equity,
            'relative_drawdown': self.peak_equity - current_equity,
            'relative_drawdown_pct': (self.peak_equity - current_equity)
                                      / self.peak_equity,
            'daily_drawdown': self.daily_start_equity - current_equity,
            'daily_drawdown_pct': (self.daily_start_equity - current_equity)
                                   / self.daily_start_equity,
            'weekly_drawdown': self.weekly_start_equity - current_equity,
            'weekly_drawdown_pct': (self.weekly_start_equity - current_equity)
                                    / self.weekly_start_equity,
            'monthly_drawdown': self.monthly_start_equity - current_equity,
            'monthly_drawdown_pct': (self.monthly_start_equity - current_equity)
                                     / self.monthly_start_equity,
            'peak_equity': self.peak_equity,
            'current_equity': current_equity
        }
```

**Drawdown Types Explained**:

- **Absolute drawdown**: The decline from the initial starting capital. If we started with USD 10,000 and equity is now USD 9,200, the absolute drawdown is USD 800 (8%). This measures how much of the original investment has been lost.

- **Relative drawdown (maximum drawdown)**: The decline from the highest equity point ever reached. If equity peaked at USD 12,000 and is now USD 10,500, the relative drawdown is USD 1,500 (12.5%). This is the most commonly cited drawdown metric because it measures the worst loss experienced relative to the best point.

- **Daily drawdown**: Decline from the equity at the start of the current trading day. Feeds into the Level 1 circuit breaker.

- **Weekly drawdown**: Decline from the equity at the start of the current trading week. Feeds into the Level 2 circuit breaker.

- **Monthly drawdown**: Decline from the equity at the start of the current calendar month. Feeds into the Level 3 circuit breaker.

### Drawdown Recovery Analysis

Understanding how long it takes to recover from a drawdown is critical for setting appropriate risk limits. The recovery time depends on the depth of the drawdown and the expected return rate of the system:

| Drawdown | Return Needed to Recover | Days to Recover (at 0.5% daily) | Days to Recover (at 0.2% daily) |
|---|---|---|---|
| 5% | 5.3% | ~11 days | ~27 days |
| 10% | 11.1% | ~22 days | ~56 days |
| 15% | 17.6% | ~35 days | ~88 days |
| 20% | 25.0% | ~49 days | ~125 days |
| 25% | 33.3% | ~65 days | ~167 days |
| 30% | 42.9% | ~84 days | ~214 days |
| 40% | 66.7% | ~131 days | ~333 days |
| 50% | 100.0% | ~199 days | ~500 days |

This table makes clear why the Level 4 circuit breaker triggers at 25% from peak: at a realistic return rate of 0.2% per day, a 25% drawdown takes over five months to recover from. A 50% drawdown takes nearly two years. This is why capital preservation is the prime directive.

### Monte Carlo Drawdown Estimation

MONEYMAKER runs a Monte Carlo simulation periodically (daily, during maintenance windows) to estimate the expected drawdown distribution for the current system parameters. This simulation:

1. Takes the actual win rate, win/loss ratio, and trade frequency from the past 90 days.
2. Generates 10,000 synthetic equity curves by randomly sampling trades.
3. Calculates the maximum drawdown of each synthetic curve.
4. Reports the 50th percentile (median expected drawdown), 95th percentile (bad-case drawdown), and 99th percentile (extreme drawdown).

If the 95th percentile expected drawdown exceeds the configured maximum acceptable drawdown, the system automatically reduces position sizes until the estimated drawdown falls within acceptable bounds. This forward-looking risk assessment complements the backward-looking drawdown tracking.

```python
import numpy as np

def monte_carlo_drawdown(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    trades_per_period: int,
    num_simulations: int = 10000,
    initial_equity: float = 10000.0
) -> dict:
    """
    Monte Carlo simulation of maximum drawdown.
    """
    max_drawdowns = []

    for _ in range(num_simulations):
        equity = initial_equity
        peak = initial_equity
        max_dd = 0.0

        for _ in range(trades_per_period):
            if np.random.random() < win_rate:
                equity += equity * avg_win
            else:
                equity -= equity * avg_loss

            if equity > peak:
                peak = equity

            dd = (peak - equity) / peak
            if dd > max_dd:
                max_dd = dd

        max_drawdowns.append(max_dd)

    max_drawdowns.sort()

    return {
        'median_drawdown': np.percentile(max_drawdowns, 50),
        'p95_drawdown': np.percentile(max_drawdowns, 95),
        'p99_drawdown': np.percentile(max_drawdowns, 99),
        'worst_drawdown': max(max_drawdowns),
        'mean_drawdown': np.mean(max_drawdowns)
    }
```

---

## 9.8 Exposure and Correlation Management

### Total Portfolio Exposure

Portfolio exposure represents the total amount of capital at risk across all open positions. MONEYMAKER tracks this in real time and enforces strict limits:

```
Maximum total exposure: 10% of equity
```

This means that if the account equity is USD 10,000, the sum of risk-at-loss across all open positions cannot exceed USD 1,000. Risk-at-loss for each position is calculated as:

```
risk_at_loss = position_size * (entry_price - stop_loss) * pip_value
```

Where the calculation accounts for the direction (buy vs sell) and the instrument's pip value.

### Per-Symbol Exposure Limits

No single symbol can account for more than 5% of total equity in risk exposure:

```
Maximum per-symbol exposure: 5% of equity
```

This prevents the system from becoming overly concentrated in a single instrument, even if the Algo Engine is generating multiple signals on that instrument across different timeframes or strategies.

### Per-Sector Exposure Limits

Correlated instruments are grouped into sectors, and each sector has a maximum exposure limit:

```
Maximum per-sector exposure: 8% of equity
```

Sector groupings for MONEYMAKER V1:

| Sector | Instruments | Rationale |
|---|---|---|
| Precious Metals | XAUUSD, XAGUSD | Highly correlated; move together on USD weakness and risk-off flows |
| Major Forex | EURUSD, GBPUSD, AUDUSD | Correlated via USD component; major pairs tend to move in sync vs USD |
| Crypto | BTCUSD, ETHUSD | Crypto assets are highly correlated with each other |
| Indices | SPX500, NAS100 | Stock indices move together on risk sentiment |

### Correlation Matrix

MONEYMAKER maintains a rolling 30-day Pearson correlation matrix between all traded instruments' daily returns. This matrix is updated at the end of each trading day:

```python
import pandas as pd
import numpy as np

def update_correlation_matrix(
    returns_data: pd.DataFrame,
    lookback_days: int = 30
) -> pd.DataFrame:
    """
    Calculate rolling correlation matrix from daily returns.

    Args:
        returns_data: DataFrame with columns = symbols,
                      rows = dates, values = daily returns
        lookback_days: Number of days to look back

    Returns:
        Correlation matrix as a DataFrame
    """
    recent_returns = returns_data.tail(lookback_days)
    correlation_matrix = recent_returns.corr(method='pearson')

    return correlation_matrix
```

When a new trade is proposed, the risk service checks the correlation between the proposed symbol and all currently open positions:

```
For each open position:
    corr = correlation_matrix[proposed_symbol][open_position_symbol]

    if abs(corr) > 0.7:
        # Highly correlated: treat as partially same position
        combined_exposure = current_exposure + proposed_exposure
        if combined_exposure > per_sector_limit:
            REJECT or REDUCE proposed position

    if abs(corr) < -0.7:
        # Negatively correlated: positions hedge each other
        # Allow full sizing but flag as hedged pair
        log_hedging_event()
```

### Currency Exposure Monitoring

In forex trading, every position involves two currencies. A long EURUSD position is simultaneously long EUR and short USD. If we are also long GBPUSD, we have doubled our USD short exposure. MONEYMAKER tracks net currency exposure:

```python
def calculate_currency_exposure(open_positions: list) -> dict:
    """
    Calculate net exposure to each currency.
    """
    currency_exposure = {}

    for pos in open_positions:
        base, quote = pos.symbol[:3], pos.symbol[3:]

        if pos.direction == "BUY":
            currency_exposure[base] = currency_exposure.get(base, 0) + pos.notional
            currency_exposure[quote] = currency_exposure.get(quote, 0) - pos.notional
        else:  # SELL
            currency_exposure[base] = currency_exposure.get(base, 0) - pos.notional
            currency_exposure[quote] = currency_exposure.get(quote, 0) + pos.notional

    return currency_exposure
```

If net exposure to any single currency exceeds 15% of equity, the risk service flags this as a concentration risk and may reduce future positions that would increase that exposure.

---

## 9.9 Market Condition Awareness

### Volatility Regime Detection

Markets cycle through distinct volatility regimes, and risk management must adapt accordingly. MONEYMAKER classifies the current volatility environment into four regimes:

```
Regime          ATR Ratio (current / 30-day avg)    Characteristics
-----------     --------------------------------    -------------------------
LOW             < 0.5                                Compression, pre-breakout
NORMAL          0.5 - 1.5                            Typical market conditions
HIGH            1.5 - 2.5                            Elevated volatility, news
EXTREME         > 2.5                                Flash crash, crisis, panic
```

Each regime triggers specific risk adjustments:

| Regime | Position Size Adj | Stop Width Adj | Max Positions | New Trades |
|---|---|---|---|---|
| LOW | 100% | 100% | 5 | Allowed (caution) |
| NORMAL | 100% | 100% | 5 | Allowed |
| HIGH | 75% | 120% | 3 | Allowed (selective) |
| EXTREME | 0% | 150% | 0 | HALTED |

During LOW volatility, the risk service adds an internal flag noting that volatility expansion is likely. It does not increase position sizes (a common mistake) because the direction of the expansion is unknown -- it could be in either direction.

### News Event Calendar Integration

MONEYMAKER integrates an economic calendar that tracks high-impact scheduled events. The risk management response to upcoming news:

```
Time Before Event    Action
-----------------    ------------------------------------------
60 minutes           Flag upcoming event in risk dashboard
30 minutes           Reduce maximum new position size by 50%
15 minutes           Halt new position opening
5 minutes            Tighten all open stops to 1.0x ATR
0 (event time)       No new trades, monitor existing positions
30 minutes after     Evaluate volatility, gradually resume
60 minutes after     Resume normal operations if volatility has subsided
```

High-impact events include: Non-Farm Payrolls, FOMC rate decisions, CPI releases, GDP releases, ECB/BOE rate decisions, and any central bank emergency announcements.

### Trading Session Awareness

Different trading sessions have different liquidity profiles, volatility characteristics, and trading patterns:

```
Session         Hours (UTC)     Characteristics
-----------     -----------     ----------------------------------------
Asian           00:00 - 08:00   Low volatility, range-bound, low liquidity
European        08:00 - 16:00   Increasing volatility, trend initiation
American        13:00 - 21:00   Highest volatility, highest liquidity
Overlap         13:00 - 16:00   Peak activity when EU and US overlap
```

Risk adjustments by session:

- **Asian session**: Reduce maximum position count to 3. Widen minimum stop to 2.0x ATR to avoid getting stopped out by low-liquidity noise.
- **European open**: Allow full positioning. Most trend moves initiate here.
- **EU/US overlap**: Allow full positioning. Highest liquidity provides best execution.
- **American close**: Reduce new positions to 50% size in the final hour. Spreads widen and liquidity thins.

### Weekend Risk

Markets close on Friday evening (23:00 UTC for forex) and reopen on Sunday evening (22:00 UTC). During this gap, positions are exposed to events that cannot be hedged or exited. Weekend risk management:

```
Friday Timeline:
  16:00 UTC   - Reduce maximum position count to 2
  18:00 UTC   - Halt new position opening
  20:00 UTC   - Tighten all stops to 1.0x ATR
  22:00 UTC   - Evaluate: close positions with < 1x ATR profit
  23:00 UTC   - Market close. Remaining positions carry weekend risk.

Weekend carry limit: No more than 2% of equity at risk over the weekend.
```

If total weekend exposure exceeds 2%, the risk service will close the positions with the smallest profit-to-risk ratio until the limit is met.

---

## 9.10 The 4-Tier Fallback Decision Engine

### Architecture

The 4-Tier Fallback Decision Engine is a cascading decision-making framework that ensures MONEYMAKER always has a structured basis for every trading decision, even when higher-tier strategies are unavailable or lacking confidence. The tiers are evaluated in order from most sophisticated to most conservative, with each tier serving as a fallback if the one above it cannot produce a reliable signal.

```
+-----------------------------------------------------------------------+
|                     TRADE DECISION PIPELINE                           |
|                                                                       |
|  Market Data ---> Feature Engineering ---> Decision Engine            |
|                                                                       |
|  +----------------------------+                                       |
|  | TIER 1: COPER Experience   |  Pattern match current market state   |
|  | Bank                       |  against historical outcomes.         |
|  | Confidence >= 70%? ------->|  YES --> Use COPER decision           |
|  |            |               |                                       |
|  |            NO              |                                       |
|  +------|---------------------+                                       |
|         v                                                             |
|  +----------------------------+                                       |
|  | TIER 2: Statistical Model  |  Query the statistical model for      |
|  | Prediction                 |  a prediction on current data.        |
|  | Confidence >= 60%? ------->|  YES --> Use model prediction         |
|  |            |               |                                       |
|  |            NO              |                                       |
|  +------|---------------------+                                       |
|         v                                                             |
|  +----------------------------+                                       |
|  | TIER 3: Technical Signal   |  Evaluate classical indicators:       |
|  | Consensus                  |  RSI, MACD, Bollinger, MA, ADX.       |
|  | 3+ indicators agree? ----->|  YES --> Use technical consensus      |
|  |            |               |                                       |
|  |            NO              |                                       |
|  +------|---------------------+                                       |
|         v                                                             |
|  +----------------------------+                                       |
|  | TIER 4: Conservative       |  Default to no action.                |
|  | No-Trade                   |  "When in doubt, stay out."           |
|  +----------------------------+                                       |
+-----------------------------------------------------------------------+
```

### Tier 1 -- COPER Experience Bank

COPER (Cumulative Outcome Pattern Experience Repository) is MONEYMAKER's pattern-matching memory system. It stores historical trade contexts -- the specific combination of market conditions, indicator values, regime classifications, and signal characteristics that preceded each past trade -- along with the actual outcome of that trade. When a new trading opportunity arises, COPER searches its database for the most similar historical patterns.

The matching process:

1. The current market state is encoded as a feature vector: regime, ATR level, RSI value, MACD histogram, trend strength, volatility percentile, session, day of week, and additional contextual features.
2. COPER searches the experience bank for the K nearest neighbors (K=10) using cosine similarity on the normalized feature vector.
3. If the average outcome of the K nearest matches exceeds a minimum confidence threshold (70%) and they agree on direction, COPER provides a signal with its confidence score.
4. The trade request includes `tier_source = "COPER"` for audit trail purposes.

COPER provides the most reliable signals because it is based on actual outcomes, not predictions. However, it can only provide signals for market states it has seen before. In novel conditions, it gracefully defers to Tier 2.

### Tier 2 -- Statistical Model Prediction

If COPER cannot find a sufficiently confident match, the decision falls to the statistical model. The model analyzes the current feature set and produces a prediction: BUY, SELL, or HOLD, along with a confidence score from 0 to 100.

The confidence threshold for Tier 2 is 60% by default, adjustable based on market conditions and spiral protection state. During a losing streak (5+ consecutive losses), the confidence threshold increases to 70%. During extreme volatility, it increases to 75%.

If the model's confidence is below the threshold, the decision falls through to Tier 3.

### Tier 3 -- Technical Signal Consensus

When neither COPER nor the statistical model provides a confident signal, MONEYMAKER falls back to classical technical analysis. This tier evaluates a set of well-established indicators and requires a consensus of at least 3 out of 5 agreeing on direction:

```
Indicators evaluated:
  1. RSI(14):       < 30 = BUY, > 70 = SELL, else NEUTRAL
  2. MACD:          MACD > Signal line = BUY, MACD < Signal line = SELL
  3. Bollinger(20,2): Price < lower band = BUY, Price > upper band = SELL
  4. MA Crossover:   Fast MA > Slow MA = BUY, Fast MA < Slow MA = SELL
  5. ADX(14):        ADX > 25 + DI+ > DI- = BUY, ADX > 25 + DI- > DI+ = SELL

Consensus rule:
  BUY signals >= 3  --> BUY
  SELL signals >= 3 --> SELL
  Otherwise          --> NEUTRAL (fall through to Tier 4)
```

Tier 3 trades are always sized at 50% of normal position size, reflecting the lower confidence level of pure technical analysis without statistical model or pattern-matching support.

### Tier 4 -- Conservative / No-Trade

If no tier produces a signal, the default action is no action. MONEYMAKER does nothing. It waits. This is the correct behavior: there is no requirement that the system must always be in a position. In fact, the most profitable trading systems spend significant time flat (no open positions), waiting for high-probability setups.

The Tier 4 disposition: "When in doubt, stay out." This is not passivity -- it is active risk management. The absence of a position is itself a position, and it is the safest one available.

### Tier Logging and Analysis

Every trade decision includes the tier that produced it. This enables retrospective analysis of which tiers generate the best risk-adjusted returns:

```sql
-- Example query: win rate by tier source
SELECT
    tier_source,
    COUNT(*) as total_trades,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
    ROUND(100.0 * SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate,
    ROUND(AVG(pnl), 2) as avg_pnl,
    ROUND(SUM(pnl), 2) as total_pnl
FROM trade_log
WHERE close_time >= NOW() - INTERVAL '30 days'
GROUP BY tier_source
ORDER BY total_pnl DESC;
```

If a tier consistently underperforms, its threshold can be adjusted or it can be temporarily disabled.

---

## 9.11 Kill Switch System

### Overview

The kill switch is the emergency brake of the MONEYMAKER ecosystem. It is the last resort when normal risk management is insufficient or when an abnormal situation requires immediate cessation of all trading activity. Unlike circuit breakers, which are graduated responses to cumulative losses, the kill switch is a binary, all-or-nothing shutdown mechanism designed for crisis situations.

### Automatic Kill Switch Triggers

The kill switch activates automatically under the following conditions:

1. **Circuit Breaker Escalation**: Level 4 circuit breaker triggers.
2. **Anomaly Detection**: The system detects behavior that falls outside normal parameters:
   - More than 10 position changes (opens + closes) within 60 seconds (possible runaway loop)
   - P&L change exceeding 5% within 60 seconds (possible error or extreme event)
   - Position size exceeding 3x the maximum configured limit (possible sizing bug)
   - Account equity reading of zero or negative (possible data corruption or margin call)
3. **System Health Failure**:
   - Risk service heartbeat missed for 30 seconds by the execution bridge
   - Database connection lost for 60 seconds
   - Three consecutive failed risk evaluations (possible service malfunction)
4. **Network Kill Switch**: Connectivity to the MT5 broker is lost for more than 60 seconds. If we cannot monitor our positions, we cannot manage risk, so we must close everything upon reconnection.

### Manual Kill Switch

The kill switch can be triggered manually through three interfaces:

1. **Dashboard**: A prominently displayed red button on the risk monitoring dashboard. Single click with confirmation dialog.
2. **API**: A gRPC call to the risk service: `TriggerKillSwitch(reason="manual: <description>")`.
3. **Telegram**: The command `/kill` sent to MONEYMAKER's Telegram bot, which must be followed by a confirmation response within 30 seconds.

### Kill Switch Execution Sequence

When the kill switch activates, the following sequence executes in strict order:

```
KILL SWITCH ACTIVATED
        |
        v
Step 1: STOP all pending orders in MT5
        |  - Query all pending orders
        |  - Cancel each one with market cancel
        |  - Verify cancellation
        v
Step 2: CLOSE all open positions at market
        |  - Query all open positions
        |  - Close each at market price
        |  - Verify closure
        |  - Log fill price and slippage
        v
Step 3: DISABLE all trading services
        |  - Set risk gate to REJECT ALL mode
        |  - Send halt signal to Algo Engine
        |  - Set execution bridge to read-only mode
        v
Step 4: SEND emergency notifications
        |  - Telegram: immediate alert with position summary
        |  - Email: full details with equity state
        |  - Dashboard: update status to EMERGENCY
        v
Step 5: LOG complete state for post-mortem
        |  - All open positions at time of trigger
        |  - All pending orders at time of trigger
        |  - Current equity, balance, margin state
        |  - All risk metrics
        |  - Trigger reason and type
        |  - System logs from last 60 minutes
        v
Step 6: WAIT for manual reset
        |  - System enters lockdown state
        |  - All trading remains disabled
        |  - Only monitoring continues
        |  - Health endpoints report KILLED status
```

### Kill Switch Reset Procedure

The kill switch can only be reset manually. The reset procedure is intentionally cumbersome to prevent accidental re-enablement:

1. Operator logs into the dashboard or Telegram.
2. Reviews the kill switch event log and post-mortem data.
3. Identifies the root cause of the trigger.
4. Executes the reset command: `/reset_kill_switch --reason "<explanation>" --confirm`.
5. The system enters a 15-minute observation period where it is online but only allows paper (simulated) trades.
6. If no anomalies are detected during the observation period, live trading is re-enabled at 25% of normal position size.
7. Normal sizing is gradually restored over the next 4 hours.

---

## 9.12 Margin and Leverage Management

### Real-Time Margin Monitoring

Margin management is the interface between MONEYMAKER's internal risk management and the broker's risk management. The broker enforces its own margin requirements: if equity falls below the required margin for open positions, the broker issues a margin call and may liquidate positions at unfavorable prices. MONEYMAKER must prevent this scenario by maintaining a comfortable margin buffer at all times.

Key margin metrics tracked in real time:

```
Margin Utilization = (Margin Used / Equity) * 100%

Free Margin Ratio = (Free Margin / Equity) * 100%

Effective Leverage = Total Notional Exposure / Equity
```

### Margin Utilization Limits

MONEYMAKER enforces a hard maximum margin utilization of 50%:

```
NEVER allow margin_utilization > 50%
```

This means that at least half of the account equity is always free and uncommitted. The rationale:

- At 50% utilization, a 50% adverse move in portfolio value would bring equity to the margin call level. For the instruments MONEYMAKER trades (primarily forex and gold), a 50% overnight move is virtually unprecedented.
- The 50% buffer provides ample room for unrealized losses on existing positions without triggering a margin call.
- It leaves sufficient free margin to manage positions (closing requires margin for the spread).

Alert thresholds:

| Margin Utilization | Status | Action |
|---|---|---|
| < 30% | GREEN | Normal operations |
| 30% - 40% | YELLOW | Warning: reduce new position sizes by 25% |
| 40% - 50% | ORANGE | Alert: halt new positions, consider reducing existing |
| > 50% | RED | Emergency: close smallest positions until below 40% |

### Leverage Limits

Even if margin utilization is within limits, MONEYMAKER monitors effective leverage per position and in aggregate:

```
Maximum per-position leverage: 10:1
Maximum aggregate leverage: 20:1
```

These limits are typically well below what brokers offer (often 100:1 or more for forex). MONEYMAKER deliberately uses a fraction of available leverage because high leverage amplifies both gains and losses, and the asymmetric risk-reward philosophy requires that losses be strictly contained.

### Proactive Margin Call Prevention

MONEYMAKER does not wait for the broker to issue a margin call. Instead, it monitors margin utilization continuously and takes proactive action:

```python
def evaluate_margin_health(
    equity: float,
    margin_used: float,
    free_margin: float,
    open_positions: list
) -> dict:
    """
    Evaluate margin health and determine if action is needed.
    """
    utilization = margin_used / equity if equity > 0 else 1.0
    free_ratio = free_margin / equity if equity > 0 else 0.0

    actions = []

    if utilization > 0.50:
        # Critical: close positions to reduce margin
        positions_by_loss = sorted(open_positions, key=lambda p: p.unrealized_pnl)
        for pos in positions_by_loss:
            actions.append(('CLOSE', pos.ticket, 'margin_critical'))
            projected_util = (margin_used - pos.margin) / equity
            if projected_util < 0.40:
                break

    elif utilization > 0.40:
        actions.append(('ALERT', 'margin_warning',
                        f'Margin utilization at {utilization:.1%}'))
        actions.append(('RESTRICT', 'halt_new_positions',
                        'Margin above 40%'))

    elif utilization > 0.30:
        actions.append(('ALERT', 'margin_caution',
                        f'Margin utilization at {utilization:.1%}'))
        actions.append(('REDUCE', 'new_position_size', 0.75))

    return {
        'utilization': utilization,
        'free_ratio': free_ratio,
        'status': 'RED' if utilization > 0.5
                  else 'ORANGE' if utilization > 0.4
                  else 'YELLOW' if utilization > 0.3
                  else 'GREEN',
        'actions': actions
    }
```

---

## 9.13 Confidence Gating System

### The Three Sequential Gates

Every trade decision must pass through three sequential gates before it can reach the execution bridge. These gates evaluate different aspects of system readiness and market appropriateness. Failure at any gate results in the trade being modified (reduced size) or rejected entirely.

```
Trade Request
     |
     v
+------------------+     FAIL     +-------------------+
| GATE 1:          | -----------> | Reduce size to    |
| Maturity Gate    |              | 25% or REJECT     |
| (Is model ready?)|              +-------------------+
+--------+---------+
         | PASS
         v
+------------------+     FAIL     +-------------------+
| GATE 2:          | -----------> | Reduce size to    |
| Drift Detection  |              | 50% or REJECT     |
| (Has market      |              +-------------------+
|  changed?)       |
+--------+---------+
         | PASS
         v
+------------------+     FAIL     +-------------------+
| GATE 3:          | -----------> | Halt trading per  |
| Silence Rule     |              | spiral protocol   |
| (Recent losses?) |              +-------------------+
+--------+---------+
         | PASS
         v
   Risk Evaluation
   (position sizing, stops, exposure checks)
```

### Gate 1 -- Maturity Gate

The Maturity Gate verifies that the statistical model currently in production is sufficiently calibrated and validated before allowing its predictions to drive real trades. This prevents the situation where a freshly initialized or poorly calibrated model makes random or destructive decisions.

**Checks performed:**

1. **Minimum calibration cycles**: The model must have completed at least N calibration cycles (configurable, default 50). A model that has been calibrated for only 5 cycles has not yet converged and its predictions are unreliable.

2. **Minimum backtest performance**: The model's backtest Sharpe ratio on the most recent validation set must exceed a minimum threshold (default 0.5). A model with a Sharpe below 0.5 is not demonstrating edge.

3. **Minimum sample size**: The model must have been evaluated on at least 200 validation trades. A model evaluated on 20 trades has insufficient statistical power to demonstrate reliability.

4. **Model age**: The model must have been calibrated within the last 30 days. A model older than 30 days is using stale data and may not reflect current market dynamics.

If any of these checks fail:

- Confidence score for Tier 2 (statistical model) is set to 0 (model bypassed entirely).
- The decision engine falls through to Tier 3 (technical signals).
- Position sizing is reduced to 25% of normal (reflecting the loss of the primary decision-making tier).

### Gate 2 -- Drift Detection Gate

Market regime changes can render a model's training data irrelevant. The Drift Detection Gate monitors for distribution shift between the training data and current live data.

**Detection methods:**

1. **Feature distribution comparison**: Compare the distribution of key input features (ATR, RSI, volume, volatility) over the last 7 days against the distribution in the training set. Use the Kolmogorov-Smirnov test with a significance level of 0.05. If more than 30% of features show statistically significant drift, the gate triggers.

2. **Prediction confidence decay**: Track the average prediction confidence over a rolling 7-day window. If confidence has declined by more than 20% from the 30-day average, the gate triggers. This is an indirect signal that the model is encountering data patterns it was not trained on.

3. **Regime mismatch**: Compare the current detected market regime (from the regime classifier) with the regimes present in the training data. If the current regime was underrepresented in training (less than 10% of training samples), flag a regime mismatch.

If the drift gate triggers:

- Position sizing reduced to 50% for Tier 2 decisions.
- Alert sent: "Model drift detected. Consider retraining."
- Flag set to initiate emergency model recalibration.

### Gate 3 -- Silence Rule Gate

The Silence Rule Gate integrates with the spiral protection system (Section 9.6). If the spiral protection has detected a losing streak at or above the threshold level, this gate blocks or reduces new trades.

**Implementation:**

```python
def silence_rule_gate(spiral_state: SpiralProtection, symbol: str,
                       strategy: str) -> tuple:
    """
    Returns (pass: bool, size_multiplier: float, halt_hours: int)
    """
    should_halt, halt_hours = spiral_state.should_halt(symbol, strategy)

    if should_halt:
        return (False, 0.0, halt_hours)

    multiplier = spiral_state.get_size_multiplier(symbol, strategy)

    if multiplier < 0.25:
        # Severe reduction effectively means no trade
        return (False, 0.0, 0)

    return (True, multiplier, 0)
```

### Combined Confidence Score

After all three gates are evaluated, the risk service calculates a combined confidence score that factors into the final position sizing:

```
combined_confidence = model_confidence
                      * maturity_factor      (1.0 if passed, 0.25 if failed)
                      * drift_factor         (1.0 if passed, 0.50 if failed)
                      * spiral_factor        (from spiral protection multiplier)

If combined_confidence < 30%: REJECT trade
If combined_confidence 30-50%: Trade at 50% size
If combined_confidence 50-70%: Trade at 75% size
If combined_confidence > 70%: Trade at full size
```

---

## 9.14 Audit Trail and Compliance

### Immutable Audit Log

Every risk decision in MONEYMAKER is recorded in an immutable audit log. "Immutable" means append-only: records can be inserted but never updated or deleted. This is enforced at the database level through PostgreSQL row-level security policies and a trigger that prevents UPDATE and DELETE operations on the risk_audit_log table:

```sql
-- Prevent modifications to audit log
CREATE OR REPLACE FUNCTION prevent_audit_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit log records cannot be modified or deleted';
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_log_immutable
    BEFORE UPDATE OR DELETE ON risk_audit_log
    FOR EACH ROW
    EXECUTE FUNCTION prevent_audit_modification();
```

### Audit Record Fields

Each audit record contains the complete context of the risk decision:

| Field | Type | Description |
|---|---|---|
| timestamp | TIMESTAMPTZ | Exact time of risk evaluation |
| request_id | UUID | Unique identifier linking to the original trade request |
| symbol | VARCHAR | Trading instrument |
| direction | VARCHAR | BUY or SELL |
| requested_lots | DECIMAL | Position size requested by Algo Engine |
| approved_lots | DECIMAL | Position size approved by risk gate (0 if rejected) |
| entry_price | DECIMAL | Intended entry price |
| stop_loss | DECIMAL | Approved stop-loss level |
| take_profit | DECIMAL | Approved take-profit level |
| model_confidence | DECIMAL | Strategy confidence score |
| decision | VARCHAR | APPROVED, MODIFIED, or REJECTED |
| reason | TEXT | Human-readable explanation of the decision |
| risk_flags | TEXT[] | Array of all risk flags that were raised |
| account_equity | DECIMAL | Account equity at time of decision |
| drawdown_pct | DECIMAL | Current drawdown percentage |
| margin_util_pct | DECIMAL | Current margin utilization percentage |
| portfolio_heat | DECIMAL | Total portfolio risk exposure |
| consecutive_losses | INT | Current consecutive loss count |
| circuit_breaker_status | VARCHAR | Current circuit breaker state |
| tier_source | VARCHAR | Which decision tier produced the signal |
| gate_results | JSONB | Detailed results from all three confidence gates |

### Daily Risk Reports

At the end of each trading day (21:00 UTC for US session close), MONEYMAKER automatically generates a daily risk report. This report is stored in the database and sent to Telegram:

```
=== MONEYMAKER DAILY RISK REPORT ===
Date: 2026-02-21

EQUITY STATUS
  Starting Equity:   $10,245.50
  Ending Equity:     $10,312.80
  Daily P&L:         +$67.30 (+0.66%)
  Peak Equity:       $10,350.00
  Current Drawdown:  -0.36% from peak

TRADE SUMMARY
  Total Decisions:   12
  Approved:          8  (66.7%)
  Modified:          2  (16.7%)
  Rejected:          2  (16.7%)
  Rejection Reasons:
    - Spiral protection (50% reduction): 1
    - Margin utilization > 40%: 1

RISK METRICS
  Sharpe Ratio (30d):     1.45
  Sortino Ratio (30d):    2.10
  Max Drawdown (30d):     -3.2%
  Win Rate (30d):         58%
  Avg Win/Loss Ratio:     1.85
  VaR (95%, daily):       -1.2%
  CVaR (95%, daily):      -1.8%

CIRCUIT BREAKER STATUS
  Level 1 (Session):  ARMED (threshold: -2.0%, current: -0.12%)
  Level 2 (Weekly):   ARMED (threshold: -5.0%, current: +1.3%)
  Level 3 (Monthly):  ARMED (threshold: -10.0%, current: +3.5%)
  Level 4 (Maximum):  ARMED (threshold: -25.0%, current: -0.36%)

SPIRAL STATUS
  Global consecutive losses: 0
  Per-symbol:  XAUUSD: 0, EURUSD: 1, BTCUSD: 0

EXPOSURE
  Total open risk:   2.3% of equity
  Margin utilization: 18.5%
  Open positions: 2

TIER DISTRIBUTION
  COPER:       3 trades (75% win rate)
  ML Model:    4 trades (50% win rate)
  Technical:   1 trade  (100% win rate)
  Conservative: 0 (no trades)
```

### Weekly Risk Review

Every Sunday, the system generates a comprehensive weekly review that includes statistical analysis, distribution plots of trade outcomes, and comparison with historical performance. This review is designed to be actionable -- it highlights specific areas where risk parameters might need adjustment.

### Regulatory Compliance Considerations

While MONEYMAKER is currently a personal trading system, the audit trail is designed to be compliant with regulatory requirements should the system ever manage third-party capital:

- All trades are timestamped to millisecond precision.
- All decisions are logged with full reasoning.
- Audit records are immutable and tamper-evident.
- The system maintains a complete record of all risk events and interventions.
- Position sizing methodology and risk limits are documented and verifiable.

---

## 9.15 Risk Monitoring Dashboard

### Real-Time Display Components

The risk monitoring dashboard is a Grafana-based interface that provides real-time visibility into all risk metrics. It is organized into panels that answer the critical questions an operator needs to monitor:

**Panel 1: Equity Curve**

- Real-time equity curve overlaid with balance curve.
- Shaded drawdown areas below the peak equity line.
- Circuit breaker trigger levels shown as horizontal reference lines.
- Annotations for circuit breaker events, kill switch events, and spiral activations.

**Panel 2: Drawdown Monitor**

- Current drawdown percentage (large display).
- Drawdown by timeframe: daily, weekly, monthly, from peak.
- Color-coded: green (< 2%), yellow (2-5%), orange (5-10%), red (> 10%).

**Panel 3: Open Position Risk**

- Table of all open positions with: symbol, direction, size, entry price, current price, unrealized P&L, stop-loss distance, risk-at-loss as % of equity.
- Total portfolio heat (aggregate risk).

**Panel 4: Circuit Breaker Status**

- Visual indicators for each circuit breaker level (green = armed, yellow = cooling down, red = triggered).
- Progress bars showing current value relative to trigger threshold.

**Panel 5: Risk Metrics**

- Rolling 30-day Sharpe ratio, Sortino ratio, Calmar ratio.
- Maximum drawdown over 30, 90, and 365 days.
- Value at Risk (VaR) at 95% and 99% confidence.
- Conditional VaR (Expected Shortfall) at 95%.
- Win rate, average win, average loss, expectancy.

**Panel 6: Kill Switch Controls**

- Manual kill switch button (red, prominent).
- Current kill switch status.
- Resume button (available only after kill switch reset procedure).
- Recent kill switch events.

**Panel 7: Alert History**

- Chronological list of all risk alerts.
- Filterable by severity: INFO, WARNING, CRITICAL, EMERGENCY.
- Clickable alerts that link to full audit log entries.

**Panel 8: Margin and Exposure**

- Margin utilization gauge (0-100%).
- Effective leverage display.
- Exposure breakdown by symbol and by sector.
- Correlation matrix heatmap.

### Alerting Rules

Grafana alerting rules trigger notifications based on the dashboard metrics:

```yaml
# Risk alerting rules
alerts:
  - name: "Drawdown Warning"
    condition: drawdown_pct > 5
    severity: WARNING
    channels: [telegram]

  - name: "Drawdown Critical"
    condition: drawdown_pct > 10
    severity: CRITICAL
    channels: [telegram, email]

  - name: "Margin Warning"
    condition: margin_utilization > 30
    severity: WARNING
    channels: [telegram]

  - name: "Margin Critical"
    condition: margin_utilization > 45
    severity: CRITICAL
    channels: [telegram, email]

  - name: "Risk Service Down"
    condition: risk_service_heartbeat_age > 15s
    severity: EMERGENCY
    channels: [telegram, email, sms]

  - name: "Spiral Detected"
    condition: consecutive_losses >= 3
    severity: WARNING
    channels: [telegram]

  - name: "Kill Switch Activated"
    condition: kill_switch_active == true
    severity: EMERGENCY
    channels: [telegram, email, sms]
```

---

## 9.16 Testing and Validation

### Backtesting Risk Systems

Before deploying any risk management configuration to live trading, it must be validated through comprehensive backtesting against historical data. The backtesting framework replays historical market data through the complete risk management pipeline, simulating:

- Position sizing decisions based on historical equity curve.
- Stop-loss triggers and trailing stop adjustments.
- Circuit breaker activations and their impact on subsequent trading.
- Spiral protection activations and position size reductions.
- The interaction between all risk layers operating simultaneously.

The backtest produces a report comparing risk-managed returns against unmanaged returns, demonstrating the value of each risk layer:

```
BACKTEST RESULTS: 2024-01-01 to 2025-12-31

                          No Risk Mgmt    With Risk Mgmt
---------------------------------------------------------
Total Return:             +145.3%         +82.6%
Max Drawdown:             -42.7%          -14.3%
Sharpe Ratio:             0.85            1.62
Sortino Ratio:            1.12            2.45
Calmar Ratio:             0.34            0.58
Win Rate:                 54.2%           54.2%
Avg Win/Loss:             1.82            1.79
Circuit Breaker Events:   N/A             8
Kill Switch Events:       N/A             1
Spiral Activations:       N/A             12
Account Survival:         NO (margin call) YES
```

The backtesting framework is deliberately conservative: if the risk management system produces lower total returns but dramatically better risk-adjusted returns and account survival, it is doing its job correctly. The purpose of risk management is not to maximize returns -- it is to ensure survival.

### Stress Testing

MONEYMAKER's risk systems are stress-tested against the most extreme market events in recent history:

1. **2008 Financial Crisis**: Simulate the September-October 2008 period when daily moves of 5-10% were common. Verify that circuit breakers activate correctly and prevent catastrophic drawdown.

2. **2015 Swiss Franc Flash Crash**: On January 15, 2015, the Swiss National Bank removed the EUR/CHF floor, causing EURCHF to drop 30% in minutes. Test the kill switch response time and verify that the system handles extreme gap risk.

3. **2020 COVID Crash**: Simulate the February-March 2020 period when volatility spiked to historic levels. Verify that volatility regime detection correctly shifts to EXTREME and halts trading.

4. **2022 Crypto Winter**: Simulate extended declining market conditions. Verify that spiral protection and circuit breakers prevent the system from bleeding out during a prolonged bear market.

5. **Flash crash scenarios**: Synthetic scenarios where price drops 5% in 60 seconds and recovers. Test that the anomaly detection triggers the kill switch before positions are opened into the crash.

### Monte Carlo Validation

Beyond historical stress tests, Monte Carlo simulation generates thousands of synthetic market scenarios to validate risk parameters:

```python
def stress_test_risk_params(
    risk_config: dict,
    num_scenarios: int = 50000,
    scenario_length_trades: int = 500
) -> dict:
    """
    Monte Carlo stress test of risk configuration.

    Generates random trade sequences and measures:
    - Probability of ruin (equity <= 0)
    - Probability of max drawdown > 25%
    - Probability of circuit breaker Level 3+
    - Expected maximum drawdown distribution
    """
    results = {
        'ruin_count': 0,
        'severe_dd_count': 0,
        'l3_breaker_count': 0,
        'max_drawdowns': [],
        'final_equities': []
    }

    for _ in range(num_scenarios):
        sim = simulate_trading_with_risk(risk_config, scenario_length_trades)
        results['max_drawdowns'].append(sim.max_drawdown)
        results['final_equities'].append(sim.final_equity)

        if sim.final_equity <= 0:
            results['ruin_count'] += 1
        if sim.max_drawdown > 0.25:
            results['severe_dd_count'] += 1
        if sim.l3_breaker_triggered:
            results['l3_breaker_count'] += 1

    return {
        'ruin_probability': results['ruin_count'] / num_scenarios,
        'severe_dd_probability': results['severe_dd_count'] / num_scenarios,
        'l3_probability': results['l3_breaker_count'] / num_scenarios,
        'median_max_dd': np.median(results['max_drawdowns']),
        'p95_max_dd': np.percentile(results['max_drawdowns'], 95),
        'p99_max_dd': np.percentile(results['max_drawdowns'], 99),
        'median_final_equity': np.median(results['final_equities']),
    }
```

The acceptance criteria for a risk configuration:

| Metric | Threshold | Rationale |
|---|---|---|
| Probability of ruin | < 0.01% | Virtually impossible to blow up the account |
| P95 max drawdown | < 25% | 95th percentile drawdown within acceptable range |
| P99 max drawdown | < 35% | Even extreme scenarios do not cause catastrophic loss |
| Probability of L3+ breaker | < 5% | Monthly breakers should be rare events |

### Unit Testing

Every individual risk rule is unit-tested in isolation. The test suite includes hundreds of test cases covering:

- **Position sizing**: Verify ATR-based sizing, Kelly calculations, correlation adjustments, and all cap constraints produce correct results for a range of inputs.
- **Stop-loss logic**: Verify trailing stops never widen, break-even triggers at correct level, time-based stops fire at correct time.
- **Circuit breakers**: Verify trigger thresholds, hysteresis behavior, reset conditions, and correct action sequences.
- **Spiral protection**: Verify consecutive loss counting, progressive size reduction, halt durations, and recovery protocol.
- **Kill switch**: Verify all trigger conditions, execution sequence, and reset procedure.
- **Confidence gates**: Verify maturity checks, drift detection, and silence rule integration.

Example unit test:

```python
def test_trailing_stop_never_widens_for_long():
    """The trailing stop for a BUY position must never move downward."""
    current_stop = 2640.00

    # Price moves up -- stop should move up
    new_stop = calculate_trailing_stop(
        direction="BUY", entry_price=2650.00, current_price=2665.00,
        current_stop=current_stop, atr_value=5.50, trail_multiplier=1.0
    )
    assert new_stop >= current_stop, "Trailing stop moved down for BUY"

    # Price moves down -- stop should NOT move down
    new_stop_2 = calculate_trailing_stop(
        direction="BUY", entry_price=2650.00, current_price=2655.00,
        current_stop=new_stop, atr_value=5.50, trail_multiplier=1.0
    )
    assert new_stop_2 >= new_stop, "Trailing stop widened on pullback"


def test_circuit_breaker_l1_triggers_at_threshold():
    """Level 1 breaker triggers when daily loss exceeds 2%."""
    breaker = SessionCircuitBreaker(threshold_pct=0.02)
    breaker.on_session_start(10000.0)

    # Loss of 1.5% -- should not trigger
    assert breaker.evaluate(9850.0) == False

    # Loss of 2.0% -- should trigger
    assert breaker.evaluate(9800.0) == True

    # Should remain triggered
    assert breaker.evaluate(9850.0) == True


def test_spiral_protection_progressive_reduction():
    """Spiral protection reduces size progressively with consecutive losses."""
    sp = SpiralProtection()
    symbol = "XAUUSD"
    strategy = "ML_MODEL"

    # Record 5 consecutive losses
    for _ in range(5):
        sp.record_trade_result(symbol, strategy, is_win=False)

    mult = sp.get_size_multiplier(symbol, strategy)
    assert mult == 0.50, f"Expected 50% reduction at 5 losses, got {mult}"

    # Record a win -- should start recovery
    sp.record_trade_result(symbol, strategy, is_win=True)
    assert sp.symbol_losses[symbol] == 0
```

### Integration Testing

Integration tests verify that the risk management components work correctly when combined with the Algo Engine and execution bridge. These tests run against a simulated MT5 environment (paper trading mode):

1. **Risk gate blocks bad trades**: Send a trade request that violates position sizing limits. Verify the risk gate returns REJECTED.
2. **Risk gate modifies oversized trades**: Send a trade request with excessive lots. Verify the risk gate returns MODIFIED with reduced lots.
3. **Circuit breaker halts trading**: Simulate a series of losing trades that trigger a circuit breaker. Verify that subsequent trade requests are rejected until the breaker resets.
4. **Kill switch closes all positions**: Trigger a kill switch and verify that all open positions in the simulated MT5 are closed and all pending orders are cancelled.
5. **End-to-end flow**: Run a complete trading session with the Algo Engine generating signals, the risk gate evaluating them, and the execution bridge placing trades. Verify all audit logs are correct and all risk metrics are accurate.

### Paper Trading Validation

Before any risk configuration change is deployed to a live account, it must be validated on a paper trading (demo) account for a minimum of 2 weeks:

1. The demo account runs the exact same code, configuration, and market data as the live account.
2. All risk systems are active and logging.
3. At the end of the validation period, the risk metrics from the demo are compared against the expected values from backtesting.
4. If the metrics are within acceptable tolerance (maximum drawdown within 1.5x backtest expectation, circuit breaker frequency within 2x), the configuration is approved for live deployment.
5. If metrics deviate significantly, the configuration is reviewed and adjusted before another validation cycle.

This validation process ensures that changes to risk parameters are never applied directly to a live account without empirical confirmation that they behave as expected in real market conditions.

---

## Configuration Reference

The complete risk management configuration is maintained in a single YAML file. All thresholds, limits, and parameters are configurable without code changes:

```yaml
# risk_config.yaml -- MONEYMAKER V1 Risk Management Configuration

risk_management:
  enabled: true
  mode: "live"  # "live", "paper", "backtest"

  position_sizing:
    method: "atr_kelly"           # "fixed", "atr", "kelly", "atr_kelly"
    fixed_risk_pct: 0.01          # 1% risk per trade (used if method=fixed)
    max_risk_pct: 0.02            # Absolute maximum 2% per trade
    kelly_fraction: 0.5           # Half-Kelly
    max_lots_per_trade: 1.0       # Maximum lot size regardless of calculation
    max_open_positions: 5
    min_lots: 0.01
    lot_step: 0.01

  stop_loss:
    sl_atr_multiplier: 1.5
    tp1_atr_multiplier: 2.0
    tp2_atr_multiplier: 3.0
    tp3_atr_multiplier: 5.0
    tp1_close_pct: 0.50           # Close 50% at TP1
    tp2_close_pct: 0.30           # Close 30% at TP2
    tp3_close_pct: 0.20           # Close 20% at TP3
    trailing_start_atr: 1.0       # Start trailing at 1x ATR profit
    trailing_distance_atr: 1.0    # Trail at 1x ATR
    breakeven_trigger_atr: 1.0    # Move to breakeven at 1x ATR
    max_holding_hours_scalp: 4
    max_holding_hours_intraday: 24
    max_holding_days_swing: 5
    never_widen_stop: true         # IRON RULE: cannot be set to false

  circuit_breakers:
    level_1:
      threshold_pct: 0.02
      scope: "session"
      action: "halt_new_trades"
      reset: "next_session"
      hysteresis_pct: 0.01
    level_2:
      threshold_pct: 0.05
      scope: "weekly"
      action: "close_all_halt_24h"
      resume_size_reduction: 0.50
      hysteresis_pct: 0.03
    level_3:
      threshold_pct: 0.10
      scope: "monthly"
      action: "close_all_halt_7d"
      require_manual_resume: true
      recovery_week1_size: 0.25
      recovery_week2_size: 0.50
    level_4:
      threshold_pct: 0.25
      scope: "peak_equity"
      action: "emergency_shutdown"
      require_manual_reset: true

  spiral_protection:
    enabled: true
    thresholds:
      - losses: 3
        size_reduction: 0.25
      - losses: 5
        size_reduction: 0.50
        min_confidence_increase: 0.10
      - losses: 7
        halt_hours: 4
      - losses: 10
        halt_hours: 24
        trigger_model_review: true
    recovery_wins_to_restore: 4
    scopes: ["global", "symbol", "strategy"]

  exposure:
    max_total_exposure_pct: 0.10
    max_per_symbol_pct: 0.05
    max_per_sector_pct: 0.08
    correlation_threshold_high: 0.70
    correlation_threshold_medium: 0.30
    correlation_lookback_days: 30
    max_currency_exposure_pct: 0.15

  margin:
    max_utilization_pct: 0.50
    warning_utilization_pct: 0.30
    critical_utilization_pct: 0.40
    max_per_position_leverage: 10
    max_aggregate_leverage: 20

  confidence_gates:
    maturity:
      min_training_epochs: 50
      min_backtest_sharpe: 0.50
      min_validation_trades: 200
      max_model_age_days: 30
    drift:
      ks_significance: 0.05
      max_feature_drift_pct: 0.30
      confidence_decay_threshold: 0.20
    silence:
      integrated_with_spiral: true

  volatility:
    high_threshold_ratio: 1.5
    very_high_threshold_ratio: 2.0
    extreme_threshold_ratio: 3.0
    high_size_reduction: 0.75
    very_high_size_reduction: 0.50
    extreme_action: "halt"

  weekend:
    reduce_positions_at: "16:00 UTC"
    halt_new_at: "18:00 UTC"
    tighten_stops_at: "20:00 UTC"
    max_weekend_risk_pct: 0.02

  notifications:
    telegram:
      enabled: true
      chat_id: "${TELEGRAM_CHAT_ID}"
      bot_token: "${TELEGRAM_BOT_TOKEN}"
    email:
      enabled: true
      recipient: "${ALERT_EMAIL}"
      smtp_server: "${SMTP_SERVER}"
    sms:
      enabled: false

  kill_switch:
    auto_triggers:
      max_position_changes_per_minute: 10
      max_pnl_change_per_minute_pct: 0.05
      max_position_size_multiplier: 3.0
      heartbeat_timeout_seconds: 30
      db_timeout_seconds: 60
      network_timeout_seconds: 60
    reset:
      observation_period_minutes: 15
      initial_size_pct: 0.25
      full_restore_hours: 4
```

---

## Summary

The Risk Management and Safety Systems described in this document form the most critical layer of the MONEYMAKER V1 ecosystem. They embody the principle that in algorithmic trading, the first and most important job is not to make money -- it is to not lose money catastrophically. Every component described here -- from position sizing through circuit breakers, spiral protection, kill switches, confidence gates, and monitoring dashboards -- works together as an integrated defense system that protects capital under all market conditions.

The risk management service operates independently, has absolute veto authority over all trading decisions, and cannot be overridden by the Algo Engine or any other component. It implements defense in depth through multiple overlapping layers, each designed to catch failures that pass through the layers above. It monitors the system in real time, logs every decision immutably, and provides the operator with full visibility into the system's risk state.

No amount of alpha generation, no sophistication of algorithmic modeling, and no elegance of execution can compensate for inadequate risk management. This is the immune system of MONEYMAKER, and it must be the strongest, most reliable, and most rigorously tested component in the entire ecosystem.

The cardinal rule stands: **survival first, profits second**. Everything in this document exists to enforce that rule.

*fine del documento 9 -- Risk Management and Safety Systems*
