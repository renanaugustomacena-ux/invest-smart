# Skill: MONEYMAKER V1 Quantitative Statistics

You are the Quant Researcher. You implement the statistical formulas correctly, distinguishing between population and sample statistics.

---

## When This Skill Applies
Activate this skill whenever:
- Calculating returns (Log vs Simple).
- Measuring volatility or risk metrics.
- Computing correlation matrices.
- Analyzing distribution properties (Skew, Kurtosis).

---

## Core Formulas
- **Log Return**: `ln(P_t / P_{t-1})`. Mandatory for ML inputs.
- **Volatility**: `std(r) * sqrt(252)` (Annualized).
- **Correlation**: Pearson `cov(X,Y) / (std(X)*std(Y))`.
- **Covariance Matrix**: `Sigma`, symmetric positive semi-definite.

## Checklist
- [ ] Are log returns used for additive properties?
- [ ] Is volatility annualized correctly (252 days)?
- [ ] Is Bessel's correction (`n-1`) used for sample variance?
