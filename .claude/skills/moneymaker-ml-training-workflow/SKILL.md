# Skill: MONEYMAKER V1 ML Training Workflow

You are the Deep Learning Engineer. You manage the rigorous training pipeline to prevent overfitting and ensure generalization.

---

## When This Skill Applies
Activate this skill whenever:
- Designing the training loop or validation strategy.
- Defining loss functions or optimizers.
- Labeling data (Triple Barrier Method).
- Configuring GPU training (Mixed Precision).

---

## Labeling Strategy: Triple Barrier
- **Logic**: Dynamic barriers based on volatility (ATR).
- **Classes**:
    - **BUY (2)**: Hit Upper Barrier (TP) first.
    - **SELL (0)**: Hit Lower Barrier (SL) first.
    - **HOLD (1)**: Time limit reached without hitting barriers.
- **Symmetry**: Must evaluate both Long and Short scenarios.

## Validation: Walk-Forward (Purged K-Fold)
- **No Shuffling**: Never shuffle time-series data.
- **Purge Gap**: **5 bars** removed between Train and Val to prevent label leakage.
- **Embargo**: **3 bars** removed after Val before next Train fold.
- **Metric**: Sharpe Ratio > Accuracy.

## Training Best Practices
- **Precision**: **AMP (Automatic Mixed Precision)** with `GradScaler` for FP16 speed.
- **Optimizer**: **AdamW** (Weight Decay 0.05) + **Cosine Annealing** with Warm Restarts.
- **Regularization**: Dropout (0.35), Label Smoothing (0.1), Early Stopping.
- **Loss**: Weighted Cross-Entropy (inverse class frequency).

## Checklist
- [ ] Is shuffling disabled for time-series splits?
- [ ] Is the Purge Gap applied?
- [ ] Is Mixed Precision enabled?
- [ ] Are barriers dynamic (ATR-based)?
