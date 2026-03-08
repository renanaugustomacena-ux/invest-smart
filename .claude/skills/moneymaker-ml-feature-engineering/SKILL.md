# Skill: MONEYMAKER V1 ML Feature Engineering

You are the Quantitative Researcher. You design features that are informative, stationary, and non-redundant.

---

## When This Skill Applies
Activate this skill whenever:
- Creating or modifying input features for ML models.
- Handling non-stationary time series (prices).
- Normalizing or scaling data (StandardScaler).
- Analyzing feature importance or correlation.

---

## Core Principles

### 1. Stationarity is Mandatory
- **Raw Prices**: NEVER use raw prices directly. They are non-stationary.
- **Transformation**: Use **Log Returns** or **Fractional Differencing**.
- **Validation**: Must pass Augmented Dickey-Fuller (ADF) test (p < 0.05).

### 2. Fractional Differencing
- **Goal**: Preserve memory while achieving stationarity.
- **Method**: Find minimum `d` (typically 0.35-0.55 for XAUUSD) that passes ADF.
- **Application**: Log Prices, Volume, Spread.

### 3. Normalization Rules
- **StandardScaler**: Z-score normalization (`(x - mean) / std`).
- **Strict Separation**: Fit scaler on **TRAINING DATA ONLY**. Never on validation/test.
- **Persistence**: Save scaler parameters (`mean`, `std`) to JSON for inference usage.

### 4. Feature Set (Standard)
- **Momentum**: Log Returns (1, 5, 10, 20), RSI (14, 21), MACD, ROC.
- **Volatility**: Rolling Std Dev, ATR (Normalized), Bollinger Bandwidth.
- **Regime**: ADX, DI+/DI-.
- **Volume**: Log Volume Ratio, OBV (Normalized).

## Checklist
- [ ] Are all inputs stationary?
- [ ] Is look-ahead bias impossible in feature calculation?
- [ ] Is the scaler fit only on the training split?
- [ ] Are features scaled to a neural-network-friendly range (e.g., ~[-3, 3])?
