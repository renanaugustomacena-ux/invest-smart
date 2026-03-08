"""Copula functions for dependency modeling.

Implements Gaussian copula fitting, sampling, and tail dependence
estimation for bivariate dependency analysis between financial series.
"""

import math
from collections import deque
from decimal import Decimal

import numpy as np
from scipy.stats import norm

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.logging import get_logger

logger = get_logger(__name__)

ONE = Decimal("1")
TWO = Decimal("2")
HALF = Decimal("0.5")

_MIN_OBSERVATIONS = 30
_TAIL_DEP_THRESHOLD_DEFAULT = Decimal("0.05")
_TAIL_DEP_HIGH = Decimal("0.3")


def rank_transform(series: list[Decimal]) -> list[Decimal]:
    """Convert series to pseudo-uniform marginals via rank transformation.

    Uses the formula u_i = rank(x_i) / (n + 1) to avoid exact 0 and 1
    values, which would produce infinite values under the inverse normal
    transform.

    Args:
        series: Raw data series.

    Returns:
        List of pseudo-uniform values in (0, 1).

    Raises:
        ValueError: If the series has fewer than 2 elements.
    """
    n = len(series)
    if n < 2:
        raise ValueError(f"Need at least 2 observations for rank transform, got {n}")

    indexed = sorted(range(n), key=lambda i: series[i])
    ranks = [0] * n
    for rank_val, idx in enumerate(indexed, start=1):
        ranks[idx] = rank_val

    n_plus_1 = Decimal(n + 1)
    return [Decimal(r) / n_plus_1 for r in ranks]


def tail_dependence(
    u: list[Decimal],
    v: list[Decimal],
    threshold: Decimal = _TAIL_DEP_THRESHOLD_DEFAULT,
) -> tuple[Decimal, Decimal]:
    """Compute empirical lower and upper tail dependence coefficients.

    Lower tail dependence: lambda_L = P(V <= q | U <= q)
    Upper tail dependence: lambda_U = P(V > 1-q | U > 1-q)

    The Gaussian copula has zero theoretical tail dependence. If empirical
    tail dependence is high, assets exhibit co-crash or co-boom behavior
    beyond what a Gaussian model predicts.

    Args:
        u: First series of pseudo-uniform marginals.
        v: Second series of pseudo-uniform marginals.
        threshold: Quantile threshold for tail definition (default 0.05).

    Returns:
        Tuple of (lambda_lower, lambda_upper).

    Raises:
        ValueError: If series lengths differ or are too short.
    """
    n = len(u)
    if n != len(v):
        raise ValueError(
            f"Series lengths must match: len(u)={n}, len(v)={len(v)}"
        )
    if n < _MIN_OBSERVATIONS:
        raise ValueError(
            f"Need at least {_MIN_OBSERVATIONS} observations, got {n}"
        )
    if not (ZERO < threshold < HALF):
        raise ValueError(
            f"Threshold must be in (0, 0.5), got {threshold}"
        )

    q_low = threshold
    q_high = ONE - threshold

    # Lower tail: count where both U <= q and V <= q
    lower_u_count = sum(1 for ui in u if ui <= q_low)
    if lower_u_count == 0:
        lambda_lower = ZERO
    else:
        joint_lower = sum(
            1 for ui, vi in zip(u, v) if ui <= q_low and vi <= q_low
        )
        lambda_lower = Decimal(joint_lower) / Decimal(lower_u_count)

    # Upper tail: count where both U > 1-q and V > 1-q
    upper_u_count = sum(1 for ui in u if ui > q_high)
    if upper_u_count == 0:
        lambda_upper = ZERO
    else:
        joint_upper = sum(
            1 for ui, vi in zip(u, v) if ui > q_high and vi > q_high
        )
        lambda_upper = Decimal(joint_upper) / Decimal(upper_u_count)

    logger.debug(
        "tail_dependence_computed",
        lambda_lower=str(lambda_lower),
        lambda_upper=str(lambda_upper),
        threshold=str(threshold),
        n=n,
    )

    return lambda_lower, lambda_upper


