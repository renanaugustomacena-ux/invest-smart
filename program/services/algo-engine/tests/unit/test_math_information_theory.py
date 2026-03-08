"""Tests for algo_engine.math.information_theory — Shannon entropy, MI, KL divergence."""

from __future__ import annotations

from decimal import Decimal

import pytest

from moneymaker_common.decimal_utils import ZERO

from algo_engine.math.information_theory import (
    DistributionShiftDetector,
    kl_divergence,
    mutual_information,
    shannon_entropy,
)


# ---------------------------------------------------------------------------
# TestShannonEntropy
# ---------------------------------------------------------------------------


class TestShannonEntropy:
    """Tests for the shannon_entropy function."""

    def test_empty_returns_zero(self) -> None:
        assert shannon_entropy([]) == ZERO

    def test_single_value_returns_zero(self) -> None:
        assert shannon_entropy([Decimal("1.0")]) == ZERO

    def test_constant_series_returns_zero(self) -> None:
        assert shannon_entropy([Decimal("5")] * 100) == ZERO

    def test_uniform_distribution_max_entropy(self) -> None:
        # 1000 values uniformly spread across 10 bins -> H ~ log2(10) = 3.3219
        values = []
        for bin_idx in range(10):
            values.extend([Decimal(str(bin_idx + 0.5))] * 100)
        result = shannon_entropy(values, n_bins=10)
        expected = Decimal("3.3219")
        assert abs(result - expected) < Decimal("0.1")

    def test_two_bin_equal_entropy(self) -> None:
        # Two equiprobable outcomes -> H = 1 bit
        values = [Decimal("0")] * 500 + [Decimal("10")] * 500
        result = shannon_entropy(values, n_bins=2)
        assert abs(result - Decimal("1.0")) < Decimal("0.05")

    def test_entropy_non_negative(self) -> None:
        values = [Decimal(str(i)) for i in range(50)]
        assert shannon_entropy(values) >= ZERO

    def test_varied_series_positive_entropy(self) -> None:
        values = [Decimal(str(i)) for i in range(100)]
        assert shannon_entropy(values) > ZERO

    def test_n_bins_parameter_affects_result(self) -> None:
        values = [Decimal(str(i)) for i in range(100)]
        h5 = shannon_entropy(values, n_bins=5)
        h50 = shannon_entropy(values, n_bins=50)
        assert h5 != h50


# ---------------------------------------------------------------------------
# TestMutualInformation
# ---------------------------------------------------------------------------


class TestMutualInformation:
    """Tests for the mutual_information function."""

    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="equal length"):
            mutual_information(
                [Decimal("1")] * 5,
                [Decimal("1")] * 3,
            )

    def test_empty_returns_zero(self) -> None:
        assert mutual_information([], []) == ZERO

    def test_single_element_returns_zero(self) -> None:
        assert mutual_information([Decimal("1")], [Decimal("2")]) == ZERO

    def test_identical_series_positive_mi(self) -> None:
        x = [Decimal(str(i)) for i in range(100)]
        assert mutual_information(x, list(x)) > ZERO

    def test_mi_non_negative(self) -> None:
        x = [Decimal(str(i)) for i in range(100)]
        y = [Decimal(str(99 - i)) for i in range(100)]
        assert mutual_information(x, y) >= ZERO

    def test_independent_series_low_mi(self) -> None:
        # Two series with no functional relationship have MI < H(X)
        import numpy as np

        rng = np.random.default_rng(42)
        x = [Decimal(str(round(v, 6))) for v in rng.standard_normal(200)]
        y = [Decimal(str(round(v, 6))) for v in rng.standard_normal(200)]
        mi = mutual_information(x, y)
        h_x = shannon_entropy(x)
        assert mi >= ZERO
        assert mi < h_x  # MI should be much less than marginal entropy


# ---------------------------------------------------------------------------
# TestKLDivergence
# ---------------------------------------------------------------------------


class TestKLDivergence:
    """Tests for the kl_divergence function."""

    def test_empty_p_returns_zero(self) -> None:
        assert kl_divergence([], [Decimal("1")] * 10) == ZERO

    def test_empty_q_returns_zero(self) -> None:
        assert kl_divergence([Decimal("1")] * 10, []) == ZERO

    def test_identical_distributions_near_zero(self) -> None:
        series = [Decimal(str(i)) for i in range(100)]
        result = kl_divergence(series, list(series))
        assert result < Decimal("0.01")

    def test_kl_non_negative(self) -> None:
        p = [Decimal(str(i)) for i in range(100)]
        q = [Decimal(str(i + 50)) for i in range(100)]
        assert kl_divergence(p, q) >= ZERO

    def test_different_distributions_positive_kl(self) -> None:
        p = [Decimal(str(i)) for i in range(200)]
        q = [Decimal(str(i + 500)) for i in range(200)]
        assert kl_divergence(p, q) > ZERO

    def test_constant_both_returns_zero(self) -> None:
        assert kl_divergence([Decimal("5")] * 50, [Decimal("5")] * 50) == ZERO


# ---------------------------------------------------------------------------
# TestDistributionShiftDetector
# ---------------------------------------------------------------------------


class TestDistributionShiftDetector:
    """Tests for the DistributionShiftDetector class."""

    def test_filling_reference_returns_false(self) -> None:
        detector = DistributionShiftDetector(reference_window=200, test_window=50)
        for i in range(200):
            assert detector.update(Decimal(str(i % 10))) is False

    def test_filling_test_window_returns_false(self) -> None:
        detector = DistributionShiftDetector(reference_window=200, test_window=50)
        # Fill reference
        for i in range(200):
            detector.update(Decimal(str(i % 10)))
        # Partially fill test window (49 values, need 50)
        for i in range(49):
            assert detector.update(Decimal(str(i % 10))) is False

    def test_no_shift_same_distribution(self) -> None:
        detector = DistributionShiftDetector(
            reference_window=200, test_window=50, threshold=Decimal("0.5")
        )
        # Fill reference and test with same repeating pattern
        for i in range(300):
            result = detector.update(Decimal(str(i % 10)))
        # Last update should still be False (same distribution)
        assert result is False

    def test_shift_detected_different_distribution(self) -> None:
        detector = DistributionShiftDetector(
            reference_window=200, test_window=50, threshold=Decimal("0.1")
        )
        # Fill reference with values near 0
        for i in range(200):
            detector.update(Decimal(str(i % 5)))
        # Fill test with values near 100
        results = []
        for i in range(50):
            results.append(detector.update(Decimal(str(100 + i % 5))))
        # The last call (test window full, very different distribution) should detect shift
        assert results[-1] is True

    def test_custom_threshold(self) -> None:
        # Very high threshold -> no shift detected even with different data
        detector = DistributionShiftDetector(
            reference_window=200, test_window=50, threshold=Decimal("100.0")
        )
        for i in range(200):
            detector.update(Decimal(str(i % 5)))
        result = False
        for i in range(50):
            result = detector.update(Decimal(str(100 + i % 5)))
        assert result is False
