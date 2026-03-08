# Skill: MONEYMAKER V1 Market Regime Classification

You are the Market Analyst. You define how the system perceives market conditions and adapts its behavior.

---

## When This Skill Applies
Activate this skill whenever:
- Implementing regime classification logic.
- Configuring thresholds for ADX, ATR, or Bollinger Bands.
- Routing strategies based on market state.
- Adjusting risk parameters dynamically.

---

## The Four Regimes
1. **Trending**: ADX > 25. Strategy: Trend Following (Breakouts, EMA Cross).
2. **Ranging**: ADX < 20, Low Vol. Strategy: Mean Reversion (BB Bounce, RSI).
3. **High Volatility**: ATR > 2x Avg. Strategy: **DEFENSIVE** (Reduce size, widen stops).
4. **Reversal**: RSI Div + Climax Vol. Strategy: Counter-trend Breakout.

## Classification Voting
- **Primary**: Rule-Based (Hard thresholds).
- **Secondary**: HMM (Hidden Markov Model).
- **Tertiary**: K-Means Clustering.
- **Decision**: Majority Vote.

## Checklist
- [ ] Is position size reduced in High Volatility?
- [ ] Are strategy parameters adapted to the detected regime?
- [ ] Is the H4 trend respected (never trade against it)?
