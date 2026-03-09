# GOLIATH V1 — Technical Reference for Traditional Architecture Migration

**Version:** 1.0
**Classification:** Internal — Engineering Team
**Target Audience:** Senior Software Engineers and Developers
**Purpose:** Complete technical specification of the GOLIATH V1 algorithmic trading ecosystem, with emphasis on translating its AI-driven architecture into a deterministic, rule-based equivalent suitable for 24/7 automated Forex and CFD trading via MetaTrader 5.

---

# PART I: FINANCIAL DOMAIN KNOWLEDGE

---

## Chapter 1 — Forex and CFD Market Fundamentals

### 1.1 Market Structure

The foreign exchange market is a decentralized over-the-counter (OTC) marketplace where currencies are traded globally. Unlike equity markets with centralized exchanges (NYSE, NASDAQ), Forex operates through a network of banks, brokers, and electronic communication networks (ECNs) without a single point of control. This decentralization has direct engineering implications: there is no single "official" price for any currency pair at any given moment, and the price a system receives depends on its liquidity provider, the broker's aggregation logic, and network latency.

The market operates in a tiered structure. At the top sits the interbank market, where major banks (JPMorgan, Deutsche Bank, Citigroup, UBS) trade directly with each other in volumes exceeding $100 million per transaction. Below that, prime brokers aggregate interbank liquidity and offer it to institutional clients. At the retail level, brokers like those accessed through MetaTrader 5 further aggregate these feeds, adding their own spread markup, and offer leveraged access to individual traders and automated systems.

For an automated trading system, the practical consequence is that every price received is a quote from a specific liquidity provider at a specific moment, subject to requoting, slippage, and spread widening during volatile periods. The system must treat every price as an approximation, never as an absolute truth, and must validate execution prices against requested prices after every order fill.

### 1.2 Currency Pairs and Instrument Classification

Forex instruments are quoted as pairs: a base currency and a quote currency. In EUR/USD = 1.0850, one Euro costs 1.0850 US Dollars. The base currency (EUR) is what you buy or sell; the quote currency (USD) is what you pay or receive.

**Major Pairs** are the most liquid instruments, all involving the US Dollar:
- EUR/USD (Euro/Dollar) — highest global volume, tightest spreads
- GBP/USD (Pound/Dollar) — volatile, sensitive to UK economic data
- USD/JPY (Dollar/Yen) — carry trade instrument, BOJ intervention risk
- USD/CHF (Dollar/Franc) — safe-haven dynamics
- AUD/USD (Dollar/Aussie) — commodity-linked, correlated with iron ore
- USD/CAD (Dollar/Canadian) — oil-price correlated
- NZD/USD (Dollar/Kiwi) — dairy-commodity linked

**Crosses** exclude the USD: EUR/GBP, EUR/JPY, GBP/JPY. These have wider spreads and lower liquidity but can offer uncorrelated trading opportunities.

**CFDs (Contracts for Difference)** extend beyond pure Forex:
- XAU/USD (Gold/Dollar) — GOLIATH's primary trading instrument. Gold has unique characteristics: it trades nearly 24 hours, exhibits strong trending behavior, is sensitive to real interest rates, and has wider pip values than Forex pairs.
- XAG/USD (Silver/Dollar) — more volatile than gold, lower liquidity.
- Index CFDs: US30, US500, NAS100 — equity index derivatives.

**Symbol Conventions** vary by provider. Polygon.io uses `C:XAUUSD` (the `C:` prefix denoting a currency/commodity pair), Binance uses `BTCUSDT` (no separator), and MetaTrader 5 uses `XAUUSD` (no separator, no prefix). A production system must maintain a normalization map that converts every provider-specific format to a canonical internal format. GOLIATH uses slash-separated symbols internally: `XAU/USD`, `EUR/USD`, `BTC/USDT`.

### 1.3 Order Types and Fill Policies

**Market Orders** execute immediately at the best available price. The system sends an order request specifying symbol, direction (BUY or SELL), volume (lots), and optional stop-loss/take-profit levels. The broker fills the order at the current ask (for BUY) or bid (for SELL). In fast-moving markets, the fill price may differ from the price displayed when the order was sent — this difference is slippage.

**Limit Orders** specify a price at which the trader is willing to enter. A BUY LIMIT is placed below the current price (expecting a dip then reversal), while a SELL LIMIT is placed above (expecting a rally then reversal). These remain pending until the market reaches the specified price or the order expires.

**Stop Orders** trigger a market order when a specified price is reached. A BUY STOP is placed above the current price (breakout entry), while a SELL STOP is placed below (breakdown entry).

**Fill Policies** determine how partial fills are handled:
- **IOC (Immediate or Cancel):** Fill whatever quantity is available immediately; cancel the remainder. GOLIATH uses this for market orders to avoid hanging orders.
- **GTC (Good Till Cancelled):** The order remains active until explicitly cancelled or filled. Used for limit/pending orders.

**Deviation (Slippage Tolerance):** When sending market orders through the MT5 API, a `deviation` parameter specifies the maximum acceptable slippage in points. GOLIATH uses 20 points, meaning if the price moves more than 20 points between request and execution, the broker may reject the order. This prevents fills at catastrophically different prices during news events.

### 1.4 Bid/Ask Spread and Liquidity

Every instrument has two prices at any moment: the bid (price at which the broker will buy from you / you can sell) and the ask (price at which the broker will sell to you / you can buy). The difference is the spread, measured in points or pips. The spread is the primary transaction cost in Forex and varies by:

- **Instrument:** EUR/USD typically 0.5-1.5 pips; XAU/USD typically 2-5 pips; exotic pairs 5-20+ pips.
- **Time of day:** Spreads are tightest during the London-New York overlap (13:00-17:00 UTC) when liquidity is highest, and widest during the Asian session rollover (21:00-22:00 UTC).
- **Market conditions:** During high-impact news events (NFP, FOMC, ECB decisions), spreads can widen 5-10x their normal levels as liquidity providers withdraw quotes.

For automated systems, spread monitoring is critical. GOLIATH rejects any trade where the current spread exceeds a configurable maximum (default: 30 points). Trading during spread-widening events is unprofitable by default because the entry cost exceeds the expected edge.

### 1.5 Leverage, Margin, and Risk

Leverage allows controlling a large position with a small deposit (margin). At 100:1 leverage, a $1,000 deposit controls a $100,000 position (1 standard lot of EUR/USD). This amplifies both profits and losses proportionally.

**Margin Terminology:**
- **Balance:** Total account value excluding open positions.
- **Equity:** Balance plus or minus the floating profit/loss of open positions. `Equity = Balance + Unrealized_PnL`.
- **Used Margin:** The margin currently locked by open positions.
- **Free Margin:** `Equity - Used Margin`. This is the amount available for opening new positions.
- **Margin Level:** `(Equity / Used Margin) × 100%`. Brokers typically issue a margin call at 100% and force-close positions (stop-out) at 50%.

For automated systems, margin validation before every order is essential. GOLIATH calls `check_margin(symbol, direction, lots)` before submitting any order, verifying that sufficient free margin exists. If the margin check fails, the signal is rejected, preventing overleverage.

### 1.6 Trading Sessions

The Forex market operates 24 hours, five days a week, structured around four major sessions:

- **Sydney Session (22:00-07:00 UTC):** Lowest liquidity, widest spreads. AUD and NZD pairs are most active.
- **Tokyo Session (00:00-09:00 UTC):** JPY pairs gain volume. Often range-bound as European and American traders are inactive.
- **London Session (07:00-16:00 UTC):** Highest liquidity, tightest spreads. 35% of global Forex volume. Most breakout setups occur at the London open.
- **New York Session (12:00-21:00 UTC):** Second-highest volume. USD pairs are most active.

**Overlap Windows** are periods when two sessions are simultaneously active:
- **London-Tokyo Overlap (07:00-09:00 UTC):** Moderate increase in EUR/JPY and GBP/JPY activity.
- **London-New York Overlap (12:00-16:00 UTC):** Peak liquidity globally. This is the optimal window for trend-following strategies on major pairs and gold.

Session awareness is a feature input to the decision engine. Strategies that work during high-liquidity London sessions may fail during the low-liquidity Asian session. The system encodes the current session as a categorical feature.

### 1.7 PIP Definition by Instrument Class

A pip (percentage in point) is the smallest standard price movement for a given instrument:

| Instrument Class | PIP Size | Example | 1 PIP Movement |
|-----------------|----------|---------|-----------------|
| Major Forex (4-decimal) | 0.0001 | EUR/USD 1.0850 → 1.0851 | 1 pip |
| JPY pairs (2-decimal) | 0.01 | USD/JPY 149.50 → 149.51 | 1 pip |
| Gold XAU/USD | 0.01 | 2050.00 → 2050.01 | 1 pip (0.01 USD) |
| Silver XAG/USD | 0.001 | 24.500 → 24.501 | 1 pip |
| Indices (US30) | 1.0 | 38500 → 38501 | 1 point |

**PIP Value** is the monetary value of a 1-pip move for a standard lot:
- EUR/USD: $10.00 per pip per standard lot
- USD/JPY: ~$6.70 per pip per standard lot (varies with USD/JPY rate)
- XAU/USD: $1.00 per pip per 0.01 lot (micro); $10.00 per pip per 0.10 lot (mini)

These values are essential for position sizing calculations. The position sizer must know the exact pip value per lot for each instrument to convert a risk percentage into a concrete lot size.

### 1.8 Correlation and Portfolio Risk

Understanding cross-asset correlations is fundamental for portfolio risk management. Highly correlated positions compound directional risk: holding simultaneous long positions in EUR/USD and GBP/USD is effectively doubling your USD-short exposure, since both pairs are inversely correlated with the dollar.

**Key Forex Correlations:**

| Pair 1 | Pair 2 | Typical Correlation | Implication |
|--------|--------|-------------------|-------------|
| EUR/USD | GBP/USD | +0.85 to +0.95 | Nearly identical directional moves |
| EUR/USD | USD/CHF | -0.90 to -0.95 | Near-perfect inverse — redundant to trade both |
| AUD/USD | NZD/USD | +0.85 to +0.90 | Commodity-bloc correlation |
| USD/JPY | US Equity Indices | +0.60 to +0.75 | Risk-on/risk-off linkage |
| XAU/USD | USD/DXY | -0.70 to -0.85 | Gold inversely correlated with dollar strength |
| XAU/USD | Real Yields | -0.80 to -0.90 | Gold falls when real rates rise |

**Portfolio Risk Rule:** The system enforces a maximum position limit (default: 5 concurrent positions) and the knowledge base contains portfolio rotation rules that discourage holding multiple positions in correlated pairs in the same direction. A new BUY signal on GBP/USD while already holding a long EUR/USD is penalized by the experience bank's correlation check.

**Correlation-Adjusted Position Sizing:**

For advanced implementations, the position sizer can reduce lot sizes when existing positions are correlated with the proposed trade:

```
correlation_factor = 1.0 - max(|correlation(new_trade, existing_position)| for each existing_position) × 0.5
adjusted_lots = base_lots × correlation_factor
```

If the proposed trade has 0.90 correlation with an existing position, the correlation factor is `1.0 - 0.90 × 0.5 = 0.55`, reducing the position to 55% of its uncorrelated size.

### 1.9 Swap and Carry

**Swap (Rollover)** is the interest rate differential applied to positions held overnight. Every currency pair involves two interest rates (one for each currency). Holding a long position in a high-interest-rate currency against a low-interest-rate currency earns positive swap (carry). The reverse costs negative swap.

```
Daily swap ≈ (Interest_base - Interest_quote) / 365 × position_size × exchange_rate
```

For automated 24/7 trading, swap costs are non-trivial. A position held for a week can accumulate meaningful swap charges (or credits). The trade recorder logs swap values for each trade in the `swap` column of `trade_executions`, enabling accurate P&L calculation that includes carry.

**Triple Swap Wednesday:** Most brokers apply 3x swap on Wednesday nights (to account for weekend settlement). The system should be aware of this — holding a negative-swap position over Wednesday night costs three times the normal daily swap.

### 1.10 Lot Sizing

Forex volumes are measured in lots:
- **Standard Lot:** 100,000 units of base currency. A standard lot of EUR/USD controls €100,000.
- **Mini Lot:** 10,000 units (0.10 lots).
- **Micro Lot:** 1,000 units (0.01 lots). The smallest size most brokers allow.

**Volume Constraints** are per-symbol and retrieved from the broker via `symbol_info()`:
- `volume_min`: Minimum order size (typically 0.01).
- `volume_max`: Maximum order size (varies by broker and instrument).
- `volume_step`: Lot size granularity (typically 0.01). Orders must be rounded to this step.

The system must quantize every computed lot size to the broker's volume step: `lots = floor(lots / volume_step) * volume_step`. If the quantized size falls below `volume_min`, the trade is rejected.

---

## Chapter 2 — Technical Analysis Mathematics

### 2.1 Momentum Indicators

**Relative Strength Index (RSI)** measures the magnitude of recent price changes to evaluate overbought or oversold conditions. The standard calculation uses Wilder's smoothing (a specific form of EMA):

```
RS = Average Gain over N periods / Average Loss over N periods
RSI = 100 - (100 / (1 + RS))
```

Where the averages use Wilder's smoothing: `Avg_Gain(t) = (Avg_Gain(t-1) × (N-1) + Gain(t)) / N`. The standard period is N=14. RSI > 70 suggests overbought conditions; RSI < 30 suggests oversold. In strong trends, RSI can remain in extreme territory for extended periods, making RSI-based reversal signals unreliable without trend confirmation.

**MACD (Moving Average Convergence Divergence)** quantifies the relationship between two exponential moving averages:

```
MACD Line = EMA(12) - EMA(26)
Signal Line = EMA(9) of MACD Line
Histogram = MACD Line - Signal Line
```

Where EMA is calculated as: `EMA(t) = Price(t) × α + EMA(t-1) × (1-α)`, with `α = 2 / (N+1)`. A bullish signal occurs when the MACD line crosses above the signal line; bearish when it crosses below. The histogram's magnitude indicates momentum strength.

**Stochastic Oscillator** compares a closing price to its range over a period:

```
%K = 100 × (Close - Lowest_Low(N)) / (Highest_High(N) - Lowest_Low(N))
%D = SMA(3) of %K
```

Standard period N=14. Readings above 80 are overbought; below 20 are oversold. The fast stochastic uses raw %K; the slow stochastic smooths %K with an additional SMA(3).

**Williams %R** is mathematically related to the stochastic:

```
%R = -100 × (Highest_High(N) - Close) / (Highest_High(N) - Lowest_Low(N))
```

Range: [-100, 0]. Values above -20 are overbought; below -80 are oversold. Period N=14.

**Rate of Change (ROC)** measures percentage price change:

```
ROC = ((Close - Close(N periods ago)) / Close(N periods ago)) × 100
```

**Momentum** is the absolute version: `Momentum = Close - Close(N periods ago)`.

**Stochastic RSI** applies the stochastic formula to RSI values instead of prices:

```
StochRSI = (RSI - Lowest_RSI(N)) / (Highest_RSI(N) - Lowest_RSI(N))
```

This creates a more sensitive indicator that reaches extremes more frequently than standard RSI.

**Ultimate Oscillator** combines three timeframes with weighted averaging:

```
BP = Close - min(Low, Previous_Close)  [Buying Pressure]
TR = max(High, Previous_Close) - min(Low, Previous_Close)  [True Range]
Avg7 = sum(BP,7) / sum(TR,7)
Avg14 = sum(BP,14) / sum(TR,14)
Avg28 = sum(BP,28) / sum(TR,28)
UO = 100 × (4×Avg7 + 2×Avg14 + Avg28) / 7
```

### 2.2 Trend Indicators

**Average Directional Index (ADX)** measures trend strength regardless of direction. It is derived from the Directional Movement system:

```
+DM = max(High(t) - High(t-1), 0) if > max(Low(t-1) - Low(t), 0), else 0
-DM = max(Low(t-1) - Low(t), 0) if > max(High(t) - High(t-1), 0), else 0

ATR(14) = Wilder smoothed True Range
+DI = 100 × Wilder_Smooth(+DM, 14) / ATR(14)
-DI = 100 × Wilder_Smooth(-DM, 14) / ATR(14)

DX = 100 × |+DI - -DI| / (+DI + -DI)
ADX = Wilder_Smooth(DX, 14)
```

ADX > 25 indicates a trending market; ADX < 20 indicates a range-bound market. The +DI/-DI crossover gives direction: +DI > -DI is bullish; -DI > +DI is bearish. ADX itself only measures strength, not direction.

**Simple Moving Average (SMA):** `SMA(N) = sum(Close, N) / N`. Lagging indicator. Common periods: 20, 50, 100, 200.

**Exponential Moving Average (EMA):** `EMA(t) = Close(t) × α + EMA(t-1) × (1-α)`, where `α = 2/(N+1)`. Reacts faster than SMA. Common periods: 12, 26 (MACD), 8, 21 (short-term trend).

**Double Exponential Moving Average (DEMA):** `DEMA = 2 × EMA(N) - EMA(EMA(N))`. Reduces lag further.

**Parabolic SAR** provides trailing stop levels and potential reversal points. The indicator places dots above or below price:

```
SAR(t+1) = SAR(t) + AF × (EP - SAR(t))
```

Where AF (Acceleration Factor) starts at 0.02 and increases by 0.02 each time a new Extreme Point (EP) is reached, capped at 0.20. When price crosses SAR, the indicator reverses (flips from below to above price or vice versa).

### 2.3 Volatility Indicators

**Average True Range (ATR)** measures market volatility using Wilder's smoothing:

```
True Range = max(High-Low, |High-Previous_Close|, |Low-Previous_Close|)
ATR(N) = Wilder_Smooth(TR, N)
```

Standard period N=14. ATR is used for stop-loss placement (e.g., SL = Entry ± 1.5×ATR), position sizing (higher ATR → smaller position), and regime detection (ATR ratio vs rolling average).

**Bollinger Bands** create dynamic support/resistance envelopes:

```
Middle Band = SMA(20)
Upper Band = SMA(20) + 2 × StdDev(Close, 20)
Lower Band = SMA(20) - 2 × StdDev(Close, 20)
Bandwidth = (Upper - Lower) / Middle
%B = (Close - Lower) / (Upper - Lower)
```

Narrow bandwidth (Bollinger Squeeze) precedes breakouts. Price touching the upper band in a trend is continuation, not reversal. %B values above 1.0 or below 0.0 indicate extreme moves beyond the bands.

**Keltner Channels** use ATR instead of standard deviation:

```
Middle = EMA(20)
Upper = EMA(20) + 2 × ATR(10)
Lower = EMA(20) - 2 × ATR(10)
```

When Bollinger Bands move inside Keltner Channels (squeeze), a breakout setup is forming. This combined signal is used in the regime detection module.

**Historical Volatility** is the annualized standard deviation of log returns:

```
Log_Return(t) = ln(Close(t) / Close(t-1))
HV = StdDev(Log_Returns, N) × sqrt(252)  [annualized for daily data]
```

**Parkinson Volatility** uses high-low range, providing a more efficient volatility estimate:

```
PV = sqrt((1/(4N×ln(2))) × sum(ln(High/Low)^2, N))
```

This captures intraday volatility that close-to-close measures miss.

### 2.4 Volume Indicators

**On-Balance Volume (OBV)** is a cumulative volume indicator:

```
If Close > Previous_Close: OBV = Previous_OBV + Volume
If Close < Previous_Close: OBV = Previous_OBV - Volume
If Close = Previous_Close: OBV = Previous_OBV
```

Rising OBV confirms uptrends; divergence (price making new highs while OBV does not) warns of potential reversal.

**Volume Weighted Average Price (VWAP):**

```
VWAP = Cumulative(Price × Volume) / Cumulative(Volume)
```

Resets daily. Institutional benchmark — price above VWAP indicates bullish intraday sentiment.

**Chaikin Money Flow (CMF)** measures buying/selling pressure:

```
MFM = ((Close - Low) - (High - Close)) / (High - Low)  [Money Flow Multiplier]
MFV = MFM × Volume  [Money Flow Volume]
CMF = sum(MFV, 20) / sum(Volume, 20)
```

CMF > 0 indicates buying pressure; CMF < 0 indicates selling pressure.

**Force Index:** `Force = (Close - Previous_Close) × Volume`. Smoothed with EMA(13).

### 2.5 Multi-Timeframe Analysis

Multi-timeframe analysis examines the same instrument across different time horizons to confirm signals. The principle: trade in the direction of the higher timeframe trend using entry signals from lower timeframes.

GOLIATH processes four timeframes simultaneously: M1 (1-minute), M5 (5-minute), M15 (15-minute), H1 (1-hour). The confirmation logic works as follows:

1. **H1 determines trend direction:** If H1 EMA(8) > EMA(21) and ADX > 25, the trend is bullish.
2. **M15 confirms momentum:** If M15 RSI is rising and MACD histogram is positive, momentum aligns with the H1 trend.
3. **M5 provides entry timing:** A pullback to M5 EMA(21) with RSI dipping to 40-50 in a bullish trend creates an entry opportunity.
4. **M1 is execution granularity:** The exact entry point is timed on the M1 chart for optimal fill.

This hierarchical confirmation reduces false signals. A BUY signal on M5 is only valid if M15 and H1 agree on bullish bias. Disagreement across timeframes forces a HOLD decision.

### 2.6 OHLCV Bar Construction

Bars (candlesticks) are constructed from tick-level data by aggregating all ticks within a time window:

```
Open = first tick price in the period
High = maximum tick price in the period
Low = minimum tick price in the period
Close = last tick price in the period
Volume = sum of all tick volumes in the period (or tick count for Forex)
```

**Time Alignment:** A 1-minute bar for 10:05 covers ticks from 10:05:00.000 to 10:05:59.999. A 5-minute bar for 10:05 covers 10:05:00 to 10:09:59.999. Bars are always aligned to their period boundaries (a 15-minute bar starts at :00, :15, :30, or :45).

When a bar's time period closes, the aggregator emits the completed bar and starts a new one. On shutdown, partial bars must be flushed to avoid data loss.

### 2.7 Heiken-Ashi Transformation

Heiken-Ashi candlesticks smooth price action to make trends more visible:

```
HA_Close = (Open + High + Low + Close) / 4
HA_Open = (Previous_HA_Open + Previous_HA_Close) / 2
HA_High = max(High, HA_Open, HA_Close)
HA_Low = min(Low, HA_Open, HA_Close)
```

Bullish HA candles have no lower wick (strong uptrend). Bearish HA candles have no upper wick (strong downtrend). Doji-like HA candles (small body, both wicks) indicate consolidation or reversal. The system uses HA-transformed OHLC as additional features in the 60-dimensional input vector.

---

## Chapter 3 — Market Regime Theory

### 3.1 The Five Canonical Regimes

Markets exhibit distinct behavioral modes that repeat over time. Correctly identifying the current regime is the single most important factor in strategy selection — a trend-following strategy will lose money in a range-bound market, and a mean-reversion strategy will lose money in a trending market.

GOLIATH classifies markets into five regimes:

**TRENDING_UP:** Price is making higher highs and higher lows. Moving averages are aligned (fast EMA above slow EMA). ADX is above 25 and rising. Optimal strategies: trend-following, breakout entries, trailing stops.

**TRENDING_DOWN:** Mirror of TRENDING_UP. Price is making lower highs and lower lows. ADX above 25. Optimal strategies: short entries on rallies, trailing stops, momentum confirmation.

**RANGING:** Price oscillates between support and resistance levels without a clear directional bias. ADX below 20-25. Bollinger Bands are relatively flat. Optimal strategies: mean-reversion, buy at support/sell at resistance, RSI extremes.

**VOLATILE:** High ATR relative to recent history. Bollinger Bands are expanding. Price makes large swings in both directions. Optimal strategies: volatility breakout, wider stops, reduced position size, shorter holding periods.

**CRISIS:** Extreme market conditions — flash crashes, circuit breaker events, extreme VIX readings (>30). Characterized by illiquidity, gapping, and spread widening. Optimal strategy: minimal or no trading, defensive positioning, kill switch activation.

A sixth state, NEUTRAL, is used when no regime can be confidently identified, typically defaulting to a conservative HOLD.

### 3.2 ADX-Based Trend Detection

The primary trend detection mechanism uses ADX with a threshold of 25:

```python
if ADX > 25:
    if EMA_fast > EMA_slow:
        regime = TRENDING_UP
    else:
        regime = TRENDING_DOWN
    confidence = clamp(0.50 + ADX / 100, 0.50, 0.90)
else:
    regime = RANGING
    confidence = clamp(0.60 + (25 - ADX) / 50, 0.60, 0.70)
```

The confidence formula scales linearly with ADX strength. An ADX of 40 produces confidence 0.90 (strong trend); ADX of 26 produces confidence 0.76 (marginal trend). This graduated confidence prevents binary flip-flopping at the threshold boundary.

The +DI/-DI crossover determines direction:
- +DI > -DI with ADX > 25 → TRENDING_UP
- -DI > +DI with ADX > 25 → TRENDING_DOWN

### 3.3 ATR-Ratio Volatility Detection

Volatility regime detection compares current ATR to its rolling average:

```python
atr_ratio = current_ATR / rolling_mean_ATR(50)

if atr_ratio > 2.0:
    regime = HIGH_VOLATILITY
    confidence = clamp(0.50 + (atr_ratio - 2.0) * 0.15, 0.50, 0.95)
```

An ATR ratio of 3.0 (current volatility is 3x the 50-period average) produces confidence 0.65 — high enough to trigger regime-specific strategy selection but not so high as to override all other signals.

Volatility detection takes priority over trend detection. If ATR ratio exceeds 2.0, the market is classified as HIGH_VOLATILITY regardless of ADX reading, because trend-following in extremely volatile conditions requires different stop-loss and position-sizing parameters.

### 3.4 Reversal Detection

Reversal detection identifies potential trend exhaustion:

```python
if previous_ADX > 40 and current_ADX < previous_ADX:  # ADX declining from high
    if RSI > 70 or RSI < 30:  # At extreme
        regime = REVERSAL
        confidence = 0.55
```

The relatively low confidence (0.55) reflects the inherent difficulty of timing reversals. The system does not attempt to "call tops and bottoms" — it merely flags conditions where a trend may be weakening, allowing the strategy layer to reduce position size or tighten stops.

### 3.5 Regime Hysteresis

Regime classification without hysteresis produces whipsaw transitions — rapid alternation between TRENDING and RANGING when ADX oscillates near 25. This causes the strategy layer to constantly switch between trend-following and mean-reversion, executing neither effectively.

Hysteresis requires N consecutive observations confirming a new regime before the transition is accepted:

```python
if proposed_regime != current_regime:
    pending_count += 1
    if pending_count >= threshold:  # Default: 3 for upgrade, 2 for downgrade
        current_regime = proposed_regime
        pending_count = 0
    # else: keep current regime
else:
    pending_count = 0  # Reset if proposal matches current
```

The asymmetric thresholds (3 for upgrade, 2 for downgrade) reflect a conservative bias: the system is slower to enter a new trading mode but faster to retreat to a safer one.

### 3.6 VIX Regime Classification

For macro-aware trading, the VIX (CBOE Volatility Index) provides a market-wide fear gauge:

- **Calm (VIX < 15):** Low implied volatility. Markets are complacent. Normal trading conditions.
- **Elevated (15 ≤ VIX < 25):** Increasing uncertainty. Consider reducing position sizes.
- **Panic (VIX ≥ 25):** High fear. Correlations spike (everything sells off together). Risk of flash crashes. System should reduce exposure or halt trading.

VIX data is ingested separately through the External Data Service and stored in the `vix_data` TimescaleDB table with term structure information (1-month, 2-month, 3-month futures) enabling contango/backwardation analysis for forward-looking volatility assessment.

---

## Chapter 4 — Risk Management Theory

### 4.1 Kelly Criterion for Position Sizing

Position sizing is the process of determining how many lots to trade on each signal. The goal is to risk a fixed percentage of equity per trade, translating that risk into a concrete lot size based on the distance to the stop-loss.

The core formula:

```
risk_amount = equity × risk_percentage
SL_distance_pips = |entry_price - stop_loss_price| / pip_size
lots = risk_amount / (SL_distance_pips × pip_value_per_lot)
```

**Worked example:** Trading XAU/USD with $10,000 equity, 1% risk per trade:
- `risk_amount = $10,000 × 0.01 = $100`
- Entry: 2050.00, Stop Loss: 2045.00 → SL distance = 5.00 / 0.01 = 500 pips
- XAU/USD pip value: $0.10 per pip per 0.01 lot (micro lot)
- `lots = $100 / (500 × $0.10) = $100 / $50 = 2.00 micro lots = 0.02 standard lots`

This ensures that if the stop-loss is hit, exactly $100 (1% of equity) is lost, regardless of the instrument or entry price. The system never risks more than the configured percentage per trade.

### 4.2 Instrument-Specific PIP Parameters

The position sizer maintains a registry mapping each symbol to its pip size and pip value:

| Symbol | pip_size | pip_value (USD/lot) |
|--------|----------|---------------------|
| EUR/USD | 0.0001 | 10.00 |
| GBP/USD | 0.0001 | 10.00 |
| USD/JPY | 0.01 | ~6.70 |
| USD/CHF | 0.0001 | ~10.00 |
| AUD/USD | 0.0001 | 10.00 |
| NZD/USD | 0.0001 | 10.00 |
| USD/CAD | 0.0001 | ~7.50 |
| XAU/USD | 0.01 | 1.00 |
| XAG/USD | 0.001 | 5.00 |

