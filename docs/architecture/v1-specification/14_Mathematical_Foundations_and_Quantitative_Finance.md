# MONEYMAKER V1 — Mathematical Foundations, Quantitative Finance, and Economic Theory

> **Autore** | Renan Augusto Macena

---

## Table of Contents

1. [Introduction and Notation Conventions](#1-introduction-and-notation-conventions)
2. [Descriptive Statistics and Return Analysis](#2-descriptive-statistics-and-return-analysis)
3. [Probability Theory and Statistical Distributions](#3-probability-theory-and-statistical-distributions)
4. [Time Series Analysis](#4-time-series-analysis)
5. [Linear Algebra, Optimization, and Portfolio Theory](#5-linear-algebra-optimization-and-portfolio-theory)
6. [Risk Management Mathematics](#6-risk-management-mathematics)
7. [Technical Indicator Mathematics](#7-technical-indicator-mathematics)
8. Statistical Learning for Finance
9. Advanced Model Architectures
10. Optimization Methods for Trading
11. Natural Language Processing for Market Sentiment
12. Signal Processing and Filtering
13. Market Microstructure Mathematics
14. Stochastic Calculus and Derivatives Pricing
15. Information Theory and Entropy Methods
16. Graph Theory and Network Analysis
17. Bayesian Methods and Probabilistic Programming
18. Numerical Methods and Computational Finance
19. Appendices and Quick-Reference Tables

---

## 1. Introduction and Notation Conventions

### 1.1 Scope and Design Philosophy

This document consolidates ALL mathematical formulas referenced across the MONEYMAKER V1 ecosystem into a single, authoritative compendium. It serves as the canonical mathematical backbone for every quantitative operation — from indicator computation in the Data Ingestion Service (Document 04) through risk calculations (Document 09) and performance monitoring (Document 10).

**Format convention**: every formula entry follows the same structure:

1. **Display equation** in `$$...$$` block
2. **Where** block defining every variable
3. **Purpose** — one sentence describing what the formula computes and why
4. **V1_Bot** — mapping to the specific service, document, or module that implements or references this formula

No lengthy derivations. No extended prose. Formula-first, implementation-aware. Where a derivation is essential for correct implementation, it appears as a compact chain of numbered steps.

### 1.2 Notation Table

| Symbol | Meaning |
|--------|---------|
| $P_t$ | Price at time $t$ |
| $r_t$ | Log return at time $t$: $r_t = \ln(P_t / P_{t-1})$ |
| $R_t$ | Simple return: $R_t = (P_t - P_{t-1}) / P_{t-1}$ |
| $\sigma$ | Volatility (standard deviation of returns) |
| $\mu$ | Mean / drift parameter |
| $\mathbf{w}$ | Portfolio weight vector |
| $\Sigma$ | Covariance matrix |
| $\theta$ | Model parameters (generic) |
| $\mathcal{L}$ | Loss function |
| $\mathbb{E}[\cdot]$ | Expected value operator |
| $\mathcal{N}(\mu, \sigma^2)$ | Normal (Gaussian) distribution |
| $\nabla$ | Gradient operator |
| $\nabla_\theta$ | Gradient with respect to $\theta$ |
| $\odot$ | Hadamard (element-wise) product |
| $H, L, O, C, V$ | High, Low, Open, Close, Volume of a price bar |
| $n$ | Lookback period / window length |
| $\alpha$ | Smoothing factor or significance level (context-dependent) |
| $d$ | Fractional differentiation order |
| $f^*$ | Kelly optimal fraction |
| $\lambda$ | Decay factor or eigenvalue (context-dependent) |
| $\rho$ | Correlation coefficient |
| $\tau$ | Tolerance threshold or scaling constant |
| $\Delta$ | Difference / change operator |
| $B$ | Backshift operator: $BX_t = X_{t-1}$ |
| $I(\cdot)$ | Indicator function |
| $\text{diag}(\cdot)$ | Diagonal matrix constructor |

### 1.3 Cross-Reference Map

| Section | Primary V1_Bot Documents | Key Services |
|---------|--------------------------|--------------|
| 2. Descriptive Statistics | Doc 04 (Data Ingestion), Doc 10 (Monitoring) | `data-ingestion-service`, `analytics-engine` |
| 3. Probability & Distributions | Doc 09 (Risk) | `algo-engine`, `risk-manager` |
| 4. Time Series | Doc 04, Algo Engine | `feature-engineering`, `signal-generator` |
| 5. Linear Algebra & Portfolio | Algo Engine, Doc 09 | `portfolio-optimizer`, `risk-manager` |
| 6. Risk Management | Doc 09, Doc 08 (MT5 Bridge) | `risk-manager`, `position-sizer` |
| 7. Technical Indicators | Doc 04, Algo Engine | `indicator-engine`, `signal-generator` |
| 8-10. Statistical / Advanced Models | Doc 09 | `algo-engine` |
| 11. NLP & Sentiment | Doc 04, Algo Engine | `sentiment-analyzer`, `news-processor` |
| 12. Signal Processing | Doc 04, Algo Engine | `feature-engineering`, `noise-filter` |
| 13. Market Microstructure | Doc 04, Doc 08 | `order-flow-analyzer`, `execution-engine` |
| 14. Stochastic Calculus | Algo Engine, Doc 09 | `pricing-engine`, `risk-manager` |
| 15. Information Theory | Doc 09 | `feature-selector`, `signal-evaluator` |
| 16. Graph Theory | Doc 09 | `correlation-network`, `regime-detector` |
| 17. Bayesian Methods | Doc 09 | `bayesian-optimizer`, `parameter-estimator` |
| 18. Numerical Methods | Doc 09 | `solver-engine`, `monte-carlo-simulator` |
| 19. Appendices | All | All |

---

## 2. Descriptive Statistics and Return Analysis

### 2.1 Measures of Central Tendency

**Arithmetic Mean**

$$\mu = \frac{1}{n}\sum_{i=1}^{n} x_i$$

Where: $x_i$ = individual observation; $n$ = number of observations.

Purpose: Computes the simple average of a dataset, used as the baseline estimator for expected returns.

V1_Bot: `data-ingestion-service` rolling statistics module; Doc 04 feature engineering; Doc 10 performance dashboards.

---

**Geometric Mean**

$$\mu_g = \left(\prod_{i=1}^{n} (1 + R_i)\right)^{1/n} - 1$$

Where: $R_i$ = simple return for period $i$; $n$ = number of periods.

Purpose: Computes the compounded average growth rate, which correctly accounts for the multiplicative nature of returns over time.

V1_Bot: Doc 10 performance analytics — CAGR calculation; Doc 09 long-run return estimation.

---

**Weighted Mean**

$$\mu_w = \frac{\sum_{i=1}^{n} w_i x_i}{\sum_{i=1}^{n} w_i}$$

Where: $w_i$ = weight assigned to observation $i$; $x_i$ = observation value.

Purpose: Computes a mean where observations have unequal importance, used in volume-weighted or recency-weighted calculations.

V1_Bot: `indicator-engine` weighted moving averages; Doc 04 VWMA computation.

---

**Exponentially Weighted Moving Average (EWMA)**

$$\text{EWMA}_t = \alpha \cdot x_t + (1 - \alpha) \cdot \text{EWMA}_{t-1}$$

Where: $\alpha = 2/(n+1)$ = smoothing factor; $n$ = equivalent lookback window; $x_t$ = current observation.

Purpose: Provides a recursively computed mean that gives exponentially decaying weight to older observations, enabling rapid adaptation to recent data.

V1_Bot: `indicator-engine` EMA calculation; Doc 04 all EMA-based indicators; Doc 09 EWMA volatility.

---

**Volume-Weighted Average Price (VWAP)**

$$\text{VWAP} = \frac{\sum_{i=1}^{n} P_i \cdot V_i}{\sum_{i=1}^{n} V_i}$$

Where: $P_i$ = typical price $(H_i + L_i + C_i)/3$ for bar $i$; $V_i$ = volume for bar $i$.

Purpose: Computes the average price weighted by volume, serving as an institutional benchmark for execution quality and a dynamic support/resistance level.

V1_Bot: `indicator-engine` VWAP module; Doc 04 intraday analytics; Doc 08 execution quality assessment.

---

### 2.2 Measures of Dispersion

**Population Variance**

$$\sigma^2 = \frac{1}{n}\sum_{i=1}^{n}(x_i - \mu)^2$$

Where: $x_i$ = observation; $\mu$ = population mean; $n$ = population size.

Purpose: Measures the average squared deviation from the mean across the entire population.

V1_Bot: Doc 09 risk calculations when full population is known.

---

**Sample Variance**

$$s^2 = \frac{1}{n-1}\sum_{i=1}^{n}(x_i - \bar{x})^2$$

Where: $x_i$ = observation; $\bar{x}$ = sample mean; $n-1$ = Bessel's correction for unbiased estimation.

Purpose: Provides an unbiased estimate of population variance from a sample, which is the standard estimator used in all rolling-window calculations.

V1_Bot: `data-ingestion-service` rolling variance; Doc 04 Bollinger Band width; Doc 10 return variance tracking.

---

**Standard Deviation**

$$\sigma = \sqrt{\sigma^2} \quad \text{(population)}, \quad s = \sqrt{s^2} \quad \text{(sample)}$$

Where: $\sigma^2$ or $s^2$ = variance as defined above.

Purpose: Returns dispersion in the same units as the data, making it directly interpretable as volatility.

V1_Bot: All volatility-dependent modules across Docs 04, 07, 09.

---

**Semi-Variance (Downside)**

$$\sigma_{\text{down}}^2 = \frac{1}{n_d}\sum_{r_i < \tau}(r_i - \tau)^2$$

Where: $r_i$ = return observation; $\tau$ = target return (often $\mu$ or $0$); $n_d$ = count of returns below $\tau$.

Purpose: Measures dispersion of returns below a target threshold only, capturing downside risk that investors actually care about.

V1_Bot: Doc 09 Sortino ratio denominator; Doc 10 downside risk reporting.

---

**True Range**

$$TR_t = \max(H_t - L_t, \; |H_t - C_{t-1}|, \; |L_t - C_{t-1}|)$$

Where: $H_t, L_t$ = current bar high/low; $C_{t-1}$ = previous close.

Purpose: Captures the maximum price movement including overnight gaps, serving as the foundation for ATR and volatility-based position sizing.

V1_Bot: `indicator-engine` ATR module; Doc 04 volatility features; Doc 09 stop-loss distance.

---

**Coefficient of Variation**

$$CV = \frac{\sigma}{\mu}$$

Where: $\sigma$ = standard deviation; $\mu$ = mean (must be nonzero).

Purpose: Normalizes dispersion by the mean, enabling comparison of variability across assets with different price scales.

V1_Bot: Algo Engine feature normalization; Doc 10 cross-asset volatility comparison.

---

**Volatility Annualization**

$$\sigma_{\text{annual}} = \sigma_{\text{daily}} \times \sqrt{252}$$

Where: $\sigma_{\text{daily}}$ = daily return standard deviation; $252$ = trading days per year (convention).

Purpose: Scales daily volatility to an annual figure for standardized reporting and comparison across timeframes.

V1_Bot: Doc 09 all annualized risk metrics; Doc 10 Sharpe ratio computation.

---

### 2.3 Higher-Order Moments

**Skewness**

$$S = \frac{n}{(n-1)(n-2)} \sum_{i=1}^{n}\left(\frac{x_i - \bar{x}}{s}\right)^3$$

Where: $n$ = sample size; $\bar{x}$ = sample mean; $s$ = sample standard deviation.

Purpose: Quantifies asymmetry of the return distribution — negative skewness (typical in equities) indicates a longer left tail with more extreme losses than gains.

V1_Bot: Doc 09 tail risk assessment; feature for regime classification; Doc 10 return quality reporting.

---

**Excess Kurtosis**

$$K = \frac{n(n+1)}{(n-1)(n-2)(n-3)} \sum_{i=1}^{n}\left(\frac{x_i - \bar{x}}{s}\right)^4 - \frac{3(n-1)^2}{(n-2)(n-3)}$$

Where: $n$ = sample size; excess kurtosis subtracts 3 so that $\mathcal{N}(0,1)$ has $K=0$.

Purpose: Measures tail heaviness — positive excess kurtosis (leptokurtic, typical in financial returns) indicates more extreme events than a normal distribution predicts.

V1_Bot: Doc 09 VaR model selection (fat-tailed distributions); risk feature.

---

**Interquartile Range and Outlier Detection**

$$IQR = Q_3 - Q_1$$

$$\text{Outlier if } x < Q_1 - 1.5 \times IQR \quad \text{or} \quad x > Q_3 + 1.5 \times IQR$$

Where: $Q_1$ = 25th percentile; $Q_3$ = 75th percentile.

Purpose: Provides a robust, non-parametric method for identifying extreme observations that may indicate data errors or genuine market dislocations.

V1_Bot: Doc 04 data cleaning pipeline.

---

### 2.4 Return Types

**Simple Return**

$$R_t = \frac{P_t - P_{t-1}}{P_{t-1}}$$

Where: $P_t$ = price at time $t$.

Purpose: Measures the percentage price change over one period; directly interpretable and additive across assets in a portfolio.

V1_Bot: Doc 04 return computation; Doc 10 PnL tracking.

---

**Log (Continuously Compounded) Return**

$$r_t = \ln\left(\frac{P_t}{P_{t-1}}\right) = \ln(1 + R_t)$$

Where: $P_t$ = price at time $t$; $R_t$ = simple return.

Purpose: Provides time-additive returns ($r_{t_0 \to t_n} = \sum r_t$) and is approximately normally distributed, making it the preferred input for statistical models.

V1_Bot: Doc 04 feature engineering; signal generation.

---

**Cumulative Return**

$$R_{\text{cum}} = \prod_{i=1}^{n}(1 + R_i) - 1 = \exp\left(\sum_{i=1}^{n} r_i\right) - 1$$

Where: $R_i$ = simple return; $r_i$ = log return for period $i$.

Purpose: Computes total return over a multi-period horizon, demonstrating the aggregation property of log returns.

V1_Bot: Doc 10 equity curve construction; Doc 09 drawdown calculation.

---

**Compound Annual Growth Rate (CAGR)**

$$\text{CAGR} = \left(\frac{V_T}{V_0}\right)^{1/T} - 1$$

Where: $V_T$ = ending value; $V_0$ = beginning value; $T$ = number of years.

Purpose: Annualizes multi-period compounded returns into a single growth rate for standardized performance comparison.

V1_Bot: Doc 10 strategy performance reporting; Doc 09 Calmar ratio numerator.

---

### 2.5 Correlation and Covariance

**Covariance**

$$\text{Cov}(X, Y) = \frac{1}{n-1}\sum_{i=1}^{n}(x_i - \bar{x})(y_i - \bar{y})$$

Where: $x_i, y_i$ = paired observations; $\bar{x}, \bar{y}$ = sample means.

Purpose: Measures the linear co-movement between two variables; positive covariance indicates they tend to move together.

V1_Bot: Algo Engine portfolio optimization inputs; Doc 09 correlation-based risk.

---

**Pearson Correlation Coefficient**

$$\rho_{xy} = \frac{\text{Cov}(X, Y)}{\sigma_x \cdot \sigma_y}$$

Where: $\text{Cov}(X,Y)$ = covariance; $\sigma_x, \sigma_y$ = standard deviations.

Purpose: Normalizes covariance to $[-1, +1]$, providing a scale-independent measure of linear dependence.

V1_Bot: Algo Engine correlation matrix computation; Doc 09 diversification analysis.

---

**Spearman Rank Correlation**

$$\rho_s = 1 - \frac{6\sum d_i^2}{n(n^2 - 1)}$$

Where: $d_i = \text{rank}(x_i) - \text{rank}(y_i)$; $n$ = number of paired observations.

Purpose: Measures monotonic (not necessarily linear) dependence between two variables, robust to outliers and non-normal distributions.

V1_Bot: Algo Engine non-parametric dependence features.

---

**Covariance Matrix**

$$\Sigma = \begin{pmatrix} \sigma_1^2 & \sigma_{12} & \cdots & \sigma_{1k} \\ \sigma_{21} & \sigma_2^2 & \cdots & \sigma_{2k} \\ \vdots & \vdots & \ddots & \vdots \\ \sigma_{k1} & \sigma_{k2} & \cdots & \sigma_k^2 \end{pmatrix}$$

Where: $\sigma_i^2$ = variance of asset $i$; $\sigma_{ij} = \text{Cov}(R_i, R_j)$; $\Sigma$ is symmetric positive semi-definite.

Purpose: Encodes all pairwise variance-covariance relationships among $k$ assets; the fundamental input for portfolio optimization.

V1_Bot: Algo Engine`portfolio-optimizer`; Doc 09 multi-asset risk computation.

---

**Correlation Distance (for HRP)**

$$d_{ij} = \sqrt{2(1 - \rho_{ij})}$$

Where: $\rho_{ij}$ = Pearson correlation between assets $i$ and $j$.

Purpose: Converts correlations into a proper metric space distance for hierarchical clustering in the HRP algorithm.

V1_Bot: Algo EngineHRP clustering step; Doc 09 portfolio construction.

---

## 3. Probability Theory and Statistical Distributions

### 3.1 Foundational Probability

**Kolmogorov Axioms**

For a probability space $(\Omega, \mathcal{F}, P)$:

$$P(\Omega) = 1, \quad P(A) \geq 0, \quad P\left(\bigcup_{i=1}^{\infty} A_i\right) = \sum_{i=1}^{\infty} P(A_i) \text{ for disjoint } A_i$$

Where: $\Omega$ = sample space; $\mathcal{F}$ = sigma-algebra of events; $P$ = probability measure.

Purpose: Establishes the axiomatic foundation upon which all probability calculations in the system rest.

V1_Bot: Theoretical foundation for all probabilistic modules in Docs 06, 07, 09.

---

**Bayes' Theorem**

$$P(A|B) = \frac{P(B|A) \cdot P(A)}{P(B)}$$

Where: $P(A|B)$ = posterior probability; $P(B|A)$ = likelihood; $P(A)$ = prior; $P(B)$ = evidence (marginal likelihood).

Purpose: Updates prior beliefs about model parameters or market regimes when new evidence (data) arrives.

V1_Bot: Algo EngineBayesian regime detection; Doc 17 full Bayesian framework.

---

**Law of Total Probability**

$$P(B) = \sum_{i=1}^{n} P(B|A_i) \cdot P(A_i)$$

Where: $\{A_i\}$ = mutually exclusive, collectively exhaustive partition of $\Omega$.

Purpose: Decomposes the probability of an event across disjoint scenarios (e.g., market regimes), enabling regime-conditional risk calculation.

V1_Bot: Algo Engine regime-weighted signal generation; Doc 09 scenario-based VaR.

---

**Conditional Probability**

$$P(A|B) = \frac{P(A \cap B)}{P(B)}, \quad P(B) > 0$$

Where: $A \cap B$ = joint occurrence of events $A$ and $B$.

Purpose: Computes the probability of $A$ given that $B$ has occurred, fundamental to all conditional trading logic.

V1_Bot: Algo Engine conditional signal filtering; Doc 09 conditional risk assessment.

---

**Statistical Independence**

$$P(A \cap B) = P(A) \cdot P(B) \iff A \perp B$$

Where: $A \perp B$ denotes independence.

Purpose: Two events are independent if knowing one provides no information about the other; critical assumption in many diversification and sampling methods.

V1_Bot: Doc 09 diversification calculations.

---

### 3.2 Discrete Distributions

**Bernoulli Distribution**

$$P(X = k) = p^k(1-p)^{1-k}, \quad k \in \{0, 1\}$$

$$\mathbb{E}[X] = p, \quad \text{Var}(X) = p(1-p)$$

Where: $p$ = probability of success (e.g., winning trade); $k$ = outcome (1 = success, 0 = failure).

Purpose: Models single binary outcomes such as win/loss on a single trade.

V1_Bot: Doc 09 trade outcome modeling; signal accuracy assessment.

---

**Binomial Distribution**

$$P(X = k) = \binom{n}{k} p^k (1-p)^{n-k}$$

$$\mathbb{E}[X] = np, \quad \text{Var}(X) = np(1-p)$$

Where: $n$ = number of independent trials; $k$ = number of successes; $p$ = probability of success per trial.

Purpose: Models the number of winning trades in $n$ independent trades, used for streak analysis and win-rate confidence intervals.

V1_Bot: Doc 09 risk-of-ruin calculation; Doc 10 win-rate statistical testing.

---

**Poisson Distribution**

$$P(X = k) = \frac{\lambda^k e^{-\lambda}}{k!}$$

$$\mathbb{E}[X] = \lambda, \quad \text{Var}(X) = \lambda$$

Where: $\lambda$ = expected number of events per interval; $k$ = observed count.

Purpose: Models the count of rare events in a fixed interval (e.g., number of extreme moves per day, order arrivals).

V1_Bot: Doc 13 order arrival modeling; Doc 09 jump-event frequency estimation.

---

**Geometric Distribution**

$$P(X = k) = (1-p)^{k-1} p$$

$$\mathbb{E}[X] = 1/p, \quad \text{Var}(X) = (1-p)/p^2$$

Where: $p$ = probability of success; $k$ = trial number of first success.

Purpose: Models the number of trades until the first win, used in consecutive-loss analysis and drawdown duration estimation.

V1_Bot: Doc 09 maximum consecutive loss estimation; Doc 10 recovery period analysis.

---

### 3.3 Continuous Distributions

**Normal (Gaussian) Distribution**

$$f(x) = \frac{1}{\sigma\sqrt{2\pi}} \exp\left(-\frac{(x - \mu)^2}{2\sigma^2}\right)$$

$$\mathbb{E}[X] = \mu, \quad \text{Var}(X) = \sigma^2$$

Where: $\mu$ = mean; $\sigma$ = standard deviation; the CDF has no closed form but is tabulated via $\Phi(z)$.

Purpose: The foundational continuous distribution; while financial returns are not perfectly normal, it serves as the first-order approximation and the basis for parametric VaR.

V1_Bot: Doc 09 parametric VaR; z-score normalization.

---

**Standard Normal and Z-Scores**

$$z = \frac{x - \mu}{\sigma}, \quad z \sim \mathcal{N}(0, 1)$$

**68-95-99.7 Rule**: $P(\mu - k\sigma \leq X \leq \mu + k\sigma)$ for $k = 1, 2, 3$ equals $68.27\%, 95.45\%, 99.73\%$.

Where: $z$ = standardized score; $\mu, \sigma$ = distribution parameters.

Purpose: Transforms any normal variable to a standard scale for probability lookup and cross-variable comparison.

V1_Bot: Algo EngineBollinger Band z-score signals; Doc 09 VaR percentile mapping.

---

**Log-Normal Distribution**

$$\text{If } \ln(X) \sim \mathcal{N}(\mu, \sigma^2), \text{ then } f(x) = \frac{1}{x\sigma\sqrt{2\pi}} \exp\left(-\frac{(\ln x - \mu)^2}{2\sigma^2}\right)$$

$$\mathbb{E}[X] = e^{\mu + \sigma^2/2}, \quad \text{Var}(X) = (e^{\sigma^2} - 1)e^{2\mu + \sigma^2}$$

Where: $x > 0$; $\mu, \sigma$ = parameters of the underlying normal distribution of $\ln(X)$.

Purpose: Models price levels (which are strictly positive) when log returns are normally distributed; the theoretical basis for geometric Brownian motion.

V1_Bot: Doc 14 GBM pricing model; Doc 09 Monte Carlo price simulation.

---

**Student's t-Distribution**

$$f(x) = \frac{\Gamma\left(\frac{\nu+1}{2}\right)}{\sqrt{\nu\pi}\;\Gamma\left(\frac{\nu}{2}\right)} \left(1 + \frac{x^2}{\nu}\right)^{-(\nu+1)/2}$$

Where: $\nu$ = degrees of freedom; $\Gamma(\cdot)$ = gamma function; as $\nu \to \infty$, $t \to \mathcal{N}(0,1)$.

Purpose: Provides heavier tails than the normal distribution, better modeling the empirical distribution of financial returns where extreme events are more frequent than Gaussian predictions.

V1_Bot: Doc 09 t-distributed VaR; robust signal thresholds.

---

**Exponential Distribution**

$$f(x) = \lambda e^{-\lambda x}, \quad x \geq 0$$

$$\mathbb{E}[X] = 1/\lambda, \quad \text{Var}(X) = 1/\lambda^2$$

Where: $\lambda$ = rate parameter (events per unit time).

Purpose: Models inter-arrival times of events (time between trades, time between regime changes), characterized by the memoryless property.

V1_Bot: Doc 13 inter-trade arrival modeling; regime duration estimation.

---

### 3.4 Financial Probability Concepts

**Win Rate and Expectancy**

$$E = (WR \times AW) - ((1 - WR) \times AL)$$

Where: $WR$ = win rate (fraction of winning trades); $AW$ = average win amount; $AL$ = average loss amount.

Purpose: Computes the expected dollar gain per trade; positive expectancy is a necessary condition for a viable trading strategy.

V1_Bot: Doc 09 strategy validation gate; Doc 10 real-time expectancy tracking.

---

**Risk of Ruin**

$$R_{\text{ruin}} = \left(\frac{1 - \text{edge}}{\text{1 + edge}}\right)^{\text{units}}$$

$$\text{edge} = \frac{(1 + b) \cdot p - 1}{b}$$

Where: $b$ = win/loss ratio ($AW/AL$); $p$ = win probability; $\text{units}$ = number of betting units in bankroll.

Purpose: Estimates the probability of total capital depletion given a fixed bet size and edge, motivating proper position sizing.

V1_Bot: Doc 09 risk-of-ruin threshold check; Doc 10 survivability dashboard.

---

**Kelly Criterion (Preview)**

$$f^* = \frac{p \cdot b - q}{b}$$

Where: $p$ = win probability; $q = 1 - p$; $b$ = ratio of average win to average loss; $f^*$ = optimal fraction of capital to risk.

Purpose: Determines the growth-rate-maximizing bet size (full derivation in Section 6).

V1_Bot: Doc 09 `position-sizer` Kelly module.

---

### 3.5 Hypothesis Testing

**Augmented Dickey-Fuller (ADF) Test**

$$\Delta X_t = \alpha + \beta t + \gamma X_{t-1} + \sum_{i=1}^{p} \delta_i \Delta X_{t-i} + \epsilon_t$$

Where: $\Delta X_t = X_t - X_{t-1}$; $\alpha$ = constant; $\beta t$ = deterministic trend; $\gamma$ = unit root coefficient (test $H_0: \gamma = 0$); $\delta_i$ = augmented lag coefficients; $\epsilon_t$ = white noise.

Purpose: Tests for unit roots (non-stationarity) in time series; rejection ($p < 0.05$) implies stationarity, a prerequisite for many statistical models.

V1_Bot: Doc 04 fractional differentiation $d$-optimization; cointegration pre-test.

---

**Ljung-Box Test**

$$Q_{LB} = n(n+2) \sum_{k=1}^{m} \frac{\hat{\rho}_k^2}{n - k}$$

Where: $n$ = sample size; $m$ = number of lags tested; $\hat{\rho}_k$ = sample autocorrelation at lag $k$; $Q_{LB} \sim \chi^2(m)$ under $H_0$ (no autocorrelation).

Purpose: Tests whether a set of autocorrelations are jointly zero, used to validate that model residuals are white noise.

V1_Bot: Algo Engine residual whiteness check post-ARIMA.

---

**Jarque-Bera Test**

$$JB = \frac{n}{6}\left(S^2 + \frac{K^2}{4}\right)$$

Where: $n$ = sample size; $S$ = skewness; $K$ = excess kurtosis; $JB \sim \chi^2(2)$ under $H_0$ (normality).

Purpose: Tests whether data follow a normal distribution; rejection motivates use of fat-tailed distributions (t, stable) for risk models.

V1_Bot: Doc 09 VaR model selection.

---

**t-Test for Return Significance**

$$t = \frac{\bar{r} - 0}{s / \sqrt{n}}$$

Where: $\bar{r}$ = sample mean return; $s$ = sample standard deviation; $n$ = number of observations; $t \sim t(n-1)$ under $H_0: \mu = 0$.

Purpose: Tests whether average strategy returns are statistically significantly different from zero, guarding against confusing noise for edge.

V1_Bot: Doc 10 strategy significance reporting.

---

### 3.6 Maximum Likelihood Estimation

**MLE Objective**

$$\hat{\theta} = \arg\max_\theta \sum_{i=1}^{n} \ln f(x_i | \theta)$$

Where: $\hat{\theta}$ = maximum likelihood estimate; $f(x_i|\theta)$ = probability density of observation $x_i$ given parameters $\theta$.

Purpose: Finds the parameter values that make the observed data most probable; the primary estimation method for GARCH, ARIMA, and distribution fitting.

V1_Bot: Algo EngineGARCH fitting.

---

**Akaike Information Criterion (AIC)**

$$AIC = 2k - 2\ln(\hat{L})$$

Where: $k$ = number of estimated parameters; $\hat{L}$ = maximized likelihood value.

Purpose: Balances model fit against complexity; lower AIC indicates a better model, penalizing overfitting with fewer parameters.

V1_Bot: Algo Engine model comparison.

---

**Bayesian Information Criterion (BIC)**

$$BIC = k\ln(n) - 2\ln(\hat{L})$$

Where: $k$ = number of parameters; $n$ = number of observations; $\hat{L}$ = maximized likelihood.

Purpose: Similar to AIC but with a stronger penalty for model complexity (scales with $\ln(n)$), preferred for large datasets.

V1_Bot: Algo Engine parsimonious model preference.

---

## 4. Time Series Analysis

### 4.1 Stationarity

**Weak (Covariance) Stationarity Conditions**

A time series $\{X_t\}$ is weakly stationary if and only if:

$$\mathbb{E}[X_t] = \mu \quad \forall t$$

$$\text{Var}(X_t) = \sigma^2 < \infty \quad \forall t$$

$$\text{Cov}(X_t, X_{t+k}) = \gamma_k \quad \text{depends only on lag } k, \text{ not on } t$$

Where: $\mu$ = constant mean; $\sigma^2$ = constant finite variance; $\gamma_k$ = autocovariance function.

Purpose: Stationarity is required for the statistical properties estimated from historical data to be valid for future predictions; violation necessitates differencing or transformation.

V1_Bot: Doc 04 feature stationarity enforcement; model input validation.

---

**Unit Root / Random Walk**

$$P_t = P_{t-1} + \epsilon_t, \quad \epsilon_t \sim \mathcal{N}(0, \sigma^2)$$

Where: $P_t$ = price at time $t$; $\epsilon_t$ = white noise innovation.

Purpose: Defines a pure random walk (non-stationary, $I(1)$) where price changes are unpredictable; first differencing yields stationary returns.

V1_Bot: Doc 04 rationale for return-based features; baseline null hypothesis for predictability.

---

**Order of Integration**

$$X_t \sim I(d) \iff (1 - B)^d X_t \text{ is stationary}$$

Where: $B$ = backshift operator; $d$ = minimum integer differencing order to achieve stationarity; most prices are $I(1)$, returns are $I(0)$.

Purpose: Classifies time series by how many times they must be differenced to become stationary, determining the $d$ parameter in ARIMA and motivating fractional differentiation.

V1_Bot: Doc 04 fractional $d$ optimization;ARIMA $d$ selection.

---

### 4.2 Autocorrelation

**Autocovariance Function**

$$\gamma_k = \text{Cov}(X_t, X_{t-k}) = \mathbb{E}[(X_t - \mu)(X_{t-k} - \mu)]$$

Where: $k$ = lag; $\mu$ = mean of stationary series.

Purpose: Measures the linear dependence between a time series and its own lagged values at lag $k$.

V1_Bot: Algo Engine feature engineering for lag selection.

---

**Autocorrelation Function (ACF)**

$$\rho_k = \frac{\gamma_k}{\gamma_0}$$

Where: $\gamma_k$ = autocovariance at lag $k$; $\gamma_0 = \text{Var}(X_t)$.

Purpose: Normalizes autocovariance to $[-1, 1]$, used in ARIMA model identification (MA order) and residual diagnostics.

V1_Bot: Algo Engine signal autocorrelation analysis.

---

**Partial Autocorrelation Function (PACF)**

$$\phi_{kk} = \text{Corr}(X_t, X_{t-k} \mid X_{t-1}, X_{t-2}, \ldots, X_{t-k+1})$$

Where: $\phi_{kk}$ = correlation between $X_t$ and $X_{t-k}$ after removing the linear effect of intervening lags.

Purpose: Isolates the direct effect of lag $k$ (removing indirect effects through intermediate lags), used to identify AR order in ARIMA models.

V1_Bot: Algo Engine direct lag dependency analysis.

---

**ACF/PACF Confidence Bands**

$$\text{95\% CI} = \pm \frac{1.96}{\sqrt{n}}$$

Where: $n$ = sample size; values outside these bands are statistically significant at the 5% level.

Purpose: Determines which autocorrelation lags are statistically significant for model specification.

V1_Bot: Automated model order selection in the Algo Engine.

---

### 4.3 Fractional Differentiation

**Fractional Differencing via Backshift Operator**

$$(1 - B)^d = \sum_{k=0}^{\infty} \binom{d}{k} (-1)^k B^k$$

Where: $d \in \mathbb{R}$ (typically $d \in [0, 1]$); $B$ = backshift operator ($B^k X_t = X_{t-k}$); $\binom{d}{k} = \frac{d!}{k!(d-k)!}$ via the gamma function for non-integer $d$.

Purpose: Generalizes integer differencing to fractional orders, allowing a continuous trade-off between stationarity and memory preservation.

V1_Bot: Doc 04 `feature-engineering` fractional differentiation module — core transformation.

---

**Recursive Weight Computation**

$$\omega_0 = 1, \quad \omega_k = -\omega_{k-1} \cdot \frac{d - k + 1}{k}$$

Where: $\omega_k$ = weight applied to $X_{t-k}$; the fractionally differenced series is $\tilde{X}_t = \sum_{k=0}^{n} \omega_k X_{t-k}$.

Purpose: Provides an efficient recursive formula for computing the binomial series weights without explicit binomial coefficient calculation.

V1_Bot: Doc 04 weight computation in frac-diff pipeline.

---

**Fixed-Window Truncation**

$$l^* = \min\{l : |\omega_l| < \tau\}$$

$$\tilde{X}_t = \sum_{k=0}^{l^*} \omega_k X_{t-k}$$

Where: $\tau$ = weight truncation threshold (e.g., $10^{-5}$); $l^*$ = cutoff lag.

Purpose: Truncates the infinite weight series at the point where weights become negligible, making the computation finite and bounding memory usage.

V1_Bot: Doc 04 fixed-width frac-diff window implementation.

---

**Optimal $d$ Selection**

$$d^* = \min\{d \in [0, 1] : \text{ADF p-value of } \tilde{X}_t(d) < 0.05\}$$

Where: $\tilde{X}_t(d)$ = fractionally differenced series at order $d$; ADF = Augmented Dickey-Fuller test.

Purpose: Finds the minimum differencing order that achieves stationarity, thereby preserving maximum memory (predictive information) from the original series.

V1_Bot: Doc 04 automated $d$-search grid; input feature stationarity pipeline.

---

**Stationarity-Memory Dilemma**

| $d$ value | Stationarity | Memory |
|-----------|--------------|--------|
| $d = 0$ | Non-stationary (raw prices) | Full memory |
| $d = d^*$ | Stationary | Maximum preserved |
| $d = 1$ | Stationary (returns) | No memory |

Purpose: Illustrates why fractional differentiation ($0 < d < 1$) is superior to the binary choice of prices ($d=0$) or returns ($d=1$) for ML features.

V1_Bot: Doc 04 Section 4.3 design rationale; feature quality justification.

---

### 4.4 ARIMA Models

**AR(p) — Autoregressive**

$$X_t = c + \sum_{i=1}^{p} \phi_i X_{t-i} + \epsilon_t$$

Where: $c$ = constant; $\phi_i$ = AR coefficients; $p$ = order; $\epsilon_t \sim WN(0, \sigma^2)$.

Purpose: Models the current value as a linear combination of $p$ past values plus noise; captures mean-reverting dynamics.

V1_Bot: Algo Engine mean-reversion signal for pairs trading.

---

**MA(q) — Moving Average**

$$X_t = c + \epsilon_t + \sum_{j=1}^{q} \theta_j \epsilon_{t-j}$$

Where: $c$ = constant; $\theta_j$ = MA coefficients; $q$ = order; $\epsilon_t \sim WN(0, \sigma^2)$.

Purpose: Models the current value as a linear combination of $q$ past shocks; captures short-lived effects of news or events.

V1_Bot: Algo Engine forecast error modeling.

---

**ARIMA(p,d,q)**

$$(1 - \sum_{i=1}^{p}\phi_i B^i)(1 - B)^d X_t = c + (1 + \sum_{j=1}^{q}\theta_j B^j)\epsilon_t$$

Where: $p$ = AR order; $d$ = differencing order; $q$ = MA order; $B$ = backshift operator.

Purpose: Combines autoregression, differencing, and moving average into a unified model for non-stationary time series forecasting.

V1_Bot: Algo Engine baseline statistical forecast.

---

**SARIMA(p,d,q)(P,D,Q)$_s$**

$$(1 - \sum\phi_i B^i)(1 - \sum\Phi_j B^{js})(1-B)^d(1-B^s)^D X_t = (1 + \sum\theta_i B^i)(1 + \sum\Theta_j B^{js})\epsilon_t$$

Where: uppercase $\Phi, \Theta, P, D, Q$ = seasonal components; $s$ = seasonal period (e.g., $s=5$ for weekly, $s=252$ for yearly in daily data).

Purpose: Extends ARIMA with seasonal AR, differencing, and MA components to model periodic patterns in financial data.

V1_Bot: Algo Engine seasonal pattern detection.

---

**Box-Jenkins Methodology**

1. **Identify**: use ACF/PACF plots to determine $p, d, q$
2. **Estimate**: fit parameters via MLE
3. **Diagnose**: check residuals (Ljung-Box, normality)
4. **Forecast**: generate predictions with confidence intervals

Purpose: Systematic four-step procedure for ARIMA model building.

V1_Bot: Automated ARIMA pipeline in the Algo Engine.

---

### 4.5 GARCH Family

**ARCH(q)**

$$\sigma_t^2 = \alpha_0 + \sum_{i=1}^{q} \alpha_i \epsilon_{t-i}^2$$

Where: $\alpha_0 > 0$; $\alpha_i \geq 0$; $\epsilon_t = \sigma_t z_t$, $z_t \sim \mathcal{N}(0,1)$; $\sigma_t^2$ = conditional variance.

Purpose: Models time-varying volatility as a function of past squared residuals, capturing the empirical observation that large shocks tend to cluster.

V1_Bot: Algo Engine volatility modeling foundation.

---

**GARCH(1,1)**

$$\sigma_t^2 = \omega + \alpha \epsilon_{t-1}^2 + \beta \sigma_{t-1}^2$$

Where: $\omega > 0$; $\alpha \geq 0$ (shock coefficient); $\beta \geq 0$ (persistence coefficient); $\alpha + \beta < 1$ for stationarity.

Purpose: The workhorse volatility model — parsimoniously captures both volatility clustering and mean-reversion in variance with just three parameters.

V1_Bot: Algo Engine primary volatility forecast; Doc 09 dynamic risk adjustment.

---

**GARCH(1,1) Unconditional Variance**

$$\bar{\sigma}^2 = \frac{\omega}{1 - \alpha - \beta}$$

Where: $\omega, \alpha, \beta$ = GARCH parameters; requires $\alpha + \beta < 1$.

Purpose: Computes the long-run average variance that the GARCH process reverts to, used as a baseline volatility estimate.

V1_Bot: Doc 09 long-run volatility anchor.

---

**GARCH Persistence**

$$\text{Persistence} = \alpha + \beta$$

Where: values near 1 indicate slow mean reversion in volatility; $\alpha + \beta = 1$ yields IGARCH (integrated GARCH, non-stationary variance).

Purpose: Measures how long volatility shocks persist, informing the speed of risk adjustment after market events.

V1_Bot: Doc 09 volatility regime classification.

---

**EGARCH (Exponential GARCH)**

$$\ln\sigma_t^2 = \omega + \alpha|z_{t-1}| + \gamma z_{t-1} + \beta\ln\sigma_{t-1}^2$$

Where: $z_t = \epsilon_t / \sigma_t$ = standardized residual; $\gamma$ = leverage parameter ($\gamma < 0$ means negative shocks increase volatility more).

Purpose: Models the log of variance (ensuring positivity without parameter constraints) and captures the asymmetric leverage effect where declines increase volatility more than equivalent rallies.

V1_Bot: Algo Engine equity volatility modeling with leverage effect.

---

**GJR-GARCH (Glosten-Jagannathan-Runkle)**

$$\sigma_t^2 = \omega + (\alpha + \gamma I_{t-1})\epsilon_{t-1}^2 + \beta\sigma_{t-1}^2$$

Where: $I_{t-1} = 1$ if $\epsilon_{t-1} < 0$ (indicator for negative shock); $\gamma > 0$ amplifies the effect of negative shocks.

Purpose: Directly models the leverage effect by adding an asymmetric term for negative innovations, simpler than EGARCH.

V1_Bot: Algo Engine alternative asymmetric volatility model.

---

**EWMA Volatility (RiskMetrics)**

$$\sigma_t^2 = \lambda\sigma_{t-1}^2 + (1 - \lambda)r_{t-1}^2$$

Where: $\lambda = 0.94$ (J.P. Morgan RiskMetrics daily convention); $r_{t-1}$ = previous return.

Purpose: Special case of GARCH(1,1) with $\omega = 0$ and $\alpha + \beta = 1$ (IGARCH), providing a parameter-free volatility estimator widely used in risk management.

V1_Bot: Doc 09 rapid volatility estimation; Doc 04 real-time volatility feature.

---

### 4.6 Cointegration

**Engle-Granger Two-Step Method**

Step 1: Estimate the cointegrating regression:

$$Y_t = \alpha + \beta X_t + \epsilon_t$$

Step 2: Test $\epsilon_t$ for stationarity via ADF.

Where: $Y_t, X_t$ = two $I(1)$ series; $\beta$ = cointegrating coefficient (hedge ratio); $\epsilon_t$ = spread.

Purpose: Identifies long-run equilibrium relationships between pairs of non-stationary series; if $\epsilon_t \sim I(0)$, the pair is cointegrated and the spread is mean-reverting.

V1_Bot: Algo Engine pairs trading spread construction; Doc 04 cointegration screening.

---

**Johansen Test**

$$\Delta Y_t = \Pi Y_{t-1} + \sum_{i=1}^{p-1} \Gamma_i \Delta Y_{t-i} + \epsilon_t$$

Where: $Y_t$ = vector of $k$ $I(1)$ series; $\Pi = \alpha\beta'$ = impact matrix; $\text{rank}(\Pi) = r$ = number of cointegrating relationships; $\alpha$ = adjustment speeds; $\beta$ = cointegrating vectors.

Purpose: Tests for the number of cointegrating relationships among $k > 2$ variables simultaneously, superior to pairwise Engle-Granger for multivariate systems.

V1_Bot: Algo Engine multi-asset cointegration analysis.

---

**Trace Statistic**

$$\lambda_{\text{trace}}(r) = -T\sum_{i=r+1}^{k} \ln(1 - \hat{\lambda}_i)$$

Where: $T$ = sample size; $\hat{\lambda}_i$ = $i$-th largest eigenvalue of $\Pi$; $r$ = hypothesized number of cointegrating vectors.

Purpose: Sequentially tests $H_0: \text{rank}(\Pi) \leq r$ against $H_1: \text{rank}(\Pi) > r$ to determine the cointegration rank.

V1_Bot: Algo EngineJohansen rank determination.

---

**Vector Error Correction Model (VECM)**

$$\Delta Y_t = \alpha(\beta' Y_{t-1} - \mu) + \sum_{j=1}^{p-1} \Gamma_j \Delta Y_{t-j} + \epsilon_t$$

Where: $\alpha$ = speed-of-adjustment vector; $\beta' Y_{t-1}$ = error correction term (deviation from equilibrium); $\mu$ = long-run mean of the spread; $\Gamma_j$ = short-run dynamics.

Purpose: Models both the short-run dynamics and the long-run equilibrium adjustment of cointegrated systems, used for spread forecasting and optimal entry/exit timing.

V1_Bot: Algo Engine pairs trading signal generation with mean-reversion speed.

---

**Half-Life of Mean Reversion**

$$H = -\frac{\ln(2)}{\ln(\phi)}$$

Where: $\phi$ = AR(1) coefficient of the spread series (from $\Delta S_t = \phi S_{t-1} + \epsilon_t$, where $-1 < \phi < 0$ for mean reversion).

Purpose: Estimates the expected time for the spread to revert halfway to its mean, used to set holding period expectations and optimize lookback windows.

V1_Bot: Algo Engine pairs trading holding period calibration; Doc 09 spread-trade timeout.

---

### 4.7 Kalman Filter

**State Equation (Transition)**

$$\beta_t = \beta_{t-1} + \omega_t, \quad \omega_t \sim \mathcal{N}(0, V_\omega)$$

Where: $\beta_t$ = unobserved state (e.g., time-varying hedge ratio); $V_\omega$ = state noise covariance.

Purpose: Models the evolution of hidden parameters as a random walk with Gaussian innovations.

V1_Bot: Algo Engine dynamic hedge ratio estimation for pairs trading.

---

**Measurement Equation (Observation)**

$$y_t = x_t \beta_t + \epsilon_t, \quad \epsilon_t \sim \mathcal{N}(0, V_\epsilon)$$

Where: $y_t$ = observed dependent variable; $x_t$ = observed regressors; $V_\epsilon$ = measurement noise variance.

Purpose: Links the observed data to the hidden state through a linear model with noise.

V1_Bot: Algo Engine spread observation model.

---

**Prediction Step**

$$\hat{\beta}_{t|t-1} = \hat{\beta}_{t-1|t-1}$$

$$P_{t|t-1} = P_{t-1|t-1} + V_\omega$$

Where: $\hat{\beta}_{t|t-1}$ = predicted state; $P_{t|t-1}$ = predicted state covariance.

Purpose: Projects the state estimate and its uncertainty one step forward before observing new data.

V1_Bot: Algo EngineKalman predict phase.

---

**Kalman Gain**

$$K_t = P_{t|t-1} x_t (x_t P_{t|t-1} x_t + V_\epsilon)^{-1}$$

Where: $K_t$ = Kalman gain matrix; controls how much the new observation updates the state estimate.

Purpose: Optimally balances trust in the model prediction versus the new observation; high gain means the new data dominates.

V1_Bot: Algo Engine adaptive weight computation.

---

**Update Step**

$$\hat{\beta}_{t|t} = \hat{\beta}_{t|t-1} + K_t(y_t - x_t \hat{\beta}_{t|t-1})$$

$$P_{t|t} = (I - K_t x_t) P_{t|t-1}$$

Where: $y_t - x_t \hat{\beta}_{t|t-1}$ = innovation (prediction error); $P_{t|t}$ = updated state covariance.

Purpose: Incorporates the new observation to refine the state estimate and reduce uncertainty, completing one filter cycle.

V1_Bot: Algo EngineKalman update phase; `signal-generator` dynamic parameter adaptation.

---

## 5. Linear Algebra, Optimization, and Portfolio Theory

### 5.1 Essential Linear Algebra

**Portfolio Return (Dot Product)**

$$R_p = \mathbf{w}^T \mathbf{r} = \sum_{i=1}^{k} w_i r_i$$

Where: $\mathbf{w}$ = weight vector $(w_1, \ldots, w_k)^T$; $\mathbf{r}$ = return vector $(r_1, \ldots, r_k)^T$; $k$ = number of assets.

Purpose: Computes the portfolio return as the weighted sum of individual asset returns.

V1_Bot: Algo Engine`portfolio-optimizer`; Doc 10 portfolio return attribution.

---

**L1 Norm (Manhattan Distance)**

$$||\mathbf{x}||_1 = \sum_{i=1}^{k} |x_i|$$

Where: $x_i$ = components of vector $\mathbf{x}$.

Purpose: Measures total absolute magnitude; used as a sparsity-inducing regularization penalty (LASSO) and in turnover constraints for portfolio rebalancing.

V1_Bot: Algo Engine turnover penalty.

---

**L2 Norm (Euclidean Distance)**

$$||\mathbf{x}||_2 = \sqrt{\sum_{i=1}^{k} x_i^2}$$

Where: $x_i$ = components of vector $\mathbf{x}$.

Purpose: Measures the standard Euclidean length; used as a shrinkage regularization penalty (Ridge) and in distance computations for clustering.

V1_Bot: Algo Engine clustering distance metric.

---

**Portfolio Variance**

$$\sigma_p^2 = \mathbf{w}^T \Sigma \mathbf{w} = \sum_{i=1}^{k}\sum_{j=1}^{k} w_i w_j \sigma_{ij}$$

Where: $\mathbf{w}$ = weight vector; $\Sigma$ = covariance matrix; $\sigma_{ij}$ = covariance between assets $i$ and $j$.

Purpose: Computes the total portfolio risk accounting for all pairwise asset interactions — the core quantity minimized in mean-variance optimization.

V1_Bot: Algo Engine`portfolio-optimizer` objective function; Doc 09 portfolio risk computation.

---

**Eigendecomposition**

$$\Sigma = Q \Lambda Q^T$$

Where: $Q$ = orthogonal matrix of eigenvectors (principal directions); $\Lambda = \text{diag}(\lambda_1, \ldots, \lambda_k)$ = eigenvalues (variance explained per direction); $\lambda_1 \geq \lambda_2 \geq \cdots \geq \lambda_k \geq 0$.

Purpose: Decomposes the covariance matrix into independent risk factors ordered by explanatory power, forming the basis of PCA and factor models.

V1_Bot: Algo EnginePCA risk decomposition.

---

**Principal Component Analysis (PCA)**

$$\mathbf{z} = Q_k^T (\mathbf{x} - \boldsymbol{\mu})$$

Where: $Q_k$ = matrix of top-$k$ eigenvectors of $\Sigma$; $\mathbf{z}$ = projected data in $k$-dimensional space; $k$ chosen such that $\sum_{i=1}^{k}\lambda_i / \sum_{i=1}^{n}\lambda_i \geq \tau$ (e.g., $\tau = 0.95$).

Purpose: Reduces dimensionality by projecting data onto the $k$ directions of maximum variance, removing noise and multicollinearity from feature sets.

V1_Bot: Algo Engine factor exposure analysis.

---

**Singular Value Decomposition (SVD)**

$$A = U \Sigma_s V^T$$

Where: $A \in \mathbb{R}^{m \times n}$; $U \in \mathbb{R}^{m \times m}$ = left singular vectors; $\Sigma_s \in \mathbb{R}^{m \times n}$ = diagonal singular values; $V \in \mathbb{R}^{n \times n}$ = right singular vectors.

Purpose: Generalizes eigendecomposition to non-square matrices; used in pseudo-inverse computation, low-rank matrix approximation, and robust PCA.

V1_Bot: Algo Engine covariance denoising.

---

**Cholesky Decomposition**

$$\Sigma = L L^T$$

Where: $L$ = lower triangular matrix; $\Sigma$ must be symmetric positive definite.

Purpose: Efficiently decomposes the covariance matrix for generating correlated random samples in Monte Carlo simulation — multiplying $L$ by independent standard normals produces correlated draws.

V1_Bot: Doc 09 Monte Carlo simulation engine; Doc 14 correlated path generation.

---

### 5.2 Markowitz Mean-Variance Optimization

**Optimization Problem**

$$\min_{\mathbf{w}} \frac{1}{2} \mathbf{w}^T \Sigma \mathbf{w}$$

$$\text{s.t.} \quad \mathbf{w}^T \boldsymbol{\mu} = \mu_p, \quad \mathbf{w}^T \mathbf{1} = 1$$

Where: $\mathbf{w}$ = weight vector; $\Sigma$ = covariance matrix; $\boldsymbol{\mu}$ = expected return vector; $\mu_p$ = target portfolio return; $\mathbf{1}$ = vector of ones.

Purpose: Finds the minimum-risk portfolio that achieves a specified target return, tracing out the efficient frontier as $\mu_p$ varies.

V1_Bot: Algo Engine`portfolio-optimizer` mean-variance module.

---

**Efficient Frontier (Two-Fund Theorem)**

Any efficient portfolio is a linear combination of two distinct efficient portfolios:

$$\mathbf{w}_{\text{eff}}(\mu_p) = \mathbf{w}_A + \frac{\mu_p - \mu_A}{\mu_B - \mu_A}(\mathbf{w}_B - \mathbf{w}_A)$$

Where: $\mathbf{w}_A, \mathbf{w}_B$ = any two distinct portfolios on the efficient frontier.

Purpose: Demonstrates that the entire efficient frontier can be generated by combining two reference portfolios, simplifying computation and portfolio blending.

V1_Bot: Algo Engine frontier construction; Doc 10 allocation visualization.

---

**Global Minimum Variance Portfolio**

$$\mathbf{w}_{GMV} = \frac{\Sigma^{-1} \mathbf{1}}{\mathbf{1}^T \Sigma^{-1} \mathbf{1}}$$

Where: $\Sigma^{-1}$ = inverse covariance matrix; $\mathbf{1}$ = vector of ones.

Purpose: Identifies the portfolio with the lowest possible risk regardless of return target; useful when expected returns are unreliable or unknown.

V1_Bot: Algo Engine conservative allocation mode; Doc 09 minimum-risk baseline.

---

**Maximum Sharpe Ratio (Tangent Portfolio)**

$$\mathbf{w}_{\text{tan}} = \frac{\Sigma^{-1}(\boldsymbol{\mu} - r_f \mathbf{1})}{\mathbf{1}^T \Sigma^{-1}(\boldsymbol{\mu} - r_f \mathbf{1})}$$

Where: $r_f$ = risk-free rate; $\boldsymbol{\mu} - r_f\mathbf{1}$ = excess return vector.

Purpose: Finds the portfolio with the highest Sharpe ratio (optimal risk-adjusted return), which is the tangent point where the capital allocation line touches the efficient frontier.

V1_Bot: Algo Engine`portfolio-optimizer` Sharpe-maximization mode.

---

### 5.3 Black-Litterman Model

**Implied Equilibrium Returns**

$$\Pi = \lambda \Sigma \mathbf{w}_{\text{mkt}}$$

Where: $\lambda$ = risk aversion coefficient ($\lambda = (E[R_m] - r_f)/\sigma_m^2$); $\Sigma$ = covariance matrix; $\mathbf{w}_{\text{mkt}}$ = market-capitalization weights.

Purpose: Reverse-engineers the expected returns implied by the current market portfolio, providing a neutral starting point that avoids extreme allocations from noisy return estimates.

V1_Bot: Algo EngineBlack-Litterman equilibrium baseline.

---

**Posterior Expected Returns (Combined with Views)**

$$E[\mathbf{R}] = \left[(\tau\Sigma)^{-1} + P^T\Omega^{-1}P\right]^{-1} \left[(\tau\Sigma)^{-1}\Pi + P^T\Omega^{-1}Q\right]$$

Where: $\tau$ = scalar (uncertainty of equilibrium); $P$ = view pick matrix ($K \times N$, where $K$ = number of views); $Q$ = view return vector; $\Omega$ = view uncertainty (diagonal) matrix.

Purpose: Blends market-implied equilibrium returns with investor/model views, weighting each by its confidence level, producing stable and intuitive portfolio allocations.

V1_Bot: Algo EngineBlack-Litterman posterior for AI-view integration.

---

### 5.4 Hierarchical Risk Parity (HRP)

**Step 1: Correlation Distance**

$$d_{ij} = \sqrt{2(1 - \rho_{ij})}$$

Where: $\rho_{ij}$ = Pearson correlation between assets $i$ and $j$; $d_{ij} \in [0, 2]$.

Purpose: Converts correlations into Euclidean distances for hierarchical clustering (assets with $\rho = 1 \Rightarrow d = 0$; $\rho = -1 \Rightarrow d = 2$).

V1_Bot: Algo EngineHRP distance matrix computation.

---

**Step 2: Quasi-Diagonalization**

Reorder the covariance matrix $\Sigma$ according to the hierarchical clustering dendrogram so that correlated assets are adjacent.

Purpose: Places similar assets nearby in the matrix, enabling the recursive bisection to split along natural cluster boundaries.

V1_Bot: Algo EngineHRP matrix reordering.

---

**Step 3: Recursive Bisection**

$$\alpha_L = 1 - \frac{V_L}{V_L + V_R}, \quad \alpha_R = 1 - \alpha_L$$

Where: $V_L = \mathbf{w}_L^T \Sigma_{LL} \mathbf{w}_L$ = variance of left sub-cluster (using inverse-variance weights within); $V_R$ = variance of right sub-cluster.

Purpose: Allocates capital between left and right sub-clusters inversely proportional to their variance, ensuring that riskier clusters receive less weight.

V1_Bot: Algo EngineHRP allocation engine; Doc 09 robust allocation without covariance inversion.

---

### 5.5 Risk Parity

**Marginal Risk Contribution**

$$MRC_i = \frac{\partial \sigma_p}{\partial w_i} = \frac{(\Sigma \mathbf{w})_i}{\sigma_p}$$

Where: $(\Sigma \mathbf{w})_i$ = $i$-th element of $\Sigma\mathbf{w}$; $\sigma_p = \sqrt{\mathbf{w}^T\Sigma\mathbf{w}}$.

Purpose: Measures how much portfolio risk changes for an infinitesimal increase in weight $w_i$.

V1_Bot: Algo Engine risk decomposition module.

---

**Risk Contribution**

$$RC_i = w_i \cdot MRC_i = \frac{w_i (\Sigma \mathbf{w})_i}{\sigma_p}$$

$$\sum_{i=1}^{k} RC_i = \sigma_p$$

Where: $RC_i$ = dollar risk contributed by asset $i$; the sum of all risk contributions equals total portfolio risk.

Purpose: Decomposes total portfolio risk into additive contributions from each asset.

V1_Bot: Algo Engine risk attribution dashboard; Doc 09 concentration monitoring.

---

**Equal Risk Contribution Objective**

$$\min_{\mathbf{w}} \sum_{i=1}^{k} \sum_{j=1}^{k} \left(RC_i - RC_j\right)^2 \quad \text{s.t.} \quad \mathbf{w}^T \mathbf{1} = 1, \; w_i \geq 0$$

Where: the objective drives all $RC_i$ toward equality.

Purpose: Finds the portfolio where every asset contributes equally to total risk, achieving maximum diversification without return estimates.

V1_Bot: Algo Engine`portfolio-optimizer` risk-parity mode.

---

### 5.6 Optimization Foundations

**Gradient Descent**

$$\theta_{t+1} = \theta_t - \eta \nabla_\theta \mathcal{L}(\theta_t)$$

Where: $\eta$ = learning rate; $\nabla_\theta \mathcal{L}$ = gradient of loss w.r.t. parameters; $t$ = iteration.

Purpose: Iteratively moves parameters in the direction of steepest descent to minimize a loss function; the backbone of gradient-based optimization.

V1_Bot: All gradient-based optimization loops in the Algo Engine.

---

**Stochastic Gradient Descent (SGD)**

$$\theta_{t+1} = \theta_t - \eta \nabla_\theta \mathcal{L}(\theta_t; x_i, y_i)$$

Where: $(x_i, y_i)$ = randomly sampled mini-batch; gradient is an unbiased estimate of the full gradient.

Purpose: Approximates the full gradient using random subsets, enabling training on large datasets with reduced per-iteration cost.

V1_Bot: Mini-batch optimization pipeline in the Algo Engine.

---

**Adam Optimizer**

$$m_t = \beta_1 m_{t-1} + (1-\beta_1)\nabla_\theta \mathcal{L}$$

$$v_t = \beta_2 v_{t-1} + (1-\beta_2)(\nabla_\theta \mathcal{L})^2$$

$$\hat{m}_t = \frac{m_t}{1-\beta_1^t}, \quad \hat{v}_t = \frac{v_t}{1-\beta_2^t}$$

$$\theta_{t+1} = \theta_t - \eta \frac{\hat{m}_t}{\sqrt{\hat{v}_t} + \epsilon}$$

Where: $m_t$ = first moment (momentum); $v_t$ = second moment (adaptive learning rate); $\beta_1 = 0.9$, $\beta_2 = 0.999$ (defaults); $\epsilon = 10^{-8}$ (numerical stability); $\hat{m}_t, \hat{v}_t$ = bias-corrected moments.

Purpose: Combines momentum (SGD with inertia) and RMSprop (per-parameter adaptive learning rates) with bias correction for fast and stable convergence.

V1\_Bot: Default optimizer for gradient-based model training.

---

**Karush-Kuhn-Tucker (KKT) Conditions**

For $\min f(\mathbf{x})$ s.t. $g_i(\mathbf{x}) \leq 0$, $h_j(\mathbf{x}) = 0$:

$$\nabla f(\mathbf{x}^*) + \sum_i \mu_i \nabla g_i(\mathbf{x}^*) + \sum_j \lambda_j \nabla h_j(\mathbf{x}^*) = 0$$

$$\mu_i \geq 0, \quad \mu_i g_i(\mathbf{x}^*) = 0 \quad \forall i$$

Where: $\mu_i$ = inequality multipliers; $\lambda_j$ = equality multipliers; $\mu_i g_i = 0$ = complementary slackness.

Purpose: Necessary conditions for optimality in constrained optimization; the theoretical foundation for portfolio optimization with inequality constraints (no shorting, position limits).

V1_Bot: Algo Engine constrained portfolio optimization solver.

---

## 6. Risk Management Mathematics

### 6.1 Value at Risk (VaR)

**Parametric (Variance-Covariance) VaR**

$$\text{VaR}_\alpha = -(\mu + z_\alpha \sigma)$$

Where: $\mu$ = expected return (often assumed $0$ for short horizons); $z_\alpha$ = standard normal quantile at confidence level $\alpha$; $\sigma$ = portfolio return standard deviation.

Key z-values: $z_{0.95} = -1.645$, $z_{0.99} = -2.326$, $z_{0.975} = -1.960$.

Purpose: Estimates the maximum loss over a given horizon at a specified confidence level under the assumption of normally distributed returns.

V1_Bot: Doc 09 parametric VaR module; Doc 10 daily risk dashboard.

---

**Historical VaR**

$$\text{VaR}_\alpha^{\text{hist}} = -\text{Percentile}_{(1-\alpha)}(\{r_1, r_2, \ldots, r_n\})$$

Where: $\{r_i\}$ = historical return series sorted ascending; the $(1-\alpha)$-th percentile is the cutoff.

Purpose: Non-parametric VaR that makes no distributional assumptions, directly using the empirical return distribution.

V1_Bot: Doc 09 historical VaR module; Doc 10 backtest VaR comparison.

---

**Monte Carlo VaR**

$$\text{VaR}_\alpha^{\text{MC}} = -\text{Percentile}_{(1-\alpha)}(\{r_1^{sim}, r_2^{sim}, \ldots, r_M^{sim}\})$$

Where: $\{r_i^{sim}\}$ = $M$ simulated portfolio returns from a fitted model (e.g., GARCH, multivariate normal, copula).

Purpose: Computes VaR from simulated distributions, accommodating non-linear positions, fat tails, and complex dependency structures.

V1_Bot: Doc 09 Monte Carlo VaR engine; Doc 14 exotic risk scenarios.

---

**Multi-Period VaR Scaling**

$$\text{VaR}_{T} = \text{VaR}_1 \times \sqrt{T}$$

Where: $T$ = holding period in days; assumes i.i.d. returns (approximate).

Purpose: Scales single-period VaR to longer horizons under the square-root-of-time rule.

V1_Bot: Doc 09 multi-day risk horizon calculation.

---

### 6.2 Conditional VaR (Expected Shortfall)

**CVaR / Expected Shortfall (ES)**

$$\text{CVaR}_\alpha = \mathbb{E}[L \mid L > \text{VaR}_\alpha] = \frac{1}{1-\alpha}\int_\alpha^1 \text{VaR}_u \, du$$

Where: $L$ = loss; $\alpha$ = confidence level (e.g., $0.95$).

Purpose: Measures the expected loss in the worst $(1-\alpha)$ fraction of scenarios, providing information about the severity of tail losses beyond VaR.

V1_Bot: Doc 09 CVaR risk limit; Doc 10 tail risk reporting.

---

**Parametric CVaR (Normal)**

$$\text{CVaR}_\alpha = -\mu + \sigma \frac{\phi(z_\alpha)}{1 - \alpha}$$

Where: $\phi(\cdot)$ = standard normal PDF; $z_\alpha = \Phi^{-1}(\alpha)$; $\Phi^{-1}$ = inverse CDF.

Purpose: Closed-form Expected Shortfall under normality; always exceeds VaR, reflecting the average of tail losses.

V1_Bot: Doc 09 analytic CVaR for rapid computation.

---

**Sub-Additivity Property**

$$\text{CVaR}(X + Y) \leq \text{CVaR}(X) + \text{CVaR}(Y)$$

Purpose: CVaR (unlike VaR) is a coherent risk measure — diversification never increases risk, making it mathematically sound for portfolio risk aggregation.

V1_Bot: Doc 09 multi-strategy risk aggregation.

---

### 6.3 Kelly Criterion

**Discrete Kelly (Win/Loss)**

$$f^* = \frac{p \cdot b - q}{b}$$

Where: $p$ = win probability; $q = 1 - p$ = loss probability; $b$ = win/loss ratio ($AW/AL$); $f^*$ = optimal fraction of capital to wager.

Purpose: Maximizes the long-run geometric growth rate of wealth under repeated betting with known edge and payoff ratio.

V1_Bot: Doc 09 `position-sizer` Kelly discrete module.

---

**Continuous Kelly (Gaussian Returns)**

$$f^* = \frac{\mu - r_f}{\sigma^2}$$

Where: $\mu$ = expected return; $r_f$ = risk-free rate; $\sigma^2$ = return variance.

Purpose: Generalizes Kelly to continuous distributions, giving the optimal leverage for an asset with normally distributed returns.

V1_Bot: Doc 09 Kelly continuous leverage calculator.

---

**Half-Kelly**

$$f = 0.5 \times f^*$$

Purpose: Applies a 50% reduction to the full Kelly fraction, significantly reducing variance of outcomes and drawdown risk at the cost of slightly lower long-run growth — the practical standard for trading.

V1_Bot: Doc 09 default position sizing mode.

---

**Log-Wealth Maximization (Kelly Derivation)**

$$\max_f \mathbb{E}[\ln(W_T)] = \max_f \sum_{t=1}^{T} \mathbb{E}[\ln(1 + f \cdot r_t)]$$

Where: $W_T$ = terminal wealth; $f$ = fraction invested; $r_t$ = per-period return.

Purpose: The Kelly fraction is derived as the $f$ that maximizes expected log-wealth, connecting information theory to optimal betting.

V1_Bot: Doc 09 theoretical foundation for growth-optimal sizing.

---

### 6.4 Position Sizing

**Fixed Fractional Position Sizing**

$$\text{lots} = \frac{\text{equity} \times \text{risk\%}}{\text{SL\_distance} \times \text{pip\_value}}$$

Where: $\text{equity}$ = current account equity; $\text{risk\%}$ = maximum fraction of equity risked per trade (e.g., 1-2%); $\text{SL\_distance}$ = stop-loss distance in pips; $\text{pip\_value}$ = dollar value per pip per lot.

Purpose: Calculates the position size that risks a fixed percentage of equity on each trade, automatically scaling with equity growth and stop-loss width.

V1_Bot: Doc 08 MT5 lot calculation; Doc 09 `position-sizer` fixed-fractional module.

---

**Volatility-Based Position Sizing**

$$\text{size} = \frac{\text{equity} \times \text{target\_vol}}{\text{ATR} \times \text{multiplier}}$$

Where: $\text{target\_vol}$ = target portfolio volatility (annualized); $\text{ATR}$ = Average True Range (current volatility proxy); $\text{multiplier}$ = contract multiplier or notional per unit.

Purpose: Normalizes position sizes so that each position contributes approximately equal volatility to the portfolio, regardless of the asset's inherent volatility.

V1_Bot: Doc 09 volatility-normalized sizing; signal strength scaling.

---

**Inverse-Volatility Risk Parity Weights**

$$w_i = \frac{1/\sigma_i}{\sum_{j=1}^{k} 1/\sigma_j}$$

Where: $\sigma_i$ = volatility of asset $i$; weights are inversely proportional to volatility and sum to 1.

Purpose: Simple risk parity approximation that equalizes volatility contribution without requiring the full covariance matrix.

V1_Bot: Doc 09 simplified risk parity; quick allocation heuristic.

---

### 6.5 Drawdown

**Drawdown at Time $t$**

$$\text{DD}_t = \frac{\text{Peak}_t - \text{Value}_t}{\text{Peak}_t}$$

Where: $\text{Peak}_t = \max_{s \leq t}(\text{Value}_s)$ = running maximum equity; $\text{Value}_t$ = current equity.

Purpose: Measures the percentage decline from the most recent peak, quantifying the pain experienced by an investor at any point in time.

V1_Bot: Doc 09 real-time drawdown monitoring; Doc 10 equity curve analytics.

---

**Maximum Drawdown**

$$\text{MDD} = \max_{t \in [0, T]} \text{DD}_t = \max_{t \in [0,T]} \frac{\text{Peak}_t - \text{Value}_t}{\text{Peak}_t}$$

Where: $T$ = total observation period.

Purpose: Captures the worst peak-to-trough decline over the entire period, the single most important risk metric for evaluating strategy survivability.

V1_Bot: Doc 09 MDD risk limit (circuit breaker); Doc 10 strategy ranking.

---

**Recovery Requirement**

$$\text{Required Gain} = \frac{d}{100 - d} \times 100\%$$

| Loss $d$% | Required Gain |
|-----------|--------------|
| 10% | 11.1% |
| 20% | 25.0% |
| 33% | 50.0% |
| 50% | 100.0% |
| 75% | 300.0% |
| 90% | 900.0% |

Purpose: Demonstrates the asymmetry of losses — larger drawdowns require disproportionately larger gains to recover, motivating strict drawdown limits.

V1_Bot: Doc 09 drawdown severity classification; Doc 10 recovery analysis.

---

### 6.6 Volatility Estimators

**Historical (Close-to-Close) Volatility**

$$\sigma = \text{std}(r_t) \times \sqrt{252} = \sqrt{\frac{252}{n-1}\sum_{t=1}^{n}(r_t - \bar{r})^2}$$

Where: $r_t$ = log return; $\bar{r}$ = mean log return; $252$ = annualization factor.

Purpose: The simplest volatility estimator using only closing prices, serving as the default benchmark.

V1_Bot: Doc 04 baseline volatility feature; Doc 09 historical vol reference.

---

**EWMA Volatility**

$$\sigma_t^2 = \lambda\sigma_{t-1}^2 + (1-\lambda)r_{t-1}^2, \quad \lambda = 0.94$$

Where: $\lambda$ = decay factor (0.94 for daily, 0.97 for monthly per RiskMetrics).

Purpose: Provides a responsive, parameter-light volatility estimate that adapts quickly to changing market conditions.

V1_Bot: Doc 09 real-time volatility tracking; Doc 04 EWMA vol feature.

---

**Parkinson Volatility (High-Low)**

$$\sigma_P = \sqrt{\frac{1}{4n\ln 2}\sum_{t=1}^{n}\left(\ln\frac{H_t}{L_t}\right)^2}$$

Where: $H_t, L_t$ = high and low prices for period $t$.

Purpose: More efficient than close-to-close volatility (uses intrabar range information), approximately 5x more efficient under GBM assumptions.

V1_Bot: Doc 04 range-based volatility feature; Doc 09 alternative vol estimator.

---

**Garman-Klass Volatility**

$$\sigma_{GK}^2 = \frac{1}{n}\sum_{t=1}^{n}\left[\frac{1}{2}\left(\ln\frac{H_t}{L_t}\right)^2 - (2\ln 2 - 1)\left(\ln\frac{C_t}{O_t}\right)^2\right]$$

Where: $O_t, H_t, L_t, C_t$ = open, high, low, close for period $t$.

Purpose: Uses all four OHLC prices for maximum efficiency (approximately 8x more efficient than close-to-close), the most information-rich single-bar volatility estimator.

V1_Bot: Doc 04 OHLC volatility feature; Doc 09 precision volatility estimation.

---

### 6.7 Performance Metrics

**Sharpe Ratio**

$$SR = \frac{\mathbb{E}[R_p] - R_f}{\sigma_p}$$

Where: $\mathbb{E}[R_p]$ = expected (mean) portfolio return; $R_f$ = risk-free rate; $\sigma_p$ = portfolio return standard deviation.

Purpose: Measures excess return per unit of total risk — the standard risk-adjusted performance metric; $SR > 1$ is generally considered good, $SR > 2$ is excellent.

V1_Bot: Doc 10 primary performance metric; Doc 09 strategy validation threshold.

---

**Sortino Ratio**

$$\text{Sortino} = \frac{\mathbb{E}[R_p] - R_f}{\sigma_{\text{down}}}$$

Where: $\sigma_{\text{down}} = \sqrt{\frac{1}{n_d}\sum_{r_i < \tau}(r_i - \tau)^2}$ = downside deviation.

Purpose: Like Sharpe but penalizes only downside volatility, not upside volatility — more appropriate for asymmetric return distributions.

V1_Bot: Doc 10 asymmetric risk-adjusted performance; Doc 09 downside-aware evaluation.

---

**Calmar Ratio**

$$\text{Calmar} = \frac{\text{CAGR}}{\text{MDD}}$$

Where: $\text{CAGR}$ = compound annual growth rate; $\text{MDD}$ = maximum drawdown (absolute value).

Purpose: Measures return per unit of worst-case drawdown, directly addressing the investor's concern about how much pain is required for a given return.

V1_Bot: Doc 10 drawdown-adjusted performance; Doc 09 strategy survivability metric.

---

**Information Ratio**

$$IR = \frac{R_p - R_b}{\text{TE}}$$

Where: $R_p$ = portfolio return; $R_b$ = benchmark return; $\text{TE} = \sigma(R_p - R_b)$ = tracking error.

Purpose: Measures the consistency of outperformance relative to a benchmark; high IR indicates reliable alpha generation.

V1_Bot: Doc 10 benchmark-relative performance; signal quality assessment.

---

**Deflated Sharpe Ratio**

$$DSR = \Phi\left(\frac{(\widehat{SR} - SR_0)\sqrt{n-1}}{\sqrt{1 - \hat{\gamma}_3 \cdot \widehat{SR} + \frac{\hat{\gamma}_4 - 1}{4}\widehat{SR}^2}}\right)$$

Where: $\widehat{SR}$ = observed Sharpe ratio; $SR_0 = \sqrt{\frac{V[\{\max SR_N\}]}{2}} \cdot ((1-\gamma_E) + \gamma_E \cdot e)$, approximated expected maximum SR under $N$ trials; $\hat{\gamma}_3$ = skewness of returns; $\hat{\gamma}_4$ = kurtosis; $\Phi$ = standard normal CDF; $N$ = number of strategies tested.

Purpose: Adjusts the Sharpe ratio for multiple testing (strategy selection bias), non-normal returns, and finite sample size — a $DSR > 0.95$ indicates genuine skill.

V1_Bot: Doc 10 strategy validation gate.

---

**Profit Factor**

$$PF = \frac{\text{Gross Profit}}{\text{Gross Loss}} = \frac{\sum_{r_i > 0} r_i}{|\sum_{r_i < 0} r_i|}$$

Where: numerator = sum of all winning trade returns; denominator = absolute sum of all losing trade returns.

Purpose: Measures how many dollars are earned for every dollar lost; $PF > 1$ indicates profitability, $PF > 2$ is robust.

V1_Bot: Doc 10 trade-level profitability; Doc 09 strategy acceptance criterion.

---

**Expectancy**

$$E = (WR \times AW) - ((1 - WR) \times AL)$$

Where: $WR$ = win rate; $AW$ = average winning trade (dollars); $AL$ = average losing trade (dollars).

Purpose: Computes the expected value per trade in dollar terms; positive expectancy is necessary (but not sufficient) for long-run profitability.

V1_Bot: Doc 10 per-trade expected value; Doc 09 minimum expectancy threshold.

---

## 7. Technical Indicator Mathematics

### 7.1 Trend Indicators

**Simple Moving Average (SMA)**

$$\text{SMA}_t(n) = \frac{1}{n}\sum_{i=0}^{n-1} C_{t-i}$$

Where: $C_{t-i}$ = closing price $i$ periods ago; $n$ = lookback window.

Purpose: Smooths price data by equally weighting the last $n$ observations, identifying the underlying trend direction.

V1_Bot: Doc 04 `indicator-engine` SMA; trend filter baseline.

---

**Exponential Moving Average (EMA)**

$$\text{EMA}_t = \alpha \cdot C_t + (1 - \alpha) \cdot \text{EMA}_{t-1}, \quad \alpha = \frac{2}{n+1}$$

Where: $\alpha$ = smoothing factor; $n$ = equivalent period; initialization: $\text{EMA}_1 = \text{SMA}(n)$.

Purpose: Applies exponentially decaying weights favoring recent prices, providing faster trend detection than SMA with the same period.

V1_Bot: Doc 04 `indicator-engine` EMA; allEMA-based signals.

---

**Double Exponential Moving Average (DEMA)**

$$\text{DEMA}_t = 2 \cdot \text{EMA}_t(n) - \text{EMA}(\text{EMA}_t(n), n)$$

Where: first term is a standard EMA; second term is an EMA of the EMA (double-smoothed).

Purpose: Reduces lag compared to a standard EMA by subtracting the smoothed version of itself, providing a more responsive trend line.

V1_Bot: Doc 04 `indicator-engine` DEMA; low-lag trend detection.

---

**Triple Exponential Moving Average (TEMA)**

$$\text{TEMA}_t = 3 \cdot \text{EMA}_t - 3 \cdot \text{EMA}(\text{EMA}_t) + \text{EMA}(\text{EMA}(\text{EMA}_t))$$

Where: three levels of EMA nesting on period $n$.

Purpose: Further reduces lag beyond DEMA by triple-correcting the smoothing delay.

V1_Bot: Doc 04 `indicator-engine` TEMA; ultra-responsive trend.

---

**Hull Moving Average (HMA)**

$$\text{HMA}_t(n) = \text{WMA}\left(2 \cdot \text{WMA}(n/2) - \text{WMA}(n), \; \lfloor\sqrt{n}\rfloor\right)$$

Where: $\text{WMA}$ = weighted moving average; $n/2$ and $\sqrt{n}$ are rounded to integers.

Purpose: Achieves near-zero lag while maintaining smoothness by using a weighted combination of different-period WMAs.

V1_Bot: Doc 04 `indicator-engine` HMA; fast trend following.

---

**Weighted Moving Average (WMA)**

$$\text{WMA}_t(n) = \frac{\sum_{i=0}^{n-1}(n-i) \cdot C_{t-i}}{\sum_{i=0}^{n-1}(n-i)} = \frac{\sum_{i=0}^{n-1}(n-i) \cdot C_{t-i}}{n(n+1)/2}$$

Where: weights decrease linearly from $n$ (most recent) to $1$ (oldest).

Purpose: Applies linearly declining weights so that recent prices carry more importance than older ones.

V1_Bot: Doc 04 `indicator-engine` WMA; HMA sub-component.

---

**Volume-Weighted Moving Average (VWMA)**

$$\text{VWMA}_t(n) = \frac{\sum_{i=0}^{n-1} C_{t-i} \cdot V_{t-i}}{\sum_{i=0}^{n-1} V_{t-i}}$$

Where: $V_{t-i}$ = volume at period $t-i$; high-volume bars receive proportionally more weight.

Purpose: Weights price by volume, causing the average to be pulled toward prices where the most trading occurred — a volume-aware trend measure.

V1_Bot: Doc 04 `indicator-engine` VWMA; volume-confirmed trend.

---

**Zero-Lag EMA (ZLEMA)**

$$\text{ZLEMA}_t = \text{EMA}(C_t + (C_t - C_{t-\text{lag}}), n), \quad \text{lag} = \lfloor(n-1)/2\rfloor$$

Where: the input is adjusted by the difference between current price and the price $\text{lag}$ bars ago.

Purpose: Compensates for EMA lag by adding a momentum correction term to the price input before smoothing.

V1_Bot: Doc 04 `indicator-engine` ZLEMA; lag-compensated signals.

---

**Kaufman Adaptive Moving Average (KAMA)**

$$\text{KAMA}_t = \text{KAMA}_{t-1} + sc_t^2 \cdot (C_t - \text{KAMA}_{t-1})$$

$$ER_t = \frac{|C_t - C_{t-n}|}{\sum_{i=0}^{n-1}|C_{t-i} - C_{t-i-1}|}$$

$$sc_t = ER_t \cdot \left(\frac{2}{f+1} - \frac{2}{s+1}\right) + \frac{2}{s+1}$$

Where: $ER_t$ = efficiency ratio (direction / volatility); $sc_t$ = scaled smoothing constant; $f$ = fast period (default 2); $s$ = slow period (default 30); $n$ = ER lookback (default 10).

Purpose: Adapts its speed to market conditions — fast during trends (high ER) and slow during chop (low ER), reducing whipsaws.

V1_Bot: Doc 04 `indicator-engine` KAMA; adaptive trend filter.

---

**Average Directional Index (ADX) and DMI — Full Derivation**

Step 1 — Directional Movement:

$$+DM_t = \begin{cases} H_t - H_{t-1} & \text{if } H_t - H_{t-1} > L_{t-1} - L_t \text{ and } H_t - H_{t-1} > 0 \\ 0 & \text{otherwise} \end{cases}$$

$$-DM_t = \begin{cases} L_{t-1} - L_t & \text{if } L_{t-1} - L_t > H_t - H_{t-1} \text{ and } L_{t-1} - L_t > 0 \\ 0 & \text{otherwise} \end{cases}$$

Step 2 — Smoothed DM and TR (Wilder smoothing, period $n$, default 14):

$$+DM_n^{(s)} = +DM_{n-1}^{(s)} - \frac{+DM_{n-1}^{(s)}}{n} + (+DM_t)$$

$$TR_n^{(s)} = TR_{n-1}^{(s)} - \frac{TR_{n-1}^{(s)}}{n} + TR_t$$

Step 3 — Directional Indicators:

$$+DI_t = \frac{+DM_n^{(s)}}{TR_n^{(s)}} \times 100, \quad -DI_t = \frac{-DM_n^{(s)}}{TR_n^{(s)}} \times 100$$

Step 4 — DX and ADX:

$$DX_t = \frac{|+DI_t - (-DI_t)|}{+DI_t + (-DI_t)} \times 100$$

$$ADX_t = \text{Wilder\_Smooth}(DX_t, n)$$

Where: $+DI$ = positive directional indicator; $-DI$ = negative directional indicator; $DX$ = directional index; Wilder smoothing uses $\alpha = 1/n$.

Purpose: Quantifies both the direction ($+DI$ vs $-DI$) and strength ($ADX$) of a trend; $ADX > 25$ indicates a strong trend.

V1_Bot: Doc 04 `indicator-engine` ADX/DMI; trend strength filter.

---

**Parabolic SAR**

$$SAR_{t+1} = SAR_t + AF \times (EP_t - SAR_t)$$

Where: $AF$ = acceleration factor (starts at $0.02$, increments by $0.02$ each new extreme, max $0.20$); $EP_t$ = extreme point (highest high in uptrend, lowest low in downtrend).

Purpose: Generates trailing stop-and-reverse levels that accelerate toward price during trends, providing both trend direction and dynamic stop-loss levels.

V1_Bot: Doc 04 `indicator-engine` SAR; Doc 09 trailing stop placement.

---

**Ichimoku Kinko Hyo — 5 Components**

$$\text{Tenkan-sen (Conversion)} = \frac{\max(H, 9) + \min(L, 9)}{2}$$

$$\text{Kijun-sen (Base)} = \frac{\max(H, 26) + \min(L, 26)}{2}$$

$$\text{Senkou Span A (Leading A)} = \frac{\text{Tenkan} + \text{Kijun}}{2} \quad \text{(plotted 26 periods ahead)}$$

$$\text{Senkou Span B (Leading B)} = \frac{\max(H, 52) + \min(L, 52)}{2} \quad \text{(plotted 26 periods ahead)}$$

$$\text{Chikou Span (Lagging)} = C_t \quad \text{(plotted 26 periods behind)}$$

Where: $\max(H, n)$ = highest high over $n$ periods; $\min(L, n)$ = lowest low over $n$ periods; default periods: 9, 26, 52.

Purpose: Provides a complete trend-following system with support/resistance (cloud), trend direction (Tenkan/Kijun cross), momentum (Chikou), and future levels (Senkou projection).

V1_Bot: Doc 04 `indicator-engine` Ichimoku; multi-timeframe trend system.

---

**Aroon Indicator**

$$\text{Aroon Up}_t = \frac{n - \text{periods since } n\text{-period high}}{n} \times 100$$

$$\text{Aroon Down}_t = \frac{n - \text{periods since } n\text{-period low}}{n} \times 100$$

$$\text{Aroon Oscillator} = \text{Aroon Up} - \text{Aroon Down}$$

Where: $n$ = lookback period (default 25).

Purpose: Identifies whether price is trending and how long since the last extreme, with crossovers signaling trend changes.

V1_Bot: Doc 04 `indicator-engine` Aroon; trend initiation detection.

---

**Vortex Indicator**

$$VM+_t = |H_t - L_{t-1}|, \quad VM-_t = |L_t - H_{t-1}|$$

$$VI+_t = \frac{\sum_{i=0}^{n-1} VM+_{t-i}}{\sum_{i=0}^{n-1} TR_{t-i}}, \quad VI-_t = \frac{\sum_{i=0}^{n-1} VM-_{t-i}}{\sum_{i=0}^{n-1} TR_{t-i}}$$

Where: $VM+, VM-$ = positive/negative vortex movement; $TR$ = True Range; $n$ = period (default 14).

Purpose: Captures positive and negative trend movement normalized by volatility; $VI+ > VI-$ indicates uptrend.

V1_Bot: Doc 04 `indicator-engine` Vortex; trend direction confirmation.

---

**SuperTrend**

$$\text{Upper Band} = \frac{H_t + L_t}{2} + m \times \text{ATR}(n)$$

$$\text{Lower Band} = \frac{H_t + L_t}{2} - m \times \text{ATR}(n)$$

$$\text{SuperTrend}_t = \begin{cases} \text{Lower Band} & \text{if } C_t > \text{SuperTrend}_{t-1} \text{ (uptrend)} \\ \text{Upper Band} & \text{if } C_t < \text{SuperTrend}_{t-1} \text{ (downtrend)} \end{cases}$$

Where: $m$ = multiplier (default 3); $\text{ATR}(n)$ = Average True Range with period $n$ (default 10).

Purpose: Provides a volatility-adaptive trend-following stop that flips between upper and lower bands based on price crossing.

V1_Bot: Doc 04 `indicator-engine` SuperTrend; Doc 09 dynamic stop-loss; trend signal.

---

### 7.2 Momentum Oscillators

**Relative Strength Index (RSI) — Wilder Smoothing**

$$RS_t = \frac{\text{AvgGain}_t(n)}{\text{AvgLoss}_t(n)}$$

$$\text{AvgGain}_t = \frac{\text{AvgGain}_{t-1} \times (n-1) + \text{Gain}_t}{n}$$

$$\text{AvgLoss}_t = \frac{\text{AvgLoss}_{t-1} \times (n-1) + \text{Loss}_t}{n}$$

$$RSI_t = 100 - \frac{100}{1 + RS_t}$$

Where: $\text{Gain}_t = \max(C_t - C_{t-1}, 0)$; $\text{Loss}_t = \max(C_{t-1} - C_t, 0)$; $n$ = period (default 14); Wilder smoothing uses $\alpha = 1/n$.

Purpose: Measures the speed and magnitude of recent price changes on a 0-100 scale; overbought $> 70$, oversold $< 30$.

V1_Bot: Doc 04 `indicator-engine` RSI; mean-reversion signal; Doc 09 overextension filter.

---

**Moving Average Convergence Divergence (MACD) — Full**

$$\text{MACD Line}_t = \text{EMA}(C, 12)_t - \text{EMA}(C, 26)_t$$

$$\text{Signal Line}_t = \text{EMA}(\text{MACD Line}, 9)_t$$

$$\text{Histogram}_t = \text{MACD Line}_t - \text{Signal Line}_t$$

Where: 12, 26, 9 are default periods; MACD Line measures momentum; Signal Line smooths it; Histogram shows the difference.

Purpose: Captures trend momentum through the convergence and divergence of two EMAs; signal line crossovers and histogram zero-crosses generate trade signals.

V1_Bot: Doc 04 `indicator-engine` MACD; momentum crossover signals.

---

**Stochastic Oscillator (%K / %D)**

$$\%K_t = \frac{C_t - \min(L, n)}{\max(H, n) - \min(L, n)} \times 100$$

$$\%D_t = \text{SMA}(\%K, m)$$

Where: $n$ = %K period (default 14); $m$ = %D smoothing period (default 3); $\min(L,n)$ = lowest low over $n$ periods; $\max(H,n)$ = highest high over $n$ periods.

Purpose: Locates the closing price relative to the recent range on a 0-100 scale; overbought $> 80$, oversold $< 20$; %K/%D crossovers signal reversals.

V1_Bot: Doc 04 `indicator-engine` Stochastic; reversal signal generator.

---

**Stochastic RSI (StochRSI)**

$$\text{StochRSI}_t = \frac{RSI_t - \min(RSI, n)}{\max(RSI, n) - \min(RSI, n)}$$

Where: $RSI_t$ = RSI value at time $t$; $n$ = lookback period (default 14); output range $[0, 1]$ (or $\times 100$).

Purpose: Applies the Stochastic formula to RSI rather than price, creating an oscillator of an oscillator that is more sensitive to short-term overbought/oversold conditions.

V1_Bot: Doc 04 `indicator-engine` StochRSI; high-sensitivity momentum.

---

**Commodity Channel Index (CCI)**

$$CCI_t = \frac{TP_t - \text{SMA}(TP, n)}{0.015 \times \text{MD}_t}$$

$$TP_t = \frac{H_t + L_t + C_t}{3}$$

$$\text{MD}_t = \frac{1}{n}\sum_{i=0}^{n-1}|TP_{t-i} - \text{SMA}(TP, n)|$$

Where: $TP_t$ = typical price; $\text{MD}$ = mean deviation; $0.015$ = Lambert's constant ensuring ~75% of values fall within $[-100, +100]$; $n$ = period (default 20).

Purpose: Measures the deviation of price from its statistical mean normalized by average deviation; values beyond $\pm 100$ indicate strong momentum.

V1_Bot: Doc 04 `indicator-engine` CCI; momentum breakout detection.

---

**Williams %R**

$$\%R_t = \frac{\max(H, n) - C_t}{\max(H, n) - \min(L, n)} \times (-100)$$

Where: $n$ = lookback period (default 14); output range $[-100, 0]$; overbought $> -20$, oversold $< -80$.

Purpose: Inverse of the Stochastic %K (reflected), measuring where the close sits relative to the recent range from the top.

V1_Bot: Doc 04 `indicator-engine` Williams %R; overbought/oversold filter.

---

**Money Flow Index (MFI)**

$$MFI_t = 100 - \frac{100}{1 + MFR_t}$$

$$MFR_t = \frac{\sum \text{Positive MF over } n}{\sum \text{Negative MF over } n}$$

$$\text{MF}_t = TP_t \times V_t, \quad \text{Positive if } TP_t > TP_{t-1}$$

Where: $TP_t$ = typical price; $V_t$ = volume; $MFR$ = money flow ratio; $n$ = period (default 14).

Purpose: Volume-weighted RSI — incorporates volume into momentum, with overbought $> 80$ and oversold $< 20$ levels.

V1_Bot: Doc 04 `indicator-engine` MFI; volume-confirmed momentum.

---

**Rate of Change (ROC)**

$$ROC_t = \frac{C_t - C_{t-n}}{C_{t-n}} \times 100$$

Where: $n$ = lookback period; $C_{t-n}$ = closing price $n$ periods ago.

Purpose: Measures the percentage price change over $n$ periods — the simplest momentum indicator.

V1_Bot: Doc 04 `indicator-engine` ROC; momentum feature.

---

**Momentum**

$$M_t = C_t - C_{t-n}$$

Where: $n$ = lookback period.

Purpose: Measures the absolute price change over $n$ periods; positive values indicate upward momentum.

V1_Bot: Doc 04 `indicator-engine` Momentum; raw momentum feature.

---

**TRIX (Triple Exponential Average)**

$$\text{TRIX}_t = \frac{\text{EMA3}_t - \text{EMA3}_{t-1}}{\text{EMA3}_{t-1}} \times 100$$

Where: $\text{EMA3} = \text{EMA}(\text{EMA}(\text{EMA}(C, n), n), n)$ = triple-smoothed EMA; $n$ = period (default 15).

Purpose: Filters out insignificant price movements through triple smoothing, showing the rate of change of a smoothed trend — zero-line crossovers signal trend changes.

V1_Bot: Doc 04 `indicator-engine` TRIX; smoothed momentum signal.

---

**True Strength Index (TSI)**

$$TSI_t = 100 \times \frac{\text{EMA}(\text{EMA}(\Delta C, r), s)}{\text{EMA}(\text{EMA}(|\Delta C|, r), s)}$$

Where: $\Delta C = C_t - C_{t-1}$; $r$ = long period (default 25); $s$ = short period (default 13); double-smoothed momentum over double-smoothed absolute momentum.

Purpose: Double-smoothed momentum oscillator that captures both trend direction and overbought/oversold conditions with reduced noise.

V1_Bot: Doc 04 `indicator-engine` TSI; smooth momentum signal.

---

**Ultimate Oscillator**

$$UO = 100 \times \frac{4 \cdot A_7 + 2 \cdot A_{14} + A_{28}}{4 + 2 + 1}$$

$$A_n = \frac{\sum_{i=0}^{n-1} BP_{t-i}}{\sum_{i=0}^{n-1} TR_{t-i}}, \quad BP_t = C_t - \min(L_t, C_{t-1})$$

Where: $BP_t$ = buying pressure; $TR_t$ = true range; periods 7, 14, 28; weights 4, 2, 1 for short, medium, long.

Purpose: Combines momentum across three timeframes to reduce false signals; overbought $> 70$, oversold $< 30$.

V1_Bot: Doc 04 `indicator-engine` Ultimate Oscillator; multi-timeframe momentum.

---

**Percentage Price Oscillator (PPO)**

$$PPO_t = \frac{\text{EMA}(C, 12) - \text{EMA}(C, 26)}{\text{EMA}(C, 26)} \times 100$$

Where: same EMAs as MACD but expressed as a percentage.

Purpose: Percentage-normalized MACD that allows cross-asset comparison of momentum magnitude.

V1_Bot: Doc 04 `indicator-engine` PPO; normalized momentum comparison.

---

**Chande Momentum Oscillator (CMO)**

$$CMO_t = \frac{\sum \text{Up}_n - \sum \text{Down}_n}{\sum \text{Up}_n + \sum \text{Down}_n} \times 100$$

Where: $\text{Up} = \max(C_t - C_{t-1}, 0)$; $\text{Down} = \max(C_{t-1} - C_t, 0)$; $n$ = period (default 14); range $[-100, +100]$.

Purpose: Unsmoothed momentum oscillator that measures the net momentum as a fraction of total movement.

V1_Bot: Doc 04 `indicator-engine` CMO; raw momentum ratio.

---

**Connors RSI**

$$\text{CRSI}_t = \frac{RSI(C, 3) + RSI(\text{streak}, 2) + \text{PercentRank}(ROC(1), 100)}{3}$$

Where: $\text{streak}$ = consecutive up/down close count (positive for up-streaks, negative for down-streaks); $\text{PercentRank}$ = percentile rank of one-period ROC over 100 bars.

Purpose: Combines short-term RSI, streak duration, and relative magnitude into a composite mean-reversion oscillator optimized for short-term trading.

V1_Bot: Doc 04 `indicator-engine` Connors RSI; short-term reversal signal.

---

**Detrended Price Oscillator (DPO)**

$$DPO_t = C_{t - (n/2 + 1)} - \text{SMA}(C, n)_t$$

Where: $n$ = period; the price is shifted back by $n/2 + 1$ periods to align with the SMA center.

Purpose: Removes the trend component from price to isolate cyclical oscillations, helping identify cycle length and turning points.

V1_Bot: Doc 04 `indicator-engine` DPO; cycle detection feature.

---

**Coppock Curve**

$$\text{Coppock}_t = \text{WMA}\left(ROC(C, 14) + ROC(C, 11), 10\right)$$

Where: $ROC(C, n)$ = rate of change over $n$ months; $WMA$ with period 10 months.

Purpose: Originally designed for monthly stock market bottoms — buy signal when the curve turns up from below zero.

V1_Bot: Doc 04 `indicator-engine` Coppock; long-term bottom detection.

---

**Fisher Transform**

$$v_t = 0.33 \times \frac{2 \times (C_t - \min(L,n)) / (\max(H,n) - \min(L,n)) - 1}{1} + 0.67 \times v_{t-1}$$

$$\text{Fisher}_t = 0.5 \times \ln\left(\frac{1 + v_t}{1 - v_t}\right)$$

Where: $v_t$ is clamped to $(-0.999, +0.999)$; $n$ = period (default 10); output is unbounded.

Purpose: Transforms price into a Gaussian-like distribution using the inverse hyperbolic tangent, making peaks and troughs sharper and easier to identify.

V1_Bot: Doc 04 `indicator-engine` Fisher Transform; sharp reversal detection.

---

**Schaff Trend Cycle (STC)**

$$\text{MACD}_t = \text{EMA}(C, \text{fast}) - \text{EMA}(C, \text{slow})$$

$$\%K_1 = \text{Stochastic}(\text{MACD}, n), \quad \%D_1 = \text{EMA}(\%K_1, n)$$

$$\%K_2 = \text{Stochastic}(\%D_1, n), \quad STC = \text{EMA}(\%K_2, n)$$

Where: fast = 23, slow = 50, $n$ = cycle period (default 10); output range $[0, 100]$.

Purpose: Applies double Stochastic smoothing to MACD to create a cycle-sensitive oscillator that detects trend changes faster than MACD alone.

V1_Bot: Doc 04 `indicator-engine` STC; cycle-aware trend signal.

---

### 7.3 Volatility Indicators

**Average True Range (ATR) — Wilder Smoothing**

$$TR_t = \max(H_t - L_t, \; |H_t - C_{t-1}|, \; |L_t - C_{t-1}|)$$

$$ATR_t = \frac{ATR_{t-1} \times (n-1) + TR_t}{n}$$

Where: $TR_t$ = true range; $n$ = period (default 14); Wilder smoothing ($\alpha = 1/n$); initialization: $ATR_1 = \text{SMA}(TR, n)$.

Purpose: Measures average volatility over $n$ periods using true range (accounting for gaps), the primary input for volatility-based stops and position sizing.

V1_Bot: Doc 04 `indicator-engine` ATR; Doc 09 stop-loss distance and position sizing.

---

**Bollinger Bands**

$$\text{Upper}_t = \text{SMA}(C, n)_t + k \times \sigma_t(n)$$

$$\text{Middle}_t = \text{SMA}(C, n)_t$$

$$\text{Lower}_t = \text{SMA}(C, n)_t - k \times \sigma_t(n)$$

Where: $n$ = SMA period (default 20); $k$ = standard deviation multiplier (default 2); $\sigma_t(n)$ = rolling standard deviation of closing prices over $n$ periods.

Purpose: Creates volatility-adaptive bands around a moving average; bands widen in high-volatility and narrow in low-volatility regimes.

V1_Bot: Doc 04 `indicator-engine` Bollinger Bands; volatility breakout and mean-reversion signals.

---

**Bollinger Bandwidth**

$$\text{BandWidth}_t = \frac{\text{Upper}_t - \text{Lower}_t}{\text{Middle}_t} \times 100$$

Where: components as defined in Bollinger Bands.

Purpose: Normalizes band width as a percentage of the middle band, directly measuring relative volatility; low BandWidth signals a potential Squeeze breakout.

V1_Bot: Doc 04 `indicator-engine` BB Width; squeeze detection.

---

**Bollinger %B**

$$\%B_t = \frac{C_t - \text{Lower}_t}{\text{Upper}_t - \text{Lower}_t}$$

Where: $\%B > 1$ means price is above the upper band; $\%B < 0$ means price is below the lower band.

Purpose: Normalizes price position within the bands to $[0, 1]$ (approximate), enabling quantitative comparison of relative overbought/oversold levels across assets.

V1_Bot: Doc 04 `indicator-engine` BB %B; mean-reversion signal.

---

**Keltner Channels**

$$\text{Upper}_t = \text{EMA}(C, n)_t + k \times \text{ATR}(m)_t$$

$$\text{Middle}_t = \text{EMA}(C, n)_t$$

$$\text{Lower}_t = \text{EMA}(C, n)_t - k \times \text{ATR}(m)_t$$

Where: $n$ = EMA period (default 20); $m$ = ATR period (default 10); $k$ = ATR multiplier (default 1.5).

Purpose: Volatility bands using ATR instead of standard deviation, less sensitive to closing-price outliers; combined with Bollinger Bands for the TTM Squeeze.

V1_Bot: Doc 04 `indicator-engine` Keltner;Squeeze (BB inside Keltner = low vol).

---

**Donchian Channels**

$$\text{Upper}_t = \max(H_{t-1}, H_{t-2}, \ldots, H_{t-n})$$

$$\text{Lower}_t = \min(L_{t-1}, L_{t-2}, \ldots, L_{t-n})$$

$$\text{Middle}_t = \frac{\text{Upper}_t + \text{Lower}_t}{2}$$

Where: $n$ = lookback period (default 20); note: current bar excluded to avoid look-ahead bias.

Purpose: Defines the highest high and lowest low channel, forming the basis for breakout systems (Turtle Trading); channel width measures volatility.

V1_Bot: Doc 04 `indicator-engine` Donchian; breakout signal; Doc 09 channel-width volatility.

---

**Donchian Channel Width**

$$\text{DCW}_t = \frac{\text{Upper}_t - \text{Lower}_t}{\text{Middle}_t} \times 100$$

Where: components from Donchian Channels.

Purpose: Normalizes channel width as a percentage, measuring range-based volatility.

V1_Bot: Doc 04 `indicator-engine` DCW; volatility regime filter.

---

**Standard Deviation (Rolling)**

$$\sigma_t(n) = \sqrt{\frac{1}{n-1}\sum_{i=0}^{n-1}(C_{t-i} - \overline{C}_n)^2}$$

Where: $\overline{C}_n$ = SMA of close over $n$ periods.

Purpose: Rolling sample standard deviation of price, used directly as a volatility measure and as the Bollinger Band width parameter.

V1_Bot: Doc 04 `indicator-engine` rolling StdDev; volatility feature.

---

**Chaikin Volatility**

$$\text{ChaikinVol}_t = \frac{\text{EMA}(H-L, n)_t - \text{EMA}(H-L, n)_{t-m}}{\text{EMA}(H-L, n)_{t-m}} \times 100$$

Where: $n$ = EMA period (default 10); $m$ = ROC period (default 10).

Purpose: Measures the rate of change of the smoothed high-low spread, capturing whether volatility is expanding or contracting.

V1_Bot: Doc 04 `indicator-engine` Chaikin Volatility; volatility expansion signal.

---

**Relative Volatility Index (RVI)**

$$RVI_t = 100 \times \frac{\text{EMA}(\text{UpDev}, n)}{\text{EMA}(\text{UpDev}, n) + \text{EMA}(\text{DownDev}, n)}$$

Where: $\text{UpDev}_t = \sigma_t(s)$ if $C_t > C_{t-1}$, else $0$; $\text{DownDev}_t = \sigma_t(s)$ if $C_t < C_{t-1}$, else $0$; $s$ = StdDev period (default 10); $n$ = smoothing period (default 14).

Purpose: RSI-like oscillator applied to standard deviation rather than price, measuring the directionality of volatility.

V1_Bot: Doc 04 `indicator-engine` RVI; volatility direction filter.

---

**Choppiness Index**

$$CI_t = \frac{100 \times \ln\left(\frac{\sum_{i=0}^{n-1} ATR_{t-i}}{\max(H, n) - \min(L, n)}\right)}{\ln(n)}$$

Where: $n$ = period (default 14); range approximately $[0, 100]$; $CI > 61.8$ = choppy; $CI < 38.2$ = trending.

Purpose: Quantifies whether the market is trending or range-bound by comparing the sum of ATR values to the total range — higher values indicate choppier markets.

V1_Bot: Doc 04 `indicator-engine` Choppiness Index; regime classifier (trend vs. range).

---

**Historical Volatility (Annualized)**

$$HV_t(n) = \sigma_t(n) \times \sqrt{252} = \sqrt{\frac{252}{n-1}\sum_{i=0}^{n-1}(r_{t-i} - \bar{r})^2}$$

Where: $r_t = \ln(C_t/C_{t-1})$; $n$ = lookback (typical: 20, 60, 252); $\bar{r}$ = mean log return over window.

Purpose: Rolling annualized volatility of log returns, the standard measure for comparing realized volatility across timeframes and assets.

V1_Bot: Doc 04 `indicator-engine` HV; Doc 09 realized-vs-implied volatility analysis.

---

### 7.4 Volume Indicators

**On-Balance Volume (OBV)**

$$OBV_t = OBV_{t-1} + \begin{cases} V_t & \text{if } C_t > C_{t-1} \\ -V_t & \text{if } C_t < C_{t-1} \\ 0 & \text{if } C_t = C_{t-1} \end{cases}$$

Where: $V_t$ = volume at time $t$; $C_t$ = closing price.

Purpose: Cumulative volume flow indicator where volume is added on up-closes and subtracted on down-closes; divergences between OBV and price indicate potential reversals.

V1_Bot: Doc 04 `indicator-engine` OBV; volume divergence signal.

---

**VWAP and Standard Deviation Bands**

$$\text{VWAP}_t = \frac{\sum_{i=1}^{t} TP_i \cdot V_i}{\sum_{i=1}^{t} V_i}$$

$$\text{VWAP\_StdDev}_t = \sqrt{\frac{\sum_{i=1}^{t} V_i \cdot (TP_i - \text{VWAP}_t)^2}{\sum_{i=1}^{t} V_i}}$$

$$\text{Upper Band}_k = \text{VWAP}_t + k \times \text{VWAP\_StdDev}_t$$

$$\text{Lower Band}_k = \text{VWAP}_t - k \times \text{VWAP\_StdDev}_t$$

Where: $TP_i = (H_i + L_i + C_i)/3$; $V_i$ = volume; reset daily for intraday VWAP; $k = 1, 2, 3$ for band levels.

Purpose: Provides the volume-weighted mean price with statistical deviation bands, serving as institutional execution benchmarks and support/resistance levels.

V1_Bot: Doc 04 `indicator-engine` VWAP bands; Doc 08 execution quality; intraday mean-reversion.

---

**Accumulation/Distribution Line and Close Location Value (CLV)**

$$CLV_t = \frac{(C_t - L_t) - (H_t - C_t)}{H_t - L_t} = \frac{2C_t - L_t - H_t}{H_t - L_t}$$

$$AD_t = AD_{t-1} + CLV_t \times V_t$$

Where: $CLV \in [-1, +1]$; $CLV = +1$ when close = high; $CLV = -1$ when close = low.

Purpose: Cumulative indicator that weights volume by where the close falls within the bar's range, measuring buying/selling pressure; divergence from price signals accumulation or distribution.

V1_Bot: Doc 04 `indicator-engine` A/D Line; accumulation/distribution divergence.

---

**Chaikin Money Flow (CMF)**

$$CMF_t = \frac{\sum_{i=0}^{n-1} CLV_{t-i} \times V_{t-i}}{\sum_{i=0}^{n-1} V_{t-i}}$$

Where: $CLV$ = close location value; $n$ = period (default 20); $CMF \in [-1, +1]$.

Purpose: Volume-weighted average of CLV over $n$ periods; positive CMF indicates buying pressure (accumulation), negative indicates selling pressure (distribution).

V1_Bot: Doc 04 `indicator-engine` CMF; money flow confirmation.

---

**Chaikin Oscillator**

$$\text{ChaikinOsc}_t = \text{EMA}(AD, 3)_t - \text{EMA}(AD, 10)_t$$

Where: $AD$ = Accumulation/Distribution Line; default fast/slow periods 3 and 10.

Purpose: MACD-style oscillator applied to the A/D Line, signaling momentum changes in accumulation/distribution.

V1_Bot: Doc 04 `indicator-engine` Chaikin Oscillator; volume momentum.

---

**Force Index**

$$FI_t = (C_t - C_{t-1}) \times V_t$$

$$FI_{\text{smoothed}} = \text{EMA}(FI, n)$$

Where: $n$ = smoothing period (default 13); positive $FI$ = bulls in control; negative $FI$ = bears in control.

Purpose: Combines price change and volume into a single oscillator measuring the force behind each price move.

V1_Bot: Doc 04 `indicator-engine` Force Index; force-based entry signal.

---

**Ease of Movement (EMV)**

$$DM_t = \frac{H_t + L_t}{2} - \frac{H_{t-1} + L_{t-1}}{2}$$

$$BR_t = \frac{V_t / 10000}{H_t - L_t}$$

$$EMV_t = \frac{DM_t}{BR_t}$$

$$\text{EMV\_SMA} = \text{SMA}(EMV, n)$$

Where: $DM$ = distance moved (midpoint change); $BR$ = box ratio (volume per unit of range); $n$ = smoothing period (default 14).

Purpose: Relates price movement to volume, measuring how easily price moves — high positive EMV indicates price rising easily on low volume.

V1_Bot: Doc 04 `indicator-engine` EMV; ease-of-movement feature.

---

**Klinger Volume Oscillator**

$$KVO_t = \text{EMA}(VF, 34)_t - \text{EMA}(VF, 55)_t$$

$$VF_t = V_t \times |2 \times \frac{dm_t}{cm_t} - 1| \times T_t \times 100$$

$$T_t = \begin{cases} +1 & \text{if } (H_t + L_t + C_t) > (H_{t-1} + L_{t-1} + C_{t-1}) \\ -1 & \text{otherwise} \end{cases}$$

Where: $dm_t = H_t - L_t$; $cm_t$ = cumulative $dm$ (reset when trend $T$ changes); $VF$ = volume force.

Purpose: Long-term volume oscillator that captures the difference between short-term and long-term volume accumulation to detect reversals.

V1_Bot: Doc 04 `indicator-engine` Klinger; long-term volume divergence.

---

**Volume Profile: POC, VAH, VAL**

$$\text{POC} = \arg\max_p \text{Volume}(p)$$

$$\text{VA} = \{p : \sum \text{Volume}(p) \geq 0.70 \times \text{TotalVolume}\}$$

$$\text{VAH} = \max(\text{VA}), \quad \text{VAL} = \min(\text{VA})$$

Where: $\text{POC}$ = Point of Control (price level with highest volume); $\text{VA}$ = Value Area (price range containing 70% of volume); $\text{VAH/VAL}$ = Value Area High/Low.

Purpose: Constructs a volume-by-price histogram to identify the most-traded price level (POC) and the range where 70% of volume occurred (VA), serving as key support/resistance.

V1_Bot: Doc 04 `indicator-engine` Volume Profile; support/resistance from volume; Doc 08 execution anchoring.

---

### 7.5 Fibonacci and Elliott Wave

**Golden Ratio**

$$\phi = \frac{1 + \sqrt{5}}{2} \approx 1.6180339887\ldots$$

$$\frac{1}{\phi} = \phi - 1 \approx 0.6180339887\ldots$$

Where: $\phi$ = the golden ratio; $F_n / F_{n-1} \to \phi$ as $n \to \infty$ for Fibonacci numbers $F_n = F_{n-1} + F_{n-2}$.

Purpose: The mathematical constant from which all Fibonacci retracement and extension levels derive, forming the theoretical basis for harmonic trading.

V1_Bot: Algo EngineFibonacci calculation engine.

---

**Fibonacci Retracement Levels**

For a move from swing low $A$ to swing high $B$ (uptrend retracements):

$$\text{Level}(r) = B - r \times (B - A)$$

| Ratio $r$ | Derivation | Level Name |
|-----------|------------|------------|
| $0.236$ | $1 - \phi^{-3} \approx 1 - 0.764$ | 23.6% |
| $0.382$ | $\phi^{-2} = 1/\phi^2$ | 38.2% |
| $0.500$ | Midpoint (not Fibonacci-derived) | 50.0% |
| $0.618$ | $\phi^{-1} = 1/\phi$ | 61.8% |
| $0.786$ | $\sqrt{\phi^{-1}} = \sqrt{0.618}$ | 78.6% |
| $0.886$ | $\phi^{-1/2} \approx \sqrt[4]{0.382}$ | 88.6% |

Where: $A$ = swing low; $B$ = swing high; for downtrend retracements, swap $A$ and $B$.

Purpose: Identifies potential support/resistance levels where price retracements are statistically more likely to stall or reverse.

V1_Bot: Doc 04 `indicator-engine` Fibonacci Retracement;S/R level generation.

---

**Fibonacci Extension Levels**

For a move $A \to B$ with retracement to $C$:

$$\text{Extension}(r) = C + r \times (B - A)$$

| Ratio $r$ | Level Name |
|-----------|------------|
| $0.618$ | 61.8% |
| $1.000$ | 100% (measured move) |
| $1.272$ | $\sqrt{\phi}$ | 127.2% |
| $1.618$ | $\phi$ | 161.8% |
| $2.000$ | 200% |
| $2.618$ | $\phi^2$ | 261.8% |
| $3.618$ | $\phi^2 + 1$ | 361.8% |
| $4.236$ | $\phi^3$ | 423.6% |

Where: $A$ = swing start; $B$ = swing end; $C$ = retracement end.

Purpose: Projects potential profit targets beyond the initial swing, where trending moves tend to find resistance/support.

V1_Bot: Doc 04 `indicator-engine` Fibonacci Extensions; take-profit targets.

---

**Harmonic Pattern Ratios**

**Gartley Pattern (222)**

| Leg | Ratio | Range |
|-----|-------|-------|
| $XA \to B$ | $0.618$ | $B = 0.618 \times XA$ retracement |
| $AB \to C$ | $0.382 - 0.886$ | $C$ retraces 38.2%-88.6% of $AB$ |
| $XA \to D$ | $0.786$ | $D = 0.786 \times XA$ retracement (PRZ) |
| $BC \to D$ | $1.272 - 1.618$ | $D = 1.272$-$1.618 \times BC$ extension |

Purpose: Defines the Gartley harmonic pattern through specific Fibonacci ratio relationships between four legs ($XA$, $AB$, $BC$, $CD$), identifying high-probability reversal zones.

V1_Bot: Algo Engine harmonic pattern scanner — Gartley module.

---

**Bat Pattern**

| Leg | Ratio |
|-----|-------|
| $XA \to B$ | $0.382 - 0.500$ |
| $AB \to C$ | $0.382 - 0.886$ |
| $XA \to D$ | $0.886$ (key level) |
| $BC \to D$ | $1.618 - 2.618$ |

Purpose: A variant of the Gartley with a deeper $D$-point ($0.886$ of $XA$), offering tighter stop-loss placement at the $X$ point.

V1_Bot: Algo Engine harmonic pattern scanner — Bat module.

---

**Butterfly Pattern**

| Leg | Ratio |
|-----|-------|
| $XA \to B$ | $0.786$ |
| $AB \to C$ | $0.382 - 0.886$ |
| $XA \to D$ | $1.272 - 1.618$ (beyond $X$) |
| $BC \to D$ | $1.618 - 2.618$ |

Purpose: An extension pattern where $D$ extends beyond the initial $X$ point, used at major market turning points.

V1_Bot: Algo Engine harmonic pattern scanner — Butterfly module.

---

**Crab Pattern**

| Leg | Ratio |
|-----|-------|
| $XA \to B$ | $0.382 - 0.618$ |
| $AB \to C$ | $0.382 - 0.886$ |
| $XA \to D$ | $1.618$ (key level) |
| $BC \to D$ | $2.618 - 3.618$ |

Purpose: The most extended harmonic pattern with $D$ at $1.618$ of $XA$, typically found at extreme market exhaustion points.

V1_Bot: Algo Engine harmonic pattern scanner — Crab module.

---

**AB=CD Pattern**

$$CD = AB \quad \text{(equal legs)}$$

$$\text{Classic: } CD = AB, \quad BC = 0.618 \times AB, \quad CD = 1.272 \times BC$$

$$\text{Extension: } CD = 1.272 \times AB, \quad BC = 0.618 \times AB, \quad CD = 1.618 \times BC$$

Where: legs $AB$ and $CD$ are equal (or related by Fibonacci ratios) in both price and time.

Purpose: The foundational harmonic pattern — price completes a symmetric (or Fibonacci-proportional) four-point structure signaling reversal at $D$.

V1_Bot: Algo Engine harmonic pattern scanner — AB=CD module.

---

**Elliott Wave — Impulse Wave Ratios**

An impulse wave consists of 5 sub-waves (1-2-3-4-5) with these typical Fibonacci relationships:

| Relationship | Typical Ratio |
|-------------|---------------|
| Wave 2 retraces Wave 1 | $0.500 - 0.618$ of Wave 1 |
| Wave 3 extends Wave 1 | $1.618 \times$ Wave 1 (most common) |
| Wave 3 (alternate) | $2.618 \times$ Wave 1 |
| Wave 4 retraces Wave 3 | $0.382$ of Wave 3 |
| Wave 4 (alternate) | $0.236 - 0.500$ of Wave 3 |
| Wave 5 equals Wave 1 | $1.000 \times$ Wave 1 (when Wave 3 is extended) |
| Wave 5 extends | $0.618 \times$ Wave 1 or $0.382 \times$ (Wave 1 through 3) |

**Rules (inviolable):**

1. Wave 2 never retraces more than 100% of Wave 1
2. Wave 3 is never the shortest of Waves 1, 3, and 5
3. Wave 4 never overlaps Wave 1 price territory (in standard impulse)

Purpose: Defines the Fibonacci-ratio structure of five-wave impulse moves in Elliott Wave Theory, used for wave counting validation and target projection.

V1_Bot: Algo EngineElliott Wave analyzer — impulse validation.

---

**Elliott Wave — Corrective Wave Ratios**

A corrective wave (A-B-C) follows an impulse with these typical relationships:

| Relationship | Typical Ratio |
|-------------|---------------|
| Wave A | Related to preceding impulse |
| Wave B retraces Wave A | $0.382 - 0.786$ of Wave A |
| Wave C equals Wave A | $1.000 \times$ Wave A (most common) |
| Wave C extends | $1.618 \times$ Wave A |
| Wave C (truncated) | $0.618 \times$ Wave A |

**Corrective Patterns:**

- **Zigzag** (5-3-5): $C = A$ or $C = 1.618 \times A$
- **Flat** (3-3-5): $B \approx A$, $C \approx A$
- **Expanded Flat**: $B > A$ (typically $1.236 \times A$), $C = 1.618 \times A$
- **Triangle** (3-3-3-3-3): each wave is $\approx 0.618$ of prior wave

Purpose: Defines the corrective wave structures that follow impulse waves, used for identifying completion of pullbacks and continuation of the larger trend.

V1_Bot: Algo EngineElliott Wave analyzer — corrective pattern recognition.

---

*End of Part A (Sections 1-7). Part B continues with Sections 8-19.*

# Document 14 -- PART B: Mathematical Reference Manual (Sections 8--13)

## MONEYMAKER V1 Trading Ecosystem

> **Scope:** Stochastic calculus, statistical learning mathematics, advanced model architectures, optimization methods, market microstructure, and information theory. Every formula includes a display equation, variable definitions, purpose statement, and V1\_Bot mapping.

---

## Section 8: Stochastic Calculus and Derivatives Pricing

### 8.1 Brownian Motion and Geometric Brownian Motion

**Wiener Process Properties:**

$$
W_0 = 0, \quad W_t - W_s \sim \mathcal{N}(0,\; t - s), \quad s < t
$$

Where:

- $W_t$ = standard Wiener process (Brownian motion) at time $t$
- $W_t - W_s$ = increment over interval $[s, t]$, normally distributed with mean 0 and variance $t - s$
- Increments on non-overlapping intervals are independent

Purpose: Defines the foundational continuous-time stochastic process that drives all diffusion-based asset price models.

V1\_Bot: Noise generation kernel for Monte Carlo simulation engine and synthetic data pipelines used in backtesting.

---

**Geometric Brownian Motion (GBM) SDE:**

$$
dS_t = \mu\, S_t\, dt + \sigma\, S_t\, dW_t
$$

Where:

- $S_t$ = asset price at time $t$
- $\mu$ = drift coefficient (expected return per unit time)
- $\sigma$ = diffusion coefficient (volatility)
- $dW_t$ = Wiener process increment

Purpose: Models asset prices as a log-normal diffusion, ensuring non-negativity and proportional returns.

V1\_Bot: Default price dynamics assumption in Monte Carlo scenario generation for backtest stress testing.

---

**GBM Closed-Form Solution:**

$$
S_T = S_0 \exp\!\left[\left(\mu - \frac{\sigma^2}{2}\right)T + \sigma W_T\right]
$$

Where:

- $S_0$ = initial asset price
- $T$ = time horizon
- $\mu - \sigma^2/2$ = drift correction (Ito correction term)
- $W_T \sim \mathcal{N}(0, T)$

Purpose: Provides an analytical expression for simulating future price paths without numerical SDE integration.

V1\_Bot: Direct formula used in synthetic data generation module; each Monte Carlo path is one draw from this distribution.

---

### 8.2 Ito's Lemma

$$
df = \left(\frac{\partial f}{\partial t} + \mu\, S\,\frac{\partial f}{\partial S} + \frac{1}{2}\sigma^2 S^2\,\frac{\partial^2 f}{\partial S^2}\right)dt + \sigma\, S\,\frac{\partial f}{\partial S}\,dW_t
$$

Where:

- $f(S_t, t)$ = twice-differentiable function of the stochastic variable $S_t$ and time $t$
- $\partial f / \partial t$ = time partial derivative
- $\partial f / \partial S$ = first spatial partial (delta)
- $\partial^2 f / \partial S^2$ = second spatial partial (gamma)
- The $\frac{1}{2}\sigma^2 S^2$ gamma term is the Ito correction absent in ordinary calculus

Purpose: Provides the chain rule for stochastic calculus, enabling derivation of dynamics for any smooth function of a diffusion process.

V1\_Bot: Theoretical foundation for deriving log-price dynamics $d\ln S_t = (\mu - \sigma^2/2)dt + \sigma\,dW_t$, which underpins the triple barrier label probability model.

---

**Application -- Log-Price Dynamics:**

$$
d\ln S_t = \left(\mu - \frac{\sigma^2}{2}\right)dt + \sigma\,dW_t
$$

Where:

- $\ln S_t$ = log-price (applying Ito's Lemma with $f = \ln S$)
- The drift shifts from $\mu$ to $\mu - \sigma^2/2$ due to the Ito correction

Purpose: Shows that log-returns under GBM are normally distributed, justifying Gaussian assumptions in many trading models.

V1\_Bot: Log-return computation basis for all feature engineering in the Algo Engine pipeline.

---

### 8.3 Heston Stochastic Volatility Model

**Price Process:**

$$
dS_t = \mu\, S_t\, dt + \sqrt{v_t}\; S_t\, dW_t^S
$$

**Variance Process:**

$$
dv_t = \kappa(\theta - v_t)\,dt + \sigma_v \sqrt{v_t}\; dW_t^v
$$

**Correlation Structure:**

$$
dW_t^S\, dW_t^v = \rho\, dt
$$

**Feller Condition (variance stays positive):**

$$
2\kappa\theta > \sigma_v^2
$$

Where:

- $v_t$ = instantaneous variance at time $t$
- $\kappa$ = mean reversion speed of variance
- $\theta$ = long-run variance level
- $\sigma_v$ = volatility of volatility (vol-of-vol)
- $\rho$ = correlation between price and variance Brownian motions (typically $\rho < 0$ for equities, producing the leverage effect)
- $W_t^S, W_t^v$ = correlated Wiener processes

Purpose: Captures the empirical observation that volatility is itself stochastic and negatively correlated with returns, producing realistic implied volatility smiles.

V1\_Bot: Gold (XAUUSD) volatility modeling engine; Heston parameters $(\kappa, \theta, \sigma_v, \rho)$ are calibrated daily and fed as features into the vol regime classifier.

---

### 8.4 Ornstein-Uhlenbeck Process

**SDE:**

$$
dX_t = \lambda(\mu - X_t)\,dt + \sigma\,dW_t
$$

**Analytical Solution:**

$$
X_t = X_0\, e^{-\lambda t} + \mu\!\left(1 - e^{-\lambda t}\right) + \sigma \int_0^t e^{-\lambda(t-s)}\,dW_s
$$

**Stationary Distribution:**

$$
X_\infty \sim \mathcal{N}\!\left(\mu,\; \frac{\sigma^2}{2\lambda}\right)
$$

**Half-Life of Mean Reversion:**

$$
H = \frac{\ln 2}{\lambda}
$$

Where:

- $X_t$ = mean-reverting process value (e.g., spread between co-integrated assets)
- $\lambda$ = mean reversion speed ($\lambda > 0$ required for stationarity)
- $\mu$ = long-run equilibrium level
- $\sigma$ = diffusion coefficient
- $H$ = time for a deviation to decay to half its initial magnitude

Purpose: Models any stationary, mean-reverting signal; the half-life parameterizes how quickly deviations from equilibrium are corrected.

V1\_Bot: Mean reversion strategy parameterization -- the OU half-life $H$ determines entry/exit timing for spread trading signals and sets the vertical barrier width in triple barrier labeling.

---

### 8.5 SVI Volatility Surface

**Raw SVI Parameterization (total implied variance):**

$$
w(k) = a + b\left\{\rho(k - m) + \sqrt{(k - m)^2 + \sigma^2}\right\}
$$

Where:

- $w(k)$ = total implied variance $= \sigma_{BS}^2 \cdot T$ as a function of log-moneyness $k = \ln(K/F)$
- $a$ = vertical translation (overall variance level)
- $b$ = controls the slope of the asymptotic wings ($b \geq 0$)
- $\rho$ = rotation/skew parameter ($-1 < \rho < 1$)
- $m$ = horizontal translation (shifts the smile center)
- $\sigma$ = ATM curvature ($\sigma > 0$)

**No-Arbitrage Constraints:**

$$
a + b\sigma\sqrt{1 - \rho^2} \geq 0 \qquad \text{(non-negative variance at ATM)}
$$

$$
b(1 + |\rho|) \leq \frac{4}{T} \qquad \text{(Roger Lee moment bound)}
$$

Purpose: Provides a parsimonious five-parameter fit to the implied volatility smile at a single expiry, enforcing absence of butterfly and calendar spread arbitrage.

V1\_Bot: Volatility surface feature extractor for options-aware models; SVI parameters are computed per expiry and interpolated across the term structure to create a smooth vol surface input tensor.

---

## Section 9: Statistical Learning Mathematics for Trading

### 9.1 Supervised Learning Foundations

**Ordinary Least Squares (OLS):**

$$
\hat{y} = X\beta, \qquad \beta^{OLS} = (X^T X)^{-1} X^T y
$$

Where:

- $X \in \mathbb{R}^{n \times p}$ = design matrix ($n$ samples, $p$ features)
- $y \in \mathbb{R}^n$ = target vector
- $\beta \in \mathbb{R}^p$ = coefficient vector
- $(X^TX)^{-1}X^T$ = Moore-Penrose pseudo-inverse (requires $X^TX$ invertible)

Purpose: Finds the linear coefficients minimizing sum of squared residuals; serves as the baseline regression model.

V1\_Bot: Baseline linear model in meta-learner stacking ensemble and diagnostic tool for feature importance sanity checks.

---

**Ridge Regression (L2 Regularization):**

$$
\min_\beta \|y - X\beta\|^2 + \lambda\|\beta\|^2
$$

**Closed-Form Solution:**

$$
\beta^{Ridge} = (X^T X + \lambda I)^{-1} X^T y
$$

Where:

- $\lambda \geq 0$ = regularization strength
- $I$ = identity matrix
- $\lambda I$ shrinks coefficients toward zero, stabilizing ill-conditioned $X^TX$

Purpose: Prevents overfitting and multicollinearity by penalizing large coefficients while keeping all features in the model.

V1\_Bot: Regularized regression component in the stacking meta-learner.

---

**Lasso Regression (L1 Regularization):**

$$
\min_\beta \|y - X\beta\|^2 + \lambda\|\beta\|_1
$$

Where:

- $\|\beta\|_1 = \sum_{j=1}^p |\beta_j|$ = L1 norm
- L1 penalty induces exact zeros in $\beta$, performing automatic feature selection

Purpose: Produces sparse models by driving irrelevant feature coefficients to exactly zero.

V1\_Bot: Feature selection pre-filter in the Algo Engine pipeline to reduce dimensionality before ensemble training.

---

**Elastic Net (L1 + L2):**

$$
\min_\beta \|y - X\beta\|^2 + \lambda\!\left(\alpha\|\beta\|_1 + (1 - \alpha)\|\beta\|^2\right)
$$

Where:

- $\alpha \in [0, 1]$ = mixing parameter ($\alpha = 1$ is Lasso, $\alpha = 0$ is Ridge)
- Combines sparsity of L1 with stability of L2

Purpose: Balances feature selection and coefficient stability when features are correlated.

V1\_Bot: Default regularized linear model for feature group selection across correlated technical indicators.

---

**Logistic Regression:**

$$
P(y = 1 \mid x) = \sigma(w^T x + b) = \frac{1}{1 + e^{-(w^T x + b)}}
$$

Where:

- $\sigma(\cdot)$ = sigmoid (logistic) function
- $w \in \mathbb{R}^p$ = weight vector
- $b$ = bias term
- Output is a probability $\in (0, 1)$

Purpose: Models the probability of a binary outcome (e.g., price up/down) as a function of input features.

V1\_Bot: Directional classification baseline and meta-label calibration model (Algo Engine).

---

**Binary Cross-Entropy Loss:**

$$
\mathcal{L} = -\sum_{i=1}^n \left[y_i \log \hat{y}_i + (1 - y_i)\log(1 - \hat{y}_i)\right]
$$

Where:

- $y_i \in \{0, 1\}$ = true label
- $\hat{y}_i \in (0, 1)$ = predicted probability
- The loss is minimized when $\hat{y}_i = y_i$ for all samples

Purpose: Standard loss function for binary classification; measures the divergence between predicted probabilities and true labels.

V1\_Bot: Training loss for all binary classification models including meta-labeling confidence models.

---

### 9.2 Decision Trees and Ensemble Methods

**Gini Impurity:**

$$
G = 1 - \sum_{i=1}^C p_i^2
$$

Where:

- $C$ = number of classes
- $p_i$ = proportion of samples belonging to class $i$
- $G = 0$ for a pure node; $G$ is maximized for a uniform distribution

Purpose: Measures the probability of misclassifying a randomly chosen sample if labeled according to the class distribution at a node.

V1\_Bot: Default split criterion for tree-based ensemble members.

---

**Entropy:**

$$
H = -\sum_{i=1}^C p_i \log_2 p_i
$$

Where:

- $p_i$ = class proportion
- $H = 0$ for a pure node; $H = \log_2 C$ for maximum uncertainty

Purpose: Measures the information content (uncertainty) at a decision tree node.

V1\_Bot: Alternative split criterion used in early hyperparameter sweeps.

---

**Information Gain:**

$$
IG = H(\text{parent}) - \sum_{j} \frac{n_j}{n}\, H(\text{child}_j)
$$

Where:

- $H(\text{parent})$ = entropy of the parent node
- $n_j / n$ = fraction of samples routed to child $j$
- $H(\text{child}_j)$ = entropy of child node $j$

Purpose: Quantifies the reduction in entropy achieved by a split; the feature-threshold pair maximizing $IG$ is selected.

V1\_Bot: Split selection metric in tree construction within the ensemble pipeline.

---

**Random Forest:**

$$
\hat{f}(x) = \frac{1}{B}\sum_{b=1}^B T_b(x)
$$

Where:

- $B$ = number of bootstrap-aggregated (bagged) trees
- $T_b$ = individual tree trained on a bootstrap sample with $m = \lfloor\sqrt{p}\rfloor$ randomly sampled candidate features per split
- Averaging reduces variance without increasing bias

Purpose: Combines many decorrelated decision trees to produce a low-variance ensemble prediction.

V1\_Bot: Feature importance extraction tool and baseline ensemble member in the Algo Engine.

---

**Gradient Boosting (sequential additive model):**

$$
f_m(x) = f_{m-1}(x) + \eta\, h_m(x)
$$

Where:

- $f_m$ = model at boosting iteration $m$
- $\eta \in (0, 1]$ = learning rate (shrinkage)
- $h_m$ = weak learner fitted to the negative gradient $-\nabla_{\hat{y}} \mathcal{L}(y, f_{m-1}(x))$

Purpose: Iteratively corrects residuals of the previous model by fitting each new tree to the gradient of the loss function.

V1\_Bot: Core training loop for LightGBM and XGBoost ensemble members.

---

**XGBoost Regularized Objective:**

$$
\mathcal{L}^{(t)} = \sum_{i=1}^n l(y_i, \hat{y}_i^{(t)}) + \sum_{k=1}^t \left[\gamma\, T_k + \frac{1}{2}\lambda \|w_k\|^2\right]
$$

Where:

- $l(\cdot)$ = differentiable convex loss
- $T_k$ = number of leaves in tree $k$
- $w_k$ = leaf weight vector
- $\gamma$ = minimum loss reduction for a split (complexity penalty)
- $\lambda$ = L2 regularization on leaf weights

Purpose: Balances predictive accuracy with model complexity via explicit regularization of tree structure and leaf weights.

V1\_Bot: Objective function for XGBoost hyperparameter tuning in Optuna sweeps.

---

**Second-Order Taylor Approximation (Newton boosting):**

$$
\mathcal{L}^{(t)} \approx \sum_{i=1}^n \left[g_i\, f_t(x_i) + \frac{1}{2}\,h_i\, f_t^2(x_i)\right] + \Omega(f_t)
$$

Where:

- $g_i = \partial \mathcal{L} / \partial \hat{y}_i^{(t-1)}$ = first-order gradient
- $h_i = \partial^2 \mathcal{L} / \partial (\hat{y}_i^{(t-1)})^2$ = second-order gradient (Hessian diagonal)
- $\Omega(f_t) = \gamma T + \frac{1}{2}\lambda\|w\|^2$

Purpose: Enables Newton-step optimization of the tree structure, giving XGBoost its speed and accuracy advantage over first-order gradient boosting.

V1\_Bot: Internal optimization used by XGBoost/LightGBM during tree construction in the Algo Engine ensemble pipeline.

---

### 9.3 Classification Metrics

**Accuracy:**

$$
\text{Accuracy} = \frac{TP + TN}{TP + TN + FP + FN}
$$

Where:

- $TP$ = true positives, $TN$ = true negatives, $FP$ = false positives, $FN$ = false negatives

Purpose: Measures overall correctness; unreliable for imbalanced datasets.

V1\_Bot: Reported but not used as primary optimization target due to class imbalance in trading labels.

---

**Precision:**

$$
\text{Precision} = \frac{TP}{TP + FP}
$$

Purpose: Measures the fraction of predicted positives that are actually positive; critical for controlling false trade signals.

V1\_Bot: Key metric for meta-labeling -- high precision means fewer losing trades are executed.

---

**Recall:**

$$
\text{Recall} = \frac{TP}{TP + FN}
$$

Purpose: Measures the fraction of actual positives that are correctly identified; controls missed opportunities.

V1\_Bot: Monitored alongside precision to ensure the system does not become overly conservative.

---

**F1-Score:**

$$
F_1 = 2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}
$$

Purpose: Harmonic mean of precision and recall; balances both error types in a single scalar.

V1\_Bot: Primary classification metric for model selection in the Algo Engine.

---

**Directional Accuracy:**

$$
DA = \frac{1}{n}\sum_{i=1}^n \mathbb{1}\!\left[\text{sign}(\hat{r}_i) = \text{sign}(r_i)\right]
$$

Where:

- $r_i$ = actual return in period $i$
- $\hat{r}_i$ = predicted return (or signal direction)
- $\mathbb{1}[\cdot]$ = indicator function

Purpose: Measures how often the model correctly predicts the direction of price movement, which is directly tied to trading profitability.

V1\_Bot: Core evaluation metric for all directional models in the ensemble (Doc 11).

---

**Confusion Matrix Interpretation:**

$$
\begin{pmatrix} TN & FP \\ FN & TP \end{pmatrix}
$$

Where:

- Rows = actual class, Columns = predicted class
- For 3-class triple barrier labels $\{-1, 0, +1\}$, extended to a $3 \times 3$ matrix

Purpose: Provides a complete picture of classification performance across all classes.

V1\_Bot: Logged to MLflow after every validation fold for audit and diagnostics (Doc 10).

---

### 9.4 Walk-Forward and Purged Cross-Validation

**Walk-Forward Validation:**

$$
\text{Train: } [0,\; t], \qquad \text{Test: } [t + g,\; t + g + h]
$$

Where:

- $t$ = end of training window
- $g$ = purge gap (embargo period removing overlapping samples)
- $h$ = test window length
- Window slides forward; no future information leaks into training

Purpose: Simulates realistic sequential deployment where models are trained on past data and evaluated on unseen future data.

V1\_Bot: Primary validation strategy for all models in the Algo Engine.

---

**Purged K-Fold Cross-Validation:**

Remove any training sample $i$ whose label span $[t_{s,i},\; t_{e,i}]$ overlaps with any test sample's label span.

$$
\text{Remove } i \text{ from train if } \exists\, j \in \text{test}: [t_{s,i}, t_{e,i}] \cap [t_{s,j}, t_{e,j}] \neq \emptyset
$$

Where:

- $[t_{s,i}, t_{e,i}]$ = start and end time of label $i$
- Overlap causes information leakage since labels depend on future prices

Purpose: Prevents leakage in cross-validation when labels span multiple time bars.

V1\_Bot: Implemented via `PurgedKFold` class in the Algo Engine validation module.

---

**Embargo Period:**

$$
\text{Embargo buffer} = [t_{e,\text{test\_end}},\; t_{e,\text{test\_end}} + \Delta_{\text{embargo}}]
$$

Where:

- $\Delta_{\text{embargo}}$ = additional time buffer after the last test sample
- Training samples in the embargo window are also removed

Purpose: Provides an extra safety margin beyond the purge to account for serial correlation in features.

V1\_Bot: Configurable parameter `embargo_pct` in the cross-validation configuration.

---

**Sample Uniqueness:**

$$
\bar{u}_i = \frac{1}{t_{e,i} - t_{s,i}} \sum_{t=t_{s,i}}^{t_{e,i}} \frac{1}{c_t}
$$

Where:

- $c_t$ = number of concurrent labels at time $t$ (labels whose span includes $t$)
- $\bar{u}_i \in (0, 1]$ = average uniqueness of sample $i$
- $\bar{u}_i = 1$ means no overlap with other labels

Purpose: Weights samples by their information content; highly overlapping samples are downweighted in training.

V1\_Bot: Sample weight computation for class-balanced, uniqueness-weighted training in all ensemble members.

---

### 9.5 Feature Scaling

**StandardScaler (Z-score normalization):**

$$
z = \frac{x - \mu}{\sigma}
$$

Where:

- $\mu$ = sample mean, $\sigma$ = sample standard deviation
- Output has mean 0 and unit variance

Purpose: Centers and scales features to prevent magnitude-driven dominance in gradient-based models.

V1\_Bot: Default scaler for model inputs in the normalization pipeline.

---

**MinMaxScaler:**

$$
z = \frac{x - x_{\min}}{x_{\max} - x_{\min}}
$$

Where:

- $x_{\min}, x_{\max}$ = observed minimum and maximum
- Output range $[0, 1]$

Purpose: Maps features to a bounded range; useful for models sensitive to absolute scale (e.g., sigmoid activations).

V1\_Bot: Applied to bounded features (e.g., RSI, oscillators) in the feature pipeline.

---

**RobustScaler:**

$$
z = \frac{x - \text{median}}{\text{IQR}}
$$

Where:

- $\text{median}$ = 50th percentile
- $\text{IQR} = Q_{75} - Q_{25}$ = interquartile range
- Robust to outliers since median and IQR are not influenced by extreme values

Purpose: Scales features using statistics that are resilient to outliers, common in financial data with fat tails.

V1\_Bot: Preferred scaler for price-derived features subject to flash crashes and gap events (Algo Engine).

---

**Winsorization:**

$$
x_{\text{winsor}} = \begin{cases} q_{\alpha} & \text{if } x < q_{\alpha} \\ q_{1-\alpha} & \text{if } x > q_{1-\alpha} \\ x & \text{otherwise} \end{cases}
$$

Where:

- $q_\alpha$ = lower $\alpha$-percentile, $q_{1-\alpha}$ = upper $(1-\alpha)$-percentile
- Typical $\alpha = 0.01$ (1st and 99th percentiles)

Purpose: Clips extreme values to percentile thresholds before scaling, preventing outliers from distorting normalization statistics.

V1\_Bot: Applied before all scalers in the preprocessing pipeline; configurable via `winsor_pct` parameter (Algo Engine).

---

### 9.6 Triple Barrier Labeling

**Upper Barrier (profit target):**

$$
u_t = P_t\!\left(1 + \mu\,\sigma_t\right)
$$

**Lower Barrier (stop loss):**

$$
l_t = P_t\!\left(1 - \lambda\,\sigma_t\right)
$$

**Vertical Barrier (time expiry):**

$$
T = t_0 + \Delta t
$$

**First Touch Time:**

$$
\tau = \min\!\left\{t : P_t \geq u_{t_0} \;\lor\; P_t \leq l_{t_0} \;\lor\; t = T\right\}
$$

**Label Assignment:**

$$
Y_i = \begin{cases} +1 & \text{if } P_\tau \geq u_{t_0} \quad \text{(profit target hit first)} \\ -1 & \text{if } P_\tau \leq l_{t_0} \quad \text{(stop loss hit first)} \\ \;\;\;0 & \text{if } \tau = T \quad \text{(time expiry)} \end{cases}
$$

Where:

- $P_t$ = asset price at time $t$
- $\sigma_t$ = rolling volatility estimate at time $t$
- $\mu$ = profit barrier multiplier (in volatility units)
- $\lambda$ = stop-loss barrier multiplier (in volatility units)
- $\Delta t$ = maximum holding period

Purpose: Transforms continuous price paths into discrete supervised learning labels that encode both direction and timing of trade outcomes.

V1\_Bot: Core labeling pipeline in the Algo Engine; barrier widths $\mu, \lambda$ are calibrated per volatility regime.

---

### 9.7 Meta-Labeling

**Primary Model Signal:**

The primary model produces a directional signal $S_t \in \{-1, +1\}$.

**Meta-Label Definition:**

$$
Z_t = \begin{cases} 1 & \text{if the primary model's prediction at } t \text{ is correct} \\ 0 & \text{otherwise} \end{cases}
$$

**Expected Strategy Value:**

$$
E[\text{Strategy}] = \text{Recall} \times \text{Precision} \times \text{BetSize}
$$

Where:

- Recall = fraction of profitable opportunities captured
- Precision = fraction of executed trades that are profitable
- BetSize = position size (scaled by meta-model confidence $\hat{Z}_t$)

Purpose: Decouples signal generation (direction) from signal filtering (confidence), allowing a secondary model to gate trade execution.

V1\_Bot: Confidence gating enhancement in the Algo Engine; the meta-model output $\hat{Z}_t$ directly scales position size.

---

### 9.8 Deflated Sharpe Ratio

**Expected Maximum Sharpe from $N$ Independent Trials:**

$$
E\!\left[\max SR_N\right] \approx \sqrt{2 \ln N}
$$

**Deflated Sharpe Ratio:**

$$
DSR = \frac{SR - E[\max SR_N]}{\sqrt{1 - \gamma_3 \cdot \text{Skew} + \frac{\gamma_4 - 1}{4}\cdot \text{Kurt}}}
$$

Where:

- $SR$ = observed Sharpe Ratio of the selected strategy
- $N$ = number of strategy variants tested (selection bias source)
- $\gamma_3$ = skewness adjustment coefficient
- $\gamma_4$ = kurtosis adjustment coefficient
- $\text{Skew}, \text{Kurt}$ = skewness and excess kurtosis of returns

**Rejection Rule:**

$$
\text{Reject strategy if } P(DSR > 0) < 0.95
$$

Purpose: Corrects the Sharpe Ratio for multiple testing bias and non-normality; a DSR that is not statistically significant indicates the observed performance may be due to overfitting.

V1\_Bot: Backtest validation gate -- strategies must pass the DSR test at the 95% confidence level before advancing to paper trading (Doc 11).

---

## Section 10: Advanced Model Architectures

### 10.1 LSTM Gate Equations

**Forget Gate:**

$$
f_t = \sigma\!\left(W_f [h_{t-1}, x_t] + b_f\right)
$$

**Input Gate:**

$$
i_t = \sigma\!\left(W_i [h_{t-1}, x_t] + b_i\right)
$$

**Candidate Cell State:**

$$
\tilde{C}_t = \tanh\!\left(W_C [h_{t-1}, x_t] + b_C\right)
$$

**Cell State Update:**

$$
C_t = f_t \odot C_{t-1} + i_t \odot \tilde{C}_t
$$

**Output Gate:**

$$
o_t = \sigma\!\left(W_o [h_{t-1}, x_t] + b_o\right)
$$

**Hidden State:**

$$
h_t = o_t \odot \tanh(C_t)
$$

Where:

- $x_t$ = input vector at time step $t$
- $h_{t-1}$ = previous hidden state
- $C_{t-1}$ = previous cell state
- $W_f, W_i, W_C, W_o$ = weight matrices for each gate
- $b_f, b_i, b_C, b_o$ = bias vectors
- $\sigma(\cdot)$ = sigmoid activation $\in (0, 1)$
- $\odot$ = element-wise (Hadamard) product

Purpose: Selectively remembers and forgets information over long sequences, solving the vanishing gradient problem that plagues vanilla RNNs.

V1\_Bot: BiLSTM ensemble member in the Algo Engine; processes temporal feature sequences for directional prediction.

---

**Bidirectional LSTM:**

$$
\overrightarrow{h_t} = \text{LSTM}_{\text{fwd}}(x_t, \overrightarrow{h_{t-1}}), \qquad \overleftarrow{h_t} = \text{LSTM}_{\text{bwd}}(x_t, \overleftarrow{h_{t+1}})
$$

$$
h_t^{\text{bi}} = [\overrightarrow{h_t} \;\|\; \overleftarrow{h_t}]
$$

Where:

- $\overrightarrow{h_t}$ = forward pass hidden state
- $\overleftarrow{h_t}$ = backward pass hidden state
- $\|$ = concatenation operator
- Output dimension = $2 \times d_h$ where $d_h$ is the LSTM hidden size

Purpose: Captures both past and future context in the sequence, improving representation quality for fixed-length input windows.

V1\_Bot: Default LSTM configuration in the ensemble; the backward pass leverages the full lookback window for richer feature extraction.

---

### 10.2 Transformer Self-Attention

**Scaled Dot-Product Attention:**

$$
\text{Attention}(Q, K, V) = \text{softmax}\!\left(\frac{QK^T}{\sqrt{d_k}}\right)V
$$

Where:

- $Q \in \mathbb{R}^{n \times d_k}$ = query matrix
- $K \in \mathbb{R}^{n \times d_k}$ = key matrix
- $V \in \mathbb{R}^{n \times d_v}$ = value matrix
- $d_k$ = key/query dimension
- $\sqrt{d_k}$ = scaling factor preventing softmax saturation for large $d_k$

Purpose: Computes a weighted sum of values where weights reflect the compatibility between queries and keys.

V1\_Bot: Core attention mechanism in the XAUTransformer primary model (Algo Engine).

---

**Multi-Head Attention:**

$$
\text{MultiHead}(Q, K, V) = \text{Concat}(\text{head}_1, \ldots, \text{head}_h)\, W^O
$$

$$
\text{head}_i = \text{Attention}(Q W_i^Q,\; K W_i^K,\; V W_i^V)
$$

Where:

- $h$ = number of attention heads
- $W_i^Q \in \mathbb{R}^{d_{\text{model}} \times d_k}$, $W_i^K \in \mathbb{R}^{d_{\text{model}} \times d_k}$, $W_i^V \in \mathbb{R}^{d_{\text{model}} \times d_v}$ = per-head projection matrices
- $W^O \in \mathbb{R}^{hd_v \times d_{\text{model}}}$ = output projection
- Each head attends to a different learned subspace

Purpose: Allows the model to jointly attend to information from different representation subspaces at different temporal positions.

V1\_Bot: Multi-head attention with $h = 8$ heads in XAUTransformer; each head specializes in different temporal patterns (e.g., short-term momentum, longer-term reversion).

---

**Positional Encoding:**

$$
PE_{(pos, 2i)} = \sin\!\left(\frac{pos}{10000^{2i/d}}\right), \qquad PE_{(pos, 2i+1)} = \cos\!\left(\frac{pos}{10000^{2i/d}}\right)
$$

Where:

- $pos$ = position index in the sequence
- $i$ = dimension index
- $d$ = model dimension ($d_{\text{model}}$)
- Sinusoidal encoding allows the model to extrapolate to unseen sequence lengths

Purpose: Injects temporal ordering information into the permutation-invariant attention mechanism.

V1\_Bot: Added to input embeddings in the XAUTransformer to encode the temporal position of each time bar in the lookback window.

---

**Layer Normalization:**

$$
\text{LN}(x) = \gamma \cdot \frac{x - \mu}{\sqrt{\sigma^2 + \epsilon}} + \beta
$$

Where:

- $\mu, \sigma^2$ = mean and variance computed across the feature dimension for a single sample
- $\gamma, \beta$ = learned scale and shift parameters
- $\epsilon$ = small constant for numerical stability

Purpose: Stabilizes training by normalizing activations within each sample, independent of batch size.

V1\_Bot: Applied after every attention and feed-forward sub-layer in the XAUTransformer (pre-norm architecture).

---

### 10.3 Temporal Fusion Transformer (TFT)

**Gated Linear Unit (GLU):**

$$
\text{GLU}(x) = \sigma(W_1 x + b_1) \odot (W_2 x + b_2)
$$

Where:

- $W_1, W_2$ = weight matrices, $b_1, b_2$ = biases
- $\sigma(\cdot)$ = sigmoid gate controlling information flow
- $\odot$ = element-wise product

Purpose: Provides a learnable gating mechanism that suppresses irrelevant inputs.

V1\_Bot: Building block of all GRN modules within the TFT candidate architecture (Concept 03).

---

**Gated Residual Network (GRN):**

$$
\text{GRN}(x) = \text{LayerNorm}\!\left(x + \text{GLU}\!\left(\text{ELU}(W_{\text{in}}\, x + b_{\text{in}})\right)\right)
$$

Where:

- $\text{ELU}(\cdot)$ = exponential linear unit activation
- The residual connection ($x + \cdots$) preserves gradient flow
- LayerNorm stabilizes the output

Purpose: Non-linear transformation with skip connections and gating, forming the core processing unit of the TFT.

V1\_Bot: Feature processing module in the TFT candidate for advanced probabilistic forecasting (Concept 03).

---

**Variable Selection Network:**

$$
v_{t,j} = \text{softmax}(\tilde{v}_{t,j}), \qquad \tilde{x}_t = \sum_{j=1}^J v_{t,j} \cdot \text{GRN}_j(x_{t,j})
$$

Where:

- $v_{t,j}$ = selection weight for feature $j$ at time $t$
- $\tilde{v}_{t,j}$ = raw logit from a context-aware GRN
- $\text{GRN}_j$ = per-feature gated residual network
- $\tilde{x}_t$ = weighted combination of transformed features

Purpose: Learns to dynamically weight input features based on the current context, providing instance-wise feature importance.

V1\_Bot: Provides interpretable per-feature attention weights; enables real-time feature contribution monitoring in the dashboard (Concept 03, Doc 10).

---

**Quantile Loss (Pinball Loss):**

$$
\mathcal{L} = \sum_{\tau \in \mathcal{T}} \max\!\left(\tau(y - \hat{y}^{(\tau)}),\; (1 - \tau)(\hat{y}^{(\tau)} - y)\right)
$$

Where:

- $\tau \in (0, 1)$ = quantile level (e.g., $\tau \in \{0.1, 0.5, 0.9\}$)
- $\hat{y}^{(\tau)}$ = predicted $\tau$-quantile
- $y$ = observed value
- Asymmetric penalty: underestimation penalized by $\tau$, overestimation by $(1-\tau)$

Purpose: Trains probabilistic models to output prediction intervals rather than point estimates.

V1\_Bot: Loss function for the TFT's multi-horizon probabilistic forecasts; quantile outputs feed directly into risk-adjusted position sizing (Concept 03).

---

### 10.4 Dilated Causal Convolutions

**Standard 1D Convolution:**

$$
(f * g)(t) = \sum_{k=0}^{K-1} f(k) \cdot g(t - k)
$$

**Dilated Convolution (dilation factor $d$):**

$$
(f *_d g)(t) = \sum_{k=0}^{K-1} f(k) \cdot g(t - d \cdot k)
$$

Where:

- $K$ = kernel size
- $d$ = dilation factor (skips $d-1$ inputs between taps)
- Standard convolution is the special case $d = 1$

Purpose: Expands the receptive field exponentially with depth without increasing parameter count, enabling efficient long-range temporal modeling.

V1\_Bot: Dilated CNN ensemble member processes multi-scale temporal patterns in the lookback window.

---

**Receptive Field:**

$$
R = 1 + \sum_{l=1}^L (K_l - 1) \cdot d_l
$$

Where:

- $L$ = number of convolutional layers
- $K_l$ = kernel size at layer $l$
- $d_l$ = dilation factor at layer $l$ (typically $d_l = 2^{l-1}$)

Purpose: Computes the total number of input time steps that influence a single output, guiding architecture design to match the desired lookback horizon.

V1\_Bot: Architecture constraint -- receptive field $R$ must equal or exceed the lookback window length configured for the model.

---

**Causal Padding:**

$$
g_{\text{causal}}(t) = \begin{cases} g(t) & \text{if } t \geq 0 \\ 0 & \text{if } t < 0 \end{cases}
$$

Purpose: Ensures the convolution output at time $t$ depends only on inputs at times $\leq t$, preventing future information leakage.

V1\_Bot: Enforced in all convolutional layers to maintain temporal causality during computation.

---

**WaveNet Gated Activation:**

$$
z = \tanh(W_f * x) \odot \sigma(W_g * x)
$$

Where:

- $W_f$ = filter convolution weights
- $W_g$ = gate convolution weights
- $\tanh(\cdot)$ = filter output (candidate values)
- $\sigma(\cdot)$ = gate output (controls information flow)
- $*$ = dilated causal convolution operator

Purpose: Combines a tanh filter with a sigmoid gate to model complex temporal distributions, as introduced in WaveNet.

V1\_Bot: Activation function in the dilated CNN ensemble member; improves modeling of non-linear price dynamics.

---

### 10.5 Domain Adversarial Networks (DANN)

**Architecture Components:**

$$
G_f: x \to z \qquad \text{(Feature Extractor)}
$$

$$
G_y: z \to \hat{y} \qquad \text{(Label Predictor)}
$$

$$
G_d: z \to \hat{d} \qquad \text{(Domain Discriminator)}
$$

**Minimax Objective:**

$$
\min_{G_f, G_y} \max_{G_d} \;\mathcal{L}_y\!\left(G_y(G_f(x)),\, y\right) - \lambda\,\mathcal{L}_d\!\left(G_d(G_f(x)),\, d\right)
$$

Where:

- $x$ = input features
- $z = G_f(x)$ = domain-invariant feature representation
- $y$ = task label (e.g., trade direction)
- $d$ = domain label (e.g., volatility regime: low/medium/high)
- $\lambda$ = domain adaptation trade-off parameter
- $\mathcal{L}_y$ = task loss (cross-entropy for classification)
- $\mathcal{L}_d$ = domain discrimination loss

Purpose: Forces the feature extractor to learn representations that are predictive of the task but invariant to the domain (regime), improving generalization across market conditions.

V1\_Bot: Regime-robust feature learning -- the DANN trains features that perform consistently across detected volatility regimes (Concept 03).

---

**Gradient Reversal Layer (GRL):**

$$
\text{Forward: } \text{GRL}(z) = z
$$

$$
\text{Backward: } \frac{\partial \mathcal{L}}{\partial z}\bigg|_{\text{GRL}} = -\lambda \cdot \frac{\partial \mathcal{L}_d}{\partial z}
$$

Where:

- During forward pass, the GRL is an identity operation
- During backward pass, it multiplies the gradient by $-\lambda$, reversing the direction
- This adversarial gradient forces $G_f$ to produce features that confuse the domain discriminator

Purpose: Implements the adversarial training without requiring alternating optimization; a single backward pass updates all components simultaneously.

V1\_Bot: Inserted between the shared feature extractor and domain discriminator head during DANN training (Concept 03).

---

### 10.6 Loss Functions for Financial Objectives

**Standard Cross-Entropy:**

$$
\mathcal{L}_{CE} = -\sum_{i=1}^C y_i \log \hat{y}_i
$$

Where:

- $C$ = number of classes
- $y_i$ = one-hot encoded true label
- $\hat{y}_i$ = predicted probability for class $i$

Purpose: Standard classification loss; penalizes confident wrong predictions heavily.

V1\_Bot: Default training loss for multi-class triple barrier label prediction.

---

**Focal Loss:**

$$
\mathcal{L}_{FL} = -\alpha_t (1 - p_t)^\gamma \log(p_t)
$$

Where:

- $p_t$ = predicted probability for the true class
- $\alpha_t$ = class balancing weight
- $\gamma \geq 0$ = focusing parameter ($\gamma = 0$ recovers standard cross-entropy)
- $(1-p_t)^\gamma$ = modulating factor that downweights easy (well-classified) examples

Purpose: Addresses class imbalance by focusing training on hard-to-classify examples.

V1\_Bot: Applied when the triple barrier label distribution is highly skewed (e.g., many $Y=0$ neutral labels); configured with $\gamma = 2.0$.

---

**Differentiable Sharpe Ratio:**

$$
SR_T = \frac{\bar{R}}{\sqrt{\overline{R^2} - \bar{R}^2}}
$$

Where:

- $\bar{R} = \frac{1}{T}\sum_{t=1}^T R_t$ = mean return
- $\overline{R^2} = \frac{1}{T}\sum_{t=1}^T R_t^2$ = mean squared return
- Gradient computed via autograd through the return sequence
- $R_t = w_t \cdot r_t - c|\Delta w_t|$ with transaction costs

Purpose: Directly optimizes the risk-adjusted return metric rather than a proxy loss, aligning the training objective with the evaluation metric.

V1\_Bot: Alternative training objective for end-to-end models that output position weights; gradient flows through the Sharpe computation (Concept 04).

---

**Hubris Loss (Confidence Calibration):**

$$
\mathcal{L}_{\text{hubris}} = \text{MSE}(P_{\text{pred}}, P_{\text{true}}) + \lambda\!\left(\text{Confidence} - \text{Accuracy}\right)^2
$$

Where:

- $\text{MSE}(P_{\text{pred}}, P_{\text{true}})$ = standard prediction error
- $\text{Confidence}$ = average predicted probability of the chosen class
- $\text{Accuracy}$ = actual fraction correct
- $\lambda$ = calibration penalty weight

Purpose: Penalizes models that are systematically overconfident (or underconfident), producing well-calibrated probability outputs.

V1\_Bot: Training objective for models feeding into the confidence gating system, ensuring predicted probabilities are reliable for position sizing (Algo Engine).

---

### 10.7 Graph-Based Models

**Graph Convolutional Network (GCN):**

$$
H^{(l+1)} = \sigma\!\left(\tilde{D}^{-1/2}\,\tilde{A}\,\tilde{D}^{-1/2}\,H^{(l)}\,W^{(l)}\right)
$$

Where:

- $\tilde{A} = A + I$ = adjacency matrix with self-loops
- $A$ = original adjacency matrix of the graph
- $I$ = identity matrix (adds self-connections)
- $\tilde{D}$ = degree matrix of $\tilde{A}$ ($\tilde{D}_{ii} = \sum_j \tilde{A}_{ij}$)
- $H^{(l)} \in \mathbb{R}^{n \times d_l}$ = node feature matrix at layer $l$
- $W^{(l)} \in \mathbb{R}^{d_l \times d_{l+1}}$ = trainable weight matrix
- $\sigma(\cdot)$ = activation function (e.g., ReLU)
- $\tilde{D}^{-1/2}\tilde{A}\tilde{D}^{-1/2}$ = symmetric normalization preventing scale issues

Purpose: Propagates and aggregates node features along graph edges, learning representations that capture network topology.

V1\_Bot: Crypto network topology analysis -- nodes represent tokens, edges represent on-chain transfer volumes or correlation (Concept 10).

---

**Graph Attention Network (GAT):**

$$
\alpha_{ij} = \frac{\exp\!\left(\text{LeakyReLU}\!\left(a^T [W h_i \| W h_j]\right)\right)}{\sum_{k \in \mathcal{N}_i} \exp\!\left(\text{LeakyReLU}\!\left(a^T [W h_i \| W h_k]\right)\right)}
$$

Where:

- $h_i, h_j$ = feature vectors of nodes $i$ and $j$
- $W$ = shared linear transformation weight matrix
- $a$ = attention weight vector
- $\|$ = concatenation
- $\mathcal{N}_i$ = neighborhood of node $i$ (including self)
- $\alpha_{ij}$ = attention coefficient (importance of node $j$ to node $i$)

Purpose: Learns adaptive, asymmetric edge weights via attention, allowing the model to focus on the most relevant neighbors.

V1\_Bot: Attention-weighted crypto token relationship graph; attention weights provide interpretable token influence scores (Concept 10).

---

**EvolveGCN (Dynamic Graph):**

$$
W_t = \text{GRU}(W_{t-1}, G_t)
$$

Where:

- $W_t$ = GCN weight matrix at time $t$
- $W_{t-1}$ = previous weight matrix
- $G_t$ = graph snapshot at time $t$
- GRU evolves the GCN parameters to track temporal changes in graph structure

Purpose: Adapts GCN weights over time as the graph topology evolves, capturing dynamic relationships without retraining.

V1\_Bot: Tracks evolving crypto token correlations and on-chain transfer patterns over time (Concept 10).

---

## Section 11: Optimization Methods for Trading

### 11.1 MDP Formulation for Trading

**State Space:**

$$
s_t = \left[\text{features}_t,\; \text{position}_t,\; \text{equity}_t\right]
$$

Where:

- $\text{features}_t$ = market feature vector at time $t$ (technical indicators, model outputs, microstructure signals)
- $\text{position}_t$ = current portfolio position (e.g., number of lots, direction)
- $\text{equity}_t$ = current account equity

Purpose: Encodes the full information set available to the agent at each decision point.

V1\_Bot: State vector construction in the RL environment wrapper (Concept 04).

---

**Action Space:**

$$
a_t \in [-1, 1] \quad \text{(continuous)} \qquad \text{or} \qquad a_t \in \{BUY, SELL, HOLD\} \quad \text{(discrete)}
$$

Where:

- Continuous: $a_t$ = target portfolio weight (short to long)
- Discrete: simplified action set for DQN-based agents
- Transaction costs are applied on $|\Delta a_t| = |a_t - a_{t-1}|$

Purpose: Defines the set of decisions available to the agent at each time step.

V1\_Bot: Continuous action space for SAC agent; discrete action space for DQN ensemble member (Concept 04,).

---

**Reward Function:**

$$
r_t = D_t - \lambda |\Delta w_t|
$$

Where:

- $D_t$ = Differential Sharpe Ratio (Section 11.4)
- $\lambda$ = transaction cost penalty coefficient
- $|\Delta w_t|$ = absolute change in portfolio weight (turnover)
- Raw PnL is NOT used as reward due to non-stationarity and scale dependence

Purpose: Provides a risk-adjusted, scale-invariant reward signal that penalizes excessive trading.

V1\_Bot: Step reward function in the RL training loop; $\lambda$ is calibrated to match realistic broker transaction costs (Concept 04).

---

**Transition Dynamics:**

$$
s_{t+1} = T(s_t, a_t, \text{market}_{t+1})
$$

Where:

- $T$ = transition function (deterministic given market realization)
- $\text{market}_{t+1}$ = next market state (exogenous, stochastic)
- The agent cannot influence market prices (price-taker assumption)

Purpose: Defines how the environment evolves in response to the agent's actions and market dynamics.

V1\_Bot: Environment step function in the OpenAI Gym-compatible trading environment (Concept 04).

---

**Objective:**

$$
\max_\pi \; E\!\left[\sum_{t=0}^T \gamma^t r_t\right]
$$

Where:

- $\pi$ = policy mapping states to actions
- $\gamma \in [0, 1)$ = discount factor
- $T$ = episode length (trading horizon)

Purpose: The agent seeks a policy that maximizes expected cumulative discounted reward over the trading horizon.

V1\_Bot: Optimization objective for all RL agents; $\gamma = 0.99$ for daily trading, $\gamma = 0.95$ for intraday (Concept 04).

---

### 11.2 Q-Learning and DQN

**Q-Value Function:**

$$
Q(s, a) = E\!\left[\sum_{k=0}^{\infty} \gamma^k r_{t+k} \;\middle|\; s_t = s,\, a_t = a\right]
$$

Where:

- $Q(s, a)$ = expected cumulative discounted reward starting from state $s$, taking action $a$, and following the optimal policy thereafter

Purpose: Quantifies the long-term value of taking action $a$ in state $s$.

V1\_Bot: Value function approximation in the DQN ensemble member.

---

**Bellman Optimality Equation:**

$$
Q^*(s, a) = r + \gamma \max_{a'} Q^*(s', a')
$$

Where:

- $Q^*$ = optimal Q-function
- $s'$ = next state after taking action $a$ in state $s$
- $\max_{a'}$ = greedy action selection in the next state

Purpose: Recursive definition of the optimal Q-function; the foundation of all value-based RL methods.

V1\_Bot: Target computation in DQN training (Concept 04).

---

**DQN Loss (with target network):**

$$
\mathcal{L} = E\!\left[\left(r + \gamma \max_{a'} Q_{\bar{\theta}}(s', a') - Q_\theta(s, a)\right)^2\right]
$$

Where:

- $Q_\theta$ = online Q-network with parameters $\theta$
- $Q_{\bar{\theta}}$ = target Q-network with frozen parameters $\bar{\theta}$
- Target network is updated periodically: $\bar{\theta} \leftarrow \theta$ every $N$ steps

Purpose: Stabilizes training by decoupling the target from the online network, preventing oscillation.

V1\_Bot: DQN training loss with target network update frequency $N = 1000$ steps.

---

**Double DQN:**

$$
Q_{\text{target}} = r + \gamma\, Q_{\bar{\theta}}\!\left(s',\, \arg\max_{a'} Q_\theta(s', a')\right)
$$

Where:

- Action selection uses the online network $Q_\theta$
- Action evaluation uses the target network $Q_{\bar{\theta}}$
- Decoupling reduces overestimation bias inherent in standard DQN

Purpose: Mitigates the maximization bias of standard DQN by separating action selection from value estimation.

V1\_Bot: Default DQN variant used in the ensemble.

---

**Dueling DQN:**

$$
Q(s, a) = V(s) + A(s, a) - \frac{1}{|\mathcal{A}|}\sum_{a'} A(s, a')
$$

Where:

- $V(s)$ = state value function (how good is this state regardless of action)
- $A(s, a)$ = advantage function (relative benefit of action $a$ over the average)
- Mean subtraction ensures identifiability

Purpose: Decomposes Q-values into state value and action advantage, improving learning efficiency when many actions have similar values.

V1\_Bot: Architecture variant tested in DQN hyperparameter sweeps (Concept 04).

---

### 11.3 Soft Actor-Critic (SAC)

**Entropy-Regularized Objective:**

$$
J(\pi) = \sum_{t=0}^T E\!\left[r_t + \alpha\, \mathcal{H}\!\left(\pi(\cdot | s_t)\right)\right]
$$

Where:

- $\mathcal{H}(\pi(\cdot|s_t)) = -E_\pi[\log\pi(a|s_t)]$ = entropy of the policy at state $s_t$
- $\alpha > 0$ = temperature parameter controlling the exploration-exploitation trade-off
- Higher $\alpha$ encourages more exploration (more random policy)

Purpose: Maximizes expected return while maintaining high entropy, promoting robust exploration and preventing premature convergence to suboptimal deterministic policies.

V1\_Bot: Primary RL algorithm for continuous portfolio allocation; entropy regularization prevents the agent from converging to a trivially always-long policy (Concept 04).

---

**Reparameterized Policy (squashed Gaussian):**

$$
a_t = \tanh\!\left(\mu_\phi(s_t) + \sigma_\phi(s_t) \odot \epsilon\right), \qquad \epsilon \sim \mathcal{N}(0, I)
$$

Where:

- $\mu_\phi(s_t)$ = mean output of the policy network
- $\sigma_\phi(s_t)$ = standard deviation output
- $\tanh(\cdot)$ squashes the output to $[-1, 1]$
- Reparameterization trick enables gradient flow through the stochastic sampling

Purpose: Produces bounded continuous actions with a differentiable sampling procedure.

V1\_Bot: SAC policy network outputs position weights $\in [-1, 1]$ representing short-to-long allocation (Concept 04).

---

**Twin Q-Network Loss:**

$$
\mathcal{L}_Q = E\!\left[\left(Q_\theta(s, a) - \left(r + \gamma\, V_{\bar{\psi}}(s')\right)\right)^2\right]
$$

Where:

- Two Q-networks $Q_{\theta_1}, Q_{\theta_2}$ are trained independently
- $V_{\bar{\psi}}(s') = \min(Q_{\theta_1}, Q_{\theta_2}) - \alpha\log\pi(a'|s')$ = soft state value
- Taking the minimum of two Q-estimates reduces overestimation

Purpose: Mitigates Q-value overestimation by maintaining two independent critics.

V1\_Bot: Twin critic architecture in SAC training; both critics must agree before a trade signal is acted upon (Concept 04).

---

**Polyak (Soft) Target Updates:**

$$
\bar{\psi} \leftarrow \tau\,\psi + (1 - \tau)\,\bar{\psi}
$$

Where:

- $\psi$ = current value network parameters
- $\bar{\psi}$ = target value network parameters
- $\tau \ll 1$ = soft update coefficient (typically $\tau = 0.005$)

Purpose: Smoothly updates the target network, providing a stable training target without abrupt parameter changes.

V1\_Bot: Polyak averaging with $\tau = 0.005$ in the SAC training loop (Concept 04).

---

### 11.4 Differential Sharpe Ratio Reward

**Exponential Moving Average of Returns:**

$$
A_t = A_{t-1} + \eta(R_t - A_{t-1})
$$

**Exponential Moving Average of Squared Returns:**

$$
B_t = B_{t-1} + \eta(R_t^2 - B_{t-1})
$$

**Differential Sharpe Ratio:**

$$
D_t = \frac{B_{t-1}\,\Delta A_t - \frac{1}{2}\,A_{t-1}\,\Delta B_t}{(B_{t-1} - A_{t-1}^2)^{3/2}}
$$

Where:

- $R_t$ = portfolio return at time $t$
- $\eta \in (0, 1)$ = EMA decay rate
- $\Delta A_t = A_t - A_{t-1}$, $\Delta B_t = B_t - B_{t-1}$
- $D_t$ = marginal contribution of the current return to the running Sharpe Ratio

Purpose: Provides an instantaneous, differentiable reward signal that reflects the current action's contribution to the cumulative risk-adjusted performance.

V1\_Bot: Step reward function replacing raw PnL in all RL training environments; $\eta = 0.01$ by default (Concept 04).

---

**Reward with Transaction Costs:**

$$
r_t = D_t - \lambda\,|\Delta w_t|
$$

Where:

- $\Delta w_t = w_t - w_{t-1}$ = change in portfolio weight
- $\lambda$ = transaction cost coefficient (calibrated to broker spreads + commissions)

Purpose: Penalizes portfolio turnover, encouraging the agent to trade only when the expected improvement in Sharpe exceeds the cost.

V1\_Bot: Final reward signal combining risk-adjusted return with realistic execution costs (Concept 04).

---

### 11.5 Domain Randomization for Robust RL

**Latency Randomization:**

$$
k \sim \text{Poisson}(\lambda_{\text{lat}})
$$

Where:

- $k$ = number of steps of execution delay
- $\lambda_{\text{lat}}$ = expected latency in steps
- The agent's action $a_t$ is applied at time $t + k$ instead of $t$

Purpose: Trains the agent to be robust to variable execution latency encountered in live trading.

V1\_Bot: Applied during RL training environment episodes; $\lambda_{\text{lat}}$ calibrated to observed MT5 bridge latency distribution (Concept 04).

---

**Slippage Randomization:**

$$
P_{\text{exec}} = P_t(1 \pm \delta), \qquad \delta \sim \mathcal{U}(0, \delta_{\max})
$$

Where:

- $P_{\text{exec}}$ = actual execution price
- $P_t$ = theoretical mid-price at time $t$
- $\delta$ = random slippage fraction
- $\delta_{\max}$ = maximum slippage (calibrated to historical fill data)

Purpose: Simulates realistic price impact and slippage during training.

V1\_Bot: Slippage injection in the RL training environment; $\delta_{\max}$ set per instrument from historical execution analysis (Concept 04, Doc 08).

---

**Adversarial Market Agent:**

$$
\min_{\pi_{\text{trader}}} \max_{\pi_{\text{adv}}} E[R]
$$

Where:

- $\pi_{\text{trader}}$ = trading agent's policy
- $\pi_{\text{adv}}$ = adversarial agent that perturbs market conditions
- The adversary injects worst-case noise into prices, spreads, and liquidity

Purpose: Produces a minimax-robust trading policy that performs well even under adversarial market conditions.

V1\_Bot: Robustness hardening step before live deployment; the adversary is trained to exploit the trader's weaknesses (Concept 04).

---

## Section 12: Market Microstructure Mathematics

### 12.1 VPIN (Volume-Synchronized Probability of Informed Trading)

**Tick Rule Classification:**

$$
b_t = \text{sign}(P_t - P_{t-1})
$$

Where:

- $b_t \in \{-1, +1\}$ = trade direction indicator (sell or buy)
- Trades at zero tick change inherit the previous classification

**VPIN Formula:**

$$
\text{VPIN} = \frac{\sum_{\tau=1}^n |V_\tau^B - V_\tau^S|}{nV}
$$

Where:

- $V_\tau^B$ = buy volume in volume bucket $\tau$
- $V_\tau^S$ = sell volume in volume bucket $\tau$
- $V$ = bucket size (fixed volume per bucket)
- $n$ = number of buckets in the estimation window
- VPIN $\in [0, 1]$; high values indicate order flow toxicity

Purpose: Estimates the probability of informed trading in real-time using volume-bucketed data, without requiring trade-level buyer/seller identification.

V1\_Bot: Order flow toxicity feature computed on tick data and fed as a real-time input to the Algo Engine.

---

### 12.2 Order Book Imbalance (OBI)

**Level 1 Order Book Imbalance:**

$$
\rho_t = \frac{q_t^b - q_t^a}{q_t^b + q_t^a}
$$

Where:

- $q_t^b$ = bid-side quantity at the best bid
- $q_t^a$ = ask-side quantity at the best ask
- $\rho_t \in [-1, 1]$; positive indicates bid-heavy (buying pressure)

Purpose: Measures the directional pressure at the top of the order book.

V1\_Bot: Real-time microstructure feature streamed from the data ingestion service (Concept 02, STRATEGY\_NOTES.md).

---

**Weighted Multi-Level Depth Imbalance:**

$$
\rho_{W,t} = \sum_{i=1}^L \frac{1}{\ln(i+1)} \cdot \frac{q_{t,i}^b - q_{t,i}^a}{q_{t,i}^b + q_{t,i}^a}
$$

Where:

- $L$ = number of price levels considered
- $i$ = price level index (1 = best bid/ask, 2 = second level, etc.)
- $1/\ln(i+1)$ = logarithmic decay weight giving more importance to levels closer to the mid-price

Purpose: Extends the imbalance measure across multiple order book levels, weighting closer levels more heavily.

V1\_Bot: Multi-level depth feature for microstructure-aware models (Concept 02).

---

**Spread Cost (in basis points):**

$$
\text{Spread}_t = \frac{A_t - B_t}{\text{Mid}_t} \times 10000
$$

Where:

- $A_t$ = best ask price
- $B_t$ = best bid price
- $\text{Mid}_t = (A_t + B_t)/2$ = mid-price
- Result in basis points (bps)

Purpose: Quantifies the round-trip cost of crossing the spread, a key component of transaction cost analysis.

V1\_Bot: Spread cost feature and execution cost input for position sizing and trade filtering (Concept 02, Doc 09).

---

### 12.3 Kyle's Lambda (Price Impact)

$$
\Delta P_t = \alpha + \lambda_K \cdot \text{OFI}_t + \epsilon_t
$$

Where:

- $\Delta P_t$ = price change over interval
- $\lambda_K$ = Kyle's lambda (price impact coefficient, in price units per unit of order flow)
- $\text{OFI}_t = \sum_k V_k \cdot \text{sign}(k)$ = order flow imbalance (signed volume)
- $\alpha$ = intercept, $\epsilon_t$ = residual

Purpose: Estimates the permanent price impact per unit of order flow; higher $\lambda_K$ indicates lower liquidity.

V1\_Bot: Liquidity estimation feature for dynamic position sizing -- high $\lambda_K$ triggers reduced position sizes (Concept 08).

---

### 12.4 Hawkes Processes

**Conditional Intensity:**

$$
\lambda(t) = \mu + \int_{-\infty}^{t} \phi(t - u)\, dN(u)
$$

Where:

- $\lambda(t)$ = event arrival rate at time $t$
- $\mu$ = baseline (exogenous) intensity
- $\phi(\cdot)$ = triggering kernel (how past events excite future events)
- $N(u)$ = counting process of events up to time $u$

Purpose: Models self-exciting point processes where the occurrence of an event increases the probability of subsequent events.

V1\_Bot: Flash crash detection -- a spike in $\lambda(t)$ indicates event clustering and triggers risk escalation (Concept 08).

---

**Exponential Triggering Kernel:**

$$
\phi(t) = \alpha\, e^{-\beta t}
$$

Where:

- $\alpha > 0$ = excitation magnitude (how much each event boosts the intensity)
- $\beta > 0$ = decay rate (how quickly the excitation fades)
- $\alpha/\beta$ = branching ratio $n$ (expected number of offspring per event)

Purpose: Parsimonious two-parameter kernel capturing the empirical observation that event clustering decays exponentially.

V1\_Bot: Kernel parameters estimated in real-time from trade and order arrival data (Concept 08).

---

**Branching Ratio (Stability Condition):**

$$
n = \frac{\alpha}{\beta} < 1
$$

Where:

- $n < 1$ ensures the process is stationary (sub-critical)
- $n \geq 1$ implies explosive behavior (super-critical regime)
- $n$ close to 1 indicates near-critical dynamics (cascade risk)

Purpose: Determines whether the self-excitation is stable or approaching a critical regime where cascading events may occur.

V1\_Bot: When $n \to 1$, the system raises a flash crash warning and tightens risk limits (Concept 08, Doc 09).

---

**Multivariate Hawkes Process:**

$$
\lambda_i(t) = \mu_i + \sum_{j=1}^D \int_{-\infty}^{t} \phi_{ij}(t - u)\, dN_j(u)
$$

Where:

- $D$ = number of event types (e.g., buys, sells, cancellations)
- $\phi_{ij}$ = cross-excitation kernel (event type $j$ exciting type $i$)
- Diagonal terms $\phi_{ii}$ = self-excitation; off-diagonal = cross-excitation

Purpose: Captures the mutual excitation structure between different event types in the order book.

V1\_Bot: Multi-dimensional event model tracking buy/sell/cancel interactions for microstructure analysis (Concept 08).

---

### 12.5 Transient Impact (Propagator Model)

**Price Impact Propagation:**

$$
P_t = P_0 + \sum_{t' < t} G(t - t')\, \epsilon_{t'}\, V_{t'}^\gamma
$$

Where:

- $G(\tau)$ = propagator (decay kernel) measuring how impact persists over time
- $\epsilon_{t'} \in \{-1, +1\}$ = trade sign at time $t'$
- $V_{t'}$ = trade volume at time $t'$
- $\gamma$ = volume exponent (typically $\gamma \approx 0.5$, square-root law)

Purpose: Models how past trades' price impact decays over time, distinguishing transient from permanent impact.

V1\_Bot: Execution cost modeling for optimizing trade scheduling (Concept 08).

---

**Power-Law Decay Kernel:**

$$
G(\tau) = \frac{C}{(1 + \tau/\tau_0)^\beta}
$$

Where:

- $C$ = impact scale factor
- $\tau_0$ = characteristic time scale
- $\beta$ = decay exponent (empirically $\beta \approx 0.5$ for equities)
- Slow power-law decay implies long-lived transient impact

Purpose: Captures the empirical observation that price impact decays as a power law, not exponentially.

V1\_Bot: Propagator kernel calibrated to XAUUSD tick data for execution simulation (Concept 08).

---

**Cross-Asset Impact:**

$$
P_j(t) = \sum_{k} \int_{-\infty}^{t} G_{jk}(t - s)\, dQ_k(s)
$$

Where:

- $P_j(t)$ = price of asset $j$ at time $t$
- $G_{jk}$ = cross-impact propagator (trading asset $k$ affects price of asset $j$)
- $dQ_k(s)$ = signed order flow in asset $k$ at time $s$

Purpose: Models how trading in one asset (e.g., gold futures) impacts the price of a related asset (e.g., XAUUSD spot).

V1\_Bot: Cross-impact estimation for correlated instrument execution in multi-asset strategies (Concept 08).

---

### 12.6 Almgren-Chriss Optimal Execution

**Temporary Impact:**

$$
h(v) = \epsilon\,\text{sgn}(v) + \eta\,|v|
$$

Where:

- $v$ = trading rate (shares per unit time)
- $\epsilon$ = fixed cost component (half-spread)
- $\eta$ = linear temporary impact coefficient
- $h(v)$ = price displacement that reverts after execution

Purpose: Models the immediate, transient price impact proportional to trading speed.

V1\_Bot: Temporary impact parameters calibrated from historical XAUUSD execution data (Concept 05).

---

**Permanent Impact:**

$$
g(v) = \gamma_p\, v
$$

Where:

- $\gamma_p$ = permanent impact coefficient
- $v$ = trading rate
- Permanent impact shifts the price level irreversibly

Purpose: Models the lasting information content of trades that permanently moves the equilibrium price.

V1\_Bot: Permanent impact estimate fed into the execution optimizer (Concept 05).

---

**Implementation Shortfall (Expected Cost):**

$$
E[C] = \sum_{k=1}^N \tau\, v_k \left(\frac{1}{2}\gamma_p\,\tau\, v_k + \eta\, v_k\right)
$$

Where:

- $N$ = number of time intervals
- $\tau$ = interval length
- $v_k$ = trading rate in interval $k$
- $\gamma_p\tau v_k / 2$ = permanent impact cost, $\eta v_k$ = temporary impact cost

Purpose: Computes the expected total execution cost (shortfall relative to arrival price) for a given trading schedule.

V1\_Bot: Objective function minimized by the execution algorithm (Concept 05).

---

**Optimal Trading Trajectory:**

$$
v_k^* = \frac{\sinh\!\left(\kappa(T - t_k)\right)}{\sinh(\kappa T)}\, X
$$

Where:

- $X$ = total shares to execute
- $T$ = execution horizon
- $t_k$ = time of interval $k$
- $\kappa \propto \sqrt{\lambda_{\text{risk}}\,\sigma^2 / \eta}$
- $\lambda_{\text{risk}}$ = risk aversion parameter
- $\sigma$ = price volatility
- The trajectory is front-loaded for high risk aversion, uniform for low risk aversion

Purpose: Computes the minimum-cost execution schedule that balances market impact cost against timing risk (price variance during execution).

V1\_Bot: Execution algorithm for large XAUUSD positions; $\lambda_{\text{risk}}$ is dynamically set based on current volatility regime (Concept 05, Doc 08).

---

## Section 13: Information Theory and Signal Processing

### 13.1 Shannon Entropy

$$
H(X) = -\sum_{i} P(x_i)\,\log_2 P(x_i)
$$

Where:

- $X$ = discrete random variable
- $P(x_i)$ = probability of outcome $x_i$
- $H(X) \geq 0$; $H(X) = 0$ when outcome is certain
- Maximum entropy is achieved by the uniform distribution: $H_{\max} = \log_2 |\mathcal{X}|$

Purpose: Measures the average information content (uncertainty) of a random variable.

V1\_Bot: Market efficiency measurement -- high entropy in return distributions indicates unpredictability; used as a regime classification feature (Concept 02).

---

### 13.2 Sample Entropy (SampEn)

$$
\text{SampEn}(m, r, N) = -\ln \frac{\sum_i C_i^{m+1}(r)}{\sum_i C_i^m(r)}
$$

Where:

- $m$ = embedding dimension (pattern length)
- $r$ = tolerance threshold (typically $r = 0.2\sigma$)
- $N$ = time series length
- $C_i^m(r)$ = number of template matches of length $m$ within tolerance $r$
- High SampEn $\to$ complex, irregular, random (mean reversion regime)
- Low SampEn $\to$ regular, predictable, trending (trend following regime)

Purpose: Quantifies the regularity/complexity of a time series without requiring stationarity, distinguishing trending from mean-reverting market regimes.

V1\_Bot: Regime detection feature -- SampEn values are computed on rolling windows and used to select between trend-following and mean-reversion strategy configurations (Concept 02).

---

### 13.3 KL Divergence (Kullback-Leibler)

$$
D_{KL}(P \| Q) = \sum_{x} P(x)\,\log \frac{P(x)}{Q(x)}
$$

Where:

- $P$ = true (reference) distribution
- $Q$ = approximate (model) distribution
- $D_{KL} \geq 0$ with equality iff $P = Q$
- Not symmetric: $D_{KL}(P \| Q) \neq D_{KL}(Q \| P)$
- $D_{KL}(P\|Q)$ is undefined when $Q(x) = 0$ for any $x$ where $P(x) > 0$

Purpose: Measures the information lost when approximating $P$ with $Q$; used to detect distributional drift.

V1\_Bot: Drift detector in the confidence gating module -- when $D_{KL}(\text{train} \| \text{live})$ exceeds a threshold, the system reduces confidence and may halt trading (Algo Engine).

---

### 13.4 Wavelet Transform

**Discrete Wavelet Transform (DWT) Decomposition:**

$$
X_t = \sum_k c_{J,k}\,\phi_{J,k}(t) + \sum_{j=1}^J \sum_k d_{j,k}\,\psi_{j,k}(t)
$$

Where:

- $\phi_{J,k}(t)$ = scaling function (father wavelet) at the coarsest level $J$
- $\psi_{j,k}(t)$ = wavelet function (mother wavelet) at level $j$, shift $k$
- $c_{J,k}$ = approximation coefficients (capture the trend/low-frequency component)
- $d_{j,k}$ = detail coefficients (capture noise/high-frequency components at each scale)
- $J$ = number of decomposition levels

Purpose: Decomposes a time series into multi-resolution components, separating trend from noise at different time scales.

V1\_Bot: Price denoising for trend extraction -- the approximation coefficients provide a clean trend signal, while detail coefficients quantify noise at each scale (Concept 02).

---

**Soft Thresholding (Wavelet Denoising):**

$$
\hat{d}_{j,k} = \text{sign}(d_{j,k})\,\max(0,\; |d_{j,k}| - \lambda)
$$

Where:

- $d_{j,k}$ = raw detail coefficient
- $\hat{d}_{j,k}$ = thresholded detail coefficient
- $\lambda$ = threshold level
- Coefficients with $|d_{j,k}| < \lambda$ are set to zero (removed as noise)
- Remaining coefficients are shrunk toward zero by $\lambda$

Purpose: Removes noise from the detail coefficients while preserving significant signal features.

V1\_Bot: Applied to detail coefficients before inverse wavelet transform to reconstruct a denoised price series (Concept 02).

---

**Universal Threshold (VisuShrink):**

$$
\lambda = \sigma\sqrt{2\ln N}
$$

Where:

- $\sigma$ = noise standard deviation (estimated from finest-level detail coefficients via MAD: $\hat{\sigma} = \text{median}(|d_{1,k}|) / 0.6745$)
- $N$ = number of data points
- This threshold asymptotically removes all pure noise with probability tending to 1

Purpose: Provides a principled, data-driven threshold for wavelet denoising that adapts to the noise level and series length.

V1\_Bot: Default threshold for the wavelet denoising module in the feature engineering pipeline; $\sigma$ is re-estimated on each rolling window (Concept 02).

---

*End of Document 14 -- PART B (Sections 8--13)*

# Document 14 -- Mathematical and Quantitative Reference Manual

## PART C: Sections 14--19

> **Scope:** Ensemble methods, blockchain/DeFi mathematics, macroeconomic models, confidence gating and statistical process control, market making and execution, and appendices.
> **Convention:** All display equations use `$$...$$`. Inline math uses `$...$`. Every formula carries a **Where**, **Purpose**, and **V1\_Bot** block.

---

# Section 14: Ensemble Methods and Meta-Strategy Mathematics

---

## 14.1 Condorcet's Jury Theorem and Portfolio Sharpe Scaling

**Theorem (Condorcet).** If each of $n$ independent voters is correct with probability $p > 0.5$, the majority vote accuracy converges to 1:

$$
P(\text{majority correct}) = \sum_{k=\lceil n/2 \rceil}^{n} \binom{n}{k} p^k (1-p)^{n-k} \;\xrightarrow{n \to \infty}\; 1
$$

**Where:**

- $n$ = number of independent voters (strategies).
- $p$ = individual accuracy, $p > 0.5$.
- $k$ = number of correct votes.

**Purpose:** Proves that aggregating many slightly-better-than-random classifiers yields near-perfect accuracy.

**V1\_Bot:** Justification for ensemble diversity in the Algo Engine.

---

**Portfolio Sharpe Scaling (uncorrelated):**

$$
SR_{\text{portfolio}} = \sqrt{N} \times SR_{\text{single}}
$$

**Where:**

- $N$ = number of uncorrelated strategies.
- $SR_{\text{single}}$ = Sharpe ratio of any single strategy (assumed identical).

**Purpose:** Quantifies the diversification benefit when combining independent alpha sources.

**V1\_Bot:** Ensemble sizing decisions in the Algo Engine.

---

**Portfolio Sharpe Scaling (correlated):**

$$
SR_{\text{portfolio}} = \frac{\sqrt{N}}{\sqrt{1 + (N-1)\bar{\rho}}} \times SR_{\text{single}}
$$

**Where:**

- $\bar{\rho}$ = average pairwise correlation between strategies.
- $N$, $SR_{\text{single}}$ as above.

**Purpose:** Extends the Sharpe scaling formula to the realistic case of nonzero inter-strategy correlation, showing diminishing returns as $\bar{\rho} \to 1$.

**V1\_Bot:** Diversity constraint enforcement in ensemble construction.

---

## 14.2 Mixture of Experts (MoE)

**Gating Network (softmax):**

$$
g_i(x) = \frac{\exp(\mathbf{v}_i^T x)}{\sum_{j=1}^{K} \exp(\mathbf{v}_j^T x)}
$$

**Where:**

- $x$ = input feature vector.
- $\mathbf{v}_i$ = learnable weight vector for expert $i$.
- $K$ = total number of experts.
- $g_i(x) \in [0, 1]$, $\sum_{i=1}^{K} g_i(x) = 1$.

**Purpose:** Computes the soft routing weight that determines how much each expert contributes to the final prediction.

**V1\_Bot:** MONEYMAKER strategy ensemble routing via weighted expert combination.

---

**Ensemble Output:**

$$
y = \sum_{i=1}^{K} g_i(x) \cdot E_i(x)
$$

**Where:**

- $E_i(x)$ = output of expert $i$ given input $x$.
- $g_i(x)$ = gating weight for expert $i$.

**Purpose:** Produces the final prediction as a convex combination of expert outputs, trained end-to-end via backpropagation through both the gating network and all experts.

**V1\_Bot:** Algo Engine final signal aggregation layer.

---

## 14.3 Weighted Signal Aggregation

**Net Signal:**

$$
s = \sum_{i=1}^{M} w_i \cdot d_i \cdot \text{strength}_i
$$

**Where:**

- $M$ = number of signal sources (indicators, models).
- $w_i$ = weight assigned to signal source $i$.
- $d_i \in \{-1, 0, +1\}$ = directional component (sell, neutral, buy).
- $\text{strength}_i \in [0, 1]$ = magnitude/conviction of signal $i$.

**Purpose:** Collapses multiple directional signals into a single scalar that drives position decisions.

**V1\_Bot:** SignalProcessor multi-timeframe analysis (Algo Engine).

---

**Multi-Timeframe Confluence:**

$$
\text{score} = w_{H4}\, s_{H4} + w_{H1}\, s_{H1} + w_{M15}\, s_{M15}
$$

**Where:**

- $s_{H4}, s_{H1}, s_{M15}$ = net signals from 4-hour, 1-hour, and 15-minute timeframes.
- $w_{H4} > w_{H1} > w_{M15}$ (cardinal rule: never trade against the highest timeframe).

**Purpose:** Enforces hierarchical timeframe alignment so that lower-timeframe entries are only taken in the direction of the dominant trend.

**V1\_Bot:** SignalProcessor multi-timeframe confluence logic (Algo Engine).

---

## 14.4 Stacking (Meta-Learning)

**Level-0 (Base Models):** $K$ base models each produce out-of-fold predictions $\hat{y}_k$ via cross-validation.

**Level-1 Input:**

$$
X_{\text{meta}} = \begin{bmatrix} \hat{y}_1 & \hat{y}_2 & \cdots & \hat{y}_K \end{bmatrix}
$$

**Meta-Learner (Logistic Regression):**

$$
\hat{y}_{\text{final}} = \sigma\!\left(\sum_{k=1}^{K} \beta_k \hat{y}_k + b\right)
$$

**Where:**

- $\hat{y}_k$ = out-of-fold prediction from base model $k$.
- $\beta_k$ = meta-learner coefficient for model $k$.
- $b$ = bias term.
- $\sigma(\cdot)$ = sigmoid function.

**Purpose:** Learns the optimal way to combine heterogeneous base-model predictions, correcting for individual model biases and exploiting complementary strengths.

**V1\_Bot:** Ensemble stacking pipeline in the Algo Engine.

---

## 14.5 Genetic Algorithm for Weight Evolution

**Genome:**

$$
\mathbf{w} = [w_1,\; w_2,\; \dots,\; w_K]
$$

**Fitness Function:**

$$
F(\mathbf{w}) = \text{net\_profit}(\mathbf{w}) \times \bigl(1 - \text{MDD}(\mathbf{w})\bigr)^2 \times \log\!\bigl(\text{trade\_count}(\mathbf{w})\bigr)
$$

**Where:**

- $\text{net\_profit}$ = cumulative P\&L of the weighted ensemble.
- $\text{MDD}$ = maximum drawdown (fraction), $\text{MDD} \in [0, 1]$.
- $\text{trade\_count}$ = number of trades executed (encourages statistical significance).

**Purpose:** Defines a composite fitness that rewards profitability, penalizes drawdown quadratically, and requires sufficient trade frequency.

**V1\_Bot:** Ensemble weight optimization via evolutionary search.

---

**Mutation Operator:**

$$
w_i' = w_i + \mathcal{N}(0, \sigma_m) \quad \text{with probability } p_m
$$

**Where:**

- $\sigma_m$ = mutation standard deviation.
- $p_m$ = per-gene mutation probability.

**Purpose:** Introduces random perturbations into the weight vector to explore the fitness landscape and escape local optima.

**V1\_Bot:** Genetic algorithm mutation step in ensemble weight evolution.

---

# Section 15: Blockchain, DeFi, and AMM Mathematics

---

## 15.1 Constant Product AMM

**Invariant:**

$$
x \cdot y = k
$$

**Where:**

- $x$ = reserve of token X in the pool.
- $y$ = reserve of token Y in the pool.
- $k$ = constant product invariant.

**Purpose:** Defines the core pricing curve of Uniswap V2-style automated market makers.

**V1\_Bot:** Crypto DEX strategy understanding.

---

**Spot Price:**

$$
P = \frac{y}{x}
$$

**Purpose:** Gives the instantaneous exchange rate of token X in terms of token Y.

**V1\_Bot:** DEX price feed derivation.

---

**Trade Output:**

$$
\Delta y = \frac{y \cdot \Delta x}{x + \Delta x}
$$

**Where:**

- $\Delta x$ = amount of token X sold into the pool.
- $\Delta y$ = amount of token Y received.

**Purpose:** Computes the exact output of a swap given the input amount and current reserves.

**V1\_Bot:** Crypto DEX execution simulation.

---

**Price Impact:**

$$
\text{Impact} = 1 - \frac{x}{x + \Delta x}
$$

**Purpose:** Measures the percentage by which the executed price deviates from the pre-trade spot price due to finite liquidity.

**V1\_Bot:** Slippage estimation for DEX trades.

---

## 15.2 Impermanent Loss

$$
\text{IL}(r) = \frac{2\sqrt{r}}{1 + r} - 1
$$

**Where:**

- $r = P_1 / P_0$ = ratio of final price to initial price.
- $\text{IL} \leq 0$ always (loss relative to holding).

**Purpose:** Quantifies the opportunity cost an LP suffers when the price ratio diverges from the entry ratio.

**V1\_Bot:** LP strategy risk assessment.

**Reference values:** At $r = 2$: IL $\approx -5.7\%$. At $r = 5$: IL $\approx -25.5\%$.

---

## 15.3 Uniswap V3 Concentrated Liquidity

**Real Reserves (Token 0):**

$$
x_{\text{real}} = L \cdot \frac{\sqrt{P_b} - \sqrt{P}}{\sqrt{P} \cdot \sqrt{P_b}}
$$

**Real Reserves (Token 1):**

$$
y_{\text{real}} = L \left(\sqrt{P} - \sqrt{P_a}\right)
$$

**Where:**

- $L$ = liquidity parameter.
- $P$ = current price.
- $[P_a, P_b]$ = price range of the concentrated position.

**Purpose:** Computes the actual token amounts held within a concentrated liquidity position bounded by a price range.

**V1\_Bot:** Concentrated liquidity strategy analysis.

---

**Tick Math:**

$$
P(i) = 1.0001^{\,i}
$$

**Where:**

- $i$ = tick index (integer).

**Purpose:** Maps discrete tick indices to continuous prices, providing basis-point granularity.

**V1\_Bot:** Tick-level position management.

---

**Capital Efficiency vs. V2:**

$$
\text{leverage} = \frac{1}{1 - \sqrt{P_a / P_b}}
$$

**Purpose:** Measures how much more capital-efficient a V3 concentrated position is compared to a full-range V2 position.

**V1\_Bot:** Capital efficiency optimization for LP strategies.

---

## 15.4 MEV and Sandwich Attack

**Front-Run Profit:**

$$
\pi = \Delta y_{\text{back}} - \Delta x_{\text{front}} - 2 \cdot \text{gas}
$$

**Where:**

- $\Delta x_{\text{front}}$ = tokens spent in the front-running transaction.
- $\Delta y_{\text{back}}$ = tokens received in the back-running transaction.
- $\text{gas}$ = gas cost per transaction (two transactions total).

**Purpose:** Computes the net profit of a sandwich attack after accounting for gas costs.

**V1\_Bot:** MEV-aware execution logic (Concept 06).

---

**Optimal Front-Run Size:**

$$
\max_{\Delta x} \left[\pi(\Delta x) - \text{gas\_cost}\right] \quad \text{s.t.} \quad P_{\text{victim}} \geq P_{\text{limit}}
$$

**Purpose:** Finds the profit-maximizing front-run trade size subject to the victim's slippage tolerance.

**V1\_Bot:** MEV protection and detection module (Concept 06).

---

## 15.5 Cyclic Arbitrage

**Edge Weight (Log-Price Graph):**

$$
w_{ij} = -\log(P_{ij})
$$

**Arbitrage Condition:**

$$
\sum_{(i,j) \in \text{cycle}} w_{ij} < 0 \;\;\Longleftrightarrow\;\; \prod_{(i,j) \in \text{cycle}} P_{ij} > 1
$$

**Fee-Adjusted Edge Weight:**

$$
w_{ij} = -\log\!\bigl(P_{ij}(1 - \text{fee})\bigr)
$$

**Where:**

- $P_{ij}$ = exchange rate from token $i$ to token $j$.
- $\text{fee}$ = per-hop trading fee (e.g., 0.003 for 0.3%).

**Purpose:** Reduces multi-hop arbitrage detection to the negative-cycle problem in a weighted directed graph, solvable via Bellman-Ford in $O(VE)$.

**V1\_Bot:** Cross-exchange arbitrage detection (Concept 06).

---

## 15.6 Block Arrival Dynamics

**Poisson Process:**

$$
P\bigl(N(T) = k\bigr) = \frac{(\lambda T)^k\, e^{-\lambda T}}{k!}
$$

**Inter-Arrival Distribution:**

$$
f(\tau) = \lambda\, e^{-\lambda \tau}
$$

**Where:**

- $\lambda$ = block arrival rate (blocks per second).
- $T$ = observation window.
- $\tau$ = time between consecutive blocks.
- $E[\tau] = 1/\lambda$ ($\approx 12\text{s}$ Ethereum, $\approx 600\text{s}$ Bitcoin).

**Purpose:** Models the stochastic timing of block production, which governs transaction confirmation latency and MEV timing windows.

**V1\_Bot:** Timing model for on-chain strategy execution.

---

## 15.7 Gas Auction Game Theory

**First-Price Sealed-Bid Utility:**

$$
U_i(b_i) = (v_i - b_i) \cdot \mathbf{1}\!\bigl[b_i > \max_{j \neq i} b_j\bigr]
$$

**Where:**

- $v_i$ = bidder $i$'s private valuation of transaction inclusion.
- $b_i$ = bidder $i$'s gas bid.

**Purpose:** Captures the trade-off between bidding high (to win) and bidding low (to keep surplus).

**V1\_Bot:** Gas fee optimization for on-chain execution.

---

**Nash Equilibrium Bid (Symmetric IPV):**

$$
b^*(v) = v - \frac{\int_0^v F(t)^{n-1}\, dt}{F(v)^{n-1}}
$$

**Where:**

- $F(\cdot)$ = CDF of the common value distribution.
- $n$ = number of competing bidders.

**Purpose:** Gives the equilibrium bidding strategy in a first-price auction with $n$ symmetric bidders.

**V1\_Bot:** Competitive gas pricing model.

---

**Block Construction (Knapsack):**

$$
\max_{S \subset \mathcal{T}} \sum_{tx \in S} b_{tx} \quad \text{s.t.} \quad \sum_{tx \in S} g_{tx} \leq C_{\text{gas}}
$$

**Where:**

- $\mathcal{T}$ = set of pending transactions in the mempool.
- $b_{tx}$ = fee bid of transaction $tx$.
- $g_{tx}$ = gas consumption of transaction $tx$.
- $C_{\text{gas}}$ = block gas limit.

**Purpose:** Models the block builder's optimization problem of selecting the most profitable subset of transactions that fits within the block gas limit.

**V1\_Bot:** Block builder simulation for MEV strategy analysis.

---

# Section 16: Macroeconomic Models and Economic Theory

---

## 16.1 GDP and National Accounts

**Expenditure Approach:**

$$
\text{GDP} = C + I + G + (X - M)
$$

**Where:**

- $C$ = household consumption.
- $I$ = gross private investment.
- $G$ = government spending.
- $X$ = exports; $M$ = imports.

**Purpose:** Decomposes aggregate output into demand-side components for macroeconomic regime classification.

**V1\_Bot:** Macro regime indicator for strategy selection.

---

**GDP Deflator:**

$$
\text{Deflator} = \frac{\text{Nominal GDP}}{\text{Real GDP}} \times 100
$$

**Purpose:** Measures the overall price level relative to a base year, used as an inflation proxy distinct from CPI.

**V1\_Bot:** Inflation feature for macro regime detection.

---

## 16.2 Price Elasticity

**Own-Price Elasticity of Demand:**

$$
\epsilon_d = \frac{\%\Delta Q_d}{\%\Delta P} = \frac{dQ}{dP} \times \frac{P}{Q}
$$

**Where:**

- $Q_d$ = quantity demanded.
- $P$ = price.
- $|\epsilon_d| > 1$: elastic demand; $|\epsilon_d| < 1$: inelastic demand.

**Purpose:** Quantifies demand sensitivity to price changes, critical for modeling commodity and currency markets.

**V1\_Bot:** Commodity supply/demand modeling.

---

**Cross-Price Elasticity:**

$$
\epsilon_{xy} = \frac{\%\Delta Q_x}{\%\Delta P_y}
$$

**Where:**

- $\epsilon_{xy} > 0$: goods $x$ and $y$ are substitutes.
- $\epsilon_{xy} < 0$: goods $x$ and $y$ are complements.

**Purpose:** Identifies inter-asset relationships for pairs trading and cross-market signal generation.

**V1\_Bot:** Cross-asset correlation features.

---

## 16.3 Yield Curve -- Nelson-Siegel Model

$$
y(\tau) = \beta_0 + \beta_1 \frac{1 - e^{-\tau/\lambda}}{\tau/\lambda} + \beta_2 \left(\frac{1 - e^{-\tau/\lambda}}{\tau/\lambda} - e^{-\tau/\lambda}\right)
$$

**Where:**

- $\tau$ = time to maturity (years).
- $\beta_0$ = long-term level (asymptotic yield).
- $\beta_1$ = slope (short-term component); $\beta_1 < 0$ implies upward-sloping curve.
- $\beta_2$ = curvature (medium-term hump/trough).
- $\lambda$ = decay parameter controlling factor loading speeds.

**Purpose:** Provides a parsimonious three-factor parametric representation of the entire yield curve from a handful of bond yields.

**V1\_Bot:** Macro feature for regime detection; yield curve inversion ($\beta_1 > 0$, equivalently 10Y-2Y spread $< 0$) as recession signal.

---

## 16.4 Taylor Rule

$$
i_t = r^* + \pi_t + 0.5\,(\pi_t - \pi^*) + 0.5\,(y_t - y^*)
$$

**Where:**

- $i_t$ = nominal policy interest rate.
- $r^*$ = neutral real rate of interest.
- $\pi_t$ = current inflation rate; $\pi^*$ = target inflation (typically 2%).
- $y_t$ = log real GDP; $y^*$ = log potential output.
- $(y_t - y^*)$ = output gap.

**Purpose:** Prescribes the central bank's optimal policy rate as a function of inflation and output deviations, enabling prediction of rate decisions.

**V1\_Bot:** Central bank policy prediction and carry trade signal generation (Algo Engine).

---

## 16.5 Interest Rate Parity

**Covered Interest Rate Parity (CIP):**

$$
\frac{F}{S} = \frac{1 + r_d}{1 + r_f}
$$

**Where:**

- $F$ = forward exchange rate.
- $S$ = spot exchange rate.
- $r_d$ = domestic interest rate; $r_f$ = foreign interest rate.

**Purpose:** Links forward FX premia to interest rate differentials; deviations signal arbitrage or credit risk.

**V1\_Bot:** Forex carry trade strategy.

---

**Carry Trade Return:**

$$
r_{\text{carry}} = (r_d - r_f) + \Delta S
$$

**Where:**

- $\Delta S$ = spot exchange rate return over the holding period.

**Purpose:** Decomposes carry trade P\&L into the interest differential earned and the currency movement.

**V1\_Bot:** Carry trade performance attribution.

---

## 16.6 Purchasing Power Parity

**Relative PPP:**

$$
\frac{S_1}{S_0} = \frac{1 + \pi_{\text{domestic}}}{1 + \pi_{\text{foreign}}}
$$

**Where:**

- $S_0, S_1$ = spot exchange rates at time 0 and 1.
- $\pi_{\text{domestic}}, \pi_{\text{foreign}}$ = inflation rates in the respective countries.

**Purpose:** Estimates the equilibrium exchange rate adjustment implied by inflation differentials, providing a long-term FX fair value anchor.

**V1\_Bot:** Long-term FX fair value estimation and mean-reversion signals.

---

# Section 17: Confidence Gating and Statistical Process Control

---

## 17.1 Page-Hinkley Change-Point Detection

**Cumulative Sum:**

$$
U_t = U_{t-1} + (x_t - \bar{x}_t - \delta)
$$

**Running Minimum:**

$$
m_t = \min(m_{t-1},\; U_t)
$$

**Alarm Condition:**

$$
U_t - m_t > \lambda
$$

**Where:**

- $x_t$ = observed value at time $t$.
- $\bar{x}_t$ = running mean up to time $t$.
- $\delta$ = minimum magnitude of detectable shift (sensitivity parameter).
- $\lambda$ = detection threshold (higher $\to$ fewer false alarms).

**Purpose:** Detects upward distributional shifts in a sequential stream; used to identify concept drift or regime change in model performance.

**V1\_Bot:** Drift detector in confidence gating pipeline (Algo Engine).

---

## 17.2 CUSUM (Cumulative Sum Control Chart)

**Upper CUSUM:**

$$
S_t^+ = \max\!\bigl(0,\; S_{t-1}^+ + (x_t - \mu_0 - K)\bigr)
$$

**Lower CUSUM:**

$$
S_t^- = \max\!\bigl(0,\; S_{t-1}^- - (x_t - \mu_0 + K)\bigr)
$$

**Alarm:** triggered if $S_t^+ > H$ or $S_t^- > H$.

**Where:**

- $\mu_0$ = in-control process mean.
- $K$ = allowance (slack) parameter, typically $K = \delta/2$ where $\delta$ is the shift to detect.
- $H$ = decision interval (threshold).

**Purpose:** Detects small, persistent shifts in a process mean in both upward and downward directions; more sensitive to sustained drift than Shewhart charts.

**V1\_Bot:** Performance degradation detection in the monitoring stack (Doc 10).

---

## 17.3 Z-Score Outlier Detection

$$
z_t = \frac{x_t - \mu}{\sigma}
$$

**Alarm:** $|z_t| > 2.5$ triggers the silence rule.

**Where:**

- $x_t$ = observed metric (e.g., recent loss, volatility spike).
- $\mu$ = historical mean of the metric.
- $\sigma$ = historical standard deviation.

**Purpose:** Flags extreme deviations from normal operating conditions, activating the confidence gating silence rule to halt trading.

**V1\_Bot:** Silence rule Condition 1 in confidence gating (Algo Engine).

---

## 17.4 Cosine Similarity

$$
\cos(\theta) = \frac{\mathbf{a} \cdot \mathbf{b}}{\|\mathbf{a}\| \cdot \|\mathbf{b}\|}
$$

**Where:**

- $\mathbf{a}, \mathbf{b}$ = feature vectors (e.g., market state embeddings).
- $\cos(\theta) \in [-1, 1]$.
- Match threshold: typically $\cos(\theta) > 0.85$.

**Purpose:** Measures directional similarity between two feature vectors, independent of magnitude, for retrieving analogous historical market states.

**V1\_Bot:** COPER experience bank pattern matching (Algo Engine).

---

## 17.5 FAISS Approximate Nearest Neighbor

**IVF (Inverted File Index):**

$$
\text{Assign } \mathbf{x} \to c^* = \arg\min_{c \in \mathcal{C}} \|\mathbf{x} - \mathbf{c}\|_2
$$

then search only the $n_{\text{probe}}$ nearest clusters.

**Product Quantization (PQ):**

$$
\mathbf{x} = [\mathbf{x}^{(1)}, \mathbf{x}^{(2)}, \dots, \mathbf{x}^{(m)}], \quad \tilde{d}(\mathbf{x}, \mathbf{y}) = \sum_{j=1}^{m} d(\mathbf{x}^{(j)}, q_j(\mathbf{y}^{(j)}))
$$

**Where:**

- $\mathcal{C}$ = set of $k$-means cluster centroids.
- $n_{\text{probe}}$ = number of clusters searched at query time.
- $m$ = number of sub-vector partitions.
- $q_j(\cdot)$ = quantizer for sub-vector $j$.

**Purpose:** Reduces nearest-neighbor search complexity from $O(n)$ brute force to $O(\sqrt{n})$ while compressing memory via product quantization.

**V1\_Bot:** COPER experience bank search acceleration (Algo Engine).

---

# Section 18: Market Making and Execution Mathematics

---

## 18.1 Avellaneda-Stoikov Inventory Model

**Reservation Price:**

$$
r(s, q, t) = s - q\,\gamma\,\sigma^2(T - t)
$$

**Where:**

- $s$ = current mid price.
- $q$ = current inventory (positive = long, negative = short).
- $\gamma$ = risk aversion coefficient.
- $\sigma^2$ = asset return variance.
- $T - t$ = time remaining to horizon.

**Purpose:** Adjusts the market maker's indifference price away from mid based on inventory risk exposure, pushing quotes to shed unwanted inventory.

**V1\_Bot:** Market making strategy framework (Concept 29).

---

**Optimal Half-Spread:**

$$
\delta^*(q) = \frac{1}{\gamma} \ln\!\left(1 + \frac{\gamma}{\kappa}\right)
$$

**Where:**

- $\kappa$ = Poisson order arrival intensity (fills per unit time per unit spread).
- $\gamma$ = risk aversion parameter.

**Purpose:** Determines the optimal distance between the reservation price and the posted bid/ask, balancing fill probability against adverse selection.

**V1\_Bot:** Market making spread calibration (Concept 29).

---

**Quote Placement:**

$$
P_{\text{bid}} = r - \delta^*, \qquad P_{\text{ask}} = r + \delta^*
$$

**Purpose:** Produces the final bid and ask prices by applying the optimal spread symmetrically around the inventory-adjusted reservation price.

**V1\_Bot:** Market making order placement engine.

---

## 18.2 Effective Spread

$$
ES = 2 \times |P_{\text{trade}} - P_{\text{mid}}|
$$

**Where:**

- $P_{\text{trade}}$ = actual execution price.
- $P_{\text{mid}}$ = midpoint of the NBBO at trade time.

**Purpose:** Measures realized transaction cost as twice the deviation from mid, serving as the primary execution quality metric.

**V1\_Bot:** Execution quality monitoring in Execution Bridge (Doc 08).

---

## 18.3 Health Factor (Collateralized Positions)

**Weighted Collateral:**

$$
EC = \sum_{i} \text{Amount}_i \times P_i \times LTV_i
$$

**Health Factor:**

$$
HF = \frac{\sum_i \bigl(\text{Collateral}_i \times \text{Threshold}_i\bigr)}{\text{Total Debt}}
$$

**Liquidation Trigger:** $HF < 1.0$.

**Where:**

- $\text{Amount}_i$ = quantity of collateral asset $i$.
- $P_i$ = current price of asset $i$.
- $LTV_i$ = loan-to-value ratio for asset $i$.
- $\text{Threshold}_i$ = liquidation threshold for asset $i$.
- $\text{Total Debt}$ = sum of all outstanding borrows denominated in the base currency.

**Purpose:** Monitors the solvency of leveraged DeFi positions; when the health factor drops below 1.0, the position becomes eligible for liquidation.

**V1\_Bot:** DeFi position risk monitoring in Risk Manager (Doc 09).

---

# Section 19: Appendices

---

## Appendix A: Master Symbol Table

| Symbol | Definition | Units / Range | First Appears |
|--------|-----------|---------------|---------------|
| $\alpha$ | Jensen's alpha; significance level | return / probability | Sec 6, 4 |
| $\beta$ | Market beta; regression coefficient | dimensionless | Sec 6 |
| $\beta_0, \beta_1, \beta_2$ | Nelson-Siegel yield curve factors | % | Sec 16.3 |
| $\gamma$ | Risk aversion coefficient | dimensionless | Sec 6, 18.1 |
| $\delta$ | Minimum detectable shift (Page-Hinkley) | same as data | Sec 17.1 |
| $\delta^*$ | Optimal half-spread (Avellaneda-Stoikov) | price units | Sec 18.1 |
| $\epsilon$ | Error term; elasticity | varies | Sec 5, 16.2 |
| $\epsilon_d$ | Own-price elasticity of demand | dimensionless | Sec 16.2 |
| $\epsilon_{xy}$ | Cross-price elasticity | dimensionless | Sec 16.2 |
| $\theta$ | Angle; mean-reversion speed (OU) | radians; $1/\text{time}$ | Sec 5, 17.4 |
| $\kappa$ | Order arrival rate (Poisson) | fills/time | Sec 18.1 |
| $\lambda$ | Detection threshold; decay parameter | varies | Sec 16.3, 17.1 |
| $\mu$ | Mean; drift | return or price | Sec 4, 5 |
| $\mu_0$ | In-control process mean | same as data | Sec 17.2 |
| $\pi$ | Profit (MEV); inflation rate | currency; % | Sec 15.4, 16 |
| $\pi^*$ | Target inflation rate | % | Sec 16.4 |
| $\bar{\rho}$ | Average pairwise strategy correlation | $[-1, 1]$ | Sec 14.1 |
| $\sigma$ | Standard deviation; volatility | return or price | Sec 4, 6 |
| $\sigma^2$ | Variance | return$^2$ | Sec 4 |
| $\sigma_m$ | Mutation standard deviation | same as weights | Sec 14.5 |
| $\tau$ | Time to maturity; inter-arrival time | time | Sec 15.6, 16.3 |
| $C$ | Consumption; gas limit | currency; gas | Sec 15.7, 16.1 |
| $d_i$ | Directional signal component | $\{-1, 0, +1\}$ | Sec 14.3 |
| $E_i(x)$ | Expert $i$ output | varies | Sec 14.2 |
| $EC$ | Effective (weighted) collateral | currency | Sec 18.3 |
| $ES$ | Effective spread | price units | Sec 18.2 |
| $F$ | Forward FX rate; CDF | currency; $[0,1]$ | Sec 15.7, 16.5 |
| $F(\mathbf{w})$ | Fitness function | composite score | Sec 14.5 |
| $g_i(x)$ | Gating weight for expert $i$ | $[0, 1]$ | Sec 14.2 |
| $G$ | Government spending | currency | Sec 16.1 |
| $H$ | Decision interval (CUSUM) | same as data | Sec 17.2 |
| $HF$ | Health factor | dimensionless | Sec 18.3 |
| $I$ | Investment | currency | Sec 16.1 |
| $i_t$ | Nominal policy rate | % | Sec 16.4 |
| $k$ | Constant product invariant | token$^2$ | Sec 15.1 |
| $K$ | Number of experts/models; allowance | count; same as data | Sec 14.2, 17.2 |
| $L$ | Liquidity parameter (Uni V3) | $\sqrt{\text{token}^2}$ | Sec 15.3 |
| $LTV$ | Loan-to-value ratio | $[0, 1]$ | Sec 18.3 |
| $M$ | Number of signal sources; imports | count; currency | Sec 14.3, 16.1 |
| $m_t$ | Running minimum (Page-Hinkley) | same as data | Sec 17.1 |
| $N$ | Number of strategies | count | Sec 14.1 |
| $n$ | Number of voters/bidders | count | Sec 14.1, 15.7 |
| $p$ | Individual accuracy; mutation prob. | $[0, 1]$ | Sec 14.1, 14.5 |
| $P$ | Price; probability | currency; $[0,1]$ | Sec 15.1 |
| $P_a, P_b$ | Lower/upper price bounds (Uni V3) | currency | Sec 15.3 |
| $q$ | Inventory | units | Sec 18.1 |
| $r$ | Price ratio; interest rate; reservation price | dimensionless; %; price | Sec 15.2, 16.5, 18.1 |
| $r^*$ | Neutral real interest rate | % | Sec 16.4 |
| $S$ | Spot FX rate; transaction subset | currency; set | Sec 15.7, 16.5 |
| $s$ | Net signal; mid price | score; price | Sec 14.3, 18.1 |
| $S_t^+, S_t^-$ | Upper/lower CUSUM statistics | same as data | Sec 17.2 |
| $SR$ | Sharpe ratio | dimensionless | Sec 14.1 |
| $T$ | Time horizon | time | Sec 15.6, 18.1 |
| $U_t$ | Cumulative sum (Page-Hinkley) | same as data | Sec 17.1 |
| $v_i$ | Private valuation; gating vector | currency; $\mathbb{R}^d$ | Sec 14.2, 15.7 |
| $w_i$ | Weight; edge weight | dimensionless; log-price | Sec 14.3, 15.5 |
| $\mathbf{w}$ | Weight vector (genome) | $\mathbb{R}^K$ | Sec 14.5 |
| $x, y$ | Pool reserves | tokens | Sec 15.1 |
| $X$ | Exports | currency | Sec 16.1 |
| $X_{\text{meta}}$ | Meta-learner feature matrix | $\mathbb{R}^{n \times K}$ | Sec 14.4 |
| $y(\tau)$ | Yield at maturity $\tau$ | % | Sec 16.3 |
| $z_t$ | Z-score | dimensionless | Sec 17.3 |

---

## Appendix B: Formula Quick-Reference Index

| Section | Formula Name | One-Line Equation | V1\_Bot Component |
|---------|-------------|-------------------|-------------------|
| **Ensemble (14)** | | | |
| 14.1 | Condorcet Majority | $P(\text{maj}) = \sum \binom{n}{k}p^k(1-p)^{n-k}$ | Algo Engine ensemble |
| 14.1 | Sharpe Scaling (uncorr.) | $SR_p = \sqrt{N} \cdot SR_s$ | Algo Engine sizing |
| 14.1 | Sharpe Scaling (corr.) | $SR_p = \frac{\sqrt{N}}{\sqrt{1+(N-1)\bar\rho}} SR_s$ | Algo Engine diversity |
| 14.2 | MoE Gating | $g_i = \text{softmax}(\mathbf{v}_i^T x)$ | Algo Engine MoE |
| 14.2 | MoE Output | $y = \sum g_i E_i(x)$ | Algo Engine |
| 14.3 | Net Signal | $s = \sum w_i d_i \cdot \text{str}_i$ | SignalProcessor |
| 14.3 | MTF Confluence | $\text{score} = \sum w_{tf} s_{tf}$ | SignalProcessor |
| 14.4 | Stacking Meta-Learner | $\hat{y} = \sigma(\sum \beta_k \hat{y}_k + b)$ | Algo Engine stacking |
| 14.5 | GA Fitness | $F = \text{profit}\cdot(1-\text{MDD})^2\cdot\log(n)$ | Algo Engine GA |
| 14.5 | GA Mutation | $w' = w + \mathcal{N}(0,\sigma_m)$ | Algo Engine GA |
| **Blockchain/DeFi (15)** | | | |
| 15.1 | Constant Product | $xy = k$ | DEX strategy |
| 15.1 | Trade Output | $\Delta y = y\Delta x/(x+\Delta x)$ | DEX execution |
| 15.1 | Price Impact | $1 - x/(x+\Delta x)$ | Slippage model |
| 15.2 | Impermanent Loss | $\text{IL} = 2\sqrt{r}/(1+r) - 1$ | LP risk |
| 15.3 | Uni V3 Reserves | $x = L(\sqrt{P_b}-\sqrt{P})/(\sqrt{P}\sqrt{P_b})$ | Conc. liquidity |
| 15.3 | Tick Math | $P(i) = 1.0001^i$ | Position mgmt |
| 15.3 | Capital Efficiency | $1/(1-\sqrt{P_a/P_b})$ | LP optimization |
| 15.4 | Sandwich Profit | $\pi = \Delta y_{back} - \Delta x_{front} - 2\cdot\text{gas}$ | MEV protection |
| 15.5 | Cyclic Arb Condition | $\prod P_{ij} > 1$ | Arb detection |
| 15.6 | Block Poisson | $P(N=k) = (\lambda T)^k e^{-\lambda T}/k!$ | On-chain timing |
| 15.7 | Gas Bid (Nash) | $b^*(v) = v - \int F(t)^{n-1}dt / F(v)^{n-1}$ | Gas optimization |
| 15.7 | Block Knapsack | $\max \sum b_{tx}$ s.t. $\sum g_{tx} \leq C$ | MEV simulation |
| **Macro (16)** | | | |
| 16.1 | GDP Expenditure | $GDP = C+I+G+(X-M)$ | Macro regime |
| 16.2 | Price Elasticity | $\epsilon = (dQ/dP)(P/Q)$ | Commodity model |
| 16.3 | Nelson-Siegel | $y(\tau) = \beta_0 + \beta_1 f_1 + \beta_2 f_2$ | Yield curve |
| 16.4 | Taylor Rule | $i = r^* + \pi + 0.5(\pi-\pi^*) + 0.5(y-y^*)$ | Policy prediction |
| 16.5 | Covered IRP | $F/S = (1+r_d)/(1+r_f)$ | Carry trade |
| 16.6 | Relative PPP | $S_1/S_0 = (1+\pi_d)/(1+\pi_f)$ | FX fair value |
| **Gating/SPC (17)** | | | |
| 17.1 | Page-Hinkley | $U_t - m_t > \lambda$ | Drift detection |
| 17.2 | CUSUM Upper | $S^+ = \max(0, S^+ + x - \mu_0 - K)$ | Degradation det. |
| 17.3 | Z-Score | $z = (x-\mu)/\sigma$ | Silence rule |
| 17.4 | Cosine Similarity | $\cos\theta = \mathbf{a}\cdot\mathbf{b}/(|a||b|)$ | COPER matching |
| 17.5 | FAISS IVF+PQ | $O(\sqrt{n})$ ANN search | COPER search |
| **Market Making (18)** | | | |
| 18.1 | Reservation Price | $r = s - q\gamma\sigma^2(T-t)$ | MM strategy |
| 18.1 | Optimal Spread | $\delta^* = \gamma^{-1}\ln(1+\gamma/\kappa)$ | MM calibration |
| 18.2 | Effective Spread | $ES = 2|P_{trade}-P_{mid}|$ | Exec. quality |
| 18.3 | Health Factor | $HF = \sum(\text{Coll}\times\text{Thr})/\text{Debt}$ | DeFi risk |

---

## Appendix C: V1\_Bot Component Cross-Reference

| MONEYMAKER Component | Document | Key Formulas Used |
|-------------------|----------|-------------------|
| **Data Ingestion** | Doc 04 | OHLCV aggregation, VWAP (Sec 7), data quality z-scores (Sec 17.3) |
| **Algo Engine** | — | All technical indicators (Sec 7), confidence gating and silence rules (Sec 17.1--17.3), COPER cosine similarity and FAISS search (Sec 17.4--17.5), ensemble routing (Sec 14.2), weighted signal aggregation (Sec 14.3), multi-timeframe confluence (Sec 14.3), tree-based models (Sec 9), walk-forward validation (Sec 9.7), stacking and ensemble methods (Sec 14.4) |
| **Risk Manager** | Doc 09 | VaR and CVaR (Sec 6.1--6.2), Kelly criterion (Sec 6.3), position sizing (Sec 6.4), maximum drawdown (Sec 6.5), health factor (Sec 18.3) |
| **Execution Bridge** | Doc 08 | Almgren-Chriss optimal execution (Sec 12.6), slippage models (Sec 12), effective spread monitoring (Sec 18.2), TWAP/VWAP benchmarks (Sec 7) |
| **Monitoring & Dashboard** | Doc 10 | Sharpe ratio, Sortino ratio (Sec 6.7), equity curve statistics, CUSUM degradation detection (Sec 17.2), performance attribution metrics |
| **Macro Module** | Algo Engine| GDP decomposition (Sec 16.1), Nelson-Siegel yield curve (Sec 16.3), Taylor rule (Sec 16.4), interest rate parity (Sec 16.5), PPP (Sec 16.6) |
| **Crypto/DeFi Module** | Concept 06 | Constant product AMM (Sec 15.1), impermanent loss (Sec 15.2), concentrated liquidity (Sec 15.3), MEV and sandwich (Sec 15.4), cyclic arbitrage (Sec 15.5), gas auction (Sec 15.7) |

---

## Appendix D: References

### Ensemble Methods and Meta-Learning

- **Condorcet, M.** (1785). *Essai sur l'application de l'analyse a la probabilite des decisions rendues a la pluralite des voix.*
- **Jacobs, R.A., Jordan, M.I., Nowlan, S.J., & Hinton, G.E.** (1991). "Adaptive mixtures of local experts." *Neural Computation*, 3(1), 79--87.
- **Wolpert, D.H.** (1992). "Stacked generalization." *Neural Networks*, 5(2), 241--259.

### Blockchain, DeFi, and AMMs

- **Angeris, G., & Chitra, T.** (2020). "Improved Price Oracles: Constant Function Market Makers." *Proceedings of the 2nd ACM Conference on Advances in Financial Technologies.*
- **Adams, H., Zinsmeister, N., Salem, M., Keefer, R., & Robinson, D.** (2021). "Uniswap v3 Core." *Uniswap Labs Whitepaper.*
- **Daian, P., Goldfeder, S., Kell, T., et al.** (2020). "Flash Boys 2.0: Frontrunning in Decentralized Exchanges, Miner Extractable Value, and Consensus Instability." *2020 IEEE Symposium on Security and Privacy.*

### Macroeconomic Models

- **Nelson, C.R., & Siegel, A.F.** (1987). "Parsimonious modeling of yield curves." *Journal of Business*, 60(4), 473--489.
- **Taylor, J.B.** (1993). "Discretion versus policy rules in practice." *Carnegie-Rochester Conference Series on Public Policy*, 39, 195--214.

### Market Microstructure and Execution

- **Avellaneda, M., & Stoikov, S.** (2008). "High-frequency trading in a limit order book." *Quantitative Finance*, 8(3), 217--224.
- **Almgren, R., & Chriss, N.** (2001). "Optimal execution of portfolio transactions." *Journal of Risk*, 3(2), 5--39.

### Statistical Learning and Quantitative Methods

- **de Prado, M. Lopez** (2018). *Advances in Financial Machine Learning.* Wiley. (Triple barrier labeling, fractional differentiation, purged cross-validation.)
- **de Prado, M. Lopez** (2020). "Building Diversified Portfolios that Outperform Out-of-Sample." *Journal of Portfolio Management*, 42(4). (Hierarchical Risk Parity.)

### Optimization Methods

- **Nocedal, J., & Wright, S.J.** (2006). *Numerical Optimization.* Springer. (Gradient-based optimization, convergence theory.)
- **Boyd, S., & Vandenberghe, L.** (2004). *Convex Optimization.* Cambridge University Press. (Portfolio optimization, risk minimization.)

### Options and Stochastic Volatility

- **Heston, S.L.** (1993). "A closed-form solution for options with stochastic volatility with applications to bond and currency options." *Review of Financial Studies*, 6(2), 327--343.
- **Black, F., & Litterman, R.** (1992). "Global portfolio optimization." *Financial Analysts Journal*, 48(5), 28--43.

---

*Fine del Documento 14* | Renan Augusto Macena
