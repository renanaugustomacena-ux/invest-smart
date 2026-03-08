"""Extreme Value Theory for tail risk analysis.

Implements Generalized Pareto Distribution fitting via probability-weighted
moments and tail risk metrics (VaR, CVaR/Expected Shortfall) without
scipy dependencies.
"""

from decimal import Decimal, InvalidOperation

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.logging import get_logger

logger = get_logger(__name__)

ONE = Decimal("1")
TWO = Decimal("2")

_MIN_EXCEEDANCES = 20
_XI_NEAR_ZERO_THRESHOLD = Decimal("1e-12")


class GeneralizedParetoDistribution:
    """Generalized Pareto Distribution with PWM-based fitting."""

    @staticmethod
    def fit(exceedances: list[Decimal]) -> tuple[Decimal, Decimal]:
        """Fit GPD shape (xi) and scale (sigma) using probability-weighted moments.

        Args:
            exceedances: Sorted list of exceedances above threshold (x - u).

        Returns:
            Tuple of (xi, sigma) parameters.

        Raises:
            ValueError: If fewer than ``_MIN_EXCEEDANCES`` data points provided
                or if the PWM denominator is degenerate.
        """
        n = len(exceedances)
        if n < _MIN_EXCEEDANCES:
            raise ValueError(
                f"Need at least {_MIN_EXCEEDANCES} exceedances for reliable "
                f"GPD fit, got {n}"
            )

        sorted_exc = sorted(exceedances)
        n_dec = Decimal(n)
        n_minus_1 = n_dec - ONE

        # b0 = mean of exceedances
        b0 = sum(sorted_exc) / n_dec

        # b1 = (1/n) * sum( (i / (n-1)) * x_(i) ) for i = 0..n-1
        if n_minus_1 == ZERO:
            raise ValueError("Cannot fit GPD with a single data point")

        b1 = ZERO
        for i, x_i in enumerate(sorted_exc):
            b1 += (Decimal(i) / n_minus_1) * x_i
        b1 /= n_dec

        denominator = b0 - TWO * b1
        if abs(denominator) < Decimal("1e-30"):
            raise ValueError(
                "PWM denominator is near zero; GPD fit is degenerate"
            )

        sigma = TWO * b0 * b1 / denominator
        xi = TWO - b0 / denominator

        if sigma <= ZERO:
            raise ValueError(
                f"Fitted scale parameter sigma={sigma} is non-positive; "
                f"data may not follow a GPD"
            )

        logger.debug(
            "gpd_fit_complete", xi=str(xi), sigma=str(sigma), n=n
        )
        return xi, sigma

    @staticmethod
    def cdf(x: Decimal, xi: Decimal, sigma: Decimal) -> Decimal:
        """Cumulative distribution function of the GPD.

        CDF(x) = 1 - (1 + xi * x / sigma) ^ (-1/xi)

        For xi near zero (exponential case):
            CDF(x) = 1 - exp(-x / sigma)

        Args:
            x: Value at which to evaluate the CDF (must be >= 0).
            xi: Shape parameter.
            sigma: Scale parameter (must be > 0).

        Returns:
            Probability value in [0, 1].
        """
        if sigma <= ZERO:
            raise ValueError(f"Scale parameter must be positive, got {sigma}")
        if x < ZERO:
            return ZERO

        if abs(xi) < _XI_NEAR_ZERO_THRESHOLD:
            # Exponential case: CDF = 1 - exp(-x/sigma)
            ratio = float(-x / sigma)
            import math
            survival = Decimal(str(math.exp(ratio)))
            return ONE - survival

        inner = ONE + xi * x / sigma
        if inner <= ZERO:
            # Beyond the support of the distribution
            return ONE if xi < ZERO else ZERO

        exponent = float(-ONE / xi)
        base = float(inner)
        survival = Decimal(str(base ** exponent))
        return ONE - survival

    @staticmethod
    def var(
        alpha: Decimal,
        xi: Decimal,
        sigma: Decimal,
        n_total: int,
        n_exceed: int,
    ) -> Decimal:
        """Compute Value at Risk at confidence level alpha.

        VaR_alpha = (sigma / xi) * ((n_total / n_exceed * (1 - alpha))^(-xi) - 1)

        For xi near zero (exponential case):
            VaR_alpha = sigma * ln(n_total / n_exceed * (1 - alpha))

        Args:
            alpha: Confidence level (e.g. 0.99).
            xi: GPD shape parameter.
            sigma: GPD scale parameter.
            n_total: Total number of observations.
            n_exceed: Number of threshold exceedances.

        Returns:
            VaR estimate as a positive Decimal (loss magnitude).
        """
        if n_exceed <= 0:
            raise ValueError("n_exceed must be positive")
        if not (ZERO < alpha < ONE):
            raise ValueError(f"alpha must be in (0, 1), got {alpha}")

        import math

        ratio = Decimal(n_total) / Decimal(n_exceed) * (ONE - alpha)

        if abs(xi) < _XI_NEAR_ZERO_THRESHOLD:
            # Exponential case
            if ratio <= ZERO:
                raise ValueError("Invalid ratio for log computation")
            result = -sigma * Decimal(str(math.log(float(ratio))))
            return result

        base = float(ratio)
        exponent = float(-xi)
        powered = Decimal(str(base ** exponent))
        result = (sigma / xi) * (powered - ONE)
        return result

    @staticmethod
    def cvar(
        alpha: Decimal,
        xi: Decimal,
        sigma: Decimal,
        threshold: Decimal,
        n_total: int,
        n_exceed: int,
    ) -> Decimal:
        """Compute Conditional Value at Risk (Expected Shortfall).

        CVaR_alpha = VaR_alpha / (1 - xi) + (sigma - xi * threshold) / (1 - xi)

        Args:
            alpha: Confidence level (e.g. 0.99).
            xi: GPD shape parameter.
            sigma: GPD scale parameter.
            threshold: The threshold used for POT extraction.
            n_total: Total number of observations.
            n_exceed: Number of threshold exceedances.

        Returns:
            CVaR (Expected Shortfall) estimate.

        Raises:
            ValueError: If xi >= 1 (CVaR is undefined).
        """
        if xi >= ONE:
            raise ValueError(
                f"CVaR is undefined for xi >= 1 (got xi={xi}); "
                f"the distribution has infinite mean"
            )

        var_value = GeneralizedParetoDistribution.var(
            alpha, xi, sigma, n_total, n_exceed
        )

        one_minus_xi = ONE - xi
        cvar_value = var_value / one_minus_xi + (sigma - xi * threshold) / one_minus_xi
        return cvar_value