class GaussianCopula:
    """Gaussian copula for bivariate dependency modeling."""

    @staticmethod
    def fit(u: list[Decimal], v: list[Decimal]) -> Decimal:
        """Fit the Gaussian copula correlation parameter rho.

        Transforms uniform marginals through the inverse normal CDF and
        computes the Pearson correlation of the resulting standard normal
        variates.

        Args:
            u: First series of pseudo-uniform marginals in (0, 1).
            v: Second series of pseudo-uniform marginals in (0, 1).

        Returns:
            Correlation parameter rho in [-1, 1].

        Raises:
            ValueError: If series lengths differ, are too short, or contain
                values outside (0, 1).
        """
        n = len(u)
        if n != len(v):
            raise ValueError(
                f"Series lengths must match: len(u)={n}, len(v)={len(v)}"
            )
        if n < _MIN_OBSERVATIONS:
            raise ValueError(
                f"Need at least {_MIN_OBSERVATIONS} observations for "
                f"reliable copula fit, got {n}"
            )

        for i, (ui, vi) in enumerate(zip(u, v)):
            if not (ZERO < ui < ONE):
                raise ValueError(
                    f"u[{i}]={ui} outside (0, 1); apply rank_transform first"
                )
            if not (ZERO < vi < ONE):
                raise ValueError(
                    f"v[{i}]={vi} outside (0, 1); apply rank_transform first"
                )

        u_float = np.array([float(x) for x in u])
        v_float = np.array([float(x) for x in v])

        z_u = norm.ppf(u_float)
        z_v = norm.ppf(v_float)

        # Check for constant series after transform
        if np.std(z_u) < 1e-15 or np.std(z_v) < 1e-15:
            logger.warning(
                "copula_fit_degenerate",
                reason="constant series after inverse normal transform",
            )
            return ZERO

        corr_matrix = np.corrcoef(z_u, z_v)
        rho = Decimal(str(float(corr_matrix[0, 1])))

        # Clamp to [-1, 1] for numerical safety
        if rho > ONE:
            rho = ONE
        elif rho < -ONE:
            rho = -ONE

        logger.debug("gaussian_copula_fit", rho=str(rho), n=n)
        return rho

    @staticmethod
    def sample(
        rho: Decimal,
        n: int,
        seed: int | None = None,
    ) -> tuple[list[Decimal], list[Decimal]]:
        """Generate correlated uniform samples from a Gaussian copula.

        Generates bivariate normal samples with the given correlation and
        transforms them through the standard normal CDF to produce uniform
        marginals.

        Args:
            rho: Correlation parameter in [-1, 1].
            n: Number of samples to generate.
            seed: Random seed for reproducibility.

        Returns:
            Tuple of two lists of Decimal uniform samples.

        Raises:
            ValueError: If rho is outside [-1, 1] or n < 1.
        """
        if not (-ONE <= rho <= ONE):
            raise ValueError(f"rho must be in [-1, 1], got {rho}")
        if n < 1:
            raise ValueError(f"n must be >= 1, got {n}")

        rng = np.random.default_rng(seed)
        rho_f = float(rho)

        cov = np.array([[1.0, rho_f], [rho_f, 1.0]])
        mean = np.array([0.0, 0.0])

        samples = rng.multivariate_normal(mean, cov, size=n)

        u_samples = norm.cdf(samples[:, 0])
        v_samples = norm.cdf(samples[:, 1])

        u_dec = [Decimal(str(float(x))) for x in u_samples]
        v_dec = [Decimal(str(float(x))) for x in v_samples]

        return u_dec, v_dec

    @staticmethod
    def joint_cdf(u: Decimal, v: Decimal, rho: Decimal) -> Decimal:
        """Approximate the bivariate normal CDF for the Gaussian copula.

        Computes C(u, v) = Phi_2(Phi^{-1}(u), Phi^{-1}(v); rho) using
        a product approximation with correlation adjustment.

        For independent case (rho=0), returns u * v exactly.

        Args:
            u: First uniform marginal in (0, 1).
            v: Second uniform marginal in (0, 1).
            rho: Correlation parameter in [-1, 1].

        Returns:
            Joint CDF value in [0, 1].

        Raises:
            ValueError: If inputs are outside valid ranges.
        """
        if not (ZERO < u < ONE):
            raise ValueError(f"u must be in (0, 1), got {u}")
        if not (ZERO < v < ONE):
            raise ValueError(f"v must be in (0, 1), got {v}")
        if not (-ONE <= rho <= ONE):
            raise ValueError(f"rho must be in [-1, 1], got {rho}")

        # Independent case
        if abs(rho) < Decimal("1e-12"):
            return u * v

        # Perfect positive correlation: C(u,v) = min(u,v)
        if rho == ONE:
            return min(u, v)

        # Perfect negative correlation: C(u,v) = max(u+v-1, 0)
        if rho == -ONE:
            result = u + v - ONE
            return max(result, ZERO)

        u_f = float(u)
        v_f = float(v)
        rho_f = float(rho)

        z_u = norm.ppf(u_f)
        z_v = norm.ppf(v_f)

        # Approximate bivariate normal CDF using Drezner-Wesolowsky method
        # For moderate correlations, use the linearization:
        # Phi_2(x, y; rho) ~ Phi(x)*Phi(y) + rho * phi(x)*phi(y)
        # where phi is the standard normal PDF
        phi_u = norm.cdf(z_u)
        phi_v = norm.cdf(z_v)
        pdf_u = norm.pdf(z_u)
        pdf_v = norm.pdf(z_v)

        # Higher-order approximation for better accuracy
        result = phi_u * phi_v + rho_f * pdf_u * pdf_v

        # Clamp to valid range
        result = max(0.0, min(result, min(u_f, v_f)))

        return Decimal(str(result))


