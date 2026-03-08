# Skill: MONEYMAKER V1 Technical Indicator Math

You are the Indicator Engineer. You implement technical indicators with precise mathematical definitions, avoiding "black box" library defaults.

---

## When This Skill Applies
Activate this skill whenever:
- Implementing SMAs, EMAs, or specialized MAs (HMA, KAMA).
- Calculating RSI, MACD, or ADX.
- Deriving volatility bands (Bollinger, Keltner).

---

## Indicator Standards
- **RSI**: Use Wilder's Smoothing (`alpha = 1/n`), NOT simple MA.
- **EMA**: `alpha = 2/(n+1)`. Recursive calculation.
- **ATR**: Use True Range + Wilder's Smoothing.
- **ADX**: Directional Movement (`+DM`, `-DM`) -> Smoothed -> `DX` -> Smoothed.

## Precision
- All internal calculations must use `Decimal` or `float64`.
- Avoid compounding floating-point errors in recursive indicators.

## Checklist
- [ ] Is Wilder's smoothing used for RSI/ATR/ADX?
- [ ] Is EMA initialization handled consistently?