class TailRiskAnalyzer:
    """Peaks-over-threshold tail risk analyzer using GPD."""

    def __init__(
        self,
        confidence: Decimal = Decimal("0.99"),
        threshold_percentile: Decimal = Decimal("0.95"),
    ) -> None:
        """Initialize the analyzer.

        Args:
            confidence: VaR/CVaR confidence level (e.g. 0.99 for 99%).
            threshold_percentile: Percentile for the POT threshold (e.g. 0.95
                means exceedances are the worst 5% of returns).
        """
        if not (ZERO < confidence < ONE):
            raise ValueError(
                f"confidence must be in (0, 1), got {confidence}"
            )
        if not (ZERO < threshold_percentile < ONE):
            raise ValueError(
                f"threshold_percentile must be in (0, 1), got {threshold_percentile}"
            )

        self._confidence = confidence
        self._threshold_pct = threshold_percentile
        self._gpd = GeneralizedParetoDistribution()

    def analyze(self, returns: list[Decimal]) -> dict:
        """Run full tail risk analysis on a return series.

        Steps:
            1. Compute threshold at the configured percentile of losses.
            2. Extract exceedances above the threshold.
            3. Fit GPD to exceedances.
            4. Compute VaR and CVaR.

        Args:
            returns: List of period returns (negative = losses).

        Returns:
            Dict with keys: ``var``, ``cvar``, ``shape``, ``scale``,
            ``threshold``, ``n_exceedances``, ``tail_index``.

        Raises:
            ValueError: If not enough data or exceedances for a reliable fit.
        """
        if len(returns) < _MIN_EXCEEDANCES:
            raise ValueError(
                f"Need at least {_MIN_EXCEEDANCES} returns, got {len(returns)}"
            )

        # Work with losses (negate returns so losses are positive)
        losses = sorted([-r for r in returns])

        # Threshold at the configured percentile
        threshold = self._percentile(losses, self._threshold_pct)

        # Extract exceedances: losses strictly above the threshold
        exceedances = [loss - threshold for loss in losses if loss > threshold]
        n_exceed = len(exceedances)

        if n_exceed < _MIN_EXCEEDANCES:
            raise ValueError(
                f"Only {n_exceed} exceedances above threshold {threshold}; "
                f"need at least {_MIN_EXCEEDANCES} for reliable GPD fit. "
                f"Consider lowering threshold_percentile."
            )

        n_total = len(returns)

        xi, sigma = self._gpd.fit(exceedances)

        var_value = self._gpd.var(
            self._confidence, xi, sigma, n_total, n_exceed
        )
        cvar_value = self._gpd.cvar(
            self._confidence, xi, sigma, threshold, n_total, n_exceed
        )

        result = {
            "var": var_value,
            "cvar": cvar_value,
            "shape": xi,
            "scale": sigma,
            "threshold": threshold,
            "n_exceedances": n_exceed,
            "tail_index": xi,
        }

        logger.info(
            "tail_risk_analysis_complete",
            var=str(var_value),
            cvar=str(cvar_value),
            shape=str(xi),
            n_exceedances=n_exceed,
        )

        return result

    @staticmethod
    def _percentile(sorted_data: list[Decimal], pct: Decimal) -> Decimal:
        """Compute the percentile of a sorted dataset via linear interpolation.

        Args:
            sorted_data: Data sorted in ascending order.
            pct: Percentile in (0, 1).

        Returns:
            Interpolated percentile value.
        """
        n = len(sorted_data)
        if n == 0:
            raise ValueError("Cannot compute percentile of empty dataset")
        if n == 1:
            return sorted_data[0]

        pos = pct * Decimal(n - 1)
        lower = int(pos)
        upper = lower + 1
        frac = pos - Decimal(lower)

        if upper >= n:
            return sorted_data[-1]

        return sorted_data[lower] + frac * (sorted_data[upper] - sorted_data[lower])


def expected_shortfall_historical(
    returns: list[Decimal],
    alpha: Decimal = Decimal("0.05"),
) -> Decimal:
    """Compute historical Expected Shortfall (non-parametric).

    Average of the worst alpha-fraction of returns. No distributional
    assumptions are made.

    Args:
        returns: List of period returns.
        alpha: Tail fraction (e.g. 0.05 for worst 5%).

    Returns:
        Expected Shortfall as a Decimal (will be negative for losses).

    Raises:
        ValueError: If returns list is empty or alpha is out of range.
    """
    if not returns:
        raise ValueError("Returns list must not be empty")
    if not (ZERO < alpha <= ONE):
        raise ValueError(f"alpha must be in (0, 1], got {alpha}")

    sorted_returns = sorted(returns)
    n = len(sorted_returns)
    cutoff = int(Decimal(n) * alpha)

    # At least one observation in the tail
    if cutoff < 1:
        cutoff = 1

    tail = sorted_returns[:cutoff]
    es = sum(tail) / Decimal(len(tail))

    logger.debug(
        "historical_es_computed",
        es=str(es),
        alpha=str(alpha),
        tail_size=len(tail),
    )

    return es
