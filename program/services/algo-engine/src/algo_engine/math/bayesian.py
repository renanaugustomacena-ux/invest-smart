"""Bayesian methods for regime detection and strategy selection.

Implements online Bayesian changepoint detection (simplified Adams & MacKay
2007), Thompson Sampling for multi-armed bandit strategy selection, and
conjugate Normal-Inverse-Gamma parameter estimation.
"""

from __future__ import annotations

import math
from decimal import Decimal, InvalidOperation

import numpy as np

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.enums import MarketRegime
from moneymaker_common.logging import get_logger

logger = get_logger(__name__)

ONE = Decimal("1")
TWO = Decimal("2")
_HALF = Decimal("0.5")
_EPSILON = Decimal("1e-30")
_TWO_PI = Decimal(str(2.0 * math.pi))


def _decimal_exp(x: Decimal) -> Decimal:
    """Compute exp(x) for a Decimal value via float conversion."""
    try:
        return Decimal(str(math.exp(float(x))))
    except (OverflowError, InvalidOperation):
        if x > ZERO:
            return Decimal("1e308")
        return ZERO


def _decimal_sqrt(x: Decimal) -> Decimal:
    """Compute sqrt(x) for a Decimal value."""
    if x <= ZERO:
        return ZERO
    return Decimal(str(math.sqrt(float(x))))


def _gaussian_pdf(x: Decimal, mu: Decimal, var: Decimal) -> Decimal:
    """Evaluate the Gaussian probability density function."""
    if var <= ZERO:
        return ONE if x == mu else ZERO
    exponent = -((x - mu) ** 2) / (TWO * var)
    normalization = ONE / _decimal_sqrt(_TWO_PI * var)
    return normalization * _decimal_exp(exponent)


