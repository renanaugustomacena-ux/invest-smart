"""Fractal analysis and fractional differencing.

Implements Hurst exponent estimation via R/S analysis and DFA,
Lopez de Prado's fractional differencing for memory-preserving
stationarity transforms, and automatic optimal-d selection.

Utilizzo:
    from algo_engine.math.fractal import hurst_exponent, fractional_difference

    H = hurst_exponent(prices)
    stationary = fractional_difference(prices, Decimal("0.4"))
"""

from __future__ import annotations

import math
from decimal import Decimal

import numpy as np

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.logging import get_logger

logger = get_logger(__name__)

ONE = Decimal("1")
TWO = Decimal("2")

_MIN_SERIES_LENGTH = 50


def hurst_exponent(series: list[Decimal], max_lag: int = 100) -> Decimal:
    """Estimate the Hurst exponent via Rescaled Range (R/S) analysis.

    Parameters
    ----------
    series:
        Price or return series with at least 50 data points.
    max_lag:
        Upper bound for lag sizes (powers of 2 up to this value).

    Returns
    -------
    Decimal
        Hurst exponent H.
        H > 0.5 persistent (trending), H < 0.5 anti-persistent
        (mean-reverting), H ~ 0.5 random walk.

    Raises
    ------
    ValueError
        If the series is too short or constant.
    """
    n = len(series)
    if n < _MIN_SERIES_LENGTH:
        raise ValueError(
            f"Series length {n} is below the minimum {_MIN_SERIES_LENGTH} "
            "required for reliable Hurst estimation"
        )

    values = np.array([float(v) for v in series], dtype=np.float64)

    if np.ptp(values) == 0.0:
        raise ValueError("Cannot compute Hurst exponent for a constant series")

    # Cap max_lag to half the series length so each chunk has content.
    effective_max_lag = min(max_lag, n // 2)

    # Build lag sizes as powers of 2: 2, 4, 8, ...
    lags: list[int] = []
    tau = 2
    while tau <= effective_max_lag:
        lags.append(tau)
        tau *= 2

    if not lags:
        raise ValueError(f"No valid lag sizes: effective_max_lag={effective_max_lag} is < 2")

    log_lags: list[float] = []
    log_rs: list[float] = []

    for tau in lags:
        rs_values: list[float] = []
        num_chunks = n // tau

        for i in range(num_chunks):
            chunk = values[i * tau : (i + 1) * tau]
            mean = chunk.mean()
            deviations = chunk - mean
            cumulative = np.cumsum(deviations)
            r = float(cumulative.max() - cumulative.min())
            s = float(chunk.std(ddof=0))

            if s > 0.0:
                rs_values.append(r / s)

        if rs_values:
            avg_rs = sum(rs_values) / len(rs_values)
            if avg_rs > 0.0:
                log_lags.append(math.log(tau))
                log_rs.append(math.log(avg_rs))

    if len(log_lags) < 2:
        logger.warning(
            "hurst_insufficient_points",
            valid_points=len(log_lags),
            total_lags=len(lags),
        )
        raise ValueError(
            "Not enough valid lag points for regression; series may be "
            "too short or nearly constant"
        )

    # OLS regression: log(R/S) = H * log(tau) + c
    slope, _ = np.polyfit(log_lags, log_rs, 1)

    h = Decimal(str(round(slope, 10)))

    logger.debug(
        "hurst_computed",
        h=str(h),
        num_lags=len(log_lags),
        series_length=n,
    )

    return h


def fractional_difference(
    series: list[Decimal],
    d: Decimal,
    threshold: Decimal = Decimal("1e-5"),
) -> list[Decimal]:
    """Apply fractional differencing (Lopez de Prado).

    Computes weights w_0 = 1, w_k = -w_{k-1} * (d - k + 1) / k and
    truncates when |w_k| < threshold.  The output preserves more memory
    of the original series than integer differencing (d=1).

    Parameters
    ----------
    series:
        Input price series.
    d:
        Fractional differencing order (typically 0 < d < 1).
    threshold:
        Minimum absolute weight before truncation.

    Returns
    -------
    list[Decimal]
        Fractionally differenced series.  Length is
        ``len(series) - len(weights) + 1``.

    Raises
    ------
    ValueError
        If the series is empty or d is negative.
    """
    if not series:
        raise ValueError("Cannot apply fractional differencing to an empty series")
    if d < ZERO:
        raise ValueError(f"Differencing order d must be >= 0, got {d}")

    # Compute weights.
    weights: list[Decimal] = [ONE]
    k = 1
    while True:
        w_k = -weights[-1] * (d - Decimal(k) + ONE) / Decimal(k)
        if abs(w_k) < threshold:
            break
        weights.append(w_k)
        k += 1
        # Safety: prevent infinite loops for unusual d values.
        if k > len(series):
            break

    weight_len = len(weights)

    if weight_len > len(series):
        logger.warning(
            "frac_diff_weights_exceed_series",
            weight_len=weight_len,
            series_len=len(series),
        )
        return []

    result: list[Decimal] = []
    for t in range(weight_len - 1, len(series)):
        val = ZERO
        for k_idx in range(weight_len):
            val += weights[k_idx] * series[t - k_idx]
        result.append(val)

    logger.debug(
        "fractional_difference_applied",
        d=str(d),
        num_weights=weight_len,
        output_length=len(result),
    )

    return result


def optimal_d(
    series: list[Decimal],
    max_d: Decimal = Decimal("1.0"),
    step: Decimal = Decimal("0.05"),
    p_value_threshold: Decimal = Decimal("0.05"),
) -> Decimal:
    """Find the minimum fractional differencing order for stationarity.

    Iterates d from 0 to *max_d* in increments of *step*, applies
    fractional differencing, then checks stationarity via a simplified
    ADF test (lag-1 autocorrelation < 1 - *p_value_threshold*).

    Parameters
    ----------
    series:
        Input price series (at least 50 data points recommended).
    max_d:
        Maximum d to try.
    step:
        Increment for the d scan.
    p_value_threshold:
        Autocorrelation threshold below which the series is deemed
        stationary.

    Returns
    -------
    Decimal
        Minimum d that achieves stationarity.

    Raises
    ------
    ValueError
        If the series is empty or no d achieves stationarity.
    """
    if not series:
        raise ValueError("Cannot compute optimal d for an empty series")

    # Autocorrelation threshold: series is considered stationary when
    # the lag-1 autocorrelation falls below this bound.
    acf_threshold = float(ONE - p_value_threshold)

    d_candidate = ZERO
    while d_candidate <= max_d:
        diffed = fractional_difference(series, d_candidate)

        if len(diffed) < 3:
            d_candidate += step
            continue

        floats = np.array([float(v) for v in diffed], dtype=np.float64)

        # Simplified ADF: use lag-1 autocorrelation as stationarity proxy.
        acf1 = _lag1_autocorrelation(floats)

        if acf1 < acf_threshold:
            logger.info(
                "optimal_d_found",
                d=str(d_candidate),
                acf1=round(acf1, 6),
            )
            return d_candidate

        d_candidate += step

    raise ValueError(f"No d in [0, {max_d}] with step {step} achieved stationarity")


def detrended_fluctuation_analysis(
    series: list[Decimal],
    min_box: int = 4,
    max_box: int = 100,
) -> Decimal:
    """Estimate the Hurst exponent via Detrended Fluctuation Analysis.

    More robust than R/S analysis for short and non-stationary series.

    Parameters
    ----------
    series:
        Input time series with at least 50 data points.
    min_box:
        Smallest box (window) size.
    max_box:
        Largest box size.

    Returns
    -------
    Decimal
        DFA scaling exponent alpha.
        alpha > 0.5: persistent, alpha < 0.5: anti-persistent,
        alpha ~ 0.5: random walk (same interpretation as Hurst).

    Raises
    ------
    ValueError
        If the series is too short or constant.
    """
    n = len(series)
    if n < _MIN_SERIES_LENGTH:
        raise ValueError(
            f"Series length {n} is below the minimum {_MIN_SERIES_LENGTH} "
            "required for reliable DFA estimation"
        )

    values = np.array([float(v) for v in series], dtype=np.float64)

    if np.ptp(values) == 0.0:
        raise ValueError("Cannot run DFA on a constant series")

    # Step 1: cumulative sum of deviations from mean (profile).
    mean = values.mean()
    profile = np.cumsum(values - mean)

    # Build box sizes as powers of 2 within [min_box, max_box].
    effective_max_box = min(max_box, n // 2)
    box_sizes: list[int] = []
    box = min_box
    while box <= effective_max_box:
        box_sizes.append(box)
        box *= 2

    if len(box_sizes) < 2:
        raise ValueError(
            f"Not enough box sizes in [{min_box}, {effective_max_box}] " "for regression"
        )

    log_boxes: list[float] = []
    log_fluct: list[float] = []

    for box_size in box_sizes:
        num_boxes = n // box_size
        if num_boxes == 0:
            continue

        rms_values: list[float] = []

        for i in range(num_boxes):
            segment = profile[i * box_size : (i + 1) * box_size]

            # Step 2: fit linear trend to each segment.
            x = np.arange(box_size, dtype=np.float64)
            coeffs = np.polyfit(x, segment, 1)
            trend = np.polyval(coeffs, x)

            # Step 3: RMS of residuals.
            residuals = segment - trend
            rms = float(np.sqrt(np.mean(residuals**2)))
            rms_values.append(rms)

        if rms_values:
            avg_fluct = sum(rms_values) / len(rms_values)
            if avg_fluct > 0.0:
                log_boxes.append(math.log(box_size))
                log_fluct.append(math.log(avg_fluct))

    if len(log_boxes) < 2:
        raise ValueError("Not enough valid box sizes for DFA regression")

    # Step 4: regress log(F) on log(box_size) to obtain scaling exponent.
    alpha, _ = np.polyfit(log_boxes, log_fluct, 1)

    result = Decimal(str(round(alpha, 10)))

    logger.debug(
        "dfa_computed",
        alpha=str(result),
        num_boxes=len(log_boxes),
        series_length=n,
    )

    return result


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _lag1_autocorrelation(values: np.ndarray) -> float:
    """Compute the lag-1 autocorrelation of a 1-D array.

    Returns 0.0 for constant or too-short arrays.
    """
    if len(values) < 3:
        return 0.0

    mean = values.mean()
    diff = values - mean
    var = float(np.dot(diff, diff))

    if var == 0.0:
        return 0.0

    cov = float(np.dot(diff[:-1], diff[1:]))
    return cov / var