For pairs where the quote currency is not USD (e.g., USD/JPY), the pip value depends on the current exchange rate: `pip_value_USD = (pip_size / current_rate) × lot_size`. The system uses a fixed approximation for simplicity, recalibrated periodically.

### 4.3 Drawdown-Based Scaling

As the account enters drawdown, position sizes are progressively reduced to protect remaining capital:

| Drawdown Range | Scaling Factor | Effect |
|---------------|----------------|--------|
| 0% - 2% | 1.00 | Full size trading |
| 2% - 4% | 0.50 | Half size |
| 4% - 5% | 0.25 | Quarter size |
| > 5% | 0.00 | Trading halted |

The formula: `adjusted_lots = base_lots × scaling_factor × spiral_multiplier`

**Drawdown calculation:**
```
drawdown_pct = ((balance - equity) / balance) × 100
```

This is a conservative, linear reduction. The rationale: losing 2% of a $10,000 account ($200) hurts but is recoverable. Losing 10% ($1,000) requires an 11.1% return to recover. Losing 20% requires a 25% return. The exponentially increasing difficulty of recovery justifies aggressive lot reduction during drawdown.

### 4.4 Daily Loss Limits

In addition to drawdown-based scaling, an absolute daily loss limit prevents catastrophic single-day losses:

```
daily_loss_pct = (-floating_pnl / balance) × 100

if daily_loss_pct >= max_daily_loss_pct:
    activate_kill_switch("Daily loss limit reached")
```

The default maximum daily loss is 2% of balance. When triggered, the kill switch halts all trading for the remainder of the session. This prevents the common failure mode of automated systems: a losing streak during a volatile session producing unbounded losses before the operator notices.

### 4.5 Spiral Protection

Spiral protection addresses the psychological and statistical reality of consecutive losses. After N consecutive losing trades, the system reduces position sizing even if drawdown hasn't reached the scaling thresholds:

```
if consecutive_losses >= spiral_threshold:
    spiral_multiplier = max(0.25, 1.0 - (consecutive_losses × 0.15))
```

With a threshold of 3 and a 0.15 reduction per loss:
- 3 consecutive losses: `1.0 - 0.45 = 0.55` (55% of normal size)
- 5 consecutive losses: `1.0 - 0.75 = 0.25` (25% of normal size, minimum floor)

The spiral multiplier is composed with the drawdown scaling factor: `final_lots = base_lots × drawdown_scale × spiral_multiplier`. Both protections must pass for any trade to execute at full size.

### 4.6 Risk-Reward Ratio

Every signal must specify a take-profit level that provides a minimum risk-reward ratio:

```
RR_ratio = |take_profit - entry| / |entry - stop_loss|

if RR_ratio < minimum_rr:  # Default: 1.5
    reject_signal("Risk-reward ratio too low")
```

A 1.5:1 ratio means the potential profit is 1.5 times the potential loss. With a 50% win rate, this produces positive expected value: `EV = 0.50 × 1.5R - 0.50 × 1.0R = +0.25R` per trade.

### 4.7 Maximum Position Count

The system limits concurrent open positions to prevent overexposure:

```
if open_position_count >= max_position_count:  # Default: 5
    reject_signal("Position limit reached")
```

This is checked during pre-execution validation by querying MT5 for current open positions. The limit prevents the system from opening dozens of correlated positions during a single market move, which would create concentrated directional risk equivalent to a single enormous position.

### 4.8 Spread-Based Trade Filtering

High spreads increase the cost of entry, reducing the expected edge of any strategy. The system rejects trades when spreads are abnormally wide:

```
if current_spread_points > max_spread_points:  # Default: 30
    reject_signal(f"Spread too high: {current_spread}")
```

Spread typically widens during:
- Low-liquidity periods (Asian session for Forex)
- News events (NFP, FOMC announcements)
- Market opening/closing times
- Technical difficulties at the broker

By filtering on spread, the system automatically avoids trading during these suboptimal periods without requiring explicit time-based blackout rules.

---

# PART II: SYSTEM ARCHITECTURE AND SOFTWARE ENGINEERING

---

## Chapter 5 — Microservices Architecture Overview

### 5.1 Service Topology

GOLIATH V1 is composed of seven core services and a monitoring stack, each deployed as an independent Docker container with defined resource limits, health checks, and inter-service communication contracts:

| Service | Language | Primary Responsibility | CPU | Memory |
|---------|----------|----------------------|-----|--------|
| Data Ingestion | Go 1.22+ | WebSocket data collection, normalization, aggregation | 1.0 | 1 GB |
| AI Brain | Python 3.11+ | Decision engine, signal generation, feature engineering | 2.0 | 4 GB |
| MT5 Bridge | Python 3.11+ | Trade execution, position tracking, order management | 1.0 | 512 MB |
| ML Training Lab | Python 3.11+ | Model training, validation, inference service | 2.0-4.0 | 4-8 GB |
| Dashboard | Python/React | Web-based monitoring, real-time data visualization | 0.5 | 512 MB |
| Console | Python (Rich) | TUI/CLI interface with 155+ commands across 22 categories | — | — |
| External Data | Python | Macroeconomic data ingestion (FRED, CBOE, CFTC) | — | — |

**Infrastructure Services:**

| Service | Version | Purpose | CPU | Memory |
|---------|---------|---------|-----|--------|
| TimescaleDB | PostgreSQL 16 | Time-series storage, audit log, ML model registry | 2.0 | 2 GB |
| Redis | 7-alpine | Real-time state, kill switch, pub/sub, rate limiting | 1.0 | 512 MB |
| Prometheus | v2.50.1 | Metrics collection (15-second scrape interval) | 1.0 | 1 GB |
| Grafana | v10.3.3 | Dashboard visualization, alerting | 0.5 | 512 MB |
| TensorBoard | 2.15.0 | ML training visualization | 0.5 | 512 MB |

### 5.2 Technology Stack Rationale

**Go for Data Ingestion:** The data ingestion service handles multiple concurrent WebSocket connections, normalizes incoming data, aggregates ticks into bars, publishes to ZeroMQ, and writes to the database — all simultaneously. Go's goroutine model provides lightweight concurrency (goroutines use ~2KB of stack vs ~1MB for OS threads) with efficient multiplexing via the Go runtime scheduler. The service maintains a 500ms tick generation rate in development mode and handles real-time WebSocket streams in production without backpressure issues.

**Python for Trading Logic:** The AI Brain, MT5 Bridge, and ML Training services use Python for its ecosystem advantages: PyTorch for neural networks, MetaTrader5 package for broker connectivity, NumPy/SciPy for numerical computation, and rich library support for gRPC, Prometheus metrics, and structured logging. The performance cost of Python is acceptable because the decision pipeline runs at bar frequency (every 1-60 seconds), not tick frequency.

**React for Dashboard:** The web dashboard uses React with TypeScript for a responsive, component-based UI with real-time WebSocket updates. The backend is FastAPI (Python) serving REST endpoints and WebSocket streams.

**gRPC for Inter-Service Communication:** Type-safe, code-generated service contracts via Protobuf ensure that interface changes are caught at compile time. Streaming RPCs support real-time signal delivery and trade update feeds. Binary serialization is more efficient than JSON for high-frequency communication paths.

**ZeroMQ for Market Data Distribution:** ZMQ PUB/SUB provides low-latency, fire-and-forget message delivery from the data ingestion service to subscribers. Topic-based routing (`bar.XAUUSD.M1`) allows subscribers to filter for specific instruments and timeframes without receiving irrelevant data.

### 5.3 Network Architecture

Three Docker bridge networks enforce security boundaries:

**backend (internal: true):** All core services, databases, and cache. The `internal: true` flag prevents any container on this network from reaching external endpoints. This contains the blast radius of a compromised container — it cannot exfiltrate data to the internet.

**frontend:** External-facing services only: Grafana (port 3000), TensorBoard (port 6006), Dashboard (port 8888). These are accessible from the host machine and, in production, through a reverse proxy.

**monitoring:** Connects Prometheus to all services for metrics scraping. Services expose `/metrics` endpoints on this network. Prometheus scrapes every 15 seconds.

### 5.4 End-to-End Data Flow

```
Exchange WebSocket (Polygon.io / Binance)
    │
    ▼
Data Ingestion (Go) ──── Port 5555 (ZMQ PUB) ────►  AI Brain (Python)
    │                                                       │
    │ batch COPY                                            │ feature engineering
    ▼                                                       │ regime detection
TimescaleDB ◄──────────────────────────────────────────     │ 4-mode cascade
    ▲                                                  │    │ maturity gating
    │                                                  │    ▼
    │                                            Port 50054 (gRPC)
    │                                                  │
    │                                                  ▼
    │                                           MT5 Bridge (Python)
    │                                                  │
    │  trade recording                                 │ 9-point validation
    │◄─────────────────────────────────────────────    │ lot clamping
    │                                              │   │ order submission
    │                                              │   ▼
    │                                              MetaTrader 5 API
    │                                                  │
    │                                                  ▼
    │                                           Live Forex Market
    │
    ▼
Prometheus (scrape /metrics) ──► Grafana (dashboards, alerts)
```

Every service publishes Prometheus metrics. Every trading decision is logged with a `reasoning` field explaining why the signal was generated. Every trade execution is recorded with slippage, commission, and fill details.

### 5.5 Service Independence

Each service is independently deployable, testable, and restartable. This independence is enforced through:

1. **Protobuf contracts:** Inter-service interfaces are defined in `.proto` files, compiled to language-specific stubs. A service can be replaced entirely as long as it implements the same Protobuf interface.

2. **Health checks:** Every service exposes a health endpoint (HTTP or gRPC). Docker Compose and production orchestrators use these to determine service readiness before routing traffic.

3. **Graceful degradation:** If the ML Training service is unavailable, the AI Brain falls back to Mode 3 (Knowledge-Only) or Mode 4 (Conservative). If Redis is unavailable, the kill switch defaults to fail-closed (no trading). No single service failure causes the entire system to crash — the system degrades gracefully.

4. **Independent configuration:** Each service reads its own YAML configuration file (`configs/development/ai-brain.yaml`, `configs/production/mt5-bridge.yaml`) plus environment variables. Configuration changes to one service do not affect others.

---

## Chapter 6 — Data Ingestion Service (Go)

### 6.1 Pipeline Architecture

The data ingestion service is the entry point of the entire trading ecosystem. It receives raw market data from external exchanges and transforms it into clean, normalized, time-aligned data structures consumed by all downstream services. The pipeline consists of five sequential stages:

```
Connectors (WebSocket) → Normalizer → Aggregator → Publisher (ZMQ) → DBWriter (TimescaleDB)
```

Each stage has a single responsibility and communicates with the next through Go function calls and callbacks, not channels or message queues. This simplifies the data flow and eliminates buffering issues within the pipeline.

### 6.2 WebSocket Connector Pattern

The connector layer abstracts exchange-specific WebSocket protocols behind a unified interface:

```go
type Connector interface {
    Connect() error
    Close() error
    Subscribe(symbols []string, channels []string) error
    ReadMessage() (RawMessage, error)
}
```

Three implementations exist:

**PolygonConnector:** Connects to `wss://socket.polygon.io/forex` for Forex tick data. Handles Polygon's authentication protocol (sending an `auth` message with the API key after connection), subscription management (sending `subscribe` messages for specific symbols), and Polygon-specific message formats. Symbols use the `C:XAUUSD` prefix convention.

**BinanceConnector:** Connects to Binance WebSocket streams for cryptocurrency data. Handles Binance's combined stream format (`/ws/btcusdt@trade`) and reconnection on disconnects.

**MockConnector:** Generates synthetic tick data for development and testing. Produces realistic Forex-like price movements using a random walk with mean reversion:

```go
// Configurable via functional options
conn := connectors.NewMockConnector("mock-dev",
    connectors.WithGenerateInterval(500 * time.Millisecond),
    connectors.WithMessageFactory(connectors.NewForexMessageFactory()),
)
```

The mock connector generates ticks for XAU/USD, EUR/USD, GBP/USD, and USD/JPY at configurable intervals (default 500ms). The ForexMessageFactory produces prices with realistic spread and volatility characteristics.

**Connector Selection:** The service selects the connector based on the `GOLIATH_ENV` environment variable:
- `production` or `staging` → PolygonConnector (with API key validation)
- Any other value → MockConnector

### 6.3 Symbol Normalization

Raw exchange data arrives with exchange-specific symbol formats. The normalizer maintains a static mapping from every known exchange format to the canonical GOLIATH format:

```go
symbolMap := map[string]string{
    "c:xauusd": "XAU/USD",   "xau/usd": "XAU/USD",   "xauusd": "XAU/USD",
    "c:eurusd": "EUR/USD",   "eur/usd": "EUR/USD",   "eurusd": "EUR/USD",
    "c:gbpusd": "GBP/USD",   "gbp/usd": "GBP/USD",   "gbpusd": "GBP/USD",
    "c:usdjpy": "USD/JPY",   "usd/jpy": "USD/JPY",   "usdjpy": "USD/JPY",
    "btcusdt":  "BTC/USDT",  "ethusdt":  "ETH/USDT",
    // ... 20+ total mappings
}
```

Normalization is case-insensitive (lowercased before lookup). If a symbol is not found in the map, the tick is logged and dropped — unknown symbols never propagate downstream. This prevents data corruption from unexpected exchange events.

The normalizer also extracts and validates:
- **Price:** Must be positive and finite.
- **Quantity/Volume:** Must be non-negative.
- **Timestamp:** Converted to UTC nanoseconds. If the exchange provides millisecond timestamps, they are multiplied by 1,000,000.
- **Exchange name:** Tagged for provenance tracking.

Output: a `NormalizedTick` struct with canonical symbol, price, quantity, timestamp, exchange, and event type.

### 6.4 OHLCV Aggregation

The aggregator accumulates normalized ticks into OHLCV bars across multiple timeframes simultaneously:

```go
timeframes := []Timeframe{M1, M5, M15, H1}
agg := aggregator.NewAggregator(timeframes, onBarComplete)
```

For each tick received, the aggregator:

1. Determines which bars the tick belongs to (a single tick updates M1, M5, M15, and H1 bars simultaneously).
2. Updates the running bar state: `High = max(High, price)`, `Low = min(Low, price)`, `Close = price`, `Volume += quantity`, `TickCount++`.
3. Checks if the tick's timestamp crosses a bar boundary. If the M1 bar for 10:05 receives a tick at 10:06:00.001, the 10:05 bar is complete.
4. On bar completion, calls the `onBarComplete` callback with the finished bar.
5. Starts a new bar with the crossing tick as its first data point.

**Time alignment** is critical: a 15-minute bar starting at 10:15 must contain only ticks from 10:15:00.000 to 10:29:59.999. The alignment function calculates the bar start time: `bar_start = tick_time.Truncate(timeframe_duration)`.

**Partial bar flushing:** On graceful shutdown, the aggregator's `FlushAll()` method emits all in-progress bars, even if their time period hasn't completed. This prevents data loss — the partial bar is stored in the database with its actual tick count, and downstream consumers can identify it as partial by its lower-than-expected tick count.

### 6.5 ZeroMQ Publisher

Completed bars and raw ticks are published to a ZeroMQ PUB socket bound to `tcp://*:5555`:

```go
pub, _ := publisher.NewPublisher("tcp://*:5555")

// Publishing a bar
topic := fmt.Sprintf("bar.%s.%s", bar.Symbol, bar.Timeframe)  // e.g., "bar.XAU/USD.M1"
pub.Publish(topic, barJSON)

// Publishing a tick
topic := fmt.Sprintf("%s.%s.%s", tick.EventType, tick.Exchange, tick.Symbol)  // e.g., "trade.polygon.XAU/USD"
pub.Publish(topic, tickJSON)
```

ZMQ PUB/SUB has specific characteristics important for trading systems:
- **No backpressure:** If a subscriber is slow, messages are dropped, not buffered. This is desirable — the AI Brain should always process the latest data, not queue up stale bars.
- **Topic filtering:** Subscribers specify topic prefixes. `SUB("bar.XAU/USD")` receives all timeframes for gold; `SUB("bar.")` receives all bars for all symbols.
- **Connection resilience:** If the subscriber disconnects and reconnects, it resumes receiving new messages without needing to re-subscribe (the subscription is stored by the PUB socket).

### 6.6 Batch Database Writer

The DBWriter persists both ticks and bars to TimescaleDB using PostgreSQL's COPY protocol for high-throughput batch insertion:

```go
type Config struct {
    DSN            string        // PostgreSQL connection string
    Enabled        bool          // Toggle DB writes
    BatchSize      int           // Flush threshold (default: 1000)
    FlushInterval  time.Duration // Max time before flush (default: 1 second)
    WorkerCount    int           // Concurrent write workers (default: 4)
    DataSourceLabel string       // "mock" or "live" — distinguishes dev from prod data
}
```

**Batch accumulation:** Ticks and bars are accumulated in memory buffers. A flush occurs when either:
1. The buffer reaches `BatchSize` entries, OR
2. `FlushInterval` has elapsed since the last flush.

This batching strategy reduces database round-trips from potentially thousands per second (one per tick) to a few per second (one per batch), dramatically improving write throughput.

**COPY protocol:** Instead of individual INSERT statements, the writer uses PostgreSQL's COPY command, which streams rows directly into the table's storage engine, bypassing per-row parsing overhead. For 1000 rows, COPY is approximately 10-50x faster than individual INSERTs.

**Worker pool:** Multiple workers allow concurrent writes to different tables (ticks vs bars) without blocking each other. Workers pull from a shared work queue and execute COPY operations independently.

**Data source labeling:** Every row written includes a `source` column indicating whether the data originated from a live exchange feed or a mock generator. This prevents test data from contaminating production analysis when both environments write to the same database during development.

### 6.7 Health Monitoring

The service exposes two HTTP endpoints:

**`/healthz`** — Overall health status. Reports HEALTHY when all registered checks pass:
- `zmq_publisher`: ZMQ socket is bound and operational.
- `timescaledb`: Database connection is alive (ping succeeds).
- `data_flow`: Ticks are flowing. Fails if no ticks received for 60 seconds (after a 90-second startup grace period).

**`/stats`** — Runtime statistics from the DBWriter:
- Total ticks written, total bars written.
- Last tick timestamp.
- Buffer sizes.
- Worker utilization.

The `data_flow` check is particularly important: it detects situations where the WebSocket connection is established but no data is arriving (exchange outage, API key expired, network issue). Without this check, the service would report healthy while the entire pipeline is starved of data.

### 6.8 Graceful Shutdown

On receiving SIGINT or SIGTERM, the service executes an orderly shutdown:

1. Set health check to NOT READY (stops new traffic from load balancers).
2. Stop the main read loop (context cancellation).
3. Flush all partial bars from the aggregator.
4. Flush all remaining ticks and bars from the DBWriter buffers.
5. Close the ZMQ publisher socket.
6. Shut down the health HTTP server (15-second timeout).
7. Log final statistics and exit.

This sequence ensures no data loss during rolling restarts or deployments.

### 6.9 Go Concurrency Patterns

The data ingestion service demonstrates several Go-idiomatic concurrency patterns:

**Context-Based Cancellation:**

```go
ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
defer stop()

go func() {
    for {
        select {
        case <-ctx.Done():
            return  // Clean exit on shutdown signal
        default:
        }
        raw, err := conn.ReadMessage()
        // ... process message
    }
}()

<-ctx.Done()  // Block main goroutine until shutdown
```

The `signal.NotifyContext` pattern creates a context that is cancelled when SIGINT or SIGTERM is received. All goroutines check `ctx.Done()` in their select loops, enabling coordinated shutdown without explicit goroutine tracking.

**Worker Pool for Database Writes:**

The DBWriter uses a configurable number of worker goroutines that pull from shared work channels:

```go
type DBWriter struct {
    tickChan chan NormalizedTick
    barChan  chan Bar
}

func (w *DBWriter) start(workers int) {
    for i := 0; i < workers; i++ {
        go w.tickWorker()
        go w.barWorker()
    }
}

func (w *DBWriter) tickWorker() {
    batch := make([]NormalizedTick, 0, w.config.BatchSize)
    timer := time.NewTimer(w.config.FlushInterval)

    for {
        select {
        case tick := <-w.tickChan:
            batch = append(batch, tick)
            if len(batch) >= w.config.BatchSize {
                w.flushTickBatch(batch)
                batch = batch[:0]
                timer.Reset(w.config.FlushInterval)
            }
        case <-timer.C:
            if len(batch) > 0 {
                w.flushTickBatch(batch)
                batch = batch[:0]
            }
            timer.Reset(w.config.FlushInterval)
        }
    }
}
```

This pattern provides backpressure management: if workers cannot keep up with incoming ticks, the `tickChan` channel buffers them. If the buffer fills, the main loop blocks on sending to the channel, slowing down message reading — which is the correct behavior, since processing should never silently drop data.

**Functional Options for Connector Configuration:**

The MockConnector uses Go's functional options pattern for flexible initialization:

```go
type MockOption func(*MockConnector)

func WithGenerateInterval(d time.Duration) MockOption {
    return func(m *MockConnector) { m.interval = d }
}

func WithMessageFactory(f MessageFactory) MockOption {
    return func(m *MockConnector) { m.factory = f }
}

func NewMockConnector(name string, opts ...MockOption) *MockConnector {
    m := &MockConnector{name: name, interval: 500 * time.Millisecond}
    for _, opt := range opts {
        opt(m)
    }
    return m
}
```

This pattern allows extensible configuration without breaking existing callers when new options are added.

### 6.10 Prometheus Metrics Integration

The data ingestion service exports metrics for operational monitoring:

```go
var (
    ticksReceived = prometheus.NewCounterVec(
        prometheus.CounterOpts{
            Name: "goliath_di_ticks_received_total",
            Help: "Total ticks received from exchange connectors",
        },
        []string{"exchange", "symbol"},
    )
    barsPublished = prometheus.NewCounterVec(
        prometheus.CounterOpts{
            Name: "goliath_di_bars_published_total",
            Help: "Total OHLCV bars published to ZMQ",
        },
        []string{"symbol", "timeframe"},
    )
    dbWriteLatency = prometheus.NewHistogram(
        prometheus.HistogramOpts{
            Name:    "goliath_di_db_write_seconds",
            Help:    "Database batch write latency",
            Buckets: prometheus.DefBuckets,
        },
    )
)
```

These metrics feed the "Data Pipeline" Grafana dashboard, showing tick ingestion rates per symbol, bar publication rates per timeframe, and database write latency percentiles.

### 6.11 Console and Dashboard Integration

**Console (TUI/CLI):**

The GOLIATH Console provides a Rich-powered text user interface with 22 command categories and approximately 155 individual commands. It communicates with services through HTTP, gRPC, Docker API, Redis, and PostgreSQL clients:

```python
# Command categories
categories = [
    "alert",    # Alert management and history
    "audit",    # Audit log queries and verification
    "brain",    # AI Brain control (start, stop, status, config)
    "build",    # Docker image building
    "config",   # Configuration management
    "data",     # Data pipeline management (ingestion, quality, gaps)
    "exit",     # Shutdown commands
    "help",     # Command reference
    "kill",     # Kill switch management
    "log",      # Log viewing and filtering
    "maint",    # Maintenance operations (backups, compression, vacuum)
    "market",   # Market data queries (bars, ticks, spreads)
    "ml",       # ML model management (train, status, compare)
    "mt5",      # MT5 Bridge control (connect, positions, history)
    "perf",     # Performance analytics (P&L, Sharpe, drawdown)
    "portfolio",# Portfolio overview
    "risk",     # Risk management (limits, drawdown, kill switch)
    "signal",   # Signal history and analysis
    "svc",      # Service management (start/stop/restart all)
    "sys",      # System operations (health, resources, network)
    "test",     # Testing commands (run tests, verify brain)
    "tool",     # Diagnostic tools (14 validators)
]
```

Example commands:
- `goliath risk kill-switch` — View kill switch status and history.
- `goliath brain status` — Show AI Brain pipeline state, current regime, maturity level.
- `goliath perf summary --days 30` — 30-day performance summary with Sharpe, win rate, P&L.
- `goliath data gaps --symbol XAUUSD` — Detect gaps in market data for a specific symbol.
- `goliath ml compare --models v1.2,v1.3` — Compare ML model metrics side-by-side.

**Dashboard (Web UI):**

The web dashboard provides 10 pages with real-time updates via WebSocket:

1. **Overview:** System health matrix, portfolio equity curve, active alerts, service status indicators.
2. **Trading:** Signal history table with filtering (by symbol, direction, source_mode), execution details, P&L per trade.
3. **Risk:** Live drawdown gauge, daily loss progress bar, kill switch status with activation history, position count vs limit.
4. **Market Data:** Tick rate sparklines per symbol, bar count per timeframe, data quality scores, spread distribution histograms.
5. **ML Models:** Model registry table, training loss curve chart, inference latency percentiles, model comparison radar chart.
6. **Macro:** VIX level with regime coloring, yield curve visualization, real rates chart, DXY trend, COT positioning bar chart.
7. **Strategy:** Per-strategy signal attribution (pie chart), win rate by strategy over time, regime-strategy correlation heatmap.
8. **Economic:** Economic calendar with countdown timers, trading blackout periods, event impact history.
9. **Logs:** Real-time log stream with severity filtering, service filtering, and full-text search.
10. **Config:** System configuration viewer and (for admin) editor.

The backend uses FastAPI with async PostgreSQL queries (asyncpg) and a WebSocket connection manager for real-time updates:

```python
class ConnectionManager:
    def __init__(self):
        self._channels: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, channel: str, websocket: WebSocket):
        await websocket.accept()
        self._channels[channel].add(websocket)

    async def broadcast(self, channel: str, data: dict):
        for ws in self._channels.get(channel, set()):
            try:
                await ws.send_json(data)
            except WebSocketDisconnect:
                self._channels[channel].discard(ws)
```

Channels include: `trading_signals`, `trade_executions`, `risk_metrics`, `system_health`, `market_data`. The frontend subscribes to relevant channels on page load and receives real-time updates without polling.

---

## Chapter 7 — AI Brain Service Architecture

### 7.1 The 24-Step Processing Pipeline

The AI Brain is the central intelligence of the trading system. It receives market data from the data ingestion service, processes it through a multi-stage pipeline, and outputs trading signals to the MT5 Bridge. The main loop processes bars sequentially, executing a 24-step pipeline for each incoming bar:

1. **Structured Logging Initialization** — Service-specific JSON logging with correlation IDs.
2. **Configuration Loading** — Environment variables + YAML configuration merged via Pydantic models.
3. **Health Check Setup** — HTTP endpoint on port 8082 for liveness/readiness probes.
4. **ZMQ Subscriber Connection** — Connects to `tcp://data-ingestion:5555`, subscribing to bar topics.
5. **Pipeline Module Initialization** — Instantiates all analysis modules in dependency order.
6. **DataSanityChecker** — Validates OHLCV plausibility (High >= Low, Close within range, non-zero volume).
7. **RegimeEnsemble** — 3-classifier voting system with weighted averaging and hysteresis.
8. **DriftMonitor** — Z-score-based feature drift detection. Flags features deviating >3σ from rolling statistics.
9. **MarketVectorizer** — Constructs the 60-dimensional feature vector from raw market data.
10. **TradingMaturity** — Observes model maturity signals (training loss convergence, validation metrics).
11. **TradingModelManager** — Manages model lifecycle: loading checkpoints, version tracking.
12. **PnLMomentumTracker** — Tracks consecutive win/loss streaks for spiral protection.
13. **AnalysisOrchestrator** — Coordinates 10 analysis submodules (indicators, patterns, correlations).
14. **TradingAdvisor** — The 4-mode cascade pipeline (COPER → Hybrid → Knowledge → Conservative).
15. **MLLifecycleController** — Monitors feature drift and signals retraining when needed.
16. **PerformanceAnalyzer** — Computes rolling performance metrics (Sharpe, win rate, profit factor).
17. **StorageManager** — Manages local checkpoint storage and cleanup.
18. **StateManager** — Persists global state to Redis for crash recovery.
19. **HybridCoachingEngine** — Post-trade coaching with rule-based and neural feedback.
20. **ShadowEngine** — Real-time neural inference for telemetry (runs in parallel, does not block signals).
21. **ReportGenerator** — Generates daily/weekly/monthly performance reports.
22. **AnalyticsEngine** — Computes trading statistics for Grafana dashboard integration.
23. **Signal Emission** — Valid signals sent to MT5 Bridge via gRPC.
24. **Prometheus Metrics Update** — Pipeline latency, signal counts, regime distribution.

Not all steps execute on every bar. Steps 6-8 run on every tick for data quality. Steps 9-14 run the main analysis pipeline. Steps 15-22 run periodically or conditionally.

### 7.2 Async Event Loop

The service runs an asyncio event loop that:

1. Subscribes to ZMQ topics for configured symbols and timeframes.
2. Deserializes incoming bar data from JSON.
3. Validates the bar's timestamp (rejects stale data beyond a configurable threshold).
4. Feeds the bar into the 24-step pipeline.
5. If the pipeline produces a non-HOLD signal with confidence above the threshold, packages it into a gRPC `TradingSignal` message and sends it to the MT5 Bridge.