class BayesianRegimeDetector:
    """Online Bayesian changepoint detection for market regime identification.

    Simplified version of the Adams & MacKay (2007) algorithm.  Maintains a
    run-length distribution and maps it to regime posteriors via a Gaussian
    observation model with online mean/variance estimation.

    Args:
        n_regimes: Number of discrete regimes to track.
        hazard_rate: Reciprocal of expected run length between changepoints.
            A value of 0.01 expects regime changes every ~100 bars.
    """

    _REGIME_NAMES: list[str] = [r.value for r in MarketRegime]

    def __init__(
        self,
        n_regimes: int = 5,
        hazard_rate: Decimal = Decimal("0.01"),
    ) -> None:
        self._n_regimes = min(n_regimes, len(self._REGIME_NAMES))
        self._hazard = hazard_rate
        self._regime_names = self._REGIME_NAMES[: self._n_regimes]

        # Run-length distribution: index i = probability that current run
        # length is i.  Index 0 = changepoint just happened.
        self._run_length_probs: list[Decimal] = [ONE]

        # Online sufficient statistics per run length for the Gaussian
        # observation model.  Each entry stores (count, mean, M2) where M2
        # is the sum of squared deviations (Welford's algorithm).
        self._stats: list[tuple[int, Decimal, Decimal]] = [(0, ZERO, ZERO)]

        self._observation_count = 0
        self._posteriors: dict[str, Decimal] = {
            name: ONE / Decimal(str(self._n_regimes))
            for name in self._regime_names
        }

    def update(self, observation: Decimal) -> dict[str, Decimal]:
        """Incorporate a new observation and return regime posteriors.

        Args:
            observation: New price return or feature value.

        Returns:
            Dictionary mapping regime names to posterior probabilities
            that sum to one.
        """
        self._observation_count += 1
        n_rl = len(self._run_length_probs)

        # --- Step 1: compute predictive probabilities for each run length ---
        pred_probs: list[Decimal] = []
        for i in range(n_rl):
            count, mean, m2 = self._stats[i]
            if count < 2:
                # Prior predictive: use a broad Gaussian.
                pred_probs.append(Decimal("0.1"))
            else:
                var = m2 / Decimal(str(count))
                if var <= ZERO:
                    var = _EPSILON
                pred_probs.append(_gaussian_pdf(observation, mean, var))

        # --- Step 2: compute growth probabilities (no changepoint) ---
        growth_probs: list[Decimal] = []
        for i in range(n_rl):
            growth_probs.append(
                self._run_length_probs[i] * pred_probs[i] * (ONE - self._hazard)
            )

        # --- Step 3: compute changepoint probability (run length = 0) ---
        cp_prob = ZERO
        for i in range(n_rl):
            cp_prob += self._run_length_probs[i] * pred_probs[i] * self._hazard

        # --- Step 4: assemble new run-length distribution ---
        new_probs = [cp_prob] + growth_probs
        total = sum(new_probs)
        if total > ZERO:
            new_probs = [p / total for p in new_probs]

        self._run_length_probs = new_probs

        # --- Step 5: update sufficient statistics (Welford's online) ---
        new_stats: list[tuple[int, Decimal, Decimal]] = [
            (0, ZERO, ZERO)  # changepoint resets statistics
        ]
        for i in range(n_rl):
            count, mean, m2 = self._stats[i]
            count += 1
            delta = observation - mean
            mean = mean + delta / Decimal(str(count))
            delta2 = observation - mean
            m2 = m2 + delta * delta2
            new_stats.append((count, mean, m2))

        self._stats = new_stats

        # --- Step 6: map run-length distribution to regime posteriors ---
        self._posteriors = self._run_length_to_regimes()

        return dict(self._posteriors)

    def _run_length_to_regimes(self) -> dict[str, Decimal]:
        """Map the run-length distribution to regime posteriors.

        Short run lengths indicate recent changepoints (high volatility /
        reversal), long run lengths indicate stable regimes.  The mapping
        divides run lengths into equal-sized bins corresponding to regimes.
        """
        n_rl = len(self._run_length_probs)
        regime_probs: dict[str, Decimal] = {
            name: ZERO for name in self._regime_names
        }

        if n_rl == 0:
            uniform = ONE / Decimal(str(self._n_regimes))
            return {name: uniform for name in self._regime_names}

        # Bin run lengths into regimes: short runs -> volatile regimes,
        # long runs -> trending regimes.
        bin_size = max(1, n_rl // self._n_regimes)

        for i, prob in enumerate(self._run_length_probs):
            bin_idx = min(i // bin_size, self._n_regimes - 1)
            regime_probs[self._regime_names[bin_idx]] += prob

        # Normalise to ensure probabilities sum to one.
        total = sum(regime_probs.values())
        if total > ZERO:
            regime_probs = {k: v / total for k, v in regime_probs.items()}

        return regime_probs

    def get_posteriors(self) -> dict[str, Decimal]:
        """Return current regime posteriors without incorporating new data."""
        return dict(self._posteriors)

    def most_likely_regime(self) -> tuple[str, Decimal]:
        """Return the regime with the highest posterior probability.

        Returns:
            Tuple of (regime_name, posterior_probability).
        """
        best_name = self._regime_names[0]
        best_prob = ZERO
        for name, prob in self._posteriors.items():
            if prob > best_prob:
                best_name = name
                best_prob = prob
        return best_name, best_prob


class ThompsonSamplingSelector:
    """Multi-armed bandit for strategy selection via Thompson Sampling.

    Maintains a Beta(alpha, beta) distribution per strategy arm.  On each
    call to :meth:`select`, a sample is drawn from every arm's Beta
    distribution and the arm with the highest sample is chosen, balancing
    exploration and exploitation naturally.

    Args:
        strategy_names: List of strategy identifiers (arm names).
    """

    def __init__(self, strategy_names: list[str]) -> None:
        if not strategy_names:
            raise ValueError("strategy_names must not be empty")

        self._strategies = list(strategy_names)
        # Beta(1, 1) = uniform prior for each arm.
        self._alpha: dict[str, Decimal] = {s: ONE for s in self._strategies}
        self._beta: dict[str, Decimal] = {s: ONE for s in self._strategies}
        self._samples: dict[str, int] = {s: 0 for s in self._strategies}

    def select(self) -> str:
        """Sample from each arm's Beta distribution and return the best.

        Returns:
            Name of the strategy with the highest Thompson sample.
        """
        best_strategy = self._strategies[0]
        best_sample = Decimal("-1")

        for strategy in self._strategies:
            a = float(self._alpha[strategy])
            b = float(self._beta[strategy])
            sample = Decimal(str(np.random.beta(a, b)))
            if sample > best_sample:
                best_sample = sample
                best_strategy = strategy

        return best_strategy

    def update(self, strategy: str, reward: Decimal) -> None:
        """Update the posterior for *strategy* based on observed reward.

        A positive reward increments alpha (success count); a non-positive
        reward increments beta (failure count).

        Args:
            strategy: Strategy name that was played.
            reward: Observed reward (profit/loss or normalised score).

        Raises:
            ValueError: If *strategy* is not a known arm.
        """
        if strategy not in self._alpha:
            raise ValueError(
                f"Unknown strategy '{strategy}'. "
                f"Known: {self._strategies}"
            )

        self._samples[strategy] += 1

        if reward > ZERO:
            self._alpha[strategy] += ONE
        else:
            self._beta[strategy] += ONE

    def get_statistics(self) -> dict[str, dict]:
        """Return summary statistics for each strategy arm.

        Returns:
            Dictionary mapping strategy name to a dict with keys
            ``alpha``, ``beta``, ``mean`` (= alpha / (alpha + beta)),
            and ``samples``.
        """
        stats: dict[str, dict] = {}
        for s in self._strategies:
            a = self._alpha[s]
            b = self._beta[s]
            total = a + b
            mean = a / total if total > ZERO else ZERO
            stats[s] = {
                "alpha": a,
                "beta": b,
                "mean": mean,
                "samples": self._samples[s],
            }
        return stats


class BayesianParameterEstimator:
    """Online Bayesian estimation of mean and variance.

    Uses a Normal-Inverse-Gamma (NIG) conjugate prior which allows closed-form
    posterior updates.  The four hyper-parameters (mu, kappa, alpha, beta) are
    updated incrementally with each new observation.

    The posterior mean of the data-generating mean is ``mu``.
    The posterior mean of the data-generating variance is ``beta / (alpha - 1)``
    (valid when alpha > 1).

    Args:
        prior_mu: Prior mean.
        prior_kappa: Prior strength (pseudo-observations for the mean).
        prior_alpha: Prior shape for the inverse-gamma on variance.
        prior_beta: Prior scale for the inverse-gamma on variance.
    """

    def __init__(
        self,
        prior_mu: Decimal = ZERO,
        prior_kappa: Decimal = ONE,
        prior_alpha: Decimal = ONE,
        prior_beta: Decimal = ONE,
    ) -> None:
        self._mu = prior_mu
        self._kappa = prior_kappa
        self._alpha = prior_alpha
        self._beta = prior_beta
        self._n = 0

    def update(self, observation: Decimal) -> None:
        """Incorporate a new observation into the posterior.

        Updates the NIG hyper-parameters in O(1) time.

        Args:
            observation: New data point.
        """
        self._n += 1
        old_mu = self._mu
        old_kappa = self._kappa

        self._kappa = old_kappa + ONE
        self._mu = (old_kappa * old_mu + observation) / self._kappa
        self._alpha = self._alpha + _HALF
        self._beta = (
            self._beta
            + (old_kappa * (observation - old_mu) ** 2) / (TWO * self._kappa)
        )

    def posterior_mean(self) -> Decimal:
        """Return the posterior estimate of the data-generating mean."""
        return self._mu

    def posterior_variance(self) -> Decimal:
        """Return the posterior estimate of the data-generating variance.

        The mean of the Inverse-Gamma posterior on variance is
        beta / (alpha - 1), valid when alpha > 1.  Returns zero if
        insufficient data to estimate.
        """
        if self._alpha <= ONE:
            return ZERO
        return self._beta / (self._alpha - ONE)

    def credible_interval(
        self, alpha: Decimal = Decimal("0.05"),
    ) -> tuple[Decimal, Decimal]:
        """Compute a symmetric credible interval for the mean.

        Uses a Gaussian approximation to the marginal posterior of the mean
        (valid with enough observations).  The interval covers
        ``1 - alpha`` of the posterior mass.

        Args:
            alpha: Significance level.  Default 0.05 gives a 95% interval.

        Returns:
            Tuple of (lower_bound, upper_bound).
        """
        if self._n == 0 or self._alpha <= ONE:
            return self._mu, self._mu

        var = self.posterior_variance()
        # Marginal variance of the mean = var / kappa.
        mean_var = var / self._kappa
        std = _decimal_sqrt(mean_var)

        # z-score for the credible level via the normal approximation.
        # For alpha=0.05, z ~ 1.96.
        from decimal import Decimal as D

        half_alpha = float(alpha) / 2.0
        # Use scipy-free inverse normal CDF approximation via math.
        # erfinv is not in stdlib, so use a rational approximation.
        z = Decimal(str(self._inv_normal_cdf(1.0 - half_alpha)))

        lower = self._mu - z * std
        upper = self._mu + z * std
        return lower, upper

    @staticmethod
    def _inv_normal_cdf(p: float) -> float:
        """Rational approximation to the inverse standard normal CDF.

        Accurate to ~4.5e-4 for 0 < p < 1.  Uses the Abramowitz & Stegun
        approximation (formula 26.2.23).
        """
        if p <= 0.0:
            return -6.0
        if p >= 1.0:
            return 6.0
        if p == 0.5:
            return 0.0

        if p > 0.5:
            return -BayesianParameterEstimator._inv_normal_cdf(1.0 - p)

        t = math.sqrt(-2.0 * math.log(p))
        # Coefficients for the rational approximation.
        c0, c1, c2 = 2.515517, 0.802853, 0.010328
        d1, d2, d3 = 1.432788, 0.189269, 0.001308
        result = t - (c0 + c1 * t + c2 * t * t) / (
            1.0 + d1 * t + d2 * t * t + d3 * t * t * t
        )
        return -result