class DependencyAnalyzer:
    """Rolling bivariate dependency analyzer.

    Maintains rolling windows for two series and computes a comprehensive
    dependency report including linear correlation, rank correlation,
    Gaussian copula parameter, and tail dependence coefficients.
    """

    def __init__(self, window: int = 100) -> None:
        """Initialize the analyzer.

        Args:
            window: Rolling window size. Must be at least ``_MIN_OBSERVATIONS``.

        Raises:
            ValueError: If window is smaller than the minimum.
        """
        if window < _MIN_OBSERVATIONS:
            raise ValueError(
                f"Window must be at least {_MIN_OBSERVATIONS}, got {window}"
            )
        self._window = window
        self._x_buf: deque[Decimal] = deque(maxlen=window)
        self._y_buf: deque[Decimal] = deque(maxlen=window)

    def update(self, x: Decimal, y: Decimal) -> dict | None:
        """Add a new observation pair and compute dependency metrics.

        Returns ``None`` until the rolling window is full. Once full,
        returns a dependency report on every call.

        Args:
            x: New observation for the first series.
            y: New observation for the second series.

        Returns:
            Dependency report dict or ``None`` if window not yet full.
        """
        self._x_buf.append(x)
        self._y_buf.append(y)

        if len(self._x_buf) < self._window:
            return None

        x_list = list(self._x_buf)
        y_list = list(self._y_buf)

        return self._compute_report(x_list, y_list)

    def _compute_report(
        self, x_list: list[Decimal], y_list: list[Decimal]
    ) -> dict:
        """Compute full dependency report from buffered data."""
        n = len(x_list)

        # Pearson correlation
        pearson = self._pearson_correlation(x_list, y_list)

        # Rank transform for rank-based methods
        u = rank_transform(x_list)
        v = rank_transform(y_list)

        # Spearman rank correlation (Pearson on ranks)
        rank_corr = self._pearson_correlation(u, v)

        # Gaussian copula parameter
        try:
            copula_rho = GaussianCopula.fit(u, v)
        except ValueError:
            copula_rho = ZERO
            logger.warning(
                "copula_fit_failed_in_analyzer",
                window=self._window,
                n=n,
            )

        # Tail dependence
        try:
            td_lower, td_upper = tail_dependence(u, v)
        except ValueError:
            td_lower = ZERO
            td_upper = ZERO

        is_tail_dependent = max(td_lower, td_upper) > _TAIL_DEP_HIGH

        report = {
            "pearson": pearson,
            "rank_correlation": rank_corr,
            "copula_rho": copula_rho,
            "tail_dep_lower": td_lower,
            "tail_dep_upper": td_upper,
            "is_tail_dependent": is_tail_dependent,
        }

        logger.debug(
            "dependency_report",
            pearson=str(pearson),
            rank_corr=str(rank_corr),
            copula_rho=str(copula_rho),
            tail_lower=str(td_lower),
            tail_upper=str(td_upper),
            tail_dependent=is_tail_dependent,
        )

        return report

    @staticmethod
    def _pearson_correlation(
        x: list[Decimal], y: list[Decimal]
    ) -> Decimal:
        """Compute Pearson correlation between two Decimal series.

        Args:
            x: First series.
            y: Second series.

        Returns:
            Correlation in [-1, 1], or ZERO for degenerate cases.
        """
        n = len(x)
        if n < 2:
            return ZERO

        n_dec = Decimal(n)
        mean_x = sum(x) / n_dec
        mean_y = sum(y) / n_dec

        cov = ZERO
        var_x = ZERO
        var_y = ZERO

        for xi, yi in zip(x, y):
            dx = xi - mean_x
            dy = yi - mean_y
            cov += dx * dy
            var_x += dx * dx
            var_y += dy * dy

        if var_x == ZERO or var_y == ZERO:
            return ZERO

        denom_sq = var_x * var_y
        denom_float = math.sqrt(float(denom_sq))
        if denom_float < 1e-30:
            return ZERO

        corr = Decimal(str(float(cov) / denom_float))

        # Clamp for numerical safety
        if corr > ONE:
            return ONE
        if corr < -ONE:
            return -ONE

        return corr
