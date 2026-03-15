"""Stochastic process models for price dynamics simulation.

Implements three canonical continuous-time models used in quantitative
finance for Monte Carlo pricing, risk estimation, and scenario analysis:

- Geometric Brownian Motion (GBM): constant volatility diffusion
- Merton Jump-Diffusion: GBM augmented with compound Poisson jumps
- Heston Stochastic Volatility: mean-reverting variance process

DESIGN RATIONALE:
    Parameter estimation returns Decimal for financial precision.
    Simulation paths use numpy float64 for computational performance
    in tight inner loops — the precision loss is acceptable for
    Monte Carlo where we average over thousands of paths.
"""

from __future__ import annotations

import math
from decimal import Decimal

import numpy as np

from moneymaker_common.decimal_utils import ZERO, to_decimal
from moneymaker_common.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MIN_OBSERVATIONS = 10
"""Minimum number of return observations required for estimation."""


def _validate_returns(returns: list[Decimal], caller: str) -> bool:
    """Validate a returns series is usable for estimation.

    Args:
        returns: Log-return series as Decimal values.
        caller: Name of the calling method for log context.

    Returns:
        True if valid, False otherwise.
    """
    if not returns:
        logger.warning("%s: empty returns series", caller)
        return False
    if len(returns) < _MIN_OBSERVATIONS:
        logger.warning(
            "%s: insufficient data — got %d, need %d",
            caller,
            len(returns),
            _MIN_OBSERVATIONS,
        )
        return False
    return True


def _decimal_mean(values: list[Decimal]) -> Decimal:
    """Arithmetic mean of a Decimal list."""
    n = Decimal(len(values))
    return sum(values, ZERO) / n


def _decimal_var(values: list[Decimal], mean: Decimal) -> Decimal:
    """Population variance of a Decimal list given the mean."""
    n = Decimal(len(values))
    return sum((v - mean) ** 2 for v in values) / n


def _decimal_std(values: list[Decimal], mean: Decimal) -> Decimal:
    """Population standard deviation of a Decimal list given the mean."""
    variance = _decimal_var(values, mean)
    if variance <= ZERO:
        return ZERO
    return to_decimal(math.sqrt(float(variance)))


# ---------------------------------------------------------------------------
# Geometric Brownian Motion
# ---------------------------------------------------------------------------


class GeometricBrownianMotion:
    """Geometric Brownian Motion (GBM) price model.

    The canonical log-normal diffusion:

        dS = mu * S * dt + sigma * S * dW

    where *mu* is the annualised drift, *sigma* is the annualised
    volatility, and *dW* is a Wiener increment.

    Parameter estimation assumes returns are sampled at a uniform
    frequency and annualises via sqrt-of-time scaling.
    """

    @staticmethod
    def fit(
        returns: list[Decimal],
        periods_per_year: int = 252,
    ) -> tuple[Decimal, Decimal]:
        """Estimate drift and volatility from a series of log returns.

        Uses the maximum-likelihood estimators for a log-normal model:
            sigma = std(returns) * sqrt(periods_per_year)
            mu    = mean(returns) * periods_per_year + 0.5 * sigma^2

        The drift adjustment (+0.5 sigma^2) converts the arithmetic
        mean return to the continuous-time drift parameter.

        Args:
            returns: Sequence of single-period log returns as Decimal.
            periods_per_year: Number of observations per year (252 for
                daily, 52 for weekly, etc.).

        Returns:
            Tuple of (mu, sigma) as Decimal values, or (ZERO, ZERO)
            when estimation is not possible.
        """
        if not _validate_returns(returns, "GBM.fit"):
            return ZERO, ZERO

        mean_r = _decimal_mean(returns)
        std_r = _decimal_std(returns, mean_r)

        if std_r == ZERO:
            logger.warning("GBM.fit: zero variance in returns")
            return ZERO, ZERO

        scale = to_decimal(periods_per_year)
        sqrt_scale = to_decimal(math.sqrt(periods_per_year))

        sigma = std_r * sqrt_scale
        mu = mean_r * scale + Decimal("0.5") * sigma * sigma

        return mu, sigma

    @staticmethod
    def simulate_paths(
        s0: float,
        mu: float,
        sigma: float,
        t: float,
        dt: float,
        n_paths: int,
        seed: int | None = None,
    ) -> np.ndarray:
        """Generate Monte Carlo price paths under GBM dynamics.

        Uses the exact log-normal solution rather than Euler
        discretisation to avoid discretisation bias:

            S(t+dt) = S(t) * exp((mu - 0.5*sigma^2)*dt + sigma*sqrt(dt)*Z)

        Args:
            s0: Initial price level (must be positive).
            mu: Annualised drift (continuous-time).
            sigma: Annualised volatility (must be non-negative).
            t: Time horizon in years.
            dt: Time step in years (e.g. 1/252 for daily).
            n_paths: Number of independent simulation paths.
            seed: Optional RNG seed for reproducibility.

        Returns:
            Array of shape (n_steps + 1, n_paths) with price paths.
            Row 0 is the initial price for every path.

        Raises:
            ValueError: If s0 <= 0, sigma < 0, dt <= 0, or t <= 0.
        """
        if s0 <= 0:
            raise ValueError(f"s0 must be positive, got {s0}")
        if sigma < 0:
            raise ValueError(f"sigma must be non-negative, got {sigma}")
        if dt <= 0 or t <= 0:
            raise ValueError(f"dt and t must be positive, got dt={dt}, t={t}")

        n_steps = int(round(t / dt))
        if n_steps == 0:
            return np.full((1, n_paths), s0)

        rng = np.random.default_rng(seed)
        z = rng.standard_normal((n_steps, n_paths))

        drift = (mu - 0.5 * sigma * sigma) * dt
        diffusion = sigma * math.sqrt(dt)

        log_increments = drift + diffusion * z
        log_paths = np.concatenate(
            [np.zeros((1, n_paths)), np.cumsum(log_increments, axis=0)],
            axis=0,
        )
        return s0 * np.exp(log_paths)


