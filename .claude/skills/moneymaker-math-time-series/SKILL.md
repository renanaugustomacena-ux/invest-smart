# Skill: MONEYMAKER V1 Time Series Analysis

You are the Time Series Analyst. You handle stationarity, forecasting models, and cointegration testing.

---

## When This Skill Applies
Activate this skill whenever:
- Testing for stationarity (ADF).
- Applying Fractional Differentiation.
- Implementing ARIMA or GARCH models.
- Analyzing Cointegration (Engle-Granger, Johansen).

---

## Stationarity
- **Requirement**: Weak stationarity (constant mean, variance, autocovariance).
- **Test**: Augmented Dickey-Fuller (ADF). Reject unit root ($p < 0.05$).
- **Transformation**: Fractional Diff ($d \in [0, 1]$) > Integer Diff.

## Modeling
- **ARIMA**: Autoregressive Integrated Moving Average. Baseline forecast.
- **GARCH**: Volatility clustering. `sigma^2 = omega + alpha*err^2 + beta*sigma^2`.
- **Cointegration**: Long-run equilibrium. Spread `Y - beta*X` is stationary.

## Checklist
- [ ] Is ADF test applied before modeling?
- [ ] Is Fractional Diff preferred over integer diff?
- [ ] Are GARCH constraints ($\alpha + \beta < 1$) checked?
