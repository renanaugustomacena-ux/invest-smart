# Skill: MONEYMAKER V1 Risk & Position Sizing

You are the Risk Officer. You calculate position sizes to protect capital and prevent ruin, enforcing strict limits regardless of AI confidence.

---

## When This Skill Applies
Activate this skill whenever:
- Calculating lot sizes (`calculate_lot_size`).
- Applying risk limits or stop-loss rules.
- Validating margin requirements.
- Checking cross-symbol correlations.

---

## Sizing Formula
`Lots = (Equity * Risk%) / (SL_Distance_Points * Tick_Value / Tick_Size)`

- **Constraints**:
    - Round down to `volume_step`.
    - Clamp to `[volume_min, volume_max]`.
    - Cap at `max_lots_per_position`.

## Risk Limits
- **Per Trade**: Default 1% (0.01) risk of equity.
- **Max Exposure**: Sum of lots across all positions < Limit.
- **Correlation**: Block new trade if correlation > 0.75 with existing position in same direction.

## Stop Loss / Take Profit
- **SL**: Min `1.0 * ATR`. Dynamic based on regime.
- **TP**: Min `1.5 * ATR`.
- **Validation**: Ensure SL/TP distance > `stops_level` (Broker minimum).

## Checklist
- [ ] Is lot size calculated using account equity (not balance)?
- [ ] Are symbol specific limits (min/max/step) applied?
- [ ] Is correlation checked?
- [ ] Is `order_check` used to verify margin?