# ---------------------------------------------------------------------------
# Merton Jump-Diffusion
# ---------------------------------------------------------------------------


class MertonJumpDiffusion:
    """Merton (1976) jump-diffusion price model.

    Augments GBM with a compound Poisson jump component:

        dS/S = (mu - lambda*k)*dt + sigma*dW + J*dN

    where *dN* is a Poisson process with intensity *lambda*, and
    *J* ~ N(mu_j, sigma_j^2) is the log-jump size.

    The parameter *k* = exp(mu_j + 0.5*sigma_j^2) - 1 is the
    compensator ensuring the drift is the expected return.
    """

    @staticmethod
    def fit(
        returns: list[Decimal],
        periods_per_year: int = 252,
    ) -> dict[str, Decimal]:
        """Estimate jump-diffusion parameters via method of moments.

        Matches the first four moments of the observed return
        distribution to the theoretical moments of the Merton model.
        The excess kurtosis identifies the jump component: returns
        with kurtosis near 3 (normal) imply negligible jump activity.

        Procedure:
            1. Compute sample mean, variance, skewness, kurtosis.
            2. Attribute excess kurtosis to jumps: higher kurtosis
               implies more frequent or larger jumps.
            3. Decompose variance into diffusion and jump components.

        Args:
            returns: Sequence of single-period log returns as Decimal.
            periods_per_year: Observations per year for annualisation.

        Returns:
            Dictionary with keys: mu, sigma, lam (jump intensity),
            mu_j (mean jump size), sigma_j (jump size std).
            Returns all-zero dict when estimation fails.
        """
        zero_result: dict[str, Decimal] = {
            "mu": ZERO,
            "sigma": ZERO,
            "lam": ZERO,
            "mu_j": ZERO,
            "sigma_j": ZERO,
        }

        if not _validate_returns(returns, "MertonJumpDiffusion.fit"):
            return zero_result

        n = len(returns)
        mean_r = _decimal_mean(returns)
        var_r = _decimal_var(returns, mean_r)

        if var_r == ZERO:
            logger.warning("MertonJumpDiffusion.fit: zero variance")
            return zero_result

        std_r = to_decimal(math.sqrt(float(var_r)))

        # Centralised third and fourth moments
        m3 = sum((r - mean_r) ** 3 for r in returns) / Decimal(n)
        m4 = sum((r - mean_r) ** 4 for r in returns) / Decimal(n)

        # Standardised skewness and excess kurtosis
        if std_r == ZERO:
            skew = ZERO
            excess_kurt = ZERO
        else:
            skew = m3 / (std_r**3)
            kurt = m4 / (std_r**4)
            excess_kurt = kurt - Decimal("3")

        # Clamp excess kurtosis to non-negative: negative excess
        # kurtosis (platykurtic) is not explained by jumps.
        if excess_kurt < ZERO:
            excess_kurt = ZERO

        # --- Moment-matching decomposition ---
        # Jump intensity from excess kurtosis.  For a Poisson-normal
        # jump model the excess kurtosis is approximately:
        #   excess_kurt ~ lam * (mu_j^4 + 6*mu_j^2*sigma_j^2 + 3*sigma_j^4) / var^2
        # As a practical simplification, assume symmetric jumps
        # (mu_j ~ 0) so kurtosis is driven by sigma_j and lam.
        # Then excess_kurt ~ 3 * lam * sigma_j^4 / var^2.
        #
        # We solve for lam and sigma_j simultaneously:
        #   Assume lam = excess_kurt / 3 (normalised intensity,
        #   then rescale with periods_per_year).
        #   sigma_j^2 = var / max(lam, 1)

        scale = to_decimal(periods_per_year)
        sqrt_scale = to_decimal(math.sqrt(periods_per_year))

        if excess_kurt == ZERO:
            # No detectable jump component — degenerate to GBM
            sigma = std_r * sqrt_scale
            mu = mean_r * scale + Decimal("0.5") * sigma * sigma
            return {
                "mu": mu,
                "sigma": sigma,
                "lam": ZERO,
                "mu_j": ZERO,
                "sigma_j": ZERO,
            }

        # Annualised jump intensity
        lam_raw = excess_kurt / Decimal("3")
        lam = lam_raw * scale
        # Ensure at least 1 expected jump per year when kurtosis is present
        if lam < Decimal("1"):
            lam = Decimal("1")

        # Jump variance: attribute a fraction of total variance
        # proportional to lam_raw / (1 + lam_raw)
        jump_var_fraction = lam_raw / (Decimal("1") + lam_raw)
        jump_var = var_r * jump_var_fraction
        diffusion_var = var_r * (Decimal("1") - jump_var_fraction)

        sigma_j = to_decimal(math.sqrt(float(jump_var))) if jump_var > ZERO else ZERO
        sigma = (
            to_decimal(math.sqrt(float(diffusion_var))) * sqrt_scale
            if diffusion_var > ZERO
            else ZERO
        )

        # Jump mean: derived from skewness
        # skew ~ lam * mu_j * (3*sigma_j^2 + mu_j^2) / var^(3/2)
        # Simplified: mu_j ~ skew * std_r / max(lam_raw, 1)
        mu_j = skew * std_r / (Decimal("1") + lam_raw) if lam_raw > ZERO else ZERO

        # Drift with jump compensator
        k = to_decimal(math.exp(float(mu_j) + 0.5 * float(sigma_j) ** 2)) - Decimal("1")
        mu = mean_r * scale + Decimal("0.5") * sigma * sigma + lam * k

        return {
            "mu": mu,
            "sigma": sigma,
            "lam": lam,
            "mu_j": mu_j,
            "sigma_j": sigma_j,
        }

    @staticmethod
    def jump_probability(
        returns: list[Decimal],
        window: int = 20,
        threshold_sigma: Decimal = Decimal("3"),
    ) -> Decimal:
        """Estimate the probability of a jump event in a recent window.

        A "jump" is defined as a return exceeding *threshold_sigma*
        standard deviations from the full-sample mean.  The returned
        value is the empirical frequency of such events in the last
        *window* observations.

        Args:
            returns: Full return series (at least *window* long).
            window: Number of recent observations to inspect.
            threshold_sigma: Multiple of sigma defining a jump.

        Returns:
            Jump probability as a Decimal in [0, 1], or ZERO when
            data is insufficient.
        """
        if not returns or len(returns) < window:
            return ZERO

        mean_r = _decimal_mean(returns)
        std_r = _decimal_std(returns, mean_r)

        if std_r == ZERO:
            return ZERO

        threshold = threshold_sigma * std_r
        recent = returns[-window:]
        jumps = sum(1 for r in recent if abs(r - mean_r) > threshold)

        return to_decimal(jumps) / to_decimal(window)

    @staticmethod
    def simulate_paths(
        params: dict[str, float],
        s0: float,
        t: float,
        dt: float,
        n_paths: int,
        seed: int | None = None,
    ) -> np.ndarray:
        """Generate Monte Carlo paths under Merton jump-diffusion.

        At each time step the log-price evolves as:

            ln S(t+dt) = ln S(t) + (mu - 0.5*sigma^2 - lam*k)*dt
                         + sigma*sqrt(dt)*Z
                         + sum_{i=1}^{N(dt)} J_i

        where N(dt) ~ Poisson(lam*dt) and J_i ~ N(mu_j, sigma_j^2).

        Args:
            params: Dict with keys mu, sigma, lam, mu_j, sigma_j
                (float values).
            s0: Initial price (must be positive).
            t: Time horizon in years.
            dt: Time step in years.
            n_paths: Number of independent paths.
            seed: Optional RNG seed.

        Returns:
            Array of shape (n_steps + 1, n_paths) with price paths.

        Raises:
            ValueError: If s0 <= 0, dt <= 0, or t <= 0.
        """
        if s0 <= 0:
            raise ValueError(f"s0 must be positive, got {s0}")
        if dt <= 0 or t <= 0:
            raise ValueError(f"dt and t must be positive, got dt={dt}, t={t}")

        mu = params.get("mu", 0.0)
        sigma = max(params.get("sigma", 0.0), 0.0)
        lam = max(params.get("lam", 0.0), 0.0)
        mu_j = params.get("mu_j", 0.0)
        sigma_j = max(params.get("sigma_j", 0.0), 0.0)

        # Jump compensator
        k = math.exp(mu_j + 0.5 * sigma_j**2) - 1.0

        n_steps = int(round(t / dt))
        if n_steps == 0:
            return np.full((1, n_paths), s0)

        rng = np.random.default_rng(seed)

        # Diffusion component
        z = rng.standard_normal((n_steps, n_paths))
        drift = (mu - 0.5 * sigma**2 - lam * k) * dt
        diffusion = sigma * math.sqrt(dt) * z

        # Jump component
        n_jumps = rng.poisson(lam * dt, (n_steps, n_paths))
        # Aggregate jump sizes: sum of N(mu_j, sigma_j^2) for each jump
        jump_sizes = np.zeros((n_steps, n_paths))
        max_jumps = int(n_jumps.max()) if n_jumps.max() > 0 else 0
        if max_jumps > 0:
            # Vectorised: generate max_jumps layers, mask by count
            for j_idx in range(1, max_jumps + 1):
                mask = n_jumps >= j_idx
                draws = rng.normal(mu_j, sigma_j if sigma_j > 0 else 1e-12, (n_steps, n_paths))
                jump_sizes += draws * mask

        log_increments = drift + diffusion + jump_sizes
        log_paths = np.concatenate(
            [np.zeros((1, n_paths)), np.cumsum(log_increments, axis=0)],
            axis=0,
        )
        return s0 * np.exp(log_paths)