The ZMQ subscriber uses non-blocking polls with a configurable timeout, allowing the event loop to perform housekeeping tasks (health check responses, metric updates, state persistence) between bar arrivals.

### 7.3 Feature Engineering Pipeline

Raw market data is transformed into a 60-dimensional feature vector consumed by both the neural network and the traditional strategy engines:

**Dimensions 0-5: Price Features**
- Open, High, Low, Close, Volume, Spread (6 features)

**Dimensions 6-39: Technical Indicators (34 features)**
- SMA(20), EMA(8), EMA(21), DEMA(20)
- MACD line, MACD signal, MACD histogram
- ADX, +DI, -DI, DI ratio
- RSI(14), Stochastic %K, Stochastic %D, Williams %R
- ROC(12), Momentum(10), Stochastic RSI, Ultimate Oscillator
- ATR(14), ATR ratio (current/average)
- Bollinger upper, middle, lower, bandwidth, %B
- Keltner upper, lower
- Historical volatility, Parkinson volatility
- OBV, VWAP, CMF, Chaikin Oscillator, Force Index, Volume Ratio

**Dimensions 40-50: Context Features (11 features)**
- Time-of-day encoding (sine/cosine pair for cyclical representation)
- Day-of-week encoding (sine/cosine pair)
- Session indicator (Sydney=0, Tokyo=1, London=2, New York=3)
- Economic event proximity (distance to next high-impact event)
- VIX level, VIX regime (calm/elevated/panic)
- Macro context flags

**Dimensions 51-59: Microstructure Features (9 features)**
- Bid-ask spread normalized by ATR
- Order book imbalance (if available)
- Hurst exponent (mean-reversion vs trending tendency)
- VPIN (Volume-Synchronized Probability of Informed Trading)
- Tick intensity (ticks per second, normalized)
- Spread percentile (current spread vs 200-period distribution)
- Additional reserved features

### 7.4 Data Quality Validation

Before any analysis, the DataSanityChecker validates each OHLCV bar:

- `High >= Low` — Inverted bars indicate data corruption.
- `Close` within `[Low, High]` range — Close outside the bar's range is impossible.
- Volume is non-negative — Negative volume is nonsensical.
- Timestamp is recent — Bars with timestamps more than a configurable threshold in the past are stale and rejected.
- No NaN or Infinity values — Any NaN in the price fields causes the bar to be dropped.
- Price is within reasonable bounds — A gold price of $0.01 or $999,999 is clearly erroneous.

Bars that fail any check are logged with the specific failure reason and dropped. The pipeline continues with the next bar. This prevents cascading errors from corrupted data propagating through indicators, regime detection, and signal generation.

### 7.5 Tensor Assembly

For neural network inference, the 60-dimensional feature vectors must be assembled into structured tensors using the TensorFactory:

**MarketTensorBundle** contains:
- `price_tensor`: Shape `(batch, seq_len, 6)` — OHLCV + spread for the last `seq_len` bars (default 64).
- `indicator_tensor`: Shape `(batch, seq_len, 34)` — All 34 technical indicators for the last 64 bars.
- `feature_tensor`: Shape `(batch, seq_len, 60)` — Full 60-dimensional concatenated features.
- `timestamps`: Shape `(batch, seq_len)` — UTC nanosecond timestamps for temporal alignment.

**Padding:** When fewer than `seq_len` bars are available (system startup), the tensor is zero-padded at the beginning. This preserves the most recent bars at the end of the sequence (unmasked) while filling missing history with zeros. The neural network's attention mechanism learns to ignore zero-padded positions.

### 7.6 Pre-Processing: RobustScaler

Raw feature values span vastly different ranges (gold price ~2000 vs RSI 0-100 vs volume 0-10000+). Normalization is required before neural inference:

**RobustScaler** uses median and interquartile range (IQR) instead of mean and standard deviation:

```
scaled_value = (value - median) / IQR
where IQR = Q75 - Q25
```

This is deliberately chosen over StandardScaler because financial data contains frequent outliers (flash crashes, news spikes). StandardScaler's mean and standard deviation are sensitive to outliers, causing normal values to be compressed near zero. RobustScaler's median and IQR are resistant to outliers, maintaining better separation of normal values.

The scaler is fit only on training data and applied (without refitting) to validation, test, and live data. This prevents data leakage — live normalization uses the same parameters learned from historical data.

### 7.7 Maturity Progression

The system implements a graduated confidence model for its own readiness:

| State | Description | Position Sizing | Trading Mode |
|-------|-------------|----------------|--------------|
| DOUBT | Untrained or insufficient data | 0% (blocked) | Backtest only |
| CRISIS | Extreme market conditions detected | 0% (blocked) | Backtest only |
| LEARNING | Early training, high variance | 35% of normal | Paper trading |
| CONVICTION | Stable performance, passing metrics | 80% of normal | Micro-live |
| MATURE | Proven track record | 100% | Full live |

**Transition logic** uses the HysteresisGate: a state upgrade requires 3 consecutive periods meeting the upgrade criteria; a downgrade requires only 2 consecutive periods. This asymmetry makes the system slow to commit capital but fast to retreat.

The ConvictionIndexCalculator computes a composite score from training metrics:

```
conviction = 0.35 × min(win_rate, 1.0)
           + 0.30 × min(max(sharpe, 0) / 3.0, 1.0)
           + 0.20 × min(max(profit_factor, 0) / 4.0, 1.0)
           + 0.15 × (1.0 - min(max(max_drawdown, 0), 1.0))
```

Each metric is capped and normalized to [0, 1] before weighting. A conviction of 0.60+ suggests CONVICTION state; 0.80+ suggests MATURE.

---

## Chapter 8 — The 4-Mode Cascade Signal Pipeline

### 8.1 Cascade Design Principle

The signal generation pipeline is designed around a cascading fallback architecture: the system attempts the most sophisticated analysis mode first and falls through to simpler modes if a higher-tier mode fails or is unavailable. This guarantees that every incoming bar produces a recommendation, even if the neural network is not loaded, the knowledge base is empty, or the experience bank has no relevant entries.

```
Mode 1: COPER (Experience Bank + ML)
    │ failure or unavailable
    ▼
Mode 2: Hybrid (ML + Knowledge Fusion)
    │ failure or unavailable
    ▼
Mode 3: Knowledge-Only (RAG without ML)
    │ failure or empty KB
    ▼
Mode 4: Conservative (Regime-Based Rules — always works)
```

Mode selection is driven by two factors: model maturity state and model availability.

```python
if maturity in (MATURE, CONVICTION) and model_loaded:
    try COPER → if fails, try Hybrid
elif maturity == LEARNING and model_loaded:
    try Hybrid → if fails, try Knowledge
elif model_loaded:
    try Hybrid → if fails, try Knowledge
else:
    try Knowledge → if fails, Conservative
```

### 8.2 Mode 1: COPER (Contextual Personalized Experience Retrieval)

COPER is the most sophisticated mode, adapted from a competitive gaming coaching system. It retrieves relevant past trading experiences, synthesizes advice, and optionally enriches with ML inference.

**Trade Context Representation:**

Every market state is captured as a `TradeContext`:

```python
@dataclass
class TradeContext:
    symbol: str         # "XAUUSD"
    timeframe: str      # "M15"
    regime: str         # "TRENDING_UP"
    session: str        # "london"
    price_zone: str     # "resistance", "support", "free_space"
    momentum_state: str # "hot", "normal", "tilt"
    direction: str      # "buy", "sell", "hold"
    timestamp_ns: int
```

The context is hashed using SHA-256 to produce a `context_hash` — a unique identifier for each exact market configuration. Two contexts with identical attributes produce the same hash.

**Trade Experience Storage:**

Each past trade is stored as a `TradeExperience`:

```python
@dataclass
class TradeExperience:
    context: TradeContext
    context_hash: str           # SHA-256 of context fields
    direction: str              # What was traded
    outcome_pnl: Decimal        # Result in pips/money
    confidence: Decimal         # Confidence at time of trade
    effectiveness: Decimal      # Updated via EMA feedback
    reasoning: str              # Why the trade was taken
    embedding: np.ndarray       # 384-dim Sentence-BERT vector
    feedback_count: int         # Number of feedback updates
```

**Embedding Computation:**

Each experience is embedded into a 384-dimensional vector using Sentence-BERT (model: all-MiniLM-L6-v2). The embedding text combines context fields and reasoning: `"XAUUSD TRENDING_UP london resistance buy: breakout above key level with ADX confirmation"`.

Fallback: If Sentence-BERT is unavailable, a deterministic SHA-256 hash expansion produces a 100-dimensional pseudo-embedding by byte-expanding the context hash and L2-normalizing. This fallback is lower-quality but ensures the system never fails due to a missing NLP model.

**Similarity Retrieval:**

When generating a new signal, COPER retrieves the top-K most similar past experiences:

```python
score = (cosine_similarity(current_embedding, experience_embedding)
         + 0.2 × hash_bonus
         + 0.4 × effectiveness) × confidence
```

Where:
- `cosine_similarity`: Semantic similarity between current context and past experience.
- `hash_bonus`: 1.0 if the context hash matches exactly (identical market configuration), 0.0 otherwise.
- `effectiveness`: Updated via exponential moving average feedback: `eff' = eff × 0.7 + outcome × 0.3`.
- `confidence`: The original trade's confidence score.

The top 5 experiences are retrieved and synthesized into an `SynthesisedAdvice` object with a recommended direction, confidence, focus area, and narrative explaining the reasoning.

**ML Enrichment:**

If a neural model is loaded, COPER requests an inference prediction and compares it with the experience-based recommendation:
- If ML agrees with the experience direction → confidence increases.
- If ML disagrees → the disagreement is logged as `conflicting_evidence`, but the experience direction is kept (experience has priority in COPER mode).

### 8.3 Mode 2: Hybrid (ML + Knowledge Fusion)

Hybrid mode fuses three signal sources with configurable weights:

| Source | Weight | Description |
|--------|--------|-------------|
| ML Inference | 0.50 | Neural network prediction (direction + confidence) |
| Knowledge Base | 0.30 | RAG retrieval from strategy knowledge entries |
| Experience Bank | 0.20 | Similar past trade outcomes |

**Z-Score Deviation Analysis:**

The HybridSignalEngine maintains rolling baselines for each (regime, session, symbol) combination:

```python
@dataclass
class HistoricalBaseline:
    mean_confidence: float
    std_confidence: float
    mean_win_rate: float
    std_win_rate: float
    sample_count: int
```

The Z-score of the current signal's confidence against the baseline determines priority:

```python
z = (current_confidence - baseline_mean) / max(baseline_std, 1e-6)

priority = CRITICAL  if |z| > 3.0    # Extreme deviation — investigate
         = HIGH      if |z| > 2.0    # Strong deviation
         = MEDIUM    if |z| > 1.0    # Moderate deviation
         = LOW       otherwise        # Normal range
```

High Z-scores can indicate either exceptional opportunity or model malfunction. The system adjusts confidence downward for extreme Z-scores to be conservative: `confidence *= (1 - min(|Z| × 0.05, 0.15))`.

**Conflict Detection:**

When ML and Knowledge disagree on direction, the conflict is explicitly logged:

```python
conflicting_evidence = ["ML predicts SELL but knowledge base suggests BUY based on support zone"]
```

Conflicts do not prevent signal generation — they are included in the `TradingRecommendation` for audit purposes. In a traditional system, conflicts can trigger automatic HOLD or reduced sizing.

### 8.4 Mode 3: Knowledge-Only

When no ML model is available, the system queries a knowledge base using retrieval-augmented generation (RAG) principles, but with keyword-based inference instead of neural language understanding.

**Knowledge Base Structure:**

The knowledge base contains curated entries across five categories:

```python
@dataclass
class KnowledgeEntry:
    title: str          # "RSI Divergence Entry"
    description: str    # "When RSI forms lower highs while price makes higher highs..."
    category: str       # "entry_timing"
    situation: str      # "TRENDING_UP with momentum weakness"
    symbol: str | None  # Specific to instrument, or None for universal
    embedding: np.ndarray  # 384-dim Sentence-BERT
```

**Retrieval:**

For collections with ≥50 entries, FAISS IndexFlatIP (inner product on L2-normalized vectors = cosine similarity) provides fast approximate nearest-neighbor search. For smaller collections, brute-force NumPy cosine similarity is used.

The query is constructed from the current market state: `"TRENDING_UP XAUUSD london"`. If features provide additional context: `"TRENDING_UP XAUUSD london oversold"` (when RSI < 30) or `"TRENDING_UP XAUUSD london trending"` (when ADX > 25).

**Direction Inference:**

Without a neural model, direction is inferred from keyword counting in retrieved entries:

```python
for entry in retrieved_entries:
    desc = entry.description.lower()
    if any(w in desc for w in ["buy", "long", "bullish", "support"]):
        buy_score += 1
    if any(w in desc for w in ["sell", "short", "bearish", "resistance"]):
        sell_score += 1

direction = "buy" if buy_score > sell_score else "sell" if sell_score > buy_score else "hold"
confidence = max(buy_score, sell_score) / max(len(entries), 1)
```

This is deliberately simple — the knowledge base entries are written by domain experts who use directional language, making keyword extraction effective. The confidence reflects the density of agreement among retrieved entries.

**FAISS Index Construction:**

For knowledge bases exceeding 50 entries, FAISS (Facebook AI Similarity Search) accelerates retrieval:

```python
class KnowledgeRetriever:
    def rebuild_index(self):
        embeddings = np.stack([e.embedding for e in self._entries])
        # L2 normalize for cosine similarity via inner product
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / np.maximum(norms, 1e-10)
        self._index = faiss.IndexFlatIP(self._embedding_dim)
        self._index.add(normalized.astype(np.float32))

    def retrieve(self, query, top_k=3, category=None, symbol=None):
        query_embedding = self._embedder.embed(query)
        query_normalized = query_embedding / np.linalg.norm(query_embedding)

        if category or symbol:
            # Over-fetch 10x, then filter post-retrieval
            scores, indices = self._index.search(query_normalized.reshape(1, -1), top_k * 10)
            results = [(self._entries[i], s) for s, i in zip(scores[0], indices[0])
                      if i >= 0 and self._matches_filter(self._entries[i], category, symbol)]
            return [entry for entry, _ in results[:top_k]]
        else:
            scores, indices = self._index.search(query_normalized.reshape(1, -1), top_k)
            return [self._entries[i] for i in indices[0] if i >= 0]
```

FAISS IndexFlatIP computes exact inner products (cosine similarity on normalized vectors) and is brute-force but fast for collections under 100,000 entries. For larger collections, FAISS provides approximate methods (IVF, HNSW) that trade accuracy for speed — these are not currently needed given the expected knowledge base size.

**Knowledge Categories:**

The knowledge base is organized into five categories, each addressing a specific aspect of trading decision-making:

1. **stop_loss_placement:** Rules for setting stop-loss levels based on market structure, ATR multiples, support/resistance levels, and volatility conditions. Example entry: "In trending markets, place stop loss below the most recent higher low for long entries, using a minimum of 1.5 ATR as a buffer."

2. **entry_timing:** Rules for optimal entry timing within a valid setup. Example: "During London session, wait for the first 30-minute candle close before entering trend continuation trades. Early entries during the London open often get stopped out by the opening volatility spike."

3. **position_sizing:** Rules for lot calculation beyond the basic Kelly formula. Example: "When VIX is above 20 and the economic calendar shows a high-impact USD event within 4 hours, reduce position size by 50% regardless of signal confidence."

4. **portfolio_rotation:** Rules for managing multiple simultaneous positions. Example: "Never hold more than two correlated pairs (EUR/USD + GBP/USD) in the same direction. If a new signal conflicts with an existing position in a correlated pair, reject the new signal."

5. **money_management:** Rules for overall capital allocation and risk budgeting. Example: "After reaching a 3% daily profit, switch to half-size for the remainder of the session to protect gains. After reaching 5% daily profit, stop trading entirely."

### 8.5 Mode 4: Conservative (Always Works)

The conservative fallback uses a regime-based strategy router that maps the current market regime to a predefined strategy and applies its rules:

```python
def _conservative(self, symbol, regime, session, features):
    direction = "hold"
    confidence = Decimal("0.30")

    if self._get_conservative is not None:
        result = self._get_conservative()  # Calls RegimeRouter
        direction = result.get("direction", "hold")
        confidence = Decimal(str(result.get("confidence", 0.30)))
```

The RegimeRouter contains simple, well-tested rules:
- **TRENDING_UP:** BUY if RSI > 50 and price > EMA(21).
- **TRENDING_DOWN:** SELL if RSI < 50 and price < EMA(21).
- **RANGING:** HOLD (no action — range-bound strategies are risky without precise support/resistance levels).
- **VOLATILE:** HOLD (volatility regimes are dangerous for rule-based strategies).
- **CRISIS:** HOLD (always — never trade during crisis conditions).

Conservative mode always returns a valid recommendation, never throws an exception, and defaults to HOLD with confidence 0.30 if even the regime router fails. This makes it the ultimate safety net.

### 8.6 Cascade Output

Every cascade execution produces a `CascadeResult`:

```python
@dataclass
class CascadeResult:
    direction: str           # "buy", "sell", "hold"
    confidence: Decimal      # [0, 1]
    source_mode: str         # "coper", "hybrid", "knowledge", "conservative", "fallback"
    reasoning: list[str]     # Human-readable explanation chain
    gated: GatedSignal       # After maturity gate application
    shadow_prediction: Any   # Shadow engine prediction (telemetry only)
    latency_ms: float        # Pipeline execution time
    blocked: bool            # Whether maturity gate blocked the signal
    symbol: str
    regime: str
```

The `reasoning` field accumulates explanations from every cascade level that was attempted, providing a full audit trail: why the signal was generated, which mode produced it, what evidence supported it, and what evidence conflicted.

---

## Chapter 9 — Neural Architecture: RAP Coach

### 9.1 Architecture Overview

The MarketRAPCoach (Recurrent-Attentional-Predictive Coach) is a 4-layer neural architecture adapted from a competitive gaming coaching system. It processes sequential market data through four stages:

```
Price/Indicator/Change streams
         │
    ┌────▼────┐
    │Perception│  3-stream 1D CNN → 128-dim spatial encoding
    └────┬────┘
         │
    ┌────▼────┐
    │  Memory  │  LTC + Hopfield → hidden 256-dim + belief 64-dim
    └────┬────┘
         │
    ┌────▼────┐
    │ Strategy │  4-Expert MoE with regime gating → signal logits (3)
    └────┬────┘
         │
    ┌────▼────┐
    │Pedagogy  │  V(s) estimation + causal attribution → value + sizing
    └─────────┘
```

### 9.2 Perception Layer: 3-Stream CNN

The perception layer extracts spatial-temporal features from three parallel input streams, each capturing a different aspect of market dynamics:

**Price Stream (6 channels → 64 dimensions):**
Input shape: `(batch, 6, seq_len)` — the 6 OHLCV+spread channels treated as a multi-channel signal.
Architecture: 1D ResNet with block configuration [3, 4, 6, 3] (similar to ResNet-50's structure but for 1D sequences). Each block contains:

```
ResNetBlock1D:
    Conv1D(in, out, kernel=3, padding=1)
    BatchNorm1D
    ReLU
    Conv1D(out, out, kernel=3, padding=1)
    BatchNorm1D
    + Identity shortcut (with optional projection if dimensions change)
    ReLU
```

The first block in each stage uses stride=2 for downsampling, halving the temporal dimension. After all blocks, global average pooling collapses the temporal dimension entirely, producing a 64-dimensional vector representing the price structure of the entire sequence.

**Indicator Stream (34 channels → 32 dimensions):**
Input shape: `(batch, 34, seq_len)` — all 34 technical indicators as parallel channels.
Architecture: Lighter 1D ResNet with block configuration [2, 2] — fewer blocks because indicators are already derived features (pre-computed from prices), requiring less transformation. Output: 32-dimensional vector.

**Change Stream (60 channels → 32 dimensions):**
Input shape: `(batch, 60, seq_len)` — first-differences of all 60 features (feature[t] - feature[t-1]).
Architecture: Single convolutional layer with ReLU and global average pooling. The change stream captures rate-of-change dynamics — whether features are increasing or decreasing and how rapidly.

**Fusion:**
The three stream outputs are concatenated: `z_spatial = concat(price_64, indicator_32, change_32) = 128 dimensions`. This 128-dimensional perception vector encodes the market's current spatial-temporal state.

A sequence-level perception is also produced: `z_spatial_seq` of shape `(batch, seq_len, 128)` (before global pooling) is passed to the memory layer for temporal processing.

### 9.3 Memory Layer: LTC + Hopfield

The memory layer processes the perception sequence through time, maintaining a belief state that accumulates evidence across bars:

**Temporal Processing: Liquid Time Constants (LTC)**

LTC networks are a variant of continuous-time recurrent neural networks where each neuron has a learnable time constant:

```
dh/dt = (-h + f(Wh·h + Wx·x + b)) / τ
```

Where τ (tau) is a learnable parameter per neuron, ranging from 0.1 to 100.0 seconds in GOLIATH. Neurons with small τ respond quickly to recent inputs (sub-minute dynamics: tick intensity, spread changes). Neurons with large τ respond slowly, accumulating information over longer horizons (multi-day trends, regime persistence).

The implementation uses NCP (Neural Circuit Policies) wiring with AutoNCP: a structured connectivity pattern inspired by the C. elegans nervous system, where sensory neurons connect to inter-neurons which connect to command neurons. This creates an inductive bias toward hierarchical information processing.

If the NCP library is unavailable, the system falls back to a standard GRU (Gated Recurrent Unit) with the same hidden dimension, trading biological plausibility for reliability.

**Input:** `concat(perception_128, metadata_60) = 188 dimensions` per timestep.
**Output:** `hidden_seq` of shape `(batch, seq_len, 256)` and `last_hidden` of shape `(batch, 256)`.

**Associative Memory: Hopfield Network**

The Hopfield layer implements a modern continuous Hopfield network with exponential storage capacity. It maintains 512 learnable memory slots across 4 attention heads:

```
Hopfield.forward(query=hidden_seq, stored_patterns=learnable_patterns)
→ retrieved: (batch, seq_len, 256)
```

The memory slots learn canonical market patterns during training: breakout patterns, consolidation zones, reversal formations, volatility expansions. During inference, the Hopfield layer retrieves the most similar learned pattern to the current hidden state, providing pattern-completion capability — even partial pattern matches activate the full learned representation.

**Belief Head:**

The combined Hopfield output and temporal hidden state are projected through a belief head:

```
belief = Linear(256, SiLU, Linear(64))
```

The 64-dimensional belief vector represents the system's compressed assessment of the current market state, incorporating both recent data (via LTC) and historical pattern matching (via Hopfield).

### 9.4 Strategy Layer: 4-Expert Mixture of Experts

The strategy layer routes the decision through four specialized expert networks, each designed for a specific market regime:

**Expert Architecture:**
Each expert is a small feedforward network with contextual modulation:

```
Expert(hidden_256, context_60):
    superposition = SuperpositionLayer(hidden_256, 128, context_60)
    activated = ReLU(superposition)
    logits = Linear(128, 3)  # 3 outputs: BUY, SELL, HOLD
```

The SuperpositionLayer multiplies the hidden state element-wise by a context-dependent gate vector, allowing the expert to attend to different aspects of the hidden state depending on the current market context (session, volatility level, macro conditions).

**Regime-Aware Gating:**

The gate mechanism determines how much weight each expert receives:

```
gate_logits = W_hidden · last_hidden + W_regime · regime_posteriors
gate_weights = softmax(gate_logits)  # Shape: (batch, 4)
```

Where `regime_posteriors` is a 5-dimensional vector of regime probabilities from the RegimeEnsemble (e.g., [0.1, 0.7, 0.1, 0.05, 0.05] for a predominantly RANGING market).

The final signal logits are a weighted combination of all experts:

```
signal_logits = Σ(gate_weight_i × expert_logits_i) for i in [0..3]
signal_probs = softmax(signal_logits)  # [P(BUY), P(SELL), P(HOLD)]
```

**Sparsity Regularization:**

To encourage expert specialization (each expert handling its designated regime rather than all experts converging to the same behavior), L1 regularization is applied to gate weights:

```
sparsity_loss = context_gate_l1_weight × mean(|gate_weights|)
```

The default weight (1e-4) gently pushes gate weights toward sparsity without forcing hard expert selection.

### 9.5 Pedagogy Layer: Value Estimation and Causal Attribution

The pedagogy layer provides two auxiliary outputs used for position sizing and interpretability:

**Value Function V(s):**

```
strategy_context = Linear(4, 256)(gate_weights)
combined = last_hidden + strategy_context  # Condition on strategy profile
value = Linear(256, ReLU, Linear(1))(combined)
```

V(s) estimates the expected risk-adjusted return from the current state. Positive values indicate favorable conditions; negative values indicate unfavorable conditions. This is used for dynamic position sizing: `position_modifier = sigmoid(value)`.

**Causal Attribution:**

The attribution mechanism explains which market factors are driving the current prediction:

```python
concepts = ["trend", "momentum", "volatility", "volume", "correlation"]

# Neural relevance scores
neural_relevance = sigmoid(Linear(256, ReLU, Linear(5))(last_hidden))  # [0, 1] per concept

# Mechanical indicator values (from features)
mechanical = [adx/100, rsi_momentum, atr_ratio, volume_ratio, correlation_coeff]

# Fused attribution
attribution = neural_relevance * mechanical  # Element-wise product
```

Each attribution value indicates how much each market concept contributes to the current signal. For example, an attribution of [0.8, 0.3, 0.1, 0.2, 0.1] for [trend, momentum, volatility, volume, correlation] indicates the signal is primarily driven by trend strength (0.8) with moderate momentum support (0.3).

**Position Sizing Head:**

```
position_raw = Linear(256, 3)(last_hidden)  # 3 outputs
long_magnitude = sigmoid(position_raw[0])    # [0, 1] how much to go long
short_magnitude = sigmoid(position_raw[1])   # [0, 1] how much to go short
flat_probability = sigmoid(position_raw[2])  # [0, 1] probability of staying flat
```

These outputs modulate the final position size: `effective_lots = base_lots × max(long_magnitude, short_magnitude) × (1 - flat_probability)`.

### 9.6 Inference Engine

The InferenceEngine wraps the MarketRAPCoach for production inference:

```python
class InferenceEngine:
    def predict(self, price_stream, indicator_stream, change_stream,
                metadata, regime_posteriors, strategy_vec, indicator_deltas):
        with torch.no_grad():
            output = self._model(price_stream, indicator_stream, change_stream,
                                 metadata, regime_posteriors, strategy_vec, indicator_deltas)

        signal_probs = output["signal_probs"]
        direction = argmax(signal_probs)  # 0=BUY, 1=SELL, 2=HOLD
        confidence = max(signal_probs).item()

        return InferenceResult(
            signal_direction=Direction(direction),
            confidence=confidence,
            belief_state=output["belief_state"],
            value_estimate=output["value_estimate"].item(),
            gate_weights={name: w for name, w in zip(expert_names, output["gate_weights"])},
            position_long=output["position_sizing"][0].item(),
            position_short=output["position_sizing"][1].item(),
            position_flat=output["position_sizing"][2].item(),
            attribution={name: a for name, a in zip(concept_names, output["attribution"])},
            model_version=self._version,
            checkpoint_hash=self._hash,
        )
```

Key properties:
- `torch.no_grad()` disables gradient computation, reducing memory usage and computation time by ~40%.
- `to_inference_mode()` sets the model to eval mode and freezes all parameters.
- Checkpoint versioning with SHA-256 hash ensures reproducibility and audit trail.

### 9.7 Shadow Engine

The ShadowEngine provides a lightweight, real-time inference path that runs in parallel with the main pipeline for telemetry purposes:

```python
class ShadowEngine:
    def predict_tick(self, market_features: np.ndarray) -> ShadowPrediction:
        if not self._model_available:
            return ShadowPrediction(signal="HOLD", confidence=0.0, model_available=False)

        tensor = torch.from_numpy(market_features).unsqueeze(0).unsqueeze(0)
        start = time.monotonic()
        with torch.no_grad():
            output = self._model(tensor)
        latency_ms = (time.monotonic() - start) * 1000

        probs = softmax(output["signal_logits"])
        signal = ["BUY", "SELL", "HOLD"][argmax(probs)]

        return ShadowPrediction(
            signal=signal,
            confidence=max(probs).item(),
            probabilities={"buy": probs[0], "sell": probs[1], "hold": probs[2]},
            latency_ms=latency_ms,
            model_available=True,
        )
```

Shadow predictions are never used for trading decisions — they are logged alongside the cascade pipeline's output for comparison analysis. This allows measuring neural network accuracy without risking capital on unvalidated predictions.

---

## Chapter 10 — Translating AI to Traditional Architecture

### 10.1 The Translation Principle

The GOLIATH AI architecture is a 4-layer neural pipeline: Perception → Memory → Strategy → Pedagogy. Each layer performs a specific computational function that can be replicated with deterministic algorithms. The translation does not aim to mimic the neural network — it aims to achieve the same functional outcome using established quantitative methods.

The key insight is that the neural network's inputs are already computed indicators and features. The 34 technical indicators, the regime classification, the market context — these are all explicitly calculated before being fed to the neural network. The neural network's contribution is learning non-linear combinations of these features that correlate with profitable trading decisions. The traditional system replaces that learned non-linear mapping with explicit, configurable rules based on quantitative trading research.

### 10.2 Replacing the Perception Layer

**Neural approach:** 3-stream CNN extracts 128-dimensional spatial encoding from price, indicator, and change streams. The CNN learns which patterns in the input sequences are predictive.

**Traditional replacement:** Skip the CNN entirely. The 34 technical indicators are already computed and available as raw feature values. Instead of learning which features matter, define explicit feature importance through domain knowledge:

**Feature Scoring Module:**

```python
class FeatureScorer:
    def score(self, features: dict) -> FeatureAssessment:
        trend_score = self._score_trend(features)
        momentum_score = self._score_momentum(features)
        volatility_score = self._score_volatility(features)
        volume_score = self._score_volume(features)

        return FeatureAssessment(
            trend=trend_score,          # [-1, +1] negative=bearish, positive=bullish
            momentum=momentum_score,     # [-1, +1]
            volatility=volatility_score, # [0, 1] low=calm, high=volatile
            volume=volume_score,         # [-1, +1] negative=selling, positive=buying
        )
```

**Trend scoring:**
```python
def _score_trend(self, f):
    score = 0.0
    if f["ema_8"] > f["ema_21"]:
        score += 0.3   # Short-term trend bullish
    if f["close"] > f["sma_200"]:
        score += 0.2   # Above 200 SMA
    if f["adx"] > 25:
        score += 0.2 * (1 if f["plus_di"] > f["minus_di"] else -1)  # Trend direction
    if f["macd_histogram"] > 0:
        score += 0.15  # MACD momentum confirms
    if f["parabolic_sar"] < f["close"]:
        score += 0.15  # SAR below price = bullish
    return clamp(score, -1.0, 1.0)
```

Each sub-score is bounded and the weights sum to 1.0 per category. The weights are initially set from quantitative research and can be optimized through walk-forward backtesting.

**Multi-Timeframe Confirmation Matrix:**

Instead of letting a CNN learn multi-timeframe relationships, build an explicit confirmation matrix:

```python
confirmation_matrix = {
    "H1_trend": trend_direction_h1,       # Primary direction
    "M15_momentum": momentum_score_m15,    # Confirmation
    "M5_entry": entry_score_m5,            # Timing
    "M1_execution": execution_score_m1,    # Precision
}

alignment = sum(1 for v in confirmation_matrix.values() if v * primary_direction > 0)
confirmation_ratio = alignment / len(confirmation_matrix)
```

A confirmation ratio of 1.0 (all timeframes agree) produces the highest confidence; 0.50 (half agree) forces HOLD.

### 10.3 Replacing the Memory Layer

**Neural approach:** LTC + Hopfield maintains a 256-dimensional hidden state that accumulates evidence over time and retrieves similar historical patterns.

**Traditional replacement:** Two components:

**Explicit State Machine for Regime Tracking:**

```python
class RegimeStateMachine:
    def __init__(self):
        self.current_regime = "NEUTRAL"
        self.regime_duration = 0      # Bars in current regime
        self.transition_count = 0     # Transitions in last N bars
        self.confidence = 0.5

    def update(self, proposed_regime, bar_features):
        if proposed_regime == self.current_regime:
            self.regime_duration += 1
            self.confidence = min(0.95, self.confidence + 0.02)
        else:
            self.pending_count += 1
            if self.pending_count >= self.hysteresis_threshold:
                self.current_regime = proposed_regime
                self.regime_duration = 0
                self.transition_count += 1
                self.confidence = 0.55
                self.pending_count = 0
```

The state machine tracks how long the current regime has persisted (regime_duration) and how many transitions have occurred recently (transition_count). Long-duration regimes have higher confidence; frequent transitions suggest choppy conditions.

**Circular Buffer for Pattern Context:**

```python
class MarketContextBuffer:
    def __init__(self, window_size=64):
        self.buffer = deque(maxlen=window_size)

    def add(self, features: dict):
        self.buffer.append(features)

    def get_rolling_statistics(self):
        return {
            "mean_rsi": np.mean([b["rsi"] for b in self.buffer]),
            "std_atr": np.std([b["atr"] for b in self.buffer]),
            "trend_consistency": self._measure_trend_consistency(),
            "volatility_trend": self._measure_volatility_trend(),
            # ... all 60 features have rolling stats
        }
```

Rolling statistics over the last 64 bars provide the temporal context that the LTC network learns implicitly. The explicit version computes mean, standard deviation, percentile rank, and linear regression slope for each feature.

**EMA-Based Belief State:**

Replace the 64-dimensional neural belief vector with explicit EMAs of key metrics:

```python
class BeliefState:
    def __init__(self, alpha=0.1):
        self.trend_belief = 0.0      # EMA of trend score
        self.momentum_belief = 0.0   # EMA of momentum score
        self.regime_belief = 0.0     # EMA of regime confidence
        self.edge_belief = 0.0       # EMA of signal effectiveness

    def update(self, trend, momentum, regime_conf, last_signal_result):
        self.trend_belief = self.trend_belief * (1-alpha) + trend * alpha
        self.momentum_belief = self.momentum_belief * (1-alpha) + momentum * alpha
        self.regime_belief = self.regime_belief * (1-alpha) + regime_conf * alpha
        if last_signal_result is not None:
            self.edge_belief = self.edge_belief * 0.9 + last_signal_result * 0.1
```

The belief state accumulates directional bias over time — a sustained bullish trend_belief indicates persistent bullish conditions, equivalent to the neural belief vector encoding trend persistence.

### 10.4 Replacing the Strategy Layer

**Neural approach:** 4-Expert Mixture of Experts with regime gating selects and blends expert outputs using softmax-weighted averaging.

**Traditional replacement:** Strategy Pattern with regime-based routing:

```python
class StrategyRouter:
    def __init__(self):
        self.strategies = {
            "TRENDING_UP": TrendFollowingStrategy(direction="long"),
            "TRENDING_DOWN": TrendFollowingStrategy(direction="short"),
            "RANGING": MeanReversionStrategy(),
            "VOLATILE": VolatilityStrategy(),
            "CRISIS": CrisisStrategy(),
        }

    def route(self, regime: str, features: dict, context: BeliefState) -> Signal:
        strategy = self.strategies.get(regime, self.strategies["RANGING"])
        return strategy.generate_signal(features, context)
```

**TrendFollowingStrategy:**
```python
def generate_signal(self, features, context):
    conditions = [
        features["adx"] > 25,                    # Trend exists
        features["ema_8"] > features["ema_21"],   # Fast EMA above slow (for long)
        features["rsi"] > 40 and features["rsi"] < 70,  # Not overbought
        features["macd_histogram"] > 0,           # MACD confirms
        context.trend_belief > 0.3,               # Sustained trend belief
    ]
    met = sum(conditions) / len(conditions)

    if met >= 0.80:
        return Signal(direction="buy", confidence=Decimal(str(met)), strategy="trend_follow")
    return Signal(direction="hold", confidence=Decimal("0.30"))
```

**MeanReversionStrategy:**
```python
def generate_signal(self, features, context):
    # Buy at lower Bollinger Band with RSI oversold
    if features["bb_pct_b"] < 0.05 and features["rsi"] < 30:
        confidence = 0.50 + (30 - features["rsi"]) / 60  # Higher confidence at lower RSI
        return Signal(direction="buy", confidence=Decimal(str(confidence)), strategy="mean_reversion")

    # Sell at upper Bollinger Band with RSI overbought
    if features["bb_pct_b"] > 0.95 and features["rsi"] > 70:
        confidence = 0.50 + (features["rsi"] - 70) / 60
        return Signal(direction="sell", confidence=Decimal(str(confidence)), strategy="mean_reversion")

    return Signal(direction="hold", confidence=Decimal("0.30"))
```

**Weighted Scoring (replaces softmax gating):**

Instead of learned softmax weights, use configurable weight tables:

```python
regime_weights = {
    "TRENDING_UP":   {"trend": 0.60, "momentum": 0.25, "mean_rev": 0.05, "vol_break": 0.10},
    "RANGING":       {"trend": 0.10, "momentum": 0.15, "mean_rev": 0.60, "vol_break": 0.15},
    "VOLATILE":      {"trend": 0.15, "momentum": 0.10, "mean_rev": 0.10, "vol_break": 0.65},
}
```

These weights can be optimized through walk-forward backtesting on historical data.

### 10.5 Replacing the Pedagogy Layer

**Neural approach:** Value function V(s) estimates expected return; causal attribution explains which concepts drive the prediction; position sizing head outputs lot modifiers.

**Traditional replacement:**

**Expected Value Calculation:**
```python
def expected_value(self, symbol, regime, session):
    key = (symbol, regime, session)
    stats = self.historical_stats.get(key)
    if stats is None or stats.trade_count < 30:
        return 0.0  # Insufficient data
    return (stats.win_rate * stats.avg_win) - (stats.loss_rate * stats.avg_loss)
```

**Indicator Contribution Tracking:**
Instead of neural attribution, track which indicators were aligned with the signal direction on winning vs losing trades:

```python
def update_attribution(self, features, direction, outcome):
    for indicator, value in features.items():
        aligned = (value > 0 and direction == "buy") or (value < 0 and direction == "sell")
        if outcome > 0:  # Winning trade
            self.indicator_win_alignment[indicator] += 1 if aligned else 0
        self.indicator_total[indicator] += 1

    # Attribution = % of winning trades where indicator was aligned
    attribution = {ind: wins / total for ind, (wins, total) in zip(self.indicator_win_alignment, self.indicator_total)}
```

**Position Sizing:**
Replace the neural position sizing head with Sharpe-based sizing:

```python
def position_modifier(self, symbol, regime, session):
    ev = self.expected_value(symbol, regime, session)
    if ev <= 0:
        return 0.0  # Never trade with negative expected value

    sharpe = self.rolling_sharpe(symbol, regime, session)
    modifier = clamp(sharpe / 2.0, 0.25, 1.00)  # Sharpe of 2.0 = full size
    return modifier
```

### 10.6 Composite Confidence Scoring

The traditional system replaces neural confidence with a multi-factor composite:

```python
def compute_confidence(self, features, regime, session, symbol):
    # Factor 1: Indicator agreement (40%)
    agreement = self.indicator_agreement(features, proposed_direction)  # [0, 1]

    # Factor 2: Historical edge (35%)
    edge = self.historical_edge(symbol, regime, session)  # [0, 1]

    # Factor 3: Signal quality (25%)
    quality = self.signal_quality(features)  # [0, 1]

    confidence = 0.40 * agreement + 0.35 * edge + 0.25 * quality
    return Decimal(str(round(confidence, 4)))
```

**Indicator agreement:** What fraction of trend, momentum, volatility, and volume indicators point in the same direction as the proposed trade.

**Historical edge:** Based on the win rate and profit factor for this specific (symbol, regime, session) combination, computed from the trade history database.

**Signal quality:** Measures how far current indicator values are from their decision thresholds. An RSI of 20 (deep oversold) is a higher-quality mean-reversion signal than an RSI of 29 (barely oversold).

### 10.7 Performance Parity Analysis

**What the traditional system gains:**

- **Determinism:** Given the same inputs, the system always produces the same output. No stochastic elements from neural inference.
- **Explainability:** Every decision can be traced to specific indicator values and rules. No "black box" components.
- **No inference latency:** Rule evaluation is microseconds vs. milliseconds for neural forward pass.
- **No GPU requirement:** The entire system runs on CPU. Reduces hardware cost and complexity.
- **Easier debugging:** When a bad trade occurs, the exact rule that triggered it is identifiable.
- **Regulatory compliance:** Some jurisdictions require explainability for automated trading decisions.

**What the traditional system loses:**

- **Non-linear feature interactions:** The neural network discovers relationships between features that explicit rules may miss (e.g., "RSI divergence combined with volume drop in a specific regime produces a 70% reversal probability").
- **Pattern generalization:** Hopfield memory can recognize novel patterns similar to learned ones; explicit pattern matching requires exact or near-exact matches.
- **Adaptive gating:** Softmax gating dynamically adjusts expert weights based on current conditions; fixed weight tables require periodic re-optimization.
- **Temporal dynamics:** LTC captures multi-scale temporal dependencies that explicit EMAs approximate but do not fully replicate.

**Mitigation strategies:**

- **Extensive backtesting:** Walk-forward optimization over multiple years of data identifies robust parameter values.
- **Ensemble rules:** Combine multiple simple rules (each capturing a different feature interaction) to approximate the neural network's non-linear capacity.
- **Regular re-optimization:** Monthly recalibration of strategy weights and thresholds keeps the system adapted to changing market dynamics.
- **A/B comparison:** Run the traditional system alongside the neural system in shadow mode, comparing signal quality metrics to identify gaps.

---

## Chapter 11 — MT5 Bridge: Order Execution Service

### 11.1 MT5 Connector Architecture

The MT5 Connector wraps the MetaTrader5 Python package, providing a clean interface for account management, symbol information retrieval, and order execution:

```python
class MT5Connector:
    def connect(self) -> bool:
        """Initialize MT5 terminal and login."""
        mt5.initialize()
        mt5.login(account=self._account, password=self._password, server=self._server)

    def reconnect(self) -> bool:
        """Retry with exponential backoff: 1s, 2s, 4s, 8s, max 30s."""
        for attempt in range(max_retries):
            delay = min(2 ** attempt, 30)
            time.sleep(delay)
            if self.connect():
                return True
        return False

    def get_account_info(self) -> dict:
        """Returns balance, equity, margin, free_margin, profit, leverage."""
        info = mt5.account_info()
        return {
            "balance": to_decimal(info.balance),
            "equity": to_decimal(info.equity),
            "margin": to_decimal(info.margin),
            "free_margin": to_decimal(info.margin_free),
            "profit": to_decimal(info.profit),
            "leverage": info.leverage,
        }
```

All returned values are converted to `Decimal` using the `to_decimal()` utility from goliath-common. This prevents floating-point arithmetic errors in subsequent financial calculations.

### 11.2 Order Manager: Signal-to-Trade Translation

The OrderManager is the critical component that translates validated signals into broker orders. It implements the principle of defense in depth — multiple independent validation checks that must all pass before any order reaches the broker.

**9-Point Pre-Execution Validation:**

1. **Signal Age Check:** `if age_sec > 30: REJECT "signal too old"`. Stale signals are dangerous — the market may have moved significantly since the signal was generated.

2. **Direction Validation:** `if direction not in ("BUY", "SELL"): REJECT`. HOLD signals should never reach the order manager.

3. **Lot Size Positive:** `if lots <= 0: REJECT`. Zero or negative lots indicate upstream computation errors.

4. **Stop Loss Required:** `if stop_loss <= 0: REJECT`. No trade is permitted without a stop loss. This is a non-negotiable safety rule.

5. **Position Count Limit:** `if len(open_positions) >= max_position_count: REJECT`. Prevents over-exposure.

6. **Spread Check:** `if current_spread > 30 points: REJECT`. Protects against trading during spread-widened conditions.

7. **Margin Verification:** `connector.check_margin(symbol, direction, lots)`. Ensures sufficient free margin exists for the trade.

8. **Daily Loss Limit:** `if daily_loss_pct >= 2.0%: REJECT`. Prevents exceeding the daily risk budget.

9. **Drawdown Limit:** `if drawdown_pct >= max_drawdown_pct: REJECT`. Prevents trading during severe equity drawdown.

Each rejected signal raises a `SignalRejectedError` with the signal ID and specific rejection reason. Rejections are logged and counted in Prometheus metrics for operational monitoring.

**Signal Deduplication:**

The order manager maintains an in-memory dictionary of recently processed signal IDs:

```python
self._recent_signals: dict[str, float] = {}  # signal_id → timestamp

if signal_id in self._recent_signals:
    raise SignalRejectedError(signal_id, "duplicate signal")

# Register BEFORE execution to prevent concurrent duplicates
self._recent_signals[signal_id] = time.time()
```

Entries older than 300 seconds are periodically cleaned up. This prevents the same signal from being executed multiple times due to gRPC retries, network duplicates, or upstream processing loops.

**Thread-Safe Execution:**

All order execution is serialized through a threading lock:

```python
def execute_signal(self, signal):
    with self._execution_lock:
        return self._execute_signal_locked(signal)
```

This prevents race conditions where two signals arrive simultaneously and both pass the position count check (because neither has been executed yet). The lock ensures signals are processed one at a time.

**Lot Size Clamping:**

After validation, the lot size is clamped to broker constraints:

```python
def _clamp_lot_size(self, lots, symbol):
    lots = min(lots, self._max_lot_size)    # System-wide maximum
    symbol_info = self._connector.get_symbol_info(symbol)
    lots = max(lots, symbol_info.volume_min)  # Broker minimum
    lots = (lots // symbol_info.volume_step) * symbol_info.volume_step  # Quantize
    return lots
```

### 11.3 Market Order Submission

```python
request = {
    "action": mt5.TRADE_ACTION_DEAL,      # Market order
    "symbol": symbol,
    "volume": float(lots),
    "type": mt5.ORDER_TYPE_BUY,           # or ORDER_TYPE_SELL
    "price": tick.ask,                     # or tick.bid for SELL
    "sl": float(stop_loss),
    "tp": float(take_profit),
    "deviation": 20,                       # Max slippage in points
    "magic": 123456,                       # GOLIATH identifier
    "comment": "GOLIATH:abc12345",         # First 8 chars of signal_id
    "type_time": mt5.ORDER_TIME_GTC,
    "type_filling": mt5.ORDER_FILLING_IOC,
}
result = mt5.order_send(request)
```

The `magic` number (123456) identifies all GOLIATH-originated trades in the MT5 terminal, distinguishing them from manual trades or trades from other EAs. The `comment` field embeds a truncated signal ID for cross-referencing between the GOLIATH database and the MT5 trade history.

After execution, slippage is computed: `slippage = executed_price - requested_price`. Positive slippage on a BUY means the fill was worse than expected (paid more); negative slippage means it was better (paid less). Slippage metrics are tracked in Prometheus histograms for quality monitoring.

### 11.4 Limit Order Submission

Limit orders use `TRADE_ACTION_PENDING` instead of `TRADE_ACTION_DEAL`:

```python
request = {
    "action": mt5.TRADE_ACTION_PENDING,
    "type": mt5.ORDER_TYPE_BUY_LIMIT,  # or SELL_LIMIT
    "price": float(limit_price),        # Entry price
    # ... same SL, TP, deviation, magic, comment
}
```

Limit orders return status `PENDING` instead of `FILLED`. The position tracker monitors pending orders and detects when they are filled, cancelled, or expire.

### 11.5 Trade Recording

Every order submission is recorded to PostgreSQL's `trade_executions` table with:
- `order_id`: MT5-assigned order identifier.
- `signal_id`: Foreign key to the originating `trading_signals` record.
- `executed_price`, `requested_price`, `slippage_pips`: Fill quality metrics.
- `commission`, `swap`: Trading costs.
- `status`: FILLED, REJECTED, PENDING, CANCELLED.
- `rejection_reason`: If rejected, why.

This creates a complete audit trail linking every trade back to the signal that generated it, the cascade mode that produced the signal, and the reasoning chain that led to the decision.

### 11.6 Prometheus Metrics

```python
ORDERS_SUBMITTED = Counter("goliath_mt5_orders_submitted_total", labels=["symbol", "direction"])
ORDERS_FILLED = Counter("goliath_mt5_orders_filled_total", labels=["symbol", "direction"])
ORDER_LATENCY = Histogram("goliath_mt5_order_execution_seconds",
                          buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0))
```

These metrics enable Grafana dashboards showing:
- Fill rate: `FILLED / SUBMITTED` per symbol.
- Execution latency percentiles: P50, P95, P99.
- Rejection reasons: grouped by validation check.

---

## Chapter 12 — Database Architecture (TimescaleDB)

### 12.1 Schema Design Philosophy

The database schema is designed around three principles:

1. **Time-series first:** Market data tables are TimescaleDB hypertables with automatic chunking, compression, and continuous aggregates. This provides orders-of-magnitude better query performance for time-range queries compared to vanilla PostgreSQL.

2. **Financial precision:** All price, volume, and monetary columns use `NUMERIC(20,8)` — 20 total digits with 8 decimal places. This avoids IEEE 754 floating-point representation errors that can compound over millions of calculations. A gold price of $2050.12345678 is stored exactly, not as an approximation.

3. **Audit immutability:** The audit log table is append-only, enforced by database triggers that prevent UPDATE and DELETE operations. Each entry contains a SHA-256 hash of the previous entry, creating a cryptographic chain that detects tampering.

### 12.2 Core Market Data Tables

**ohlcv_bars:**
```sql
CREATE TABLE ohlcv_bars (
    time        TIMESTAMPTZ    NOT NULL,
    symbol      TEXT           NOT NULL,
    timeframe   TEXT           NOT NULL,  -- M1, M5, M15, H1, H4, D1
    open        NUMERIC(20,8) NOT NULL,
    high        NUMERIC(20,8) NOT NULL,
    low         NUMERIC(20,8) NOT NULL,
    close       NUMERIC(20,8) NOT NULL,
    volume      NUMERIC(20,8) DEFAULT 0,
    tick_count  INTEGER        DEFAULT 0,
    spread_avg  NUMERIC(10,5) DEFAULT 0,
    source      TEXT           NOT NULL DEFAULT 'unknown'
);
-- Hypertable with 1-day chunks
SELECT create_hypertable('ohlcv_bars', 'time', chunk_time_interval => INTERVAL '1 day');
-- Compression after 7 days, segmented by symbol and timeframe
ALTER TABLE ohlcv_bars SET (timescaledb.compress, timescaledb.compress_segmentby = 'symbol,timeframe');
SELECT add_compression_policy('ohlcv_bars', INTERVAL '7 days');
```

The `source` column distinguishes data origin: `"aggregator"` for bars built from live ticks, `"mock"` for development data, `"backfill"` for historical data loads. The unique index on `(time, symbol, timeframe)` prevents duplicate bars from re-ingestion.

**market_ticks:**
```sql
CREATE TABLE market_ticks (
    time        TIMESTAMPTZ    NOT NULL,
    symbol      TEXT           NOT NULL,
    bid         NUMERIC(20,8) NOT NULL,
    ask         NUMERIC(20,8) NOT NULL,
    last_price  NUMERIC(20,8),
    volume      NUMERIC(20,8) DEFAULT 0,
    spread      NUMERIC(10,5),
    source      TEXT           NOT NULL DEFAULT 'unknown'
);
-- Hypertable with 1-hour chunks (ticks are high-volume)
SELECT create_hypertable('market_ticks', 'time', chunk_time_interval => INTERVAL '1 hour');
-- Aggressive compression after 1 day
SELECT add_compression_policy('market_ticks', INTERVAL '1 day');
```

Tick data has much higher volume than bar data (potentially thousands of ticks per minute vs one bar per minute). The 1-hour chunk interval and 1-day compression policy keep storage manageable.

### 12.3 Trading Tables

**trading_signals:** Stores every signal generated by the AI Brain, whether executed or not.

**trade_executions:** Stores every order submitted to MT5, with a foreign key to the originating signal. This enables analysis of signal quality: which cascade modes produce the most profitable trades, which symbols have the best fill rates, and where slippage is highest.

### 12.4 Audit Log with Hash Chain

```sql
CREATE TABLE audit_log (
    id          BIGSERIAL      PRIMARY KEY,
    created_at  TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    service     TEXT           NOT NULL,
    action      TEXT           NOT NULL,
    entity_type TEXT,
    entity_id   TEXT,
    details     JSONB          NOT NULL DEFAULT '{}',
    prev_hash   TEXT           NOT NULL,
    hash        TEXT           NOT NULL
);
```

Each entry's `hash` is computed as: `SHA256(prev_hash + service + action + entity_type + entity_id + details)`. This creates a chain: any attempt to modify a historical entry would break the hash chain from that point forward, making tampering detectable.

Database triggers enforce append-only behavior:

```sql
CREATE TRIGGER audit_no_update
    BEFORE UPDATE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();

CREATE TRIGGER audit_no_delete
    BEFORE DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();
```

The `prevent_audit_modification()` function unconditionally raises an exception, making it impossible to update or delete audit entries even with administrative database access.

### 12.5 Macroeconomic Data Tables

The database stores macroeconomic data used for regime-aware trading:

**vix_data:** VIX spot and futures data with term structure analysis. Includes a `regime` column classifying the VIX environment: `'calm'` (< 15), `'elevated'` (15-25), `'panic'` (≥ 25).

**yield_curve_data:** US Treasury yields (2Y, 5Y, 10Y, 30Y) with calculated slopes:
- `slope_2_10`: 10Y - 2Y yield (negative = inverted curve = recession signal)
- `slope_2_30`: 30Y - 2Y yield

**cot_reports:** CFTC Commitment of Traders data showing institutional positioning:

```sql
CREATE TABLE cot_reports (
    time            TIMESTAMPTZ NOT NULL,
    symbol          TEXT        NOT NULL,
    asset_class     TEXT        NOT NULL,  -- "forex", "metals", "energy"
    commercial_long NUMERIC(20,4),         -- Commercial hedger longs
    commercial_short NUMERIC(20,4),        -- Commercial hedger shorts
    noncommercial_long NUMERIC(20,4),      -- Large speculator longs
    noncommercial_short NUMERIC(20,4),     -- Large speculator shorts
    nonreportable_long NUMERIC(20,4),      -- Retail trader longs
    nonreportable_short NUMERIC(20,4),     -- Retail trader shorts
    open_interest   NUMERIC(20,4),         -- Total open contracts
    net_speculative NUMERIC(20,4),         -- Net large spec position
    pct_long_spec   NUMERIC(8,4),          -- % of OI held long by specs
);
```

COT data provides a weekly snapshot of institutional positioning. Key signals:
- **Extreme net speculative positioning** (>2σ from historical mean) indicates a crowded trade that may reverse.
- **Commercial hedger positioning** opposite to speculators often precedes trend changes — commercials are considered "smart money."
- **Open interest declining** while price advances indicates weakening conviction in the trend.

The system uses COT data as a macro context feature (dimensions 40-50 in the feature vector). Extreme readings reduce position sizing through the volatility adjustment factor.

**recession_probability:** FRED's smoothed recession probability, updated monthly:

```sql
CREATE TABLE recession_probability (
    time        TIMESTAMPTZ NOT NULL,
    probability NUMERIC(6,4) NOT NULL,  -- 0.0000 to 1.0000
    source      TEXT DEFAULT 'FRED',
    indicator   TEXT DEFAULT 'RECPROUSM156N'
);
```

Values above 30% trigger increased caution in position sizing. Values above 50% activate a macro-level defensive posture that overrides regime classification for risk-on assets.

**Economic Calendar:**

```sql
CREATE TABLE economic_events (
    id          SERIAL PRIMARY KEY,
    time        TIMESTAMPTZ NOT NULL,
    currency    TEXT NOT NULL,           -- "USD", "EUR", "GBP", etc.
    event_name  TEXT NOT NULL,           -- "Non-Farm Payrolls", "FOMC Rate Decision"
    impact      TEXT NOT NULL,           -- "high", "medium", "low"
    actual      NUMERIC(20,8),           -- Released value
    forecast    NUMERIC(20,8),           -- Market consensus
    previous    NUMERIC(20,8),           -- Prior period value
    surprise    NUMERIC(20,8),           -- actual - forecast
);

CREATE TABLE trading_blackouts (
    id          SERIAL PRIMARY KEY,
    start_time  TIMESTAMPTZ NOT NULL,
    end_time    TIMESTAMPTZ NOT NULL,
    event_name  TEXT NOT NULL,
    currencies  TEXT[] NOT NULL,          -- Affected currencies
    reason      TEXT,
);
```

High-impact events (NFP, FOMC, ECB Rate Decision, CPI) create automatic trading blackout periods. The system stops opening new positions 30 minutes before a high-impact USD event and resumes 15 minutes after release. This avoids the extreme spread widening and slippage that occurs during news releases.

**Event Impact Rules:**

```sql
CREATE TABLE event_impact_rules (
    id              SERIAL PRIMARY KEY,
    event_pattern   TEXT NOT NULL,           -- LIKE pattern: "%NFP%", "%FOMC%"
    asset_class     TEXT NOT NULL,           -- "forex", "metals", "all"
    pre_event_minutes INTEGER DEFAULT 30,     -- Blackout before event
    post_event_minutes INTEGER DEFAULT 15,    -- Blackout after event
    sizing_multiplier NUMERIC(4,2) DEFAULT 0.50,  -- Position size during event window
    max_spread_override INTEGER,              -- Override max spread during event
);
```

These rules are configurable per event type and asset class. For example, FOMC decisions create a 60-minute pre-event and 30-minute post-event blackout for all USD pairs, while minor economic indicators only trigger a 15-minute pre-event window with 50% position sizing.

### 12.6 RBAC Roles

Four database roles enforce the principle of least privilege:

| Role | Permissions | Rationale |
|------|------------|-----------|
| `data_ingestion_svc` | INSERT/SELECT on ohlcv_bars, market_ticks, macro tables | Can write market data but not read/modify trading signals |
| `ai_brain_svc` | SELECT on all market/ML/macro data; INSERT/UPDATE on signals, strategy_performance | Can read all data and write signals but cannot modify trade executions |
| `mt5_bridge_svc` | SELECT on trading_signals; INSERT/UPDATE on trade_executions | Can read signals and write executions but cannot modify market data |
| `goliath_admin` | Full privileges | For migrations, maintenance, and emergency operations only |

Each service connects to the database using its own credentials. If the AI Brain service is compromised, the attacker can read market data and write signals but cannot directly modify trade execution records or delete audit logs.

### 12.7 Continuous Aggregates

For dashboard performance, pre-computed materialized views aggregate raw data:

```sql
CREATE MATERIALIZED VIEW strategy_daily_summary
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', ts) AS bucket,
    strategy_name,
    symbol,
    COUNT(*) AS total_signals,
    SUM(CASE WHEN status='win' THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN status='loss' THEN 1 ELSE 0 END) AS losses,
    AVG(confidence) AS avg_confidence
FROM strategy_performance
GROUP BY bucket, strategy_name, symbol;
```

This view is automatically refreshed by TimescaleDB, providing sub-second query times for dashboard panels that would otherwise require full table scans.

---

## Chapter 13 — Inter-Service Communication

### 13.1 gRPC and Protobuf Contracts

All inter-service communication uses gRPC with Protocol Buffers, providing type-safe, versioned, language-agnostic interfaces. Five `.proto` files define the complete communication contract:

**trading_signal.proto** — Brain → MT5 Bridge:

```protobuf
message TradingSignal {
    string signal_id       = 1;
    string symbol          = 2;
    Direction direction    = 3;     // BUY, SELL, HOLD
    string confidence      = 4;     // Decimal string "0.7500"
    string suggested_lots  = 5;     // Decimal string "0.02"
    string stop_loss       = 6;     // Decimal string "2045.00"
    string take_profit     = 7;     // Decimal string "2060.00"
    int64 timestamp        = 8;     // Unix nanoseconds UTC
    string model_version   = 9;
    string regime          = 10;    // "TRENDING_UP"
    SourceTier source_tier = 11;    // ML_PRIMARY, TECHNICAL, RULE_BASED
    string reasoning       = 12;    // "COPER mode: 5 similar experiences..."
    string risk_reward_ratio = 13;  // Decimal string "1.85"
}

service TradingSignalService {
    rpc SendSignal(TradingSignal) returns (SignalAck);
    rpc StreamSignals(stream TradingSignal) returns (stream SignalAck);
}
```

**Critical design decision:** All financial values are `string` fields containing decimal representations, not `float` or `double`. Protobuf's `double` type uses IEEE 754, which cannot exactly represent values like 0.10. Using strings ensures that `"2050.12345678"` is transmitted and received exactly, with parsing into `Decimal` at the receiving end.

**Nanosecond timestamps** (`int64`) provide sub-microsecond precision for signal ordering and latency measurement. Unix nanoseconds can represent dates from 1677 to 2262 without overflow.

**execution.proto** — MT5 Bridge trade lifecycle:

```protobuf
message TradeExecution {
    string order_id        = 1;
    string signal_id       = 2;
    string symbol          = 3;
    Direction direction    = 4;
    string requested_price = 5;
    string executed_price  = 6;
    string quantity        = 7;     // Lots
    string stop_loss       = 8;
    string take_profit     = 9;
    Status status          = 10;    // PENDING, FILLED, REJECTED, CANCELLED
    string slippage_pips   = 11;
    string commission      = 12;
    string swap            = 13;
    int64 executed_at      = 14;
    string rejection_reason = 15;
}

service ExecutionBridgeService {
    rpc ExecuteTrade(TradingSignal) returns (TradeExecution);
    rpc StreamTradeUpdates(HealthCheckRequest) returns (stream TradeExecution);
    rpc CheckHealth(HealthCheckRequest) returns (HealthCheckResponse);
}
```

**ml_inference.proto** — ML Training Lab inference service:

```protobuf
message PredictionRequest {
    string symbol          = 1;
    string regime          = 2;
    map<string, string> features = 3;  // 60-dim feature vector as key-value pairs
    string model_version   = 4;
    int64 timestamp        = 5;
}

message PredictionResponse {
    string direction       = 1;    // "BUY", "SELL", "HOLD"
    string confidence      = 2;    // Decimal string "0.7500"
    string reasoning       = 3;
    string model_version   = 4;
    string model_type      = 5;    // "jepa", "gnn", "mlp", "ensemble"
    map<string, string> metadata = 6;  // Gate weights, attribution, etc.
    int64 inference_time_us = 7;    // Inference latency in microseconds
}

service MLInferenceService {
    rpc Predict(PredictionRequest) returns (PredictionResponse);
    rpc GetModelInfo(ModelInfoRequest) returns (ModelInfoResponse);
}
```

The `features` map uses string keys (`"f0"` through `"f59"`) mapping to string-encoded decimal values. This avoids defining a rigid protobuf message with 60 named fields, allowing the feature vector to evolve without schema changes.

**health.proto** — Standard health check protocol:

```protobuf
message HealthCheckRequest {
    string service_name = 1;
}

enum HealthStatus {
    STATUS_UNKNOWN = 0;
    STATUS_HEALTHY = 1;
    STATUS_DEGRADED = 2;
    STATUS_UNHEALTHY = 3;
}

message HealthCheckResponse {
    HealthStatus status = 1;
    string message = 2;
    map<string, string> details = 3;
    int64 timestamp = 4;           // UTC nanoseconds
    double uptime_seconds = 5;
}
```

Every gRPC service implements the health check protocol. The AI Brain's health response includes details like: `{"regime": "TRENDING_UP", "maturity": "CONVICTION", "signal_count": "142", "pipeline_latency_p95_ms": "12.3"}`.

### 13.2 Shared Python Library (goliath-common)

The `goliath-common` package provides shared utilities used by all Python services:

**decimal_utils.py** — Safe financial arithmetic:

```python
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

ZERO = Decimal("0")

def to_decimal(value) -> Decimal:
    """Convert any value to Decimal safely."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))  # str() avoids float representation issues
    if isinstance(value, (int, str)):
        return Decimal(value)
    return Decimal(str(value))

def safe_div(numerator: Decimal, denominator: Decimal, default: Decimal = ZERO) -> Decimal:
    """Division with zero-division protection."""
    if denominator == ZERO:
        return default
    return numerator / denominator
```

The `to_decimal(float_value)` pattern — converting to string first — is essential. `Decimal(0.1)` produces `Decimal('0.1000000000000000055511151231257827021181583404541015625')` (the IEEE 754 representation), while `Decimal(str(0.1))` produces `Decimal('0.1')` (the intended value).

**enums.py** — Shared enumerations:

```python
class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

class SignalType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"

class SourceTier(str, Enum):
    ML_PRIMARY = "ML_PRIMARY"
    TECHNICAL = "TECHNICAL"
    SENTIMENT = "SENTIMENT"
    RULE_BASED = "RULE_BASED"
```

Using `str` enums enables direct JSON serialization and comparison with string values from configuration and database.

**metrics.py** — Prometheus instrumentation helpers:

```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server

def setup_metrics_server(port: int):
    """Start Prometheus metrics HTTP server on the given port."""
    start_http_server(port)

# Pre-defined metric families for brain pipeline
brain_pipeline_latency = Histogram(
    "goliath_brain_pipeline_seconds",
    "Time to process one bar through the full pipeline",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)
brain_signals_generated = Counter(
    "goliath_brain_signals_total",
    "Total trading signals generated",
    ["symbol", "direction", "source_tier"],
)
brain_current_regime = Gauge(
    "goliath_brain_current_regime",
    "Current market regime (encoded as integer)",
    ["symbol"],
)
```

### 13.3 ZeroMQ PUB/SUB

Data Ingestion publishes market data to a ZMQ PUB socket. The AI Brain subscribes to specific topics:

```
Publisher topics:
    "bar.XAU/USD.M1"   — 1-minute gold bars
    "bar.EUR/USD.M5"   — 5-minute EURUSD bars
    "trade.polygon.XAU/USD"  — raw tick data

Subscriber filter:
    subscriber.subscribe("bar.")  — receive all bars for all symbols
    subscriber.subscribe("bar.XAU/USD")  — receive all timeframes for gold
```

ZMQ is chosen over Redis PUB/SUB for market data because:
- ZMQ is brokerless (no Redis dependency for critical data path).
- ZMQ PUB/SUB drops messages to slow subscribers rather than buffering (desirable for real-time data).
- ZMQ supports multi-part messages and topic filtering at the network level.

### 13.3 Redis Usage Patterns

Redis serves four distinct purposes:

1. **Kill Switch State:** Key `goliath:kill_switch` stores JSON with `active` flag, reason, and timestamp. All services check this key before performing trading operations. The 1-second local cache TTL balances responsiveness with Redis query volume.

2. **Rate Limiting:** Token bucket state stored per-service. Sliding window counters for API rate limiting on the MT5 Bridge.

3. **PUB/SUB Alerts:** Channel `goliath:alerts` broadcasts critical notifications (kill switch activation, circuit breaker trips) to all subscribing services and the dashboard.

4. **Real-Time Cache:** Latest tick data cached with 5-second TTL for dashboard quick-access queries without hitting TimescaleDB.

### 13.4 Service Discovery

**Development (Docker Compose):** Services resolve each other by container name: `data-ingestion`, `ai-brain`, `postgres`, `redis`. Docker's internal DNS handles name resolution.

**Production (Proxmox VMs):** Services use static IP addresses defined in `configs/goliath_services.yaml`:

```yaml
services:
  data_ingestion:
    host: 10.0.1.10
    grpc_port: 5555
  ai_brain:
    host: 10.0.4.10
    grpc_port: 50054
  mt5_bridge:
    host: 10.0.4.11
    grpc_port: 50055
```

---

## Chapter 14 — Kill Switch and Safety Systems

### 14.1 Kill Switch Architecture

The kill switch is the most critical safety component in the system. When activated, it immediately halts all trading activity across all services. It is designed with a fail-closed principle: any uncertainty about the kill switch's state defaults to "trading halted."

**Redis-Backed Distributed State:**

```python
KILL_SWITCH_KEY = "goliath:kill_switch"

# State when active:
{
    "active": true,
    "reason": "Daily loss limit reached: 2.1% >= 2.0%",
    "activated_at": 1709123456.789
}
```

**Fail-Closed Design:**

```python
class KillSwitch:
    def __init__(self):
        self._cached_active = True   # Default: BLOCK TRADING until Redis confirms safe
        self._cache_ts = 0.0
        self._cache_ttl = 1.0        # 1-second local cache

    async def connect(self):
        self._redis = await aioredis.from_url(redis_url)
        await self._redis.ping()
        self._cached_active = False  # Redis is reachable → safe to trade
```

If Redis is unreachable at startup, `_cached_active` remains `True` and all trading is blocked. This is the correct behavior — if the system cannot verify the kill switch state, the safe default is to not trade.

If Redis becomes unreachable during operation (network partition), the cached state is preserved. If the last known state was "active," trading remains halted. If the last known state was "inactive," trading continues until the cache expires (1 second), after which the system logs a warning and keeps the cached state (does not default to blocking — this prevents a Redis blip from halting an otherwise healthy system).

Corrupt Redis data (JSON parse failure) triggers fail-closed: `self._cached_active = True`.

**Auto-Check Triggers:**

```python
async def auto_check(self, daily_loss_pct, max_daily_loss_pct, drawdown_pct, max_drawdown_pct):
    if daily_loss_pct >= max_daily_loss_pct:
        await self.activate(f"Daily loss {daily_loss_pct}% >= limit {max_daily_loss_pct}%")
    elif drawdown_pct >= max_drawdown_pct:
        await self.activate(f"Drawdown {drawdown_pct}% >= limit {max_drawdown_pct}%")
```

The auto-check runs after every trade execution and periodically during the AI Brain's main loop. Default limits: 2% daily loss, 10% maximum drawdown.

**Alert Broadcasting:**

On activation, the kill switch publishes to the `goliath:alerts` Redis channel:

```python
await self._redis.publish("goliath:alerts", json.dumps({
    "level": "CRITICAL",
    "title": "KILL SWITCH ACTIVATED",
    "body": reason,
}))
```

All services subscribing to `goliath:alerts` receive this notification immediately. The dashboard displays it as a critical alert. The monitoring service can forward it to Telegram or email.

**Audit Log:**

Every activation, deactivation, and auto-check trigger is persisted to Redis as an audit entry:

```python
await self._redis.rpush(KILL_SWITCH_AUDIT_KEY, json.dumps({
    "timestamp": time.time(),
    "action": "ACTIVATED",
    "reason": reason,
    "actor": "auto_check",
    "daily_loss_pct": str(daily_loss_pct),
    "drawdown_pct": str(drawdown_pct),
}))
await self._redis.ltrim(KILL_SWITCH_AUDIT_KEY, -200, -1)  # Keep last 200 entries
```

### 14.2 Maturity Gate

The maturity gate implements progressive trading enablement. It prevents the system from trading with full capital before the model or strategy has proven itself:

**Sizing Multipliers:**

| State | Multiplier | Trading Mode | Max Lot |
|-------|-----------|-------------|---------|
| DOUBT | 0.00 | BACKTEST_ONLY | 0.00 |
| CRISIS | 0.00 | BACKTEST_ONLY | 0.00 |
| LEARNING | 0.35 | PAPER_TRADING | 0.25 |
| CONVICTION | 0.80 | MICRO_LIVE | 0.50 |
| MATURE | 1.00 | FULL_LIVE | 1.00 |

The gate applies the multiplier to the signal's confidence:

```python
def apply(self, direction, confidence, maturity):
    multiplier = MATURITY_SIZING[maturity]
    if multiplier == 0.0:
        return GatedSignal(direction="hold", confidence=Decimal("0"), blocked=True)
    adjusted_confidence = confidence * Decimal(str(multiplier))
    return GatedSignal(direction=direction, confidence=adjusted_confidence, blocked=False)
```

**Hysteresis Gate:**

State transitions require consecutive confirmations:

```python
class HysteresisGate:
    up_threshold = 3     # 3 consecutive periods to upgrade
    down_threshold = 2   # 2 consecutive periods to downgrade

    def update(self, proposed_state):
        if proposed_state > self.current_state:
            # Upgrade attempt
            if self.pending_state == proposed_state:
                self.pending_count += 1
            else:
                self.pending_state = proposed_state
                self.pending_count = 1

            if self.pending_count >= self.up_threshold:
                self.current_state = proposed_state
                self.pending_count = 0
        elif proposed_state < self.current_state:
            # Downgrade attempt (faster)
            if self.pending_count >= self.down_threshold:
                self.current_state = proposed_state
                self.pending_count = 0
```

### 14.3 Spiral Protection

Consecutive losses trigger automatic position size reduction through the PnLMomentumTracker:

```python
class PnLMomentumTracker:
    def record_trade(self, pnl):
        if pnl < 0:
            self.consecutive_losses += 1
            self.consecutive_wins = 0
        else:
            self.consecutive_wins += 1
            self.consecutive_losses = 0

    @property
    def spiral_multiplier(self):
        if self.consecutive_losses < 3:
            return 1.0
        reduction = self.consecutive_losses * 0.15
        return max(0.25, 1.0 - reduction)
```

The spiral multiplier compounds with the drawdown scaling factor: `final_lots = base_lots × drawdown_scale × spiral_multiplier`. This creates multiple layers of defense against runaway losses.

---

# PART III: DEVSECOPS AND OPERATIONS

---

## Chapter 15 — Security Architecture

### 15.1 TLS/mTLS Infrastructure

All inter-service communication in production uses TLS encryption. The certificate infrastructure supports both server-side TLS (clients verify server identity) and mutual TLS (mTLS, where both client and server authenticate each other).

**Certificate Authority Setup:**

A self-signed root CA is generated for development and staging environments:

```bash
# Generate CA private key (4096-bit RSA)
openssl genrsa -out ca.key 4096

# Generate CA certificate (365-day validity)
openssl req -x509 -new -nodes -key ca.key -sha256 -days 365 \
    -out ca.crt -subj "/CN=GOLIATH Root CA"
```

**Per-Service Certificates:**

Each service receives its own certificate signed by the CA, with Subject Alternative Names (SANs) covering all possible hostnames:

```bash
# Generate service key
openssl genrsa -out ai-brain.key 4096

# Generate CSR with SAN configuration
openssl req -new -key ai-brain.key -out ai-brain.csr \
    -config <(cat <<EOF
[req]
distinguished_name = dn
req_extensions = v3_req
[dn]
CN = ai-brain
[v3_req]
subjectAltName = DNS:ai-brain,DNS:localhost,DNS:goliath-ai-brain,IP:127.0.0.1
EOF
)

# Sign with CA
openssl x509 -req -in ai-brain.csr -CA ca.crt -CAkey ca.key \
    -CAcreateserial -out ai-brain.crt -days 365 -sha256 \
    -extfile <(echo "subjectAltName=DNS:ai-brain,DNS:localhost,DNS:goliath-ai-brain,IP:127.0.0.1")
```

Six service certificates are generated: ai-brain, mt5-bridge, data-ingestion, ml-training, postgres-server, redis-server.

**File permissions:**
- Private keys: `chmod 600` (owner read-only)
- Public certificates: `chmod 644` (world-readable)
- `.gitignore` excludes all `.key` files from version control

**Container-Level TLS Configuration:**

In docker-compose.yml, certificates are mounted as read-only volumes:

```yaml
volumes:
  - ./certs/ca.crt:/etc/ssl/certs/ca.crt:ro
  - ./certs/ai-brain.crt:/etc/ssl/certs/ai-brain.crt:ro
  - ./certs/ai-brain.key:/etc/ssl/private/ai-brain.key:ro
```

TLS is toggled globally via `GOLIATH_TLS_ENABLED`:
- When `false` (development default): All services communicate in plaintext. Faster startup, simpler debugging.
- When `true` (production): PostgreSQL requires TLS connections. Redis disables the non-TLS port (`--port 0`). gRPC services use mTLS with the CA certificate for mutual authentication.

**Production recommendation:** Replace self-signed certificates with CA-signed certificates from an internal PKI or Let's Encrypt for any externally-accessible endpoints.

### 15.2 mTLS for gRPC Communication

When `GOLIATH_TLS_ENABLED=true`, all gRPC channels use mutual TLS. The client (e.g., AI Brain calling MT5 Bridge) must present its certificate, and the server (MT5 Bridge) verifies it against the CA:

```python
# From goliath_common/grpc_credentials.py
import grpc

def create_secure_channel(target: str, ca_cert_path: str,
                          client_cert_path: str, client_key_path: str):
    with open(ca_cert_path, "rb") as f:
        ca_cert = f.read()
    with open(client_cert_path, "rb") as f:
        client_cert = f.read()
    with open(client_key_path, "rb") as f:
        client_key = f.read()

    credentials = grpc.ssl_channel_credentials(
        root_certificates=ca_cert,
        private_key=client_key,
        certificate_chain=client_cert,
    )
    return grpc.secure_channel(target, credentials)


def create_server_credentials(ca_cert_path: str,
                               server_cert_path: str, server_key_path: str):
    with open(ca_cert_path, "rb") as f:
        ca_cert = f.read()
    with open(server_cert_path, "rb") as f:
        server_cert = f.read()
    with open(server_key_path, "rb") as f:
        server_key = f.read()

    return grpc.ssl_server_credentials(
        [(server_key, server_cert)],
        root_certificates=ca_cert,
        require_client_auth=True,  # mTLS: client must present certificate
    )
```

With mTLS enabled, even if an attacker gains network access to the backend Docker network, they cannot communicate with any service without possessing a valid client certificate signed by the CA. This provides defense-in-depth: network isolation (Docker internal network) + transport encryption (TLS) + mutual authentication (mTLS).

**PostgreSQL TLS Configuration:**

When TLS is enabled, PostgreSQL is configured to require SSL connections:

```yaml
postgres:
    command: >
        postgres
        -c ssl=on
        -c ssl_cert_file=/etc/ssl/certs/postgres-server.crt
        -c ssl_key_file=/etc/ssl/private/postgres-server.key
        -c ssl_ca_file=/etc/ssl/certs/ca.crt
```

Services connect with `sslmode=verify-full`, ensuring the server's certificate is valid and matches the expected hostname.

**Redis TLS Configuration:**

When TLS is enabled, Redis disables the plaintext port and listens only on the TLS port:

```yaml
redis:
    command: >
        redis-server
        --requirepass ${GOLIATH_REDIS_PASSWORD}
        --port 0
        --tls-port 6379
        --tls-cert-file /etc/ssl/certs/redis-server.crt
        --tls-key-file /etc/ssl/private/redis-server.key
        --tls-ca-cert-file /etc/ssl/certs/ca.crt
        --tls-auth-clients yes
```

The `--port 0` flag ensures no unencrypted Redis traffic is possible.

### 15.3 Database RBAC

The database implements role-based access control with four service-specific roles, each with the minimum permissions needed for its function:

**data_ingestion_svc:**
```sql
GRANT SELECT, INSERT ON ohlcv_bars, market_ticks TO data_ingestion_svc;
GRANT SELECT, INSERT ON vix_data, yield_curve_data, cot_reports TO data_ingestion_svc;
-- Cannot read trading_signals or trade_executions
-- Cannot modify or delete any data
```

**ai_brain_svc:**
```sql
GRANT SELECT ON ohlcv_bars, market_ticks, vix_data, yield_curve_data TO ai_brain_svc;
GRANT SELECT ON model_registry, model_metrics, ml_predictions TO ai_brain_svc;
GRANT INSERT, UPDATE ON trading_signals, strategy_performance TO ai_brain_svc;
GRANT CREATE ON SCHEMA public TO ai_brain_svc;  -- For own temp tables
-- Cannot modify trade_executions or market data
```

**mt5_bridge_svc:**
```sql
GRANT SELECT ON trading_signals TO mt5_bridge_svc;
GRANT INSERT, UPDATE ON trade_executions, strategy_performance TO mt5_bridge_svc;
-- Cannot modify market data, signals, or ML models
```

**goliath_admin:**
```sql
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO goliath_admin;
-- Used only for migrations, maintenance, emergency operations
```

Per-service passwords are set through environment variables (`DI_DB_PASSWORD`, `BRAIN_DB_PASSWORD`, `MT5_DB_PASSWORD`) and initialized by the `007_rbac_passwords.sh` script during database first boot.

### 15.3 Secrets Management

All secrets are loaded from environment variables, never hardcoded:

```python
# From goliath_common/secrets.py
def get_secret(key: str, required: bool = True) -> str:
    value = os.environ.get(key, "")
    if required and not value:
        raise RuntimeError(f"Required secret {key} not set")
    return value
```

The `.env.example` file documents all required secrets without containing actual values:

```bash
GOLIATH_DB_PASSWORD=         # Required, min 16 chars
GOLIATH_REDIS_PASSWORD=      # Required, min 16 chars
POLYGON_API_KEY=             # Required for production
MT5_ACCOUNT=                 # Required for live trading
MT5_PASSWORD=                # Required for live trading
```

**Security controls:**
- `.env` is in `.gitignore` — never committed to version control.
- Docker Compose validates required passwords with `${VARIABLE:?required}` syntax.
- The CI pipeline runs `trufflehog filesystem` to detect accidentally committed secrets.

### 15.4 Rate Limiting

The MT5 Bridge implements rate limiting to prevent runaway signal submission:

**Sliding Window Rate Limiter:**
```python
class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests    # Default: 10
        self.window_seconds = window_seconds  # Default: 60
        self.timestamps = deque()

    def allow(self) -> bool:
        now = time.time()
        # Remove timestamps outside the window
        while self.timestamps and now - self.timestamps[0] > self.window_seconds:
            self.timestamps.popleft()
        if len(self.timestamps) >= self.max_requests:
            return False
        self.timestamps.append(now)
        return True
```

**Token Bucket Rate Limiter:**
```python
class TokenBucketRateLimiter:
    def __init__(self, rate: float, burst: int):
        self.rate = rate       # Tokens per second
        self.burst = burst     # Maximum bucket size
        self.tokens = burst    # Start full
        self.last_refill = time.monotonic()

    def allow(self) -> bool:
        self._refill()
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False
```

Both implementations are used at different layers: sliding window for per-client API rate limiting, token bucket for internal signal processing rate control.

### 15.5 Audit Trail Integrity

The SHA-256 hash chain in the audit log provides cryptographic tamper detection:

```python
# From goliath_common/audit_pg.py
import hashlib

def compute_hash(prev_hash: str, service: str, action: str, entity_type: str,
                 entity_id: str, details: dict) -> str:
    payload = f"{prev_hash}|{service}|{action}|{entity_type}|{entity_id}|{json.dumps(details, sort_keys=True)}"
    return hashlib.sha256(payload.encode()).hexdigest()
```

**Verification:** To verify the integrity of the audit log, read all entries in order and recompute each hash:

```python
def verify_audit_chain(entries: list[dict]) -> bool:
    for i, entry in enumerate(entries):
        expected_hash = compute_hash(
            entries[i-1]["hash"] if i > 0 else "genesis",
            entry["service"], entry["action"],
            entry["entity_type"], entry["entity_id"],
            entry["details"]
        )
        if entry["hash"] != expected_hash:
            return False  # Chain broken at entry i
    return True
```

If any entry has been modified, its hash will not match the recomputed value, and all subsequent entries will also fail verification (since they depend on the previous hash).

---

## Chapter 16 — CI/CD and Build Pipeline

### 16.1 GitHub Actions CI Pipeline

The main CI pipeline (`ci.yml`) triggers on pushes to `main` and pull requests targeting `main`. It runs five parallel jobs:

**Job 1: Python Lint and Test (Ubuntu)**
```yaml
steps:
  - Checkout code
  - Setup Python 3.11
  - Install dependencies (pip install -e shared/python-common)
  - Ruff lint check (import sorting, unused imports, style violations)
  - Black format check (120 char line width, consistent formatting)
  - Mypy type check (strict mode for core services)
  - pytest: python-common unit tests
  - pytest: ai-brain tests (321+ tests)
  - pytest: ml-training tests
  - pytest: mt5-bridge tests
  - pytest: console tests
  - pytest: dashboard backend tests
  - GOLIATH health check (dev_health.py)
  - Brain verification (brain_verify.py --quick)
```

The brain verification (`brain_verify.py`) runs 115 rules checking that the AI Brain satisfies deployment requirements: all configuration parameters are within acceptable ranges, all pipeline modules load successfully, and basic inference produces valid outputs.

**Job 2: Python Test on Windows**
```yaml
runs-on: windows-latest
steps:
  - Run regression tests for Windows-specific signal handler behavior
```

This catches platform-specific issues: Python's `signal` module behaves differently on Windows (no SIGTERM, limited signal support), which affects graceful shutdown logic.

**Job 3: Dashboard Frontend (Node.js 22)**
```yaml
steps:
  - npm ci (install dependencies from lockfile)
  - npm run lint (ESLint + TypeScript checks)
  - npm test (React component tests: App, GaugeChart, KPICard)
```

**Job 4: Go Lint and Test**
```yaml
steps:
  - Setup Go 1.22
  - go vet ./... (static analysis)
  - golangci-lint run (comprehensive linting)
  - go test -v -race ./... (tests with race detector enabled)
```

The `-race` flag enables Go's race detector, which instruments the binary to detect concurrent memory access violations at runtime. This catches data races in the WebSocket connector and aggregator that would be invisible without the detector.

**Job 5: Docker Build**
```yaml
steps:
  - Build data-ingestion image
  - Build ai-brain image
  - Build mt5-bridge image
  - Build ml-training image
  - Build dashboard image
  # Images are built but not pushed (validation only)
```

**Concurrency control:** `concurrency: group: ci-${{ github.ref }}, cancel-in-progress: true`. If a new push arrives while a CI run is in progress for the same branch, the old run is cancelled to conserve compute resources.

### 16.2 Security Scanning Pipeline

The security pipeline (`security.yml`) runs weekly (Monday 06:00 UTC), on dependency changes, and on manual trigger:

**Python Dependency Audit:**
```yaml
- pip-audit --strict --desc
  # Checks all installed packages against the Python Advisory Database
  # --strict: fail on any known vulnerability
  # --desc: include vulnerability descriptions in output
```

**Go Vulnerability Check:**
```yaml
- govulncheck ./...
  # Checks Go modules against the Go Vulnerability Database
  # Only reports vulnerabilities that affect reachable code paths
```

**Secret Scanning:**
```yaml
- trufflehog filesystem --directory=. --fail
  # Scans entire repository for accidentally committed secrets
  # Detects patterns: API keys, passwords, private keys, tokens
  # --fail: exit with non-zero if any secrets found
```

### 16.3 Makefile Build Orchestration

The Makefile provides a unified interface for all build and test operations:

```makefile
VENV := .venv/bin
PYTHON := $(VENV)/python
PYTEST := $(VENV)/pytest
RUFF := $(VENV)/ruff
BLACK := $(VENV)/black
MYPY := $(VENV)/mypy

.PHONY: proto build-go test lint fmt typecheck ci docker-build docker-up docker-down

proto:
    protoc --python_out=shared/proto/gen/python --go_out=shared/proto/gen/go shared/proto/*.proto

build-go:
    cd services/data-ingestion && go build -o ../../bin/data-ingestion cmd/server/main.go

test: test-python test-go

test-python:
    $(PYTEST) shared/python-common/tests/ -v
    $(PYTEST) services/ai-brain/tests/ -v
    $(PYTEST) services/ml-training/tests/ -v
    $(PYTEST) services/mt5-bridge/tests/ -v

test-go:
    cd services/data-ingestion && go test -v -race ./...

lint:
    $(RUFF) check .
    $(BLACK) --check .
    cd services/data-ingestion && go vet ./... && golangci-lint run

ci: lint typecheck test docker-build
```

The `ci` target chains all validation steps in order. If any step fails, the chain stops (Make's default behavior with `&&`-style chaining).

### 16.4 Docker Image Construction

**Multi-Stage Builds** minimize final image size by separating build dependencies from runtime:

**Dashboard (example of 2-stage build):**
```dockerfile
# Stage 1: Build React frontend
FROM node:22-alpine AS frontend-build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci --production=false
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend + built frontend
FROM python:3.11-slim
RUN useradd -m -u 1000 goliath
WORKDIR /app
COPY backend/ ./backend/
COPY --from=frontend-build /app/dist ./frontend/dist
RUN pip install --no-cache-dir -r backend/requirements.txt
USER goliath
EXPOSE 8888
CMD ["python", "-m", "backend.main"]
```

**Security practices in Dockerfiles:**
- Non-root user execution (`USER goliath` with UID 1000).
- `--no-cache-dir` prevents pip from storing downloaded packages in the image.
- Minimal base images (`python:3.11-slim`, `golang:1.22-alpine`).
- `.dockerignore` excludes `.git/`, `__pycache__/`, `*.pyc`, `.env`, and test files from the build context.

---

## Chapter 17 — Container Orchestration and Deployment

### 17.1 Docker Compose Configuration

The main `docker-compose.yml` defines 11 services across 3 networks with 6 persistent volumes:

**Service Dependencies:**

```
postgres ──┬──► data-ingestion ──► ai-brain ──► mt5-bridge
redis   ───┘                          │
                                      └──► ml-training

prometheus ──► grafana
tensorboard (standalone)
dashboard ──► postgres, redis
```

Dependencies are enforced with `depends_on` and health check conditions:

```yaml
ai-brain:
    depends_on:
        data-ingestion:
            condition: service_healthy
        postgres:
            condition: service_healthy
        redis:
            condition: service_healthy
```

The AI Brain will not start until data-ingestion, postgres, and redis all pass their health checks. This prevents startup races where the Brain tries to query the database before it has finished initializing.

**Health Check Configuration:**

```yaml
postgres:
    healthcheck:
        test: ["CMD-SHELL", "pg_isready -U ${GOLIATH_DB_USER:-goliath}"]
        interval: 10s
        timeout: 5s
        retries: 5

redis:
    healthcheck:
        test: ["CMD", "redis-cli", "-a", "${GOLIATH_REDIS_PASSWORD}", "ping"]
        interval: 10s
        timeout: 5s
        retries: 5

ai-brain:
    healthcheck:
        test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:9092/')\""]
        interval: 30s
        timeout: 10s
        retries: 3
        start_period: 60s
```

The `start_period` for ai-brain (60 seconds) allows time for model loading and pipeline initialization before health checks begin failing.

### 17.2 Network Isolation

```yaml
networks:
    backend:
        internal: true   # No external access
    frontend:
        # External access allowed
    monitoring:
        # Prometheus scrape network
```

The `internal: true` flag on the backend network is a critical security measure. Even if a container on the backend network is compromised, it cannot make outbound HTTP requests to external servers. Data exfiltration requires first pivoting to a container on the frontend network.

### 17.3 GPU Support

ML training with GPU acceleration uses Docker Compose profiles:

```yaml
ml-training-gpu:
    profiles: ["gpu"]
    build:
        dockerfile: Dockerfile.rocm   # AMD ROCm 7.1
    deploy:
        resources:
            limits:
                cpus: "4.0"
                memory: 8G
    devices:
        - /dev/kfd:/dev/kfd
        - /dev/dri:/dev/dri
    group_add:
        - video
        - render
```

To launch with GPU support: `docker compose --profile gpu up ml-training-gpu`. Without the profile flag, the CPU-based `ml-training` service is used instead.

The ROCm Dockerfile installs AMD's ROCm 7.1 runtime and PyTorch ROCm wheels, enabling training on AMD GPUs (Radeon RX 7900 XTX and similar). HSA (Heterogeneous System Architecture) environment variables are configured for optimal GPU memory management.

### 17.4 Production Deployment on Proxmox

In production, services are distributed across Proxmox VMs with static IP addressing:

| VM | Services | IP Range | Purpose |
|----|----------|----------|---------|
| Data VM | Data Ingestion | 10.0.1.x | Market data collection |
| Database VM | PostgreSQL, Redis | 10.0.2.x | Data persistence |
| Trading VM | AI Brain, MT5 Bridge, ML Training | 10.0.4.x | Trading logic |
| Monitoring VM | Prometheus, Grafana, TensorBoard | 10.0.5.x | Observability |

Each VM runs Docker Compose with environment-specific configuration (`configs/production/` YAML files). The production configs differ from development in:
- Longer timeouts for database connections and gRPC calls.
- TLS enabled (`GOLIATH_TLS_ENABLED=true`).
- Tuned resource limits based on actual usage patterns.
- Connection pooling configured for production load.

---

## Chapter 18 — Monitoring and Observability

### 18.1 Prometheus Metrics Collection

Prometheus scrapes metrics from all services every 15 seconds:

```yaml
scrape_configs:
  - job_name: 'data-ingestion'
    static_configs:
      - targets: ['data-ingestion:9090']
  - job_name: 'ai-brain'
    static_configs:
      - targets: ['ai-brain:9092']
  - job_name: 'mt5-bridge'
    static_configs:
      - targets: ['mt5-bridge:9094']
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

Each service exposes metrics via the `/metrics` endpoint using the standard Prometheus client libraries (prometheus_client for Python, promhttp for Go).

**Key Business Metrics:**

| Metric | Type | Labels | Purpose |
|--------|------|--------|---------|
| `goliath_pipeline_latency_seconds` | Histogram | service | End-to-end signal generation time |
| `goliath_signals_total` | Counter | symbol, direction, source_tier | Signal generation rate |
| `goliath_mt5_orders_submitted_total` | Counter | symbol, direction | Order submission rate |
| `goliath_mt5_orders_filled_total` | Counter | symbol, direction | Fill rate |
| `goliath_mt5_order_execution_seconds` | Histogram | — | Broker execution latency |
| `goliath_current_drawdown_pct` | Gauge | — | Current account drawdown |
| `goliath_daily_loss_pct` | Gauge | — | Current day's loss percentage |
| `goliath_kill_switch_active` | Gauge | — | Kill switch state (0 or 1) |
| `goliath_ticks_total` | Counter | symbol | Ingested tick count |
| `goliath_bars_total` | Counter | symbol, timeframe | Generated bar count |
| `goliath_ml_inference_seconds` | Histogram | model_type | Neural inference latency |
| `goliath_regime` | Gauge | regime | Current market regime encoding |

### 18.2 Alert Rules

Nine alert rules are defined across two severity groups:

**Safety Alerts (evaluated every 15 seconds):**

```yaml
- alert: KillSwitchActivated
  expr: goliath_kill_switch_active == 1
  for: 0m
  labels:
    severity: critical
  annotations:
    summary: "Kill switch is ACTIVE — all trading halted"

- alert: CriticalDrawdown
  expr: goliath_current_drawdown_pct > 5.0
  for: 0m
  labels:
    severity: critical
  annotations:
    summary: "Drawdown exceeds 5% — kill switch imminent"

- alert: CriticalDailyLoss
  expr: goliath_daily_loss_pct >= 2.0
  for: 0m
  labels:
    severity: critical
  annotations:
    summary: "Daily loss limit reached — immediate kill switch"

- alert: SpiralProtectionActive
  expr: goliath_consecutive_losses > 3
  for: 0m
  labels:
    severity: warning
  annotations:
    summary: "3+ consecutive losses — position sizing reduced"
```

**Infrastructure Alerts (evaluated every 30 seconds):**

```yaml
- alert: NoTicksReceived
  expr: rate(goliath_ticks_total[5m]) == 0
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "No market data received for 5 minutes"

- alert: HighPipelineLatency
  expr: histogram_quantile(0.99, goliath_pipeline_latency_seconds) > 0.1
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "P99 pipeline latency exceeds 100ms"

- alert: ServiceDown
  expr: up == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Service {{ $labels.instance }} is unreachable"
```

### 18.3 Grafana Dashboards

Five pre-provisioned dashboards auto-load on Grafana startup:

1. **GOLIATH Overview:** System health, service status, pipeline throughput, active alerts.
2. **Data Pipeline:** Tick ingestion rates, bar publication rates, WebSocket connection status, database write latency.
3. **Trading Performance:** Win rate, P&L curve, signal confidence distribution, regime breakdown, strategy attribution.
4. **Risk Management:** Drawdown history, daily loss tracking, kill switch history, position count, spiral protection status.
5. **ML Training:** Training loss curves, validation accuracy, inference latency percentiles, model comparison.

Dashboards use Prometheus as the data source with PromQL queries. Auto-provisioning ensures dashboards are recreated on container restart:

```yaml
grafana:
    volumes:
        - ./grafana/provisioning:/etc/grafana/provisioning:ro
        - ./grafana/dashboards:/var/lib/grafana/dashboards:ro
```

### 18.4 Structured Logging

All Python services use structlog for JSON-formatted structured logging:

```python
from goliath_common.logging import setup_logging, get_logger

setup_logging("ai-brain", level="INFO")
logger = get_logger(__name__)

logger.info("Signal generated",
    symbol="XAUUSD",
    direction="buy",
    confidence="0.75",
    source_mode="hybrid",
    regime="TRENDING_UP",
    latency_ms=12.5,
)
```

Output:
```json
{
    "timestamp": "2024-03-01T14:30:00.123Z",
    "level": "info",
    "service": "ai-brain",
    "module": "ai_brain.orchestrator",
    "event": "Signal generated",
    "symbol": "XAUUSD",
    "direction": "buy",
    "confidence": "0.75",
    "source_mode": "hybrid",
    "regime": "TRENDING_UP",
    "latency_ms": 12.5
}
```

Go services use uber-go/zap with the same JSON output format, enabling unified log aggregation across language boundaries.

---

## Chapter 19 — ML Training Pipeline

### 19.1 Training Orchestrator

The ML Training Lab is a separate service responsible for model training, validation, and serving inference requests. The training orchestrator manages the full lifecycle:

```python
class TrainingOrchestrator:
    def train(self, dataset, config):
        for epoch in range(config.max_epochs):
            # Forward + backward pass
            train_loss = self._training_cycle.run_epoch(
                model=self._model,
                dataloader=train_loader,
                optimizer=optimizer,
                grad_clip_norm=1.0,
            )

            # Validation
            val_loss = self._evaluate(val_loader)

            # Early stopping check
            if val_loss < self._best_val_loss:
                self._best_val_loss = val_loss
                self._patience_counter = 0
                self._save_checkpoint(epoch, val_loss)
            else:
                self._patience_counter += 1
                if self._patience_counter >= config.patience:
                    logger.info("Early stopping", epoch=epoch, best_val_loss=self._best_val_loss)
                    break
```

**Gradient clipping** at norm 1.0 prevents exploding gradients during training on volatile market data where extreme values can produce large loss gradients.

**Deterministic seeding:** All random operations use seed 42 for reproducibility. Given the same data and configuration, training produces identical results.

### 19.2 Walk-Forward Validation

Walk-forward validation prevents temporal data leakage by enforcing strict chronological ordering:

```python
def generate_walk_forward_windows(n_samples, n_windows=5, min_train_size=200):
    """Generate expanding-window train/val/test splits."""
    windows = []
    for i in range(n_windows):
        train_end = min_train_size + i * step_size
        val_end = train_end + val_size
        test_end = val_end + test_size

        windows.append(WalkForwardWindow(
            train_start=0, train_end=train_end,
            val_start=train_end, val_end=val_end,
            test_start=val_end, test_end=test_end,
        ))
    return windows
```

**Key principle:** The model never sees future data during training. Train on bars 1-1000, validate on 1001-1150, test on 1151-1300. Then expand: train on 1-1200, validate on 1201-1350, test on 1351-1500. Each window produces a model, and the overall performance is averaged across windows.

The temporal split ratios are 70% training, 15% validation, 15% test. Data is never shuffled — the time ordering is preserved exactly.

### 19.3 Data Preprocessing

**Outlier Filtering:**

```python
z_scores = np.abs((features - features.mean(axis=0)) / features.std(axis=0))
mask = (z_scores < 4.0).all(axis=1)
filtered_features = features[mask]
```

A Z-score threshold of 4.0 removes extreme outliers (flash crashes, data glitches) while preserving genuinely volatile but valid market conditions. A threshold of 3.0 would be too aggressive, removing legitimate high-volatility events.

**RobustScaler Fitting:**

```python
scaler = RobustScaler()
scaler.fit(train_features)  # Fit ONLY on training data

train_scaled = scaler.transform(train_features)
val_scaled = scaler.transform(val_features)      # Same scaler
test_scaled = scaler.transform(test_features)     # Same scaler
live_scaled = scaler.transform(live_features)     # Same scaler in production
```

The scaler parameters (median, IQR per feature) are serialized alongside the model checkpoint, ensuring that live inference uses identical normalization.

### 19.4 Model Architectures

The ML Training Lab supports multiple architectures, selectable by configuration:

**JEPA (Joint Embedding Predictive Architecture):** The default architecture. Learns representations by predicting masked portions of the input sequence. Effective for self-supervised pretraining on large unlabeled market data.

**GNN (Graph Neural Network):** Treats instruments as nodes in a correlation graph. Edges represent cross-asset correlations. Captures inter-market dependencies (gold-dollar inverse correlation, equity-volatility relationship).

**MLP (Multi-Layer Perceptron):** Simple feedforward network as a baseline. Fast training, lower capacity.

**Ensemble:** Combines predictions from multiple models using weighted averaging. Weights are optimized on validation data.

### 19.5 Checkpoint Management

Checkpoints are saved when validation loss improves:

```python
def _save_checkpoint(self, epoch, val_loss):
    checkpoint = {
        "epoch": epoch,
        "model_state_dict": self._model.state_dict(),
        "optimizer_state_dict": self._optimizer.state_dict(),
        "val_loss": val_loss,
        "config": self._config,
        "scaler_params": self._scaler.get_params(),
    }
    path = f"/data/models/checkpoint_epoch{epoch}_loss{val_loss:.6f}.pt"
    torch.save(checkpoint, path)

    # SHA-256 hash for audit trail
    with open(path, "rb") as f:
        hash_hex = hashlib.sha256(f.read()).hexdigest()
    logger.info("Checkpoint saved", path=path, hash=hash_hex[:16])
```

The SHA-256 hash enables traceability: every signal generated by the AI Brain includes the `model_version` (hash) of the checkpoint used for inference. If a signal produces a bad trade, the exact model state can be recovered and analyzed.

### 19.6 gRPC Inference Service

The ML Training Lab also serves as an inference endpoint:

```protobuf
service MLInferenceService {
    rpc Predict(PredictionRequest) returns (PredictionResponse);
    rpc GetModelInfo(ModelInfoRequest) returns (ModelInfoResponse);
}
```

The AI Brain can request inference from the ML Training Lab when local inference is not configured or when the training service has a newer model. The response includes direction, confidence, reasoning, model version, and inference latency in microseconds.

### 19.7 Model Registry

The database tracks all trained models:

```sql
CREATE TABLE model_registry (
    id               SERIAL PRIMARY KEY,
    model_name       TEXT NOT NULL,
    model_type       TEXT NOT NULL,       -- "jepa", "gnn", "mlp", "ensemble"
    version          TEXT UNIQUE NOT NULL,
    checkpoint_path  TEXT NOT NULL,
    validation_accuracy NUMERIC(8,6),
    validation_loss  NUMERIC(12,8),
    is_active        BOOLEAN DEFAULT FALSE,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    config           JSONB
);
```

Only one model can be `is_active = TRUE` at a time. The AI Brain loads the active model's checkpoint on startup and reloads when the active model changes.

### 19.8 External Data Service

The External Data Service ingests macroeconomic data from three primary sources, enriching the system's market context beyond pure price action:

**FRED (Federal Reserve Economic Data):**
- US Treasury yields (2Y, 5Y, 10Y, 30Y) — updated daily.
- Federal Funds Rate — updated at each FOMC meeting.
- Smoothed US Recession Probabilities — updated monthly.
- Consumer Price Index (CPI) — updated monthly.
- Non-Farm Payrolls (NFP) — updated monthly (first Friday).

**CBOE (Chicago Board Options Exchange):**
- VIX spot index — updated continuously during market hours.
- VIX futures (1-month, 2-month, 3-month) — enables term structure analysis.
- Term structure slope: when near-term VIX futures trade above spot (backwardation), it indicates immediate fear; when below spot (contango), it indicates complacency.

**CFTC (Commodity Futures Trading Commission):**
- Commitment of Traders reports — released weekly (Friday, based on Tuesday positions).
- Net speculative positioning for gold, euro, pound, yen, Australian dollar.
- Open interest trends — expanding OI confirms trend conviction; declining OI warns of exhaustion.

**Data Ingestion Pattern:**

```python
class ExternalDataService:
    def __init__(self):
        self.fred_client = FREDClient(api_key=os.environ["FRED_API_KEY"])
        self.cboe_scraper = CBOEScraper()
        self.cftc_parser = CFTCParser()

    async def ingest_cycle(self):
        """Run periodically (every 6 hours for daily data, weekly for COT)."""
        # Treasury yields
        yields = self.fred_client.get_series(["DGS2", "DGS5", "DGS10", "DGS30"])
        self._store_yield_curve(yields)

        # VIX data
        vix = self.cboe_scraper.get_vix_data()
        self._store_vix(vix)

        # COT reports (weekly only)
        if self._is_cot_update_day():
            cot = self.cftc_parser.get_latest_report()
            self._store_cot(cot)

        # Recession probability
        recession = self.fred_client.get_series(["RECPROUSM156N"])
        self._store_recession_probability(recession)
```

**Yield Curve Analysis:**

The yield curve provides forward-looking economic signals:

```python
def analyze_yield_curve(self, yields: dict) -> YieldCurveAnalysis:
    slope_2_10 = yields["DGS10"] - yields["DGS2"]
    slope_2_30 = yields["DGS30"] - yields["DGS2"]

    if slope_2_10 < 0:
        curve_state = "INVERTED"  # Recession signal
        risk_adjustment = 0.70    # Reduce position sizing by 30%
    elif slope_2_10 < 0.25:
        curve_state = "FLAT"      # Late cycle warning
        risk_adjustment = 0.85
    elif slope_2_10 < 1.0:
        curve_state = "NORMAL"    # Healthy economy
        risk_adjustment = 1.00
    else:
        curve_state = "STEEP"     # Early recovery / easing cycle
        risk_adjustment = 1.00

    return YieldCurveAnalysis(
        slope_2_10=slope_2_10,
        slope_2_30=slope_2_30,
        state=curve_state,
        risk_adjustment=Decimal(str(risk_adjustment)),
    )
```

An inverted yield curve (10Y yield below 2Y yield) has preceded every US recession since 1955. The trading system uses this as a long-lead-time defensive signal: when the curve inverts, position sizing is reduced by 30% across all instruments as a precautionary measure.

**VIX Term Structure Analysis:**

```python
def analyze_vix_term_structure(self, spot, m1_future, m2_future, m3_future):
    # Contango: futures > spot (normal, complacent market)
    # Backwardation: futures < spot (fear, hedging demand)
    contango_ratio = m1_future / max(spot, 0.01)

    if contango_ratio < 0.95:
        structure = "BACKWARDATION"  # Immediate fear
        risk_level = "HIGH"
    elif contango_ratio < 1.05:
        structure = "FLAT"           # Transitional
        risk_level = "MEDIUM"
    else:
        structure = "CONTANGO"       # Normal, complacent
        risk_level = "LOW"

    return VIXTermStructure(
        spot=spot,
        m1=m1_future,
        contango_ratio=contango_ratio,
        structure=structure,
        risk_level=risk_level,
    )
```

Backwardation in VIX futures is a strong signal of institutional hedging demand and typically precedes or accompanies sharp market declines. The system treats VIX backwardation as a risk-off signal that reduces maximum position sizes.

### 19.9 Feature Drift Detection and Retraining

The MLLifecycleController monitors feature distributions for drift — changes in the statistical properties of input features that indicate the model's training data is no longer representative of current market conditions:

```python
class MLLifecycleController:
    def __init__(self, drift_threshold=3.0, window_size=1000):
        self.drift_threshold = drift_threshold
        self.window_size = window_size
        self.baseline_stats = {}  # {feature_name: (mean, std)} from training

    def check_drift(self, features: dict) -> DriftReport:
        drifted_features = []

        for feature_name, value in features.items():
            if feature_name in self.baseline_stats:
                mean, std = self.baseline_stats[feature_name]
                z_score = (value - mean) / max(std, 1e-10)

                if abs(z_score) > self.drift_threshold:
                    drifted_features.append(DriftedFeature(
                        name=feature_name,
                        z_score=z_score,
                        current_value=value,
                        baseline_mean=mean,
                        baseline_std=std,
                    ))

        drift_ratio = len(drifted_features) / max(len(features), 1)

        return DriftReport(
            drifted_features=drifted_features,
            drift_ratio=drift_ratio,
            needs_retraining=drift_ratio > 0.15,  # >15% of features drifted
        )
```

When more than 15% of features show significant drift (Z-score > 3.0 from training baseline), the system signals that retraining is needed. The maturity gate may downgrade from MATURE to CONVICTION or LEARNING in response, reducing position sizing while the model is retrained.

**Retraining Trigger Flow:**

```
Feature Drift Detected (>15% features drifted)
    │
    ├─► Log drift report with specific features and Z-scores
    ├─► Publish alert to goliath:alerts Redis channel
    ├─► Reduce maturity state (MATURE → CONVICTION)
    └─► Queue retraining job:
            1. Fetch latest 6 months of market data from TimescaleDB
            2. Rebuild feature pipeline with updated data
            3. Run walk-forward training with early stopping
            4. Validate new model on hold-out period
            5. If validation_loss < current_model_loss × 1.05:
                   Deploy new model (update model_registry, set is_active)
            6. Else:
                   Keep current model, log validation failure
```

This automated retraining loop ensures the model stays adapted to evolving market conditions without manual intervention. The 1.05 factor (5% tolerance) prevents deploying a new model that is only marginally better — the improvement must be meaningful to justify the deployment risk.

### 19.10 Training Loss Functions

The MarketRAPCoach training uses a composite loss function:

```python
class CompositeTrainingLoss:
    def __init__(self, signal_weight=1.0, value_weight=0.3, sparsity_weight=1e-4):
        self.signal_weight = signal_weight
        self.value_weight = value_weight
        self.sparsity_weight = sparsity_weight

    def compute(self, output, targets):
        # Signal classification loss (cross-entropy)
        signal_loss = F.cross_entropy(output["signal_logits"], targets["direction_label"])

        # Value estimation loss (MSE)
        value_loss = F.mse_loss(output["value_estimate"].squeeze(), targets["forward_return"])

        # Gate sparsity regularization (L1)
        gate_weights = output["gate_weights"]
        sparsity_loss = torch.mean(torch.abs(gate_weights))

        # Composite
        total = (self.signal_weight * signal_loss +
                self.value_weight * value_loss +
                self.sparsity_weight * sparsity_loss)

        return total, {
            "signal_loss": signal_loss.item(),
            "value_loss": value_loss.item(),
            "sparsity_loss": sparsity_loss.item(),
            "total_loss": total.item(),
        }
```

**Direction Labels:** Training labels are generated from forward returns: if the price moved up by more than 1 ATR in the next N bars, the label is BUY; if it moved down by more than 1 ATR, the label is SELL; otherwise, HOLD. This creates labels based on actual market outcomes rather than lagging indicators.

**Forward Return Targets:** The `forward_return` target for the value head is the risk-adjusted return over the next N bars, computed as: `forward_return = (close[t+N] - close[t]) / ATR[t]`. Normalizing by ATR makes the target comparable across instruments and volatility regimes.

**Class Imbalance:** Financial data is heavily imbalanced — HOLD labels typically outnumber BUY and SELL by 3:1 or more. The training pipeline uses weighted cross-entropy loss with class weights inversely proportional to class frequency: `weight[class] = total_samples / (n_classes × class_count)`. This prevents the model from converging to "always predict HOLD."

---

# PART IV: TRADITIONAL SYSTEM DESIGN

---

## Chapter 20 — Complete Non-AI System Design

### 20.1 Architecture Overview

This chapter provides a complete blueprint for building a trading system with equivalent power to GOLIATH V1 but without neural network inference. The traditional system reuses the data ingestion, database, communication, risk management, and execution layers unchanged. Only the decision engine — the AI Brain — is replaced with a deterministic, rule-based analysis pipeline.

**What stays identical (no changes needed):**
- Data Ingestion Service (Go): WebSocket connectors, normalization, aggregation, ZMQ publishing, DB writer.
- TimescaleDB schema: All tables, hypertables, compression, audit log.
- Redis: Kill switch, rate limiting, pub/sub, real-time cache.
- MT5 Bridge: Order manager, connector, position tracker, trade recorder.
- gRPC contracts: TradingSignal, TradeExecution, Health — same Protobuf definitions.
- Monitoring stack: Prometheus, Grafana, alert rules.
- Security: TLS/mTLS, RBAC, secrets management, audit trail.
- CI/CD: Same GitHub Actions pipelines, Makefile targets, Docker builds.

**What changes:**
The AI Brain service's internal pipeline is restructured. The neural network components (MarketRAPCoach, InferenceEngine, ShadowEngine) are removed. The 4-mode cascade is simplified. The feature engineering pipeline remains identical — the 60-dimensional feature vector is still computed. The difference is what consumes those features.

### 20.2 Traditional Decision Engine Architecture

The traditional engine replaces the neural cascade with a three-stage deterministic pipeline:

```
Stage 1: Market Assessment
    ├── Feature Scoring (indicator-based)
    ├── Regime Classification (same algorithm)
    └── Context Analysis (session, macro, volatility)

Stage 2: Strategy Selection and Signal Generation
    ├── Regime Router (Strategy Pattern)
    ├── Strategy Execution (regime-specific rules)
    ├── Multi-Timeframe Confirmation
    └── Composite Confidence Scoring

Stage 3: Signal Validation and Emission
    ├── Experience Lookup (historical pattern match)
    ├── Confidence Gating (minimum threshold)
    ├── Maturity Gate (same as neural version)
    └── gRPC Signal Emission (same as neural version)
```

### 20.3 Stage 1: Market Assessment

**Feature Scoring Module:**

The feature scorer replaces the CNN perception layer. Instead of learning which features matter, it applies domain-knowledge-driven scoring:

```python
class MarketAssessment:
    def __init__(self):
        self.trend_scorer = TrendScorer()
        self.momentum_scorer = MomentumScorer()
        self.volatility_scorer = VolatilityScorer()
        self.volume_scorer = VolumeScorer()
        self.structure_scorer = MarketStructureScorer()

    def assess(self, features: dict, regime: str, session: str) -> Assessment:
        return Assessment(
            trend=self.trend_scorer.score(features),
            momentum=self.momentum_scorer.score(features),
            volatility=self.volatility_scorer.score(features),
            volume=self.volume_scorer.score(features),
            structure=self.structure_scorer.score(features),
            regime=regime,
            session=session,
        )
```

**TrendScorer (detailed implementation):**

```python
class TrendScorer:
    """Scores trend strength and direction on [-1, +1]."""

    def score(self, f: dict) -> float:
        components = []

        # Moving average alignment (30% weight)
        if f["ema_8"] > f["ema_21"] > f["sma_50"]:
            components.append(("ma_align", 0.30, +1.0))  # Strong bullish alignment
        elif f["ema_8"] < f["ema_21"] < f["sma_50"]:
            components.append(("ma_align", 0.30, -1.0))  # Strong bearish alignment
        elif f["ema_8"] > f["ema_21"]:
            components.append(("ma_align", 0.30, +0.5))  # Partial bullish
        elif f["ema_8"] < f["ema_21"]:
            components.append(("ma_align", 0.30, -0.5))  # Partial bearish
        else:
            components.append(("ma_align", 0.30, 0.0))

        # ADX trend strength (25% weight)
        adx = f.get("adx", 0)
        di_direction = 1.0 if f.get("plus_di", 0) > f.get("minus_di", 0) else -1.0
        adx_score = min(adx / 50.0, 1.0) * di_direction  # Normalize ADX to [0, 1]
        components.append(("adx", 0.25, adx_score))

        # MACD direction (20% weight)
        macd_hist = f.get("macd_histogram", 0)
        macd_score = clamp(macd_hist / max(abs(f.get("atr", 1)), 0.0001), -1.0, 1.0)
        components.append(("macd", 0.20, macd_score))

        # Price position relative to key levels (15% weight)
        close = f.get("close", 0)
        sma_200 = f.get("sma_200", close)
        if sma_200 > 0:
            deviation = (close - sma_200) / sma_200
            pos_score = clamp(deviation * 10, -1.0, 1.0)
        else:
            pos_score = 0.0
        components.append(("price_position", 0.15, pos_score))

        # Parabolic SAR (10% weight)
        if f.get("sar", 0) < close:
            sar_score = 0.5  # Bullish
        elif f.get("sar", 0) > close:
            sar_score = -0.5  # Bearish
        else:
            sar_score = 0.0
        components.append(("sar", 0.10, sar_score))

        # Weighted sum
        total = sum(weight * value for _, weight, value in components)
        return clamp(total, -1.0, 1.0)
```

**MomentumScorer:**

```python
class MomentumScorer:
    """Scores momentum on [-1, +1]."""

    def score(self, f: dict) -> float:
        components = []

        # RSI position (30% weight)
        rsi = f.get("rsi", 50)
        rsi_score = (rsi - 50) / 50  # Map [0, 100] to [-1, +1]
        components.append(("rsi", 0.30, rsi_score))

        # Stochastic (20% weight)
        stoch_k = f.get("stoch_k", 50)
        stoch_score = (stoch_k - 50) / 50
        components.append(("stochastic", 0.20, stoch_score))

        # ROC (20% weight)
        roc = f.get("roc", 0)
        roc_score = clamp(roc / 2.0, -1.0, 1.0)  # Normalize: 2% ROC = max score
        components.append(("roc", 0.20, roc_score))

        # MACD histogram trend (15% weight)
        hist = f.get("macd_histogram", 0)
        prev_hist = f.get("prev_macd_histogram", 0)
        if hist > prev_hist:
            macd_trend = 0.5   # Increasing momentum
        elif hist < prev_hist:
            macd_trend = -0.5  # Decreasing momentum
        else:
            macd_trend = 0.0
        components.append(("macd_trend", 0.15, macd_trend))

        # Williams %R (15% weight)
        williams = f.get("williams_r", -50)
        williams_score = (williams + 50) / 50  # Map [-100, 0] to [-1, +1]
        components.append(("williams", 0.15, williams_score))

        total = sum(weight * value for _, weight, value in components)
        return clamp(total, -1.0, 1.0)
```

**VolatilityScorer:**

```python
class VolatilityScorer:
    """Scores volatility on [0, 1]. 0=calm, 1=extreme."""

    def score(self, f: dict) -> float:
        components = []

        # ATR ratio (40% weight)
        atr_ratio = f.get("atr_ratio", 1.0)
        atr_score = min((atr_ratio - 0.5) / 2.5, 1.0)  # Normalize: ratio 3.0 = max
        components.append(("atr", 0.40, max(0, atr_score)))

        # Bollinger bandwidth (30% weight)
        bb_bw = f.get("bb_bandwidth", 0)
        bb_score = min(bb_bw / 0.1, 1.0)  # Normalize: 10% bandwidth = max
        components.append(("bb_bw", 0.30, bb_score))

        # Historical volatility (20% weight)
        hv = f.get("hist_vol", 0)
        hv_score = min(hv / 0.5, 1.0)  # Normalize: 50% annualized = max
        components.append(("hist_vol", 0.20, hv_score))

        # Parkinson volatility (10% weight)
        pv = f.get("parkinson_vol", 0)
        pv_score = min(pv / 0.4, 1.0)
        components.append(("parkinson", 0.10, pv_score))

        total = sum(weight * value for _, weight, value in components)
        return clamp(total, 0.0, 1.0)
```

### 20.4 Stage 2: Strategy Selection and Signal Generation

**Strategy Pattern Implementation:**

```python
class StrategyInterface(ABC):
    @abstractmethod
    def generate_signal(self, assessment: Assessment, features: dict,
                       context: MarketContextBuffer) -> StrategySignal: ...

class RegimeRouter:
    def __init__(self):
        self._strategies = {
            "TRENDING_UP": TrendFollowingStrategy(bias="long"),
            "TRENDING_DOWN": TrendFollowingStrategy(bias="short"),
            "RANGING": MeanReversionStrategy(),
            "HIGH_VOLATILITY": VolatilityStrategy(),
            "CRISIS": CrisisStrategy(),
            "NEUTRAL": NeutralStrategy(),
        }

    def route(self, assessment: Assessment, features: dict,
              context: MarketContextBuffer) -> StrategySignal:
        strategy = self._strategies.get(assessment.regime, self._strategies["NEUTRAL"])
        return strategy.generate_signal(assessment, features, context)
```

**TrendFollowingStrategy (complete implementation):**

```python
class TrendFollowingStrategy(StrategyInterface):
    def __init__(self, bias: str = "long"):
        self.bias = bias  # "long" for TRENDING_UP, "short" for TRENDING_DOWN

    def generate_signal(self, assessment, features, context):
        direction = "buy" if self.bias == "long" else "sell"

        # Entry conditions
        conditions = {
            "trend_aligned": assessment.trend > 0.3 if self.bias == "long" else assessment.trend < -0.3,
            "momentum_confirms": assessment.momentum > 0.1 if self.bias == "long" else assessment.momentum < -0.1,
            "adx_strong": features.get("adx", 0) > 25,
            "not_overbought": features.get("rsi", 50) < 75 if self.bias == "long" else features.get("rsi", 50) > 25,
            "volume_supports": assessment.volume > -0.2,
        }

        met_count = sum(1 for v in conditions.values() if v)
        total = len(conditions)
        agreement = met_count / total

        if agreement >= 0.80:  # 4 of 5 conditions met
            # Calculate stop loss and take profit
            atr = features.get("atr", 0)
            close = features.get("close", 0)

            if self.bias == "long":
                stop_loss = close - 1.5 * atr
                take_profit = close + 2.5 * atr  # 1.67 RR ratio
            else:
                stop_loss = close + 1.5 * atr
                take_profit = close - 2.5 * atr

            # Confidence from agreement + trend strength
            confidence = 0.50 + (agreement - 0.80) * 2.5  # 0.80 → 0.50, 1.0 → 1.0
            confidence *= min(abs(assessment.trend) * 1.5, 1.0)  # Scale by trend strength

            return StrategySignal(
                direction=direction,
                confidence=Decimal(str(round(confidence, 4))),
                stop_loss=Decimal(str(round(stop_loss, 8))),
                take_profit=Decimal(str(round(take_profit, 8))),
                strategy_name="trend_following",
                conditions_met=conditions,
                reasoning=[f"Trend following ({self.bias}): {met_count}/{total} conditions met"],
            )

        return StrategySignal(direction="hold", confidence=Decimal("0.30"),
                             strategy_name="trend_following")
```

**MeanReversionStrategy:**

```python
class MeanReversionStrategy(StrategyInterface):
    def generate_signal(self, assessment, features, context):
        close = features.get("close", 0)
        bb_lower = features.get("bb_lower", 0)
        bb_upper = features.get("bb_upper", 0)
        bb_pct_b = features.get("bb_pct_b", 0.5)
        rsi = features.get("rsi", 50)
        atr = features.get("atr", 0)

        # Buy signal: price at lower Bollinger Band + RSI oversold
        if bb_pct_b < 0.10 and rsi < 35:
            stop_loss = close - 1.0 * atr
            take_profit = features.get("bb_middle", close + 1.5 * atr)
            confidence = 0.45 + (35 - rsi) / 70 + (0.10 - bb_pct_b) * 3

            return StrategySignal(
                direction="buy",
                confidence=Decimal(str(round(min(confidence, 0.85), 4))),
                stop_loss=Decimal(str(round(stop_loss, 8))),
                take_profit=Decimal(str(round(take_profit, 8))),
                strategy_name="mean_reversion",
                reasoning=[f"Mean reversion BUY: BB%B={bb_pct_b:.3f}, RSI={rsi:.1f}"],
            )

        # Sell signal: price at upper Bollinger Band + RSI overbought
        if bb_pct_b > 0.90 and rsi > 65:
            stop_loss = close + 1.0 * atr
            take_profit = features.get("bb_middle", close - 1.5 * atr)
            confidence = 0.45 + (rsi - 65) / 70 + (bb_pct_b - 0.90) * 3

            return StrategySignal(
                direction="sell",
                confidence=Decimal(str(round(min(confidence, 0.85), 4))),
                stop_loss=Decimal(str(round(stop_loss, 8))),
                take_profit=Decimal(str(round(take_profit, 8))),
                strategy_name="mean_reversion",
                reasoning=[f"Mean reversion SELL: BB%B={bb_pct_b:.3f}, RSI={rsi:.1f}"],
            )

        return StrategySignal(direction="hold", confidence=Decimal("0.30"),
                             strategy_name="mean_reversion")
```

**VolatilityStrategy:**

```python
class VolatilityStrategy(StrategyInterface):
    """Trades volatility breakouts with reduced sizing and wider stops."""

    def generate_signal(self, assessment, features, context):
        # Only trade extreme volatility breakouts with strong directional bias
        if abs(assessment.trend) < 0.5:
            return StrategySignal(direction="hold", confidence=Decimal("0.25"),
                                 strategy_name="volatility",
                                 reasoning=["Volatility regime but no directional bias"])

        direction = "buy" if assessment.trend > 0 else "sell"
        atr = features.get("atr", 0)
        close = features.get("close", 0)

        # Wider stops for volatile conditions (2x ATR instead of 1.5x)
        if direction == "buy":
            stop_loss = close - 2.0 * atr
            take_profit = close + 3.0 * atr  # 1.5 RR
        else:
            stop_loss = close + 2.0 * atr
            take_profit = close - 3.0 * atr

        # Reduced confidence to trigger smaller position sizing
        confidence = min(abs(assessment.trend) * 0.6, 0.65)

        return StrategySignal(
            direction=direction,
            confidence=Decimal(str(round(confidence, 4))),
            stop_loss=Decimal(str(round(stop_loss, 8))),
            take_profit=Decimal(str(round(take_profit, 8))),
            strategy_name="volatility_breakout",
            reasoning=[f"Volatility breakout {direction}: trend={assessment.trend:.2f}, ATR×2 stops"],
        )
```

**CrisisStrategy:**

```python
class CrisisStrategy(StrategyInterface):
    """Never trades during crisis conditions."""

    def generate_signal(self, assessment, features, context):
        return StrategySignal(
            direction="hold",
            confidence=Decimal("0.00"),
            strategy_name="crisis",
            reasoning=["Crisis regime detected — trading halted for safety"],
        )
```

### 20.5 Multi-Timeframe Confirmation

```python
class MultiTimeframeConfirmation:
    def __init__(self, timeframe_features: dict[str, dict]):
        """timeframe_features: {"M5": features, "M15": features, "H1": features}"""
        self.tf_features = timeframe_features

    def confirm(self, proposed_direction: str) -> ConfirmationResult:
        alignments = {}

        for tf, features in self.tf_features.items():
            scorer = TrendScorer()
            trend = scorer.score(features)

            if proposed_direction == "buy" and trend > 0.2:
                alignments[tf] = True
            elif proposed_direction == "sell" and trend < -0.2:
                alignments[tf] = True
            else:
                alignments[tf] = False

        ratio = sum(alignments.values()) / max(len(alignments), 1)

        return ConfirmationResult(
            confirmed=ratio >= 0.67,  # At least 2 of 3 timeframes agree
            alignment_ratio=ratio,
            per_timeframe=alignments,
        )
```

A signal is only emitted if at least two of three higher timeframes (M5, M15, H1) confirm the direction proposed by the strategy. This filters out noise-driven signals that lack higher-timeframe support.

### 20.6 Composite Confidence Scoring

The traditional system's confidence score replaces neural confidence with a transparent, multi-factor composite:

```python
class CompositeConfidenceScorer:
    def score(self, strategy_signal: StrategySignal, confirmation: ConfirmationResult,
              experience_confidence: float, assessment: Assessment) -> Decimal:

        # Factor 1: Strategy condition agreement (35%)
        strategy_conf = float(strategy_signal.confidence)

        # Factor 2: Multi-timeframe alignment (25%)
        mtf_conf = confirmation.alignment_ratio

        # Factor 3: Historical edge for this regime/session (20%)
        historical_edge = self._lookup_historical_edge(
            strategy_signal.strategy_name,
            assessment.regime,
            assessment.session,
        )

        # Factor 4: Experience similarity (10%)
        exp_conf = experience_confidence

        # Factor 5: Volatility adjustment (10%)
        # Lower confidence in high volatility
        vol_adj = max(0.3, 1.0 - assessment.volatility * 0.7)

        composite = (
            0.35 * strategy_conf +
            0.25 * mtf_conf +
            0.20 * historical_edge +
            0.10 * exp_conf +
            0.10 * vol_adj
        )

        return Decimal(str(round(clamp(composite, 0.0, 0.95), 4)))

    def _lookup_historical_edge(self, strategy, regime, session):
        """Query database for historical win rate of this strategy in this context."""
        # SELECT win_rate FROM strategy_daily_summary
        # WHERE strategy_name = strategy AND regime = regime
        # Returns rolling 30-day win rate, or 0.50 if insufficient data
        ...
```

Each factor is bounded and weighted. The composite is capped at 0.95 to prevent overconfidence. The weights can be tuned through walk-forward optimization.

### 20.7 Experience System Without Embeddings

The neural COPER system uses Sentence-BERT embeddings for semantic similarity. The traditional replacement uses hash-based matching and feature-distance scoring:

```python
class TraditionalExperienceBank:
    def retrieve_similar(self, context: TradeContext, features: dict, top_k=5):
        candidates = []

        for experience in self._experiences:
            # Exact context match bonus
            hash_match = 1.0 if experience.context_hash == context.hash else 0.0

            # Feature distance (Euclidean on normalized features)
            feature_vec = np.array([features[f"f{i}"] for i in range(60)])
            exp_vec = np.array(experience.feature_snapshot)
            distance = np.linalg.norm(feature_vec - exp_vec)
            similarity = 1.0 / (1.0 + distance)  # Convert distance to similarity [0, 1]

            # Regime match bonus
            regime_match = 0.3 if experience.context.regime == context.regime else 0.0

            # Session match bonus
            session_match = 0.2 if experience.context.session == context.session else 0.0

            score = (
                0.30 * similarity +
                0.25 * hash_match +
                0.20 * regime_match +
                0.15 * session_match +
                0.10 * float(experience.effectiveness)
            )

            candidates.append((experience, score))

        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:top_k]
```

This approach requires no NLP models, no embeddings, and no FAISS index. It is simpler, faster, and fully deterministic. The trade-off is lower semantic flexibility — the hash-based matching cannot infer that "breakout above resistance" and "price broke through ceiling" are similar concepts. However, since contexts are structured fields (regime, session, symbol), the exact matching captures the most important similarity dimensions.

### 20.8 Knowledge System Without ML Fusion

The traditional system uses the same KnowledgeRetriever but with pure keyword-based inference (Mode 3 of the cascade), without the ML fusion weights:

```python
class TraditionalKnowledgeEngine:
    def query(self, regime, symbol, session, features):
        retriever = self._get_retriever()
        query = f"{regime} {symbol} {session}"

        # Add feature-based qualifiers
        if features.get("rsi", 50) < 30:
            query += " oversold"
        elif features.get("rsi", 50) > 70:
            query += " overbought"
        if features.get("adx", 0) > 25:
            query += " trending"
        if features.get("bb_pct_b", 0.5) < 0.05:
            query += " lower band"
        elif features.get("bb_pct_b", 0.5) > 0.95:
            query += " upper band"

        entries = retriever.retrieve(query, top_k=5, symbol=symbol)
        return self._infer_direction(entries)
```

### 20.9 Position Sizing: Identical Implementation

Position sizing uses the exact same Kelly Criterion formula as the neural system. No changes needed:

```python
lots = (equity * risk_pct) / (sl_pips * pip_value_per_lot)
lots *= drawdown_scaling_factor
lots *= spiral_multiplier
lots = clamp(lots, min_lots, max_lots)
lots = quantize_to_step(lots, volume_step)
```

### 20.10 Risk Management: Identical Implementation

All risk management components are reused without modification:
- Kill switch (Redis-backed, fail-closed)
- Drawdown-based scaling (progressive lot reduction)
- Daily loss limits (auto-activation threshold)
- Spiral protection (consecutive loss tracking)
- Signal deduplication (in-memory hash map)
- Maximum position count limits
- Spread-based trade filtering
- Maturity gate with hysteresis

### 20.11 Complete Traditional Pipeline

Putting it all together, the traditional system's main loop:

```python
class TraditionalBrain:
    def process_bar(self, bar: dict) -> CascadeResult:
        # 1. Feature engineering (identical to neural version)
        features = self.feature_pipeline.compute(bar)

        # 2. Data quality validation
        if not self.sanity_checker.validate(bar):
            return CascadeResult(direction="hold", source_mode="quality_rejection")

        # 3. Regime classification (identical algorithm)
        regime = self.regime_classifier.classify(features)

        # 4. Market assessment (replaces CNN perception)
        assessment = self.market_assessment.assess(features, regime.regime, self.current_session)

        # 5. Strategy selection and signal generation (replaces MoE strategy)
        signal = self.regime_router.route(assessment, features, self.context_buffer)

        # 6. Multi-timeframe confirmation
        if signal.direction != "hold":
            confirmation = self.mtf_confirmer.confirm(signal.direction)
            if not confirmation.confirmed:
                signal = StrategySignal(direction="hold", confidence=Decimal("0.30"),
                                       reasoning=["MTF confirmation failed"])

        # 7. Experience lookup (replaces COPER with hash-based matching)
        exp_confidence = 0.0
        if signal.direction != "hold":
            similar = self.experience_bank.retrieve_similar(
                self.current_context, features, top_k=5)
            if similar:
                exp_confidence = float(similar[0][1])  # Best match score

        # 8. Composite confidence scoring (replaces neural confidence)
        if signal.direction != "hold":
            signal.confidence = self.confidence_scorer.score(
                signal, confirmation, exp_confidence, assessment)

        # 9. Confidence gating
        if signal.confidence < self.min_confidence_threshold:
            signal = StrategySignal(direction="hold", confidence=signal.confidence)

        # 10. Maturity gate (identical)
        gated = self.maturity_gate.apply(signal.direction, signal.confidence, self.maturity_state)

        # 11. Position sizing (identical Kelly Criterion)
        if gated.direction != "hold":
            lots = self.position_sizer.calculate(
                symbol=bar["symbol"],
                entry_price=Decimal(str(features["close"])),
                stop_loss=signal.stop_loss,
                equity=self.account_equity,
                drawdown_pct=self.current_drawdown,
                spiral_multiplier=self.pnl_tracker.spiral_multiplier,
            )
        else:
            lots = Decimal("0")

        return CascadeResult(
            direction=gated.direction,
            confidence=gated.confidence,
            source_mode=signal.strategy_name,
            reasoning=signal.reasoning,
            lots=lots,
        )
```

### 20.12 Performance Expectations

**Where the traditional system matches or exceeds the neural system:**

- **Trending markets:** Well-defined trend-following rules with ADX and EMA alignment perform comparably to neural trend detection. Clear entry/exit conditions are easy to optimize.
- **Extreme conditions:** The crisis strategy's unconditional HOLD matches the neural system's behavior in crisis regimes.
- **Execution speed:** Rule evaluation is microseconds vs. milliseconds for neural inference. Lower latency means more responsive signal generation.
- **Explainability:** Every decision traces to specific indicator values and rule conditions. No "black box" components.

**Where the traditional system may underperform:**

- **Regime transitions:** The neural system's Hopfield memory recognizes emerging patterns before explicit indicators confirm them. The traditional system's hysteresis-gated regime classifier is reactive, not predictive.
- **Novel market structures:** The neural system can generalize from similar past patterns. The traditional system only matches against explicitly coded rules and exact hash matches in the experience bank.
- **Feature interactions:** The neural system's MoE can discover non-linear interactions between 60 features. The traditional system's weighted scoring captures linear combinations and simple thresholds.

**Mitigation through optimization:**

- **Walk-forward optimization:** Run the strategy suite on 2+ years of historical data with rolling 3-month train, 1-month validate, 1-month test windows. Optimize scoring weights, indicator thresholds, and strategy parameters for each (regime, session, symbol) combination.
- **Ensemble rules:** Instead of a single trend score, run 5 variant strategies (each with slightly different parameters) and take the majority vote. This approximates the neural system's ensemble capacity.
- **Monthly recalibration:** Re-run walk-forward optimization monthly to adapt to changing market dynamics. Update the experience bank with recent trade outcomes.
- **Target metrics:** Sharpe > 1.0, maximum drawdown < 10%, win rate > 55%, profit factor > 1.3.

### 20.13 Backtesting Framework

The traditional system requires a rigorous backtesting framework for parameter optimization:

```python
class WalkForwardBacktester:
    def run(self, historical_data, strategy_config, n_windows=5):
        results = []

        for window in generate_walk_forward_windows(len(historical_data), n_windows):
            train_data = historical_data[window.train_start:window.train_end]
            val_data = historical_data[window.val_start:window.val_end]
            test_data = historical_data[window.test_start:window.test_end]

            # Optimize on training data
            best_params = self.optimize(train_data, strategy_config)

            # Validate: ensure optimization didn't overfit
            val_result = self.simulate(val_data, best_params)
            if val_result.sharpe < 0.5:
                continue  # Overfitted — skip this window

            # Test: out-of-sample performance
            test_result = self.simulate(test_data, best_params)
            results.append(test_result)

        return AggregatedResult(
            avg_sharpe=np.mean([r.sharpe for r in results]),
            avg_win_rate=np.mean([r.win_rate for r in results]),
            max_drawdown=max(r.max_drawdown for r in results),
            total_trades=sum(r.trade_count for r in results),
        )
```

**Progression to live trading:**

1. **In-sample optimization:** Walk-forward on historical data. Target: Sharpe > 1.0 across all windows.
2. **Out-of-sample validation:** Hold-out period not used in optimization. Target: performance within 80% of in-sample.
3. **Paper trading:** Run the system live but without real capital. Compare signals and theoretical P&L against the live market for 30+ days. Target: correlation > 0.9 with backtest results.
4. **Micro-live trading:** Trade with minimum lot sizes (0.01 lots). Validate execution quality, slippage, and real-world performance for 30+ days. Target: positive P&L.
5. **Full-live trading:** Gradually increase position sizing over 90 days, monitoring all risk metrics continuously.

This graduated deployment mirrors the maturity gate progression (DOUBT → LEARNING → CONVICTION → MATURE) but applied to the system itself rather than a neural model.

### 20.14 Diagnostic and Validation Tooling

The traditional system inherits GOLIATH's 14 diagnostic validators, which verify system correctness before and during deployment:

**brain_verify.py (115 rules):** The deployment gate validator checks:
- All configuration parameters are within acceptable ranges.
- All pipeline modules load successfully.
- Database connectivity is established and schema matches expectations.
- Redis connectivity is established and kill switch state is readable.
- gRPC channels to MT5 Bridge and ML Training are connectable.
- Feature engineering produces valid 60-dimensional vectors.
- Regime classification produces valid regime labels.
- Position sizing computes within expected bounds for known inputs.
- Signal deduplication correctly rejects duplicate signal IDs.
- Maturity gate blocks signals in DOUBT state.

Running `brain_verify.py --quick` performs a fast subset (30 seconds) suitable for CI pipelines. The full verification takes several minutes and includes integration tests with live service connections.

**headless_validator.py:** Runs the complete pipeline on historical data without GUI or gRPC, validating that every bar produces a valid CascadeResult. Used for regression testing after code changes.

**ml_debugger.py:** Visualizes model internals: gate weights, attribution values, belief states, loss curves. Useful for diagnosing why the model is generating unexpected signals.

**data_quality_checker.py:** Scans the database for data quality issues: gaps in bar sequences, anomalous price values, duplicate entries, missing timeframes.

Each validator produces a structured report with pass/fail status per check, enabling automated deployment gating: if brain_verify fails, the deployment pipeline blocks the release.

### 20.15 Operational Procedures

**Daily Operations:**
1. Morning check: Review overnight performance via Grafana dashboard.
2. Verify data pipeline health: tick rates, bar publication, no gaps.
3. Check kill switch history: any auto-activations during the night.
4. Review pending positions: ensure all positions have valid SL/TP.
5. Verify model maturity state: no unexpected downgrades.

**Weekly Operations:**
1. Database maintenance: run TimescaleDB compression on aged chunks.
2. Review strategy performance attribution: which strategies are profitable.
3. Check COT data update: verify latest CFTC positioning data was ingested.
4. Review audit log integrity: run hash chain verification.
5. Update knowledge base: add entries from the week's notable market events.

**Monthly Operations:**
1. Walk-forward re-optimization: recalibrate strategy parameters on the latest 6 months of data.
2. Security audit: verify certificate expiry dates, rotate Redis password, check RBAC roles.
3. Performance review: calculate monthly Sharpe, drawdown, win rate, profit factor.
4. Experience bank maintenance: decay stale experiences, boost validated winning patterns.
5. Infrastructure review: disk usage, database size, log retention, backup verification.

**Emergency Procedures:**
1. Kill switch activation: `goliath risk kill-switch activate "reason"` or automatic via auto_check.
2. Manual position close: `goliath mt5 close-all` closes all open positions.
3. Service restart: `goliath svc restart ai-brain` restarts a specific service.
4. Database recovery: restore from latest backup via `goliath maint restore`.
5. Rollback: revert to previous Docker image version via Compose tag change.

---

# APPENDIX

---

## Appendix A — Key Formulas Reference

### Position Sizing
```
lots = (equity × risk%) / (SL_distance_pips × pip_value_per_lot)
lots_adjusted = lots × drawdown_scale × spiral_multiplier
lots_final = quantize(clamp(lots_adjusted, vol_min, vol_max), vol_step)
```

### Drawdown
```
drawdown_pct = ((balance - equity) / balance) × 100
```

### Risk-Reward Ratio
```
RR = |take_profit - entry| / |entry - stop_loss|
```

### Conviction Index
```
conviction = 0.35 × min(win_rate, 1.0)
           + 0.30 × min(max(sharpe, 0) / 3.0, 1.0)
           + 0.20 × min(max(pf, 0) / 4.0, 1.0)
           + 0.15 × (1.0 - min(max(dd, 0), 1.0))
```

### Composite Confidence
```
confidence = 0.35 × strategy_agreement
           + 0.25 × mtf_alignment
           + 0.20 × historical_edge
           + 0.10 × experience_similarity
           + 0.10 × (1 - volatility × 0.7)
```

### Experience Scoring
```
score = 0.30 × feature_similarity
      + 0.25 × hash_match
      + 0.20 × regime_match
      + 0.15 × session_match
      + 0.10 × effectiveness
```

### EMA Update
```
EMA(t) = value(t) × α + EMA(t-1) × (1-α)
α = 2 / (period + 1)
```

### Z-Score
```
z = (value - mean) / std
```

### RSI
```
RS = avg_gain(14) / avg_loss(14)
RSI = 100 - (100 / (1 + RS))
```

### ATR
```
TR = max(High-Low, |High-Prev_Close|, |Low-Prev_Close|)
ATR(14) = Wilder_Smooth(TR, 14)
```

### Bollinger Bands
```
Middle = SMA(20)
Upper = SMA(20) + 2 × σ(20)
Lower = SMA(20) - 2 × σ(20)
%B = (Close - Lower) / (Upper - Lower)
```

---

## Appendix B — Configuration Reference

### Critical Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOLIATH_DB_PASSWORD` | Yes | — | PostgreSQL admin password |
| `GOLIATH_REDIS_PASSWORD` | Yes | — | Redis authentication password |
| `POLYGON_API_KEY` | Production | — | Polygon.io Forex data API key |
| `MT5_ACCOUNT` | Production | — | MetaTrader 5 account number |
| `MT5_PASSWORD` | Production | — | MetaTrader 5 account password |
| `MT5_SERVER` | Production | — | MT5 broker server address |
| `BRAIN_CONFIDENCE_THRESHOLD` | No | 0.65 | Minimum confidence for signal emission |
| `BRAIN_MAX_SIGNALS_PER_HOUR` | No | 10 | Signal rate limiter |
| `BRAIN_MAX_OPEN_POSITIONS` | No | 5 | Concurrent position limit |
| `BRAIN_MAX_DAILY_LOSS_PCT` | No | 2.0 | Daily loss kill switch trigger |
| `BRAIN_MAX_DRAWDOWN_PCT` | No | 5.0 | Drawdown kill switch trigger |
| `SIGNAL_MAX_AGE_SEC` | No | 30 | Maximum signal age for execution |
| `SIGNAL_DEDUP_WINDOW_SEC` | No | 60 | Signal deduplication window |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | No | 10 | API rate limit |
| `RATE_LIMIT_BURST_SIZE` | No | 5 | Rate limit burst capacity |
| `GOLIATH_TLS_ENABLED` | No | false | Enable TLS/mTLS |
| `GOLIATH_MOCK_INTERVAL_MS` | No | 500 | Dev mode tick generation rate |

### Port Assignments

| Service | gRPC | REST/Health | Metrics | Other |
|---------|------|-------------|---------|-------|
| Data Ingestion | — | 8081 | 9090 | 5555 (ZMQ) |
| AI Brain | 50054 | 8082 | 9092 | — |
| MT5 Bridge | 50055 | — | 9094 | — |
| ML Training | 50056 | — | 9095 | — |
| Dashboard | — | 8888 | — | — |
| PostgreSQL | — | — | — | 5432 |
| Redis | — | — | — | 6379 |
| Prometheus | — | — | — | 9091 |
| Grafana | — | 3000 | — | — |
| TensorBoard | — | 6006 | — | — |

---

## Appendix C — Glossary

| Term | Definition |
|------|-----------|
| **ADX** | Average Directional Index — measures trend strength (0-100) |
| **ATR** | Average True Range — measures market volatility in price units |
| **Cascade** | The 4-mode fallback pipeline: COPER → Hybrid → Knowledge → Conservative |
| **COPER** | Contextual Personalized Experience Retrieval — experience-based signal generation |
| **Drawdown** | Percentage decline from peak equity to current equity |
| **EMA** | Exponential Moving Average — weighted moving average with exponential decay |
| **FAISS** | Facebook AI Similarity Search — library for fast nearest-neighbor search |
| **gRPC** | Google Remote Procedure Call — binary protocol for inter-service communication |
| **Hysteresis** | Requiring multiple consecutive confirmations before changing state |
| **Kill Switch** | Emergency mechanism that halts all trading across the system |
| **LTC** | Liquid Time Constants — recurrent neural network with learnable time constants |
| **Maturity Gate** | Progressive trading enablement based on model/strategy proven performance |
| **MoE** | Mixture of Experts — neural architecture routing inputs through specialized networks |
| **mTLS** | Mutual TLS — both client and server authenticate each other with certificates |
| **OHLCV** | Open, High, Low, Close, Volume — standard candlestick data format |
| **PIP** | Percentage In Point — smallest standard price increment for an instrument |
| **Protobuf** | Protocol Buffers — language-neutral serialization format for structured data |
| **RAG** | Retrieval-Augmented Generation — combining retrieval with generative reasoning |
| **RAP Coach** | Recurrent-Attentional-Predictive Coach — the neural architecture name |
| **RBAC** | Role-Based Access Control — permission model based on user roles |
| **Regime** | Market behavioral mode: Trending, Ranging, Volatile, Crisis, Neutral |
| **RobustScaler** | Normalization using median and IQR instead of mean and standard deviation |
| **SAN** | Subject Alternative Name — TLS certificate field for multiple hostnames |
| **Slippage** | Difference between requested and actual fill price |
| **Spiral Protection** | Automatic size reduction after consecutive losses |
| **TimescaleDB** | PostgreSQL extension for time-series data with hypertables and compression |
| **ZMQ** | ZeroMQ — brokerless message passing library for distributed systems |

---

## Appendix D — Architecture Decision Records

### ADR-001: Decimal Strings for Financial Values in Protobuf

**Context:** Protobuf's `double` type uses IEEE 754, which cannot exactly represent many decimal fractions (0.1, 0.01, etc.). In financial calculations, these representation errors compound over thousands of operations.

**Decision:** All financial values in Protobuf messages are encoded as `string` fields containing exact decimal representations.

**Consequence:** Services must parse strings into language-native decimal types (Python `Decimal`, Go `decimal.Decimal`) on receipt. This adds parse overhead (~1μs per field) but guarantees exact arithmetic for prices, lots, and monetary values. The alternative — transmitting floats and rounding at boundaries — introduces non-deterministic rounding errors that are unacceptable in a trading system where a $0.01 discrepancy on 10,000 trades totals $100 of unaccounted P&L.

### ADR-002: Go for Data Ingestion, Python for Trading Logic

**Context:** The system needs both high-throughput I/O (WebSocket connections, ZMQ publishing, database batch writes) and rich library support (PyTorch, MetaTrader5, NumPy).

**Decision:** Use Go for the data ingestion service where concurrency and I/O throughput are critical. Use Python for all trading logic where library ecosystem and development velocity matter more than raw performance.

**Consequence:** The codebase is polyglot (Go + Python + TypeScript), requiring developers to be proficient in multiple languages. Protobuf contracts ensure type-safe communication despite language boundaries. The 15-second bar cycle of the AI Brain means Python's performance is not a bottleneck — even a 100ms pipeline latency is well within the 1000ms (M1 bar) processing budget.

### ADR-003: ZeroMQ over Redis PUB/SUB for Market Data

**Context:** Market data needs low-latency, reliable delivery from the data ingestion service to the AI Brain.

**Decision:** Use ZeroMQ PUB/SUB for market data distribution.

**Consequence:** ZMQ is brokerless — no dependency on Redis availability for the critical data path. If Redis fails, the AI Brain still receives market data. ZMQ's "drop slow subscribers" behavior is correct for real-time data: the Brain should always process the latest bar, not queue up stale ones. Redis PUB/SUB would buffer messages in Redis memory, potentially causing memory pressure during high-throughput periods. The trade-off: ZMQ adds a C library dependency and requires careful socket lifecycle management in Go.

### ADR-004: Fail-Closed Kill Switch Design

**Context:** The kill switch must prevent trading when its state cannot be determined (Redis unavailable, corrupt data, network partition).

**Decision:** Default state is `active = True` (trading blocked). Redis connectivity is required to confirm the kill switch is inactive.

**Consequence:** A Redis outage halts all trading. This is the correct behavior — the system prioritizes capital preservation over trading opportunity. A brief Redis blip (< 1 second) is masked by the local cache. A prolonged outage triggers alerts, and an operator must intervene. The alternative (fail-open, trading continues when Redis is down) risks unbounded losses if the kill switch was supposed to be active.

### ADR-005: Append-Only Audit Log with Hash Chain

**Context:** Regulatory and operational requirements demand tamper-evident trading records.

**Decision:** The audit log table uses database triggers to prevent UPDATE and DELETE operations. Each entry contains a SHA-256 hash of the previous entry, creating a cryptographic chain.

**Consequence:** The audit log can only grow, never shrink. Storage costs increase linearly with trading volume, but TimescaleDB compression on aged audit entries mitigates this. Hash chain verification runs in O(n) time and can be scheduled as a periodic integrity check. The trade-off: legitimate corrections cannot modify historical entries — instead, corrective entries are appended that reference the original, maintaining the chain's integrity while documenting the correction.

### ADR-006: 4-Mode Cascade with Graceful Degradation

**Context:** The neural network may be unavailable (not trained, checkpoint corrupted, inference timeout). The system must trade even without ML inference.

**Decision:** Implement a 4-mode cascade that degrades gracefully from ML-enhanced signal generation to pure rule-based strategies.

**Consequence:** The system never stops generating recommendations due to a single component failure. Mode 4 (Conservative) is guaranteed to always return a valid result. The trade-off: conservative mode's rules are intentionally restrictive (mostly HOLD), meaning the system loses trading opportunities when higher modes are unavailable. This is acceptable — a missed trade costs nothing, while a bad trade costs capital.

### ADR-007: TimescaleDB over InfluxDB or QuestDB

**Context:** The system needs time-series storage for market data with strong SQL support for complex analytical queries.

**Decision:** Use TimescaleDB (PostgreSQL extension) for all time-series and relational data.

**Consequence:** A single database serves both time-series (OHLCV bars, ticks) and relational (signals, executions, audit log, model registry) workloads. This eliminates the complexity of synchronizing data across multiple databases. TimescaleDB's continuous aggregates provide pre-computed materialized views for dashboard queries. The trade-off: TimescaleDB's write throughput for tick data (~50,000 ticks/second on commodity hardware) is lower than purpose-built time-series databases like QuestDB (~1M rows/second), but the system's tick volume (< 1,000/second across all symbols) is well within TimescaleDB's capacity.

---

## Appendix E — Data Flow Diagrams

### E.1 Signal Lifecycle

```
Exchange → WebSocket → Data Ingestion (Go)
    │
    ├─► TimescaleDB: ohlcv_bars, market_ticks (batch COPY)
    ├─► Redis: latest tick cache (TTL 5s)
    └─► ZMQ PUB: bar.SYMBOL.TIMEFRAME

AI Brain (Python) ◄── ZMQ SUB
    │
    ├─► Feature Engineering: 60-dim vector
    ├─► Regime Classification: 5-state FSM
    ├─► 4-Mode Cascade:
    │       Mode 1 (COPER): Experience + ML
    │       Mode 2 (Hybrid): ML + Knowledge
    │       Mode 3 (Knowledge): RAG retrieval
    │       Mode 4 (Conservative): Rule-based
    ├─► Maturity Gate: DOUBT → MATURE filter
    ├─► Confidence Gate: min threshold filter
    ├─► Position Sizing: Kelly + drawdown + spiral
    ├─► TimescaleDB: trading_signals (INSERT)
    └─► gRPC: TradingSignalService.SendSignal()

MT5 Bridge (Python) ◄── gRPC
    │
    ├─► Kill Switch Check: Redis goliath:kill_switch
    ├─► 9-Point Validation:
    │       Signal age, direction, lots, SL,
    │       position count, spread, margin,
    │       daily loss, drawdown
    ├─► Deduplication: in-memory hash map
    ├─► Lot Clamping: vol_min, vol_step, max_lot
    ├─► MT5 API: order_send(request)
    ├─► Slippage Computation: executed - requested
    ├─► TimescaleDB: trade_executions (INSERT)
    ├─► TimescaleDB: audit_log (INSERT with hash chain)
    └─► Prometheus: orders_submitted, orders_filled, execution_latency

MetaTrader 5 ◄── MT5 API
    │
    └─► Live Forex Market (fill, SL hit, TP hit)
```

### E.2 Monitoring Data Flow

```
Services (/metrics endpoints)
    │
    └─► Prometheus (scrape every 15s)
            │
            ├─► Alert Rules (evaluated every 15-30s)
            │       │
            │       └─► Alert Manager → Notifications
            │
            └─► Grafana (PromQL queries)
                    │
                    └─► 5 Dashboards (auto-provisioned)

Services (structlog JSON → stdout)
    │
    └─► Docker Log Driver
            │
            └─► Console / Dashboard Log Viewer

ML Training (TensorBoard events)
    │
    └─► TensorBoard (reload every 30s)

Kill Switch Events
    │
    └─► Redis PUB/SUB: goliath:alerts
            │
            ├─► Dashboard WebSocket → Browser Alert
            ├─► Console Alert Display
            └─► External Notification (Telegram, email)
```

---

## Appendix F — Advanced Financial and Trading Knowledge

This appendix provides the deeper financial domain knowledge that an engineering team needs to build a production-grade automated trading system. The concepts here go beyond basic market mechanics and cover the operational realities that determine whether a system survives live markets.

### F.1 Market Microstructure and Order Book Dynamics

Every price displayed on a trading terminal is the result of an order matching process. Understanding this process is essential for building a system that executes efficiently.

**The Order Book.** At any given moment, a market has a stack of limit buy orders (the bid side) and a stack of limit sell orders (the ask side). The highest bid and lowest ask form the "spread" — the gap where no orders exist. When a market order arrives, it consumes liquidity from the opposite side of the book. A market buy order fills against the lowest ask; a market sell fills against the highest bid. If the order is larger than the volume available at the best price, it "walks the book," filling at progressively worse prices. This is the mechanical origin of slippage.

**Liquidity Depth.** Retail Forex brokers typically show only the top-of-book price (best bid and best ask). The system has no visibility into how much volume sits at that price or what prices are available beyond it. This means a 10-lot market order might fill entirely at the quoted price, or it might fill 3 lots at the best price and 7 lots at a worse price. The system must always treat the quoted price as indicative, not guaranteed, and must measure actual fill prices against expected prices for every execution.

**Market Maker Behavior.** In retail Forex, brokers often act as market makers — they are the counterparty to every trade. This creates an inherent conflict of interest: the broker profits when the client loses. Practically, this means the system should expect occasional requotes during volatile periods, spread widening at news events, and execution delays during high-volume moments. The system should log every requote and measure execution quality over time to detect broker-side deterioration.

**Last-Look Execution.** Many Forex liquidity providers reserve the right to reject a trade within a short window (typically 50-200ms) after receiving the order — a practice called "last look." If the price has moved against the liquidity provider during that window, they reject the fill. From the system's perspective, this manifests as rejected orders that must be retried, potentially at a worse price. The MT5 Bridge must handle rejection codes gracefully and implement retry logic with price re-evaluation.

**Price Aggregation.** ECN brokers aggregate quotes from multiple liquidity providers and present the best composite bid/ask. The system may see a bid of 1.08500 from Bank A and an ask of 1.08502 from Bank B, creating a synthetic spread of 0.2 pips even though neither bank individually offers that spread. During stress events, liquidity providers may widen their quotes or withdraw entirely, causing the aggregated spread to blow out from 0.2 pips to 5+ pips within milliseconds.

### F.2 Spread Dynamics and Their Trading Implications

Spread is not a fixed cost — it is a dynamic variable that changes based on time of day, market volatility, liquidity conditions, and the specific broker's risk management. An automated system must model spread behavior to avoid systematic overpayment.

**Time-of-Day Patterns.** Spreads follow a predictable daily cycle tied to trading sessions:
- **Asian session (00:00-08:00 GMT):** Wider spreads on EUR/USD and GBP/USD (low liquidity), tighter on USD/JPY and AUD/USD.
- **London open (08:00 GMT):** Spreads tighten dramatically as European banks come online. Peak liquidity begins.
- **London-New York overlap (13:00-17:00 GMT):** Tightest spreads of the day. Maximum liquidity. Optimal execution window.
- **New York close (21:00-22:00 GMT):** Spreads begin widening. Rollover (swap) processing occurs.
- **Weekend gap:** No liquidity from Friday 22:00 GMT to Sunday 22:00 GMT. Positions held over the weekend face gap risk — prices may open significantly different from Friday's close.

For Gold (XAU/USD), spreads are typically 1.5-3.0 pips during peak hours and can widen to 5-15 pips during low-liquidity periods. For EUR/USD, typical spreads range from 0.1-0.3 pips during London-New York overlap to 1.0-2.0 pips during Asian session.

**Volatility-Driven Widening.** During high-impact news releases (Non-Farm Payrolls, FOMC rate decisions, ECB press conferences), spreads can widen by 10-50x their normal value for periods ranging from seconds to minutes. An automated system must either:
1. Halt trading during scheduled news events (using an economic calendar blackout system), or
2. Accept wider spreads and factor them into position sizing, or
3. Place limit orders in advance and accept the risk of non-fill.

GOLIATH uses approach (1) with a configurable blackout window (default: 15 minutes before and 15 minutes after high-impact events).

**Spread as a Filter.** The spread relative to the expected profit target is a critical viability metric. If the system's average profit target is 15 pips and the current spread is 5 pips, the spread consumes 33% of the expected profit. The system should reject trades where the spread exceeds a configurable percentage of the expected profit target. A common threshold is 10-15% — if spread/target > 0.15, skip the trade.

### F.3 Slippage: Measurement, Expectation, and Mitigation

Slippage is the difference between the price at which the system requests execution and the price at which the order actually fills. It is an unavoidable cost of live trading and must be quantified and managed.

**Positive vs. Negative Slippage.** Slippage can work in the system's favor (positive slippage: filled at a better price than requested) or against it (negative slippage: filled at a worse price). Over large sample sizes, slippage should be approximately symmetric in a fair market. If the system consistently observes negative slippage without corresponding positive slippage, it indicates broker-side execution manipulation.

**Expected Slippage by Instrument:**
- EUR/USD: 0.0-0.3 pips typical, 1.0+ pips during news
- GBP/USD: 0.1-0.5 pips typical, 2.0+ pips during news
- XAU/USD: 0.5-2.0 pips typical, 5.0+ pips during news
- USD/JPY: 0.0-0.3 pips typical, 1.0+ pips during news

**Slippage in Stop-Loss Orders.** Stop-loss orders are executed as market orders when the stop price is reached. During fast-moving markets, the actual fill price may be significantly worse than the stop price. A stop-loss at 1.08500 might fill at 1.08480 (2 pips slippage) during normal conditions, or at 1.08400 (10 pips slippage) during a flash crash. The system's risk calculations must account for this by adding a slippage buffer to the nominal stop-loss distance. A conservative approach: assume 1-2 pips of slippage on every stop-loss fill and size positions accordingly.

**Deviation Tolerance.** In MetaTrader 5, market orders include a `deviation` parameter specifying the maximum acceptable slippage in points. GOLIATH uses 20 points (2 pips for standard pairs). If the broker cannot fill within this tolerance, the order is rejected. Too tight a deviation leads to frequent rejections in volatile markets; too loose a deviation leads to poor fills. The optimal value depends on the instrument, session, and broker execution model.

### F.4 Swap Rates, Carry Trade, and Overnight Costs

Any position held past the daily rollover time (typically 21:00 or 22:00 GMT, depending on the broker) incurs a swap charge or credit. This is the interest rate differential between the two currencies in the pair, adjusted by the broker.

**Mechanics.** In Forex, when a trader buys EUR/USD, they are effectively borrowing USD (paying USD interest) and depositing EUR (earning EUR interest). If the EUR interest rate exceeds the USD interest rate, the trader receives a net credit. If the reverse, they pay. Brokers apply an additional markup on both sides, meaning the swap is almost always slightly negative for both long and short positions.

**Triple Wednesday (or Triple Swap Day).** Most brokers charge three days of swap on Wednesday night to account for the T+2 settlement cycle covering the weekend. This means holding a position from Wednesday to Thursday costs three times the normal daily swap. For Gold, where swap rates are typically $-3 to $-8 per lot per day, triple swap Wednesday means $-9 to $-24 per lot.

**Impact on Strategy Design.** For a system trading instruments with significant negative swap (like XAU/USD), holding periods matter:
- Intraday strategies (positions closed before rollover) pay zero swap.
- Swing strategies (holding 2-10 days) must subtract expected swap cost from profit targets.
- A strategy with a 15-pip average profit on XAU/USD and a $-5/lot/day swap cost that holds positions for an average of 3 days faces $15/lot in swap costs. At $10/pip for a standard lot, the 15-pip profit is $150, and the $15 swap cost reduces net profit by 10%.

The system must track swap rates per instrument and include them in expected profit calculations. This data is available from the MT5 API via `symbol_info().swap_long` and `symbol_info().swap_short`.

### F.5 Session Overlap Characteristics and Optimal Execution Windows

The 24-hour Forex market is not uniform. Each trading session has distinct personality traits driven by the institutions and economic regions active during that window. An automated system that ignores session context will systematically underperform.

**Sydney Session (22:00-07:00 GMT):**
- Lowest global volume. Thin liquidity on major pairs.
- AUD, NZD, and JPY pairs are most active.
- Price action tends to be range-bound. Breakouts are unreliable due to low follow-through.
- Strategy implication: Mean-reversion strategies perform better. Trend-following strategies generate false signals.

**Tokyo Session (00:00-09:00 GMT):**
- Japanese institutional activity drives JPY pairs.
- Gold often tests levels established during the prior New York session.
- Volatility is moderate. Defined ranges form that London session will test.
- Strategy implication: Range boundaries from Tokyo become key support/resistance for London.

**London Session (08:00-17:00 GMT):**
- Highest volume session. European banks, hedge funds, and central banks are active.
- Major pairs see their tightest spreads and deepest liquidity.
- Frequently "hunts" Tokyo session stops — price moves beyond Tokyo's range to trigger stop-loss clusters, then reverses.
- Strategy implication: The first 90 minutes of London (08:00-09:30 GMT) is the most volatile and trend-setting. Breakouts from this window have the highest follow-through probability.

**New York Session (13:00-22:00 GMT):**
- US economic data releases (typically 13:30 GMT) cause the largest single-event price moves.
- London-New York overlap (13:00-17:00 GMT) is the highest-volume period of the entire day.
- After 17:00 GMT, volume drops significantly as London closes and New York winds down.
- Strategy implication: Trend-following strategies are most effective during the overlap. After 17:00 GMT, the probability of trend continuation drops sharply.

**Weekend Gaps.** The market closes Friday at 22:00 GMT and reopens Sunday at 22:00 GMT. During this 48-hour window, geopolitical events, economic announcements, and natural disasters can shift fair value. When the market reopens, prices may "gap" — open at a level significantly different from Friday's close. Stop-loss orders do not protect against gaps; a stop at 1.0850 provides no benefit if the market opens at 1.0800. The system should either close positions before the weekend or reduce position sizes for weekend holds.

### F.6 Economic Calendar Integration and News Event Trading

Macroeconomic data releases are the single largest source of sudden, violent price movements in Forex. An automated system must have awareness of the economic calendar or risk being caught in moves that invalidate all technical analysis assumptions.

**High-Impact Events (trade-halting):**
- Non-Farm Payrolls (NFP) — First Friday of each month, 13:30 GMT. Moves of 50-100+ pips on EUR/USD within minutes.
- Federal Reserve Interest Rate Decision — 8 times per year, 19:00 GMT. Direction-setting for USD pairs.
- ECB Rate Decision — 8 times per year, 13:15 GMT. Euro-moving event with press conference at 13:45 GMT.
- CPI (Consumer Price Index) — Monthly, 13:30 GMT. Inflation data directly affects rate expectations.
- GDP releases — Quarterly. Growth data for major economies.

**Medium-Impact Events (spread widening, caution):**
- PMI (Purchasing Managers' Index) — Monthly. Leading indicator of economic health.
- Retail Sales — Monthly. Consumer spending data.
- Employment Change (non-US) — Monthly. UK, Australian, Canadian employment data.
- Trade Balance — Monthly. Import/export data affecting currency supply/demand.

**Low-Impact Events (monitor only):**
- Housing data, consumer confidence surveys, manufacturing output, business sentiment.

**Blackout Window Implementation.** The system maintains a schedule of high-impact events and enforces a trading blackout around each one. During a blackout:
1. No new positions are opened.
2. Existing positions may be closed if close to profit targets (optional, configurable).
3. Existing positions with adequate stop-losses are left in place.
4. The blackout lifts after a configurable delay (default: 15 minutes after the event).

The rationale is simple: during high-impact news, price behavior is driven by the data release versus market expectations, not by technical patterns. Technical analysis is temporarily invalid, and the system's edge disappears. It is more profitable to sit out than to participate in a coin flip with amplified spreads.

### F.7 Position Correlation and Portfolio-Level Risk

An automated system trading multiple instruments simultaneously must account for correlation between positions. Opening a long EUR/USD and a long GBP/USD is not two independent trades — it is approximately 1.7 correlated bets against the US Dollar.

**Correlation Matrix (approximate, varies over time):**

| | EUR/USD | GBP/USD | USD/JPY | AUD/USD | XAU/USD |
|---|---|---|---|---|---|
| EUR/USD | 1.00 | 0.85 | -0.60 | 0.70 | 0.40 |
| GBP/USD | 0.85 | 1.00 | -0.55 | 0.65 | 0.35 |
| USD/JPY | -0.60 | -0.55 | 1.00 | -0.50 | -0.30 |
| AUD/USD | 0.70 | 0.65 | -0.50 | 1.00 | 0.55 |
| XAU/USD | 0.40 | 0.35 | -0.30 | 0.55 | 1.00 |

**Practical implications:**
- A long EUR/USD and long GBP/USD with identical lot sizes creates approximately 1.85x the risk of a single position (not 2.0x, because correlation is <1.0, but far more than 1.0x).
- A long EUR/USD and short USD/JPY are partially correlated (both are USD-bearish) — combined risk is elevated.
- A long EUR/USD and long USD/JPY partially hedge each other.

**Portfolio Risk Calculation.** The system must compute aggregate portfolio risk, not just per-position risk. The formula for portfolio volatility with two correlated assets:

```
σ_portfolio = sqrt(w1²·σ1² + w2²·σ2² + 2·w1·w2·ρ·σ1·σ2)
```

Where `w` is position weight, `σ` is volatility, and `ρ` is correlation. For N assets, this generalizes to:

```
σ_portfolio = sqrt(W' · Σ · W)
```

Where `W` is the weight vector and `Σ` is the covariance matrix.

The system should enforce maximum aggregate exposure limits. If the maximum risk per trade is 1% of equity, and the system has 3 highly correlated positions open (combined effective exposure ~2.5%), it should refuse to open a 4th correlated position.

### F.8 Backtesting Pitfalls and Statistical Validity

The difference between a profitable backtest and a profitable live system is vast. Engineering teams must understand the biases that make backtests unrealistically optimistic.

**Look-Ahead Bias.** Using information that would not have been available at the time of the trading decision. Examples: using the daily close price to make a decision at 10:00 AM; using an indicator value that requires the current bar to close; normalizing features using the full dataset's statistics rather than only data available up to that point. The fix: strict temporal ordering. The system must process data in chronological order and never access future data.

**Survivorship Bias.** Testing only on instruments that currently exist, ignoring instruments that were delisted, merged, or became untradeable. In Forex, this is less severe than in equities (currencies rarely disappear), but it applies to exotic pairs that may lose liquidity or to CFD instruments that brokers add and remove.

**Overfitting.** Optimizing parameters to fit historical noise rather than genuine market patterns. A strategy with 47 tunable parameters can be made to show spectacular results on any historical dataset — and will fail catastrophically in live trading. The defense: walk-forward validation (train on in-sample, validate on out-of-sample, repeat on rolling windows), minimum parameter count, and insistence on logical justification for every parameter.

**Transaction Cost Neglect.** Backtests that assume zero spread, zero slippage, and zero swap will dramatically overstate profitability. A strategy that generates 5 pips of profit per trade with a 2-pip round-trip cost (spread + slippage) has a real profit of only 3 pips — a 40% reduction. The system must apply realistic transaction costs: historical spread data (not current spreads), expected slippage based on instrument and time-of-day, and swap costs for positions held past rollover.

**Fill Assumption Errors.** Backtests assume that any order can be filled at the quoted price, regardless of size. In reality, large orders move the market, partial fills occur, and liquidity may not exist at the desired level. For a retail system trading standard lots, this is less of a concern, but for a system scaled to 10+ lots per trade, it becomes significant.

**Minimum Trade Count.** A strategy that shows 80% win rate on 10 trades has no statistical significance. The minimum sample size for meaningful conclusions depends on the desired confidence level, but a practical guideline is:
- 30+ trades: Minimum for any preliminary assessment.
- 100+ trades: Required for basic parameter tuning.
- 500+ trades: Required for confidence in live deployment.
- 1000+ trades: Required for statistical robustness claims.

The confidence interval for win rate is: `win_rate ± 1.96 × sqrt(win_rate × (1 - win_rate) / N)`. A 60% win rate on 100 trades has a 95% CI of [50.4%, 69.6%] — the true win rate could be barely above 50%. On 1000 trades, the CI narrows to [56.9%, 63.1%].

### F.9 Execution Quality Metrics

A production trading system must continuously measure execution quality and detect degradation before it erodes profitability.

**Fill Rate.** Percentage of orders that are filled without rejection. Target: >99% during normal market hours. A declining fill rate indicates broker issues, excessive slippage tolerance settings, or liquidity deterioration.

**Average Slippage.** Mean slippage across all executed orders, measured in pips. Should be tracked separately for market orders, stop-loss fills, and take-profit fills. Target: <0.5 pips for EUR/USD market orders during London session.

**Execution Latency.** Time from order submission to fill confirmation. Measured at the system level (application sends order to MT5 API → receives fill response). Target: <500ms for market orders. Consistently high latency indicates network issues or broker-side throttling.

**Requote Rate.** Percentage of orders that receive a requote (broker offers a different price). Target: <2% during normal hours. High requote rates during non-volatile periods indicate poor broker execution.

**Asymmetric Slippage Ratio.** Ratio of average positive slippage to average negative slippage. In a fair market, this should be approximately 1.0. A ratio significantly below 1.0 (e.g., 0.3 — meaning negative slippage is 3x more common) indicates the broker is systematically providing worse fills. This is a strong signal to evaluate changing brokers.

All these metrics must be stored in the database, tracked over time, and surfaced in monitoring dashboards with alert thresholds.

### F.10 Broker Selection Criteria for Automated Systems

Not all brokers are suitable for automated trading. The engineering team should evaluate brokers against these criteria:

**Execution Model.** ECN/STP (Straight-Through Processing) brokers pass orders directly to liquidity providers. Market-maker brokers take the opposite side of every trade. ECN is strongly preferred for automated systems due to transparent pricing and no conflict of interest.

**API Support.** The broker must support MetaTrader 5 with the MT5 terminal's built-in API (Python, MQL5). Some brokers restrict automated trading or throttle API access. Verify that the broker explicitly allows Expert Advisors and automated trading via API.

**VPS Proximity.** Execution latency depends on the physical distance between the system and the broker's trading servers. Most brokers offer VPS hosting in the same datacenter as their servers. For a production system, co-locating the MT5 terminal near the broker's servers reduces latency from ~100ms (typical internet) to ~1-5ms (same datacenter).

**Regulatory Status.** Brokers regulated by tier-1 authorities (FCA in the UK, ASIC in Australia, CySEC in the EU) provide segregated client funds, negative balance protection, and dispute resolution. Unregulated or offshore brokers offer higher leverage but with significantly higher counterparty risk.

**Leverage and Margin Requirements.** Higher leverage allows smaller margin per position but increases the risk of margin call during adverse moves. GOLIATH's risk management limits effective leverage regardless of the broker's offering, so the broker's maximum leverage is less critical — but the margin call level (typically 50-100%) and stop-out level (typically 20-50%) must be known and factored into the position sizer's calculations.

---

*End of Document*
