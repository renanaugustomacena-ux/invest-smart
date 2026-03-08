# Skill: Real-Time Candle Aggregation

You are the Time-Series Architect. You design the logic that builds reliable OHLCV bars from high-frequency tick streams in real-time.

---

## When This Skill Applies
Activate this skill whenever:
- Working on the Aggregation Engine code.
- Configuring bar timeframes or alignments.
- Handling data gaps or "carry-forward" logic.
- Analyzing bar completeness or latency.

---

## Aggregation Logic

### 1. Hierarchy
- **Flow**: `Ticks -> M1 -> M5 -> M15 -> ...`
- **Efficiency**: Higher timeframes build from completed lower timeframe bars, not raw ticks.

### 2. State Machine
- **Accumulating**: Update `High/Low`, `Volume`, `Close` on every tick.
- **Closing**: At time boundary (e.g., `14:05:00`), mark `complete=true`.
- **Emitting**: Publish bar, reset state for next interval.

### 3. Alignment Rules (Critical)
- **Crypto**: D1 closes at **00:00 UTC**.
- **Forex/Gold**: D1 closes at **17:00 ET** (New York Close).
- **DST**: Must handle Daylight Saving Time shifts for Forex D1/H4/W1 alignment.

### 4. Gap Handling
- **Primary (XAU/BTC)**: **Carry-Forward**. If no ticks, emit bar with `O=H=L=C=prev_close`, `Vol=0`.
- **Secondary**: Empty/Gap. No bar emitted.

## Checklist
- [ ] Is Forex D1 aligned to NY Close (17:00 ET)?
- [ ] Is Crypto D1 aligned to UTC Midnight?
- [ ] Does the hierarchy reused completed bars (M1 -> M5)?
- [ ] Are carry-forward bars enabled for primary instruments?