# ---------------------------------------------------------------------------
# Heston Stochastic Volatility
# ---------------------------------------------------------------------------


class HestonStochasticVolatility:
    """Heston (1993) stochastic volatility model.

    Models price and variance as a coupled SDE system:

        dS = mu * S * dt + sqrt(V) * S * dW_S
        dV = kappa * (theta - V) * dt + xi * sqrt(V) * dW_V
        corr(dW_S, dW_V) = rho

    Parameters:
        kappa: Mean-reversion speed of the variance process.
        theta: Long-run (equilibrium) variance level.
        xi:    Volatility of variance ("vol of vol").
        rho:   Instantaneous correlation between price and
               variance Brownian motions.

    The Feller condition 2*kappa*theta > xi^2 ensures that the
    variance process remains strictly positive in continuous time.
    In discrete simulation the full truncation scheme is used to
    handle negative variance samples.
    """

    @staticmethod
    def fit(
        returns: list[Decimal],
        realized_vol_series: list[Decimal],
        periods_per_year: int = 252,
    ) -> dict[str, Decimal]:
        """Estimate Heston parameters via method of moments.

        This is a simplified estimator suitable for initialisation.
        For production calibration, use a characteristic-function
        based approach (not implemented here).

        Procedure:
            1. theta:  long-run variance from mean of realised
                       variance series.
            2. kappa:  mean-reversion speed from first-order
                       autocorrelation of variance increments.
            3. xi:     vol-of-vol from standard deviation of
                       variance changes.
            4. rho:    sample correlation between returns and
                       variance changes (leverage effect).
            5. mu:     drift from mean return adjusted for variance.

        Args:
            returns: Log-return series (Decimal).
            realized_vol_series: Corresponding realised volatility
                observations (same length as returns).
            periods_per_year: Observations per year.

        Returns:
            Dictionary with keys: mu, kappa, theta, xi, rho.
            All-zero dict when estimation fails.
        """
        zero_result: dict[str, Decimal] = {
            "mu": ZERO,
            "kappa": ZERO,
            "theta": ZERO,
            "xi": ZERO,
            "rho": ZERO,
        }

        if not _validate_returns(returns, "Heston.fit"):
            return zero_result

        if len(realized_vol_series) != len(returns):
            logger.warning(
                "Heston.fit: returns length %d != vol series length %d",
                len(returns),
                len(realized_vol_series),
            )
            return zero_result

        if len(realized_vol_series) < _MIN_OBSERVATIONS:
            logger.warning("Heston.fit: insufficient vol data")
            return zero_result

        # Convert realised vol to variance (V = sigma^2)
        variance_series = [v * v for v in realized_vol_series]

        scale = to_decimal(periods_per_year)

        # --- theta: long-run variance (annualised) ---
        theta = _decimal_mean(variance_series) * scale

        if theta == ZERO:
            logger.warning("Heston.fit: zero mean variance")
            return zero_result

        # --- kappa: mean-reversion speed ---
        # From discrete AR(1) on variance: V(t) = a + b*V(t-1) + eps
        # kappa = -ln(b) * periods_per_year
        # Approximate b from first-order autocorrelation of V
        mean_v = _decimal_mean(variance_series)
        n = len(variance_series)

        numerator = ZERO
        denominator = ZERO
        for i in range(1, n):
            dev_prev = variance_series[i - 1] - mean_v
            dev_curr = variance_series[i] - mean_v
            numerator += dev_prev * dev_curr
            denominator += dev_prev * dev_prev

        if denominator == ZERO:
            logger.warning("Heston.fit: zero variance in vol series")
            return zero_result

        autocorr = numerator / denominator
        # Clamp to (0, 1) to ensure positive, finite kappa
        autocorr_f = float(autocorr)
        autocorr_f = max(0.01, min(autocorr_f, 0.99))
        kappa = to_decimal(-math.log(autocorr_f) * periods_per_year)

        # --- xi: vol of vol ---
        # Standard deviation of variance changes, annualised
        var_changes = [variance_series[i] - variance_series[i - 1] for i in range(1, n)]
        mean_dv = _decimal_mean(var_changes)
        std_dv = _decimal_std(var_changes, mean_dv)
        # xi relates to std of dV: xi = std(dV) / sqrt(mean(V) * dt)
        mean_v_f = float(mean_v)
        dt_f = 1.0 / periods_per_year
        if mean_v_f > 0 and dt_f > 0:
            xi = to_decimal(float(std_dv) / math.sqrt(mean_v_f * dt_f))
        else:
            xi = ZERO

        # --- rho: leverage correlation ---
        # Correlation between returns and variance changes
        if len(var_changes) != len(returns) - 1:
            # Align: use returns[1:] with var_changes
            aligned_returns = returns[1:]
        else:
            aligned_returns = returns[1:]

        if len(aligned_returns) != len(var_changes):
            # Trim to matching length
            min_len = min(len(aligned_returns), len(var_changes))
            aligned_returns = aligned_returns[:min_len]
            var_changes = var_changes[:min_len]

        mean_ret = _decimal_mean(aligned_returns)
        mean_dv = _decimal_mean(var_changes)
        std_ret = _decimal_std(aligned_returns, mean_ret)
        std_dv = _decimal_std(var_changes, mean_dv)

        if std_ret > ZERO and std_dv > ZERO:
            cov_rv = sum(
                (aligned_returns[i] - mean_ret) * (var_changes[i] - mean_dv)
                for i in range(len(aligned_returns))
            ) / Decimal(len(aligned_returns))
            rho = cov_rv / (std_ret * std_dv)
            # Clamp rho to [-1, 1]
            if rho > Decimal("1"):
                rho = Decimal("1")
            elif rho < Decimal("-1"):
                rho = Decimal("-1")
        else:
            rho = ZERO

        # --- mu: drift ---
        mean_r = _decimal_mean(returns)
        mu = mean_r * scale + Decimal("0.5") * theta if theta > ZERO else mean_r * scale

        return {
            "mu": mu,
            "kappa": kappa,
            "theta": theta,
            "xi": xi,
            "rho": rho,
        }

    @staticmethod
    def simulate_paths(
        params: dict[str, float],
        s0: float,
        v0: float,
        t: float,
        dt: float,
        n_paths: int,
        seed: int | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Generate Monte Carlo paths under Heston dynamics.

        Uses Euler-Maruyama discretisation with full truncation:
        the variance is floored at zero in both the drift and
        diffusion terms to prevent negative variance samples from
        contaminating the simulation.

            V_plus = max(V, 0)
            S(t+dt) = S(t) * exp((mu - 0.5*V_plus)*dt
                      + sqrt(V_plus*dt)*Z_S)
            V(t+dt) = V(t) + kappa*(theta - V_plus)*dt
                      + xi*sqrt(V_plus*dt)*Z_V

        Correlated Brownian motions are constructed via Cholesky
        decomposition: Z_V = rho*Z_S + sqrt(1 - rho^2)*Z_indep.

        Args:
            params: Dict with keys mu, kappa, theta, xi, rho
                (float values).
            s0: Initial price (must be positive).
            v0: Initial variance (must be non-negative).
            t: Time horizon in years.
            dt: Time step in years.
            n_paths: Number of independent paths.
            seed: Optional RNG seed.

        Returns:
            Tuple of (price_paths, vol_paths), each of shape
            (n_steps + 1, n_paths).

        Raises:
            ValueError: If s0 <= 0, v0 < 0, dt <= 0, or t <= 0.
        """
        if s0 <= 0:
            raise ValueError(f"s0 must be positive, got {s0}")
        if v0 < 0:
            raise ValueError(f"v0 must be non-negative, got {v0}")
        if dt <= 0 or t <= 0:
            raise ValueError(f"dt and t must be positive, got dt={dt}, t={t}")

        mu = params.get("mu", 0.0)
        kappa = params.get("kappa", 0.0)
        theta = max(params.get("theta", 0.0), 0.0)
        xi = max(params.get("xi", 0.0), 0.0)
        rho = params.get("rho", 0.0)
        rho = max(-1.0, min(1.0, rho))

        n_steps = int(round(t / dt))
        if n_steps == 0:
            return (
                np.full((1, n_paths), s0),
                np.full((1, n_paths), v0),
            )

        rng = np.random.default_rng(seed)

        # Pre-allocate output arrays
        price_paths = np.empty((n_steps + 1, n_paths))
        vol_paths = np.empty((n_steps + 1, n_paths))
        price_paths[0] = s0
        vol_paths[0] = v0

        sqrt_dt = math.sqrt(dt)
        sqrt_one_minus_rho2 = math.sqrt(max(1.0 - rho * rho, 0.0))

        for step in range(n_steps):
            v_current = vol_paths[step]

            # Full truncation: floor variance at zero
            v_plus = np.maximum(v_current, 0.0)
            sqrt_v_plus = np.sqrt(v_plus)

            # Correlated normals via Cholesky
            z1 = rng.standard_normal(n_paths)
            z_indep = rng.standard_normal(n_paths)
            z2 = rho * z1 + sqrt_one_minus_rho2 * z_indep

            # Price update (log-Euler for positivity)
            price_paths[step + 1] = price_paths[step] * np.exp(
                (mu - 0.5 * v_plus) * dt + sqrt_v_plus * sqrt_dt * z1
            )

            # Variance update (Euler-Maruyama with full truncation)
            vol_paths[step + 1] = (
                v_current + kappa * (theta - v_plus) * dt + xi * sqrt_v_plus * sqrt_dt * z2
            )

        return price_paths, vol_paths
