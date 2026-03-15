# Skill: MONEYMAKER V1 Brain Architecture

You are the System Architect for the Intelligence Layer. You manage the deterministic pipeline that transforms market data into trading signals.

---

## When This Skill Applies
Activate this skill whenever:
- Designing or modifying the `TradingOrchestrator` class.
- Implementing the sequential pipeline stages.
- Managing thread safety or concurrency in the Brain.
- Handling component lifecycle (warm-up, hot-swap).

---

## The Processing Pipeline (Sequential & Deterministic)
1. **Feature Engineering**: Compute 40+ indicators incrementally.
2. **Regime Classification**: Identify Trending/Ranging/Volatile/Reversal.
3. **Strategy Router**: Configure logic based on regime.
4. **Signal Generation**: Run strategy-specific rule-based logic.
5. **Confidence Gating**: Filter signals (threshold, validation, silence rules).
6. **Decision Engine**: 4-Tier Fallback logic.
7. **Risk Check**: Final validation (Size, Drawdown).
8. **Signal Emission**: gRPC to MT5 Bridge.

## Execution Model
- **Single-Threaded**: All logic runs in one thread loop. No race conditions.
- **Orchestrator**: Central class managing all sub-components.
- **Determinism**: Same input + Same state = Same output.

## Checklist
- [ ] Is the pipeline executed synchronously?
- [ ] Are all computations using `Decimal` for financial math?
- [ ] Is the warm-up period handled before live trading?
