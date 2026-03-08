"""Ornstein-Uhlenbeck process for mean reversion analysis.

Implements parameter estimation via OLS regression, half-life calculation,
standardised s-score signals, and Euler-Maruyama simulation of the OU
stochastic differential equation: dX = theta(mu - X)dt + sigma*dW.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from decimal import Decimal

import numpy as np

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.logging import get_logger

logger = get_logger(__name__)

ONE = Decimal("1")
TWO = Decimal("2")
_LN2 = Decimal(str(math.log(2)))
_MIN_OBSERVATIONS = 30


@dataclass(frozen=True)
class OUParams:
    """Fitted parameters of an Ornstein-Uhlenbeck process.

    Attributes:
        theta: Mean reversion speed (positive for genuine mean reversion).
        mu: Long-run equilibrium mean.
        sigma: Volatility of the process.
        half_life: Time for the process to revert halfway to the mean,
            computed as ln(2) / theta.
        sigma_eq: Equilibrium standard deviation, sigma / sqrt(2 * theta).
        r_squared: Goodness of fit from the OLS regression.
        is_valid: True if theta > 0 (genuine mean reversion).
    """

    theta: Decimal
    mu: Decimal
    sigma: Decimal
    half_life: Decimal
    sigma_eq: Decimal
    r_squared: Decimal
    is_valid: bool


class OrnsteinUhlenbeck:
    """Ornstein-Uhlenbeck process estimator and simulator."""

    @staticmethod
    def fit(series: list[Decimal], dt: Decimal = ONE) -> OUParams:
        """Fit OU parameters via OLS regression on discrete differences.

        Regresses X(t+1) - X(t) = a + b * X(t) + epsilon and recovers
        the continuous-time OU parameters:
            theta = -b / dt
            mu    = -a / b
            sigma = std(epsilon) / sqrt(dt)

        Args:
            series: Time series of observations (minimum 30 points).
            dt: Time step between observations (default 1).

        Returns:
            Fitted OUParams dataclass.

        Raises:
            ValueError: If fewer than ``_MIN_OBSERVATIONS`` data points
                are provided.
        """
        n = len(series)
        if n < _MIN_OBSERVATIONS:
            raise ValueError(
                f"Need at least {_MIN_OBSERVATIONS} observations for "
                f"reliable OU fit, got {n}"
            )

        # Convert to numpy for efficient OLS
        x = np.array([float(v) for v in series], dtype=np.float64)

        # Dependent variable: differences
        dy = x[1:] - x[:-1]
        # Regressor: lagged values
        x_lag = x[:-1]

        # OLS: dy = a + b * x_lag + epsilon
        # Design matrix [x_lag, 1]
        n_obs = len(dy)
        X_mat = np.column_stack([x_lag, np.ones(n_obs)])

        # Normal equation: (X'X)^-1 X'y
        XtX = X_mat.T @ X_mat
        det = XtX[0, 0] * XtX[1, 1] - XtX[0, 1] * XtX[1, 0]

        if abs(det) < 1e-30:
            # Constant or near-constant series
            logger.warning(
                "ou_fit_degenerate",
                detail="Design matrix is singular; series may be constant",
            )
            return OUParams(
                theta=ZERO,
                mu=Decimal(str(x[0])),
                sigma=ZERO,
                half_life=Decimal("Infinity"),
                sigma_eq=ZERO,
                r_squared=ZERO,
                is_valid=False,
            )

        XtX_inv = np.array([
            [XtX[1, 1] / det, -XtX[0, 1] / det],
            [-XtX[1, 0] / det, XtX[0, 0] / det],
        ])

        beta = XtX_inv @ (X_mat.T @ dy)
        b = beta[0]
        a = beta[1]

        # Residuals for sigma and r-squared
        residuals = dy - X_mat @ beta
        sigma_eps = float(np.std(residuals, ddof=0))

        # R-squared: 1 - SS_res / SS_tot
        ss_res = float(np.sum(residuals ** 2))
        dy_mean = float(np.mean(dy))
        ss_tot = float(np.sum((dy - dy_mean) ** 2))

        if ss_tot < 1e-30:
            r_squared = ZERO
        else:
            r_sq = 1.0 - ss_res / ss_tot
            r_squared = Decimal(str(max(0.0, r_sq)))

        dt_f = float(dt)

        # Recover continuous-time parameters
        theta_f = -b / dt_f
        theta = Decimal(str(theta_f))

        if abs(b) < 1e-30:
            # b ~ 0 means no mean reversion
            mu = Decimal(str(float(np.mean(x))))
        else:
            mu = Decimal(str(-a / b))

        sigma = Decimal(str(sigma_eps / math.sqrt(dt_f)))

        # Derived quantities
        if theta_f > 0:
            hl = Decimal(str(math.log(2) / theta_f))
            sigma_eq = Decimal(str(sigma_eps / math.sqrt(2.0 * theta_f * dt_f)))
            is_valid = True
        else:
            hl = Decimal("Infinity")
            sigma_eq = ZERO
            is_valid = False

        logger.debug(
            "ou_fit_complete",
            theta=str(theta),
            mu=str(mu),
            sigma=str(sigma),
            half_life=str(hl),
            r_squared=str(r_squared),
            is_valid=is_valid,
        )

        return OUParams(
            theta=theta,
            mu=mu,
            sigma=sigma,
            half_life=hl,
            sigma_eq=sigma_eq,
            r_squared=r_squared,
            is_valid=is_valid,
        )

    @staticmethod
    def half_life(theta: Decimal) -> Decimal:
        """Compute the half-life of mean reversion.

        Half-life = ln(2) / theta. This is the expected time for the
        process to revert halfway from its current level to the mean.

        Args:
            theta: Mean reversion speed (must be positive).

        Returns:
            Half-life as a Decimal.

        Raises:
            ValueError: If theta is not positive.
        """
        if theta <= ZERO:
            raise ValueError(
                f"theta must be positive for half-life calculation, got {theta}"
            )
        return _LN2 / theta

    @staticmethod
    def s_score(current: Decimal, mu: Decimal, sigma_eq: Decimal) -> Decimal:
        """Compute the standardised s-score.

        s = (X - mu) / sigma_eq

        The s-score measures how many equilibrium standard deviations
        the current value is from the long-run mean. It is the core
        signal for mean reversion trading strategies.

        Args:
            current: Current observed value.
            mu: Long-run mean from OU fit.
            sigma_eq: Equilibrium standard deviation (sigma / sqrt(2*theta)).

        Returns:
            Standardised distance from the mean.

        Raises:
            ValueError: If sigma_eq is not positive.
        """
        if sigma_eq <= ZERO:
            raise ValueError(
                f"sigma_eq must be positive for s-score, got {sigma_eq}"
            )
        return (current - mu) / sigma_eq

    @staticmethod
    def is_mean_reverting(
        theta: Decimal, min_theta: Decimal = Decimal("0.01")
    ) -> bool:
        """Check whether the fitted theta indicates significant mean reversion.

        Args:
            theta: Mean reversion speed from OU fit.
            min_theta: Minimum threshold for theta to be considered
                significant (default 0.01).

        Returns:
            True if theta exceeds min_theta.
        """
        return theta > min_theta

    @staticmethod
    def simulate(
        params: OUParams,
        X0: Decimal,
        n_steps: int,
        dt: Decimal = ONE,
        seed: int | None = None,
    ) -> list[Decimal]:
        """Simulate an OU process using the Euler-Maruyama method.

        At each step:
            X(t+dt) = X(t) + theta * (mu - X(t)) * dt + sigma * sqrt(dt) * Z

        where Z ~ N(0, 1).

        Args:
            params: Fitted OUParams with theta, mu, sigma.
            X0: Initial value of the process.
            n_steps: Number of time steps to simulate.
            dt: Time step size (default 1).
            seed: Random seed for reproducibility.

        Returns:
            List of simulated values of length n_steps + 1 (including X0).
        """
        rng = np.random.default_rng(seed)

        theta_f = float(params.theta)
        mu_f = float(params.mu)
        sigma_f = float(params.sigma)
        dt_f = float(dt)
        sqrt_dt = math.sqrt(dt_f)

        path = np.empty(n_steps + 1, dtype=np.float64)
        path[0] = float(X0)

        noise = rng.standard_normal(n_steps)

        for i in range(n_steps):
            x = path[i]
            path[i + 1] = (
                x + theta_f * (mu_f - x) * dt_f + sigma_f * sqrt_dt * noise[i]
            )

        return [Decimal(str(v)) for v in path]


class SpreadAnalyzer:
    """Rolling OU-based spread analyser for pairs trading.

    Maintains a sliding window of spread observations, refits the OU
    model on each update, and produces mean-reversion trading signals
    based on the standardised s-score.

    Args:
        lookback: Number of spread observations to keep in the rolling
            window (default 100).
    """

    _BUY_THRESHOLD = Decimal("-1.5")
    _SELL_THRESHOLD = Decimal("1.5")
    _CLOSE_THRESHOLD = Decimal("0.5")

    def __init__(self, lookback: int = 100) -> None:
        self._lookback = lookback
        self._window: deque[Decimal] = deque(maxlen=lookback)
        self._ou = OrnsteinUhlenbeck()

    def update(self, spread: Decimal) -> OUParams | None:
        """Add a spread observation and refit the OU model.

        Args:
            spread: Latest spread value.

        Returns:
            Fitted OUParams if enough data has accumulated (at least
            ``_MIN_OBSERVATIONS``), otherwise None.
        """
        self._window.append(spread)

        if len(self._window) < _MIN_OBSERVATIONS:
            return None

        try:
            params = self._ou.fit(list(self._window))
        except ValueError as exc:
            logger.warning("ou_fit_failed", error=str(exc))
            return None

        return params

    def get_signal(self, spread: Decimal, params: OUParams) -> dict:
        """Generate a trading signal from the current spread and OU params.

        Signal logic:
            - ``"BUY"``  if s_score < -1.5  (spread is significantly below mean)
            - ``"SELL"`` if s_score >  1.5  (spread is significantly above mean)
            - ``"CLOSE"`` if |s_score| < 0.5 (spread has reverted near the mean)
            - ``"HOLD"`` otherwise

        Args:
            spread: Current spread value.
            params: Fitted OU parameters (must have positive sigma_eq).

        Returns:
            Dict with keys ``s_score``, ``half_life``, and ``signal``.
        """
        if not params.is_valid or params.sigma_eq <= ZERO:
            return {
                "s_score": ZERO,
                "half_life": Decimal("Infinity"),
                "signal": "HOLD",
            }

        score = self._ou.s_score(spread, params.mu, params.sigma_eq)

        if score < self._BUY_THRESHOLD:
            signal = "BUY"
        elif score > self._SELL_THRESHOLD:
            signal = "SELL"
        elif abs(score) < self._CLOSE_THRESHOLD:
            signal = "CLOSE"
        else:
            signal = "HOLD"

        return {
            "s_score": score,
            "half_life": params.half_life,
            "signal": signal,
        }
