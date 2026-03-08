"""Information-theoretic measures for financial time series.

Provides entropy, mutual information, and KL divergence calculations
for analysing market uncertainty, nonlinear dependence between series,
and distribution shift detection useful as regime-change early warning.
"""

from __future__ import annotations

import math
from collections import deque
from decimal import Decimal

import numpy as np

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.logging import get_logger

logger = get_logger(__name__)

_EPSILON = Decimal("1e-15")


def shannon_entropy(values: list[Decimal], n_bins: int = 20) -> Decimal:
    """Compute Shannon entropy of a value distribution.

    Discretises *values* into *n_bins* equal-width bins and returns
    H = -sum(p_i * log2(p_i)) in bits.

    High entropy indicates an uncertain / noisy market; low entropy
    signals a clear, predictable regime.

    Args:
        values: Observations to analyse.
        n_bins: Number of histogram bins for discretisation.

    Returns:
        Shannon entropy in bits as a Decimal.
    """
    if len(values) < 2:
        return ZERO

    floats = np.array([float(v) for v in values], dtype=np.float64)

    if np.all(floats == floats[0]):
        return ZERO

    counts, _ = np.histogram(floats, bins=n_bins)
    total = counts.sum()
    if total == 0:
        return ZERO

    entropy = 0.0
    for c in counts:
        if c > 0:
            p = c / total
            entropy -= p * math.log2(p)

    return Decimal(str(round(entropy, 15)))


def _joint_entropy(x_floats: np.ndarray, y_floats: np.ndarray, n_bins: int) -> float:
    """Compute joint entropy H(X, Y) using a 2-D histogram."""
    counts, _, _ = np.histogram2d(x_floats, y_floats, bins=n_bins)
    total = counts.sum()
    if total == 0:
        return 0.0

    entropy = 0.0
    for row in counts:
        for c in row:
            if c > 0:
                p = c / total
                entropy -= p * math.log2(p)
    return entropy


def mutual_information(
    x: list[Decimal], y: list[Decimal], n_bins: int = 20
) -> Decimal:
    """Compute mutual information MI(X, Y) = H(X) + H(Y) - H(X, Y).

    Uses a 2-D histogram for joint entropy estimation.  Captures
    nonlinear dependence between two series — unlike Pearson correlation
    which only measures linear relationships.

    Args:
        x: First series.
        y: Second series (must be same length as *x*).
        n_bins: Number of histogram bins per dimension.

    Returns:
        Mutual information in bits as a Decimal (>= 0).

    Raises:
        ValueError: If *x* and *y* differ in length.
    """
    if len(x) != len(y):
        raise ValueError(
            f"Series must have equal length: len(x)={len(x)}, len(y)={len(y)}"
        )

    if len(x) < 2:
        return ZERO

    h_x = shannon_entropy(x, n_bins)
    h_y = shannon_entropy(y, n_bins)

    x_floats = np.array([float(v) for v in x], dtype=np.float64)
    y_floats = np.array([float(v) for v in y], dtype=np.float64)

    h_xy = Decimal(str(round(_joint_entropy(x_floats, y_floats, n_bins), 15)))

    mi = h_x + h_y - h_xy

    # Clamp to zero — numerical imprecision can produce tiny negatives.
    if mi < ZERO:
        mi = ZERO

    return mi


def kl_divergence(
    p: list[Decimal], q: list[Decimal], n_bins: int = 20
) -> Decimal:
    """Compute Kullback-Leibler divergence KL(P || Q).

    KL(P||Q) = sum(p_i * log2(p_i / q_i)).  A small epsilon is added
    to both distributions to avoid log(0).

    Measures how much distribution *P* diverges from reference
    distribution *Q*.  KL >= 0 with equality iff P == Q.

    Args:
        p: Sample values drawn from distribution P.
        q: Sample values drawn from reference distribution Q.
        n_bins: Number of histogram bins for discretisation.

    Returns:
        KL divergence in bits as a Decimal (>= 0).
    """
    if len(p) < 2 or len(q) < 2:
        return ZERO

    p_floats = np.array([float(v) for v in p], dtype=np.float64)
    q_floats = np.array([float(v) for v in q], dtype=np.float64)

    # Use a shared bin range so distributions are comparable.
    global_min = min(float(p_floats.min()), float(q_floats.min()))
    global_max = max(float(p_floats.max()), float(q_floats.max()))

    if global_min == global_max:
        return ZERO

    bin_edges = np.linspace(global_min, global_max, n_bins + 1)

    p_counts, _ = np.histogram(p_floats, bins=bin_edges)
    q_counts, _ = np.histogram(q_floats, bins=bin_edges)

    eps = float(_EPSILON)

    p_probs = p_counts / p_counts.sum() + eps
    q_probs = q_counts / q_counts.sum() + eps

    # Re-normalise after adding epsilon.
    p_probs = p_probs / p_probs.sum()
    q_probs = q_probs / q_probs.sum()

    divergence = 0.0
    for pi, qi in zip(p_probs, q_probs):
        divergence += pi * math.log2(pi / qi)

    # Clamp — numerical noise can produce tiny negatives.
    if divergence < 0.0:
        divergence = 0.0

    return Decimal(str(round(divergence, 15)))


class DistributionShiftDetector:
    """Detect distribution shifts via KL divergence between windows.

    Maintains a reference window and a test window of recent values.
    When the KL divergence between them exceeds *threshold*, a shift
    is signalled — useful as a regime-change early warning.

    Args:
        reference_window: Number of observations in the reference window.
        test_window: Number of observations in the sliding test window.
        threshold: KL divergence threshold to signal a shift.
    """

    def __init__(
        self,
        reference_window: int = 200,
        test_window: int = 50,
        threshold: Decimal = Decimal("0.5"),
    ) -> None:
        self._reference_window = reference_window
        self._test_window = test_window
        self._threshold = threshold

        self._reference: deque[Decimal] = deque(maxlen=reference_window)
        self._test: deque[Decimal] = deque(maxlen=test_window)
        self._total_count = 0

    def update(self, value: Decimal) -> bool:
        """Add a new observation and check for distribution shift.

        The first *reference_window* values populate the reference
        buffer.  Subsequent values enter the test buffer.  Once the
        test buffer is full, KL divergence is computed on every call.

        Args:
            value: New observation.

        Returns:
            ``True`` if a distribution shift is detected (KL divergence
            exceeds the configured threshold), ``False`` otherwise.
        """
        self._total_count += 1

        if self._total_count <= self._reference_window:
            self._reference.append(value)
            return False

        self._test.append(value)

        if len(self._test) < self._test_window:
            return False

        ref_list = list(self._reference)
        test_list = list(self._test)

        divergence = kl_divergence(test_list, ref_list)

        if divergence > self._threshold:
            logger.info(
                "Distribution shift detected: KL=%.6f threshold=%.6f",
                divergence,
                self._threshold,
            )
            return True

        return False
