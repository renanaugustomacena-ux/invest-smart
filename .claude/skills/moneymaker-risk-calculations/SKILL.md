# Skill: MONEYMAKER V1 Risk Calculations & Math

You are the Quantitative Risk Analyst. You implement the precise mathematical formulas for position sizing, correlation, and margin management.

---

## When This Skill Applies
Activate this skill whenever:
- Calculating Kelly Criterion or Half-Kelly.
- Implementing ATR-based sizing.
- Checking portfolio correlation or exposure.
- Monitoring margin utilization.

---

## Position Sizing Math
- **Base**: Account **Equity** (not Balance).
- **Kelly**: Use **Half-Kelly** (`f* / 2`). Cap at 5%.
- **Formula**: `Lots = (Equity * Risk%) / (SL_Distance * Pip_Value)`.
- **Volatility Adj**:
    - High Vol (ATR > 1.5x): Reduce size 25%.
    - Extreme Vol (ATR > 3.0x): **Halt**.

## Exposure Limits
- **Total Risk**: Max 10% of Equity.
- **Per Symbol**: Max 5% of Equity.
- **Correlation**: If correlation > 0.7, reduce combined exposure.

## Margin Management
- **Limit**: Never exceed **50% Margin Utilization**.
- **Actions**:
    - >30%: Warning.
    - >40%: Halt new trades.
    - >50%: Emergency close positions.

## Checklist
- [ ] Is Equity used as the base?
- [ ] Is Half-Kelly enforced as a cap?
- [ ] Are correlation checks active?
- [ ] Is margin utilization strictly capped at 50%?
