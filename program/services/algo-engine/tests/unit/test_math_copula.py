"""Tests for algo_engine.math.copula — rank_transform, tail_dependence, GaussianCopula, DependencyAnalyzer."""

from __future__ import annotations

from decimal import Decimal

import numpy as np
import pytest

from moneymaker_common.decimal_utils import ZERO

from algo_engine.math.copula import (
    DependencyAnalyzer,
    GaussianCopula,
    rank_transform,
    tail_dependence,
)

ONE = Decimal("1")


# ---------------------------------------------------------------------------
# Helper: generate pseudo-uniform marginals
# ---------------------------------------------------------------------------


def _uniform_pair(
    n: int = 50, rho: float = 0.0, seed: int = 42
) -> tuple[list[Decimal], list[Decimal]]:
    """Generate correlated uniform samples via Gaussian copula sampling."""
    u, v = GaussianCopula.sample(Decimal(str(rho)), n, seed=seed)
    return u, v


def _raw_correlated_pair(
    n: int = 50, rho: float = 0.8, seed: int = 42
) -> tuple[list[Decimal], list[Decimal]]:
    """Generate correlated raw data (not yet rank-transformed)."""
    rng = np.random.default_rng(seed)
    cov = np.array([[1.0, rho], [rho, 1.0]])
    data = rng.multivariate_normal([0, 0], cov, size=n)
    x = [Decimal(str(round(v, 8))) for v in data[:, 0]]
    y = [Decimal(str(round(v, 8))) for v in data[:, 1]]
    return x, y


# ---------------------------------------------------------------------------
# TestRankTransform
# ---------------------------------------------------------------------------


class TestRankTransform:
    """Tests for the rank_transform function."""

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="at least 2"):
            rank_transform([Decimal("1")])

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="at least 2"):
            rank_transform([])

    def test_ascending_known_values(self) -> None:
        result = rank_transform([Decimal("10"), Decimal("20"), Decimal("30")])
        # ranks: 1, 2, 3; n+1=4; u = [0.25, 0.5, 0.75]
        assert result == [Decimal("0.25"), Decimal("0.5"), Decimal("0.75")]

    def test_values_in_open_interval(self) -> None:
        series = [Decimal(str(i)) for i in range(50)]
        result = rank_transform(series)
        for u in result:
            assert ZERO < u < ONE

    def test_output_length_preserved(self) -> None:
        series = [Decimal(str(i)) for i in range(100)]
        result = rank_transform(series)
        assert len(result) == 100

    def test_descending_reverses_ranks(self) -> None:
        result = rank_transform([Decimal("30"), Decimal("20"), Decimal("10")])
        # ranks: 3, 2, 1; n+1=4; u = [0.75, 0.5, 0.25]
        assert result == [Decimal("0.75"), Decimal("0.5"), Decimal("0.25")]


# ---------------------------------------------------------------------------
# TestTailDependence
# ---------------------------------------------------------------------------


class TestTailDependence:
    """Tests for the tail_dependence function."""

    def test_mismatched_lengths_raises(self) -> None:
        with pytest.raises(ValueError, match="lengths must match"):
            tail_dependence(
                [Decimal("0.5")] * 50,
                [Decimal("0.5")] * 30,
            )

    def test_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="at least 30"):
            tail_dependence(
                [Decimal("0.5")] * 10,
                [Decimal("0.5")] * 10,
            )

    def test_invalid_threshold_raises(self) -> None:
        u = [Decimal("0.5")] * 50
        with pytest.raises(ValueError, match="Threshold"):
            tail_dependence(u, u, threshold=Decimal("0.6"))

    def test_result_in_range(self) -> None:
        u, v = _uniform_pair(n=50, rho=0.5, seed=42)
        lower, upper = tail_dependence(u, v)
        assert ZERO <= lower <= ONE
        assert ZERO <= upper <= ONE

    def test_independent_low_tail_dep(self) -> None:
        u, v = _uniform_pair(n=100, rho=0.0, seed=42)
        lower, upper = tail_dependence(u, v)
        # Independent series should have low tail dependence
        assert lower < Decimal("0.5")
        assert upper < Decimal("0.5")

    def test_returns_tuple_of_two(self) -> None:
        u, v = _uniform_pair(n=50, rho=0.3, seed=42)
        result = tail_dependence(u, v)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# TestGaussianCopula
# ---------------------------------------------------------------------------


class TestGaussianCopula:
    """Tests for the GaussianCopula class."""

    # --- fit tests ---

    def test_fit_mismatched_raises(self) -> None:
        with pytest.raises(ValueError, match="lengths must match"):
            GaussianCopula.fit(
                [Decimal("0.5")] * 50,
                [Decimal("0.5")] * 30,
            )

    def test_fit_too_short_raises(self) -> None:
        u = [Decimal(str(i / 11)) for i in range(1, 11)]  # 10 values in (0,1)
        with pytest.raises(ValueError, match="at least 30"):
            GaussianCopula.fit(u, u)

    def test_fit_outside_01_raises(self) -> None:
        n = 50
        u = [Decimal(str(i / (n + 1))) for i in range(1, n + 1)]
        v = list(u)
        v[0] = Decimal("0")  # exactly 0 is outside (0,1)
        with pytest.raises(ValueError, match="outside"):
            GaussianCopula.fit(u, v)

    def test_fit_correlated_positive_rho(self) -> None:
        u, v = _uniform_pair(n=100, rho=0.7, seed=42)
        rho = GaussianCopula.fit(u, v)
        assert rho > Decimal("0.3")

    def test_fit_rho_in_range(self) -> None:
        u, v = _uniform_pair(n=50, rho=0.5, seed=42)
        rho = GaussianCopula.fit(u, v)
        assert -ONE <= rho <= ONE

    # --- sample tests ---

    def test_sample_length(self) -> None:
        u, v = GaussianCopula.sample(Decimal("0.5"), 100, seed=42)
        assert len(u) == 100
        assert len(v) == 100

    def test_sample_values_in_01(self) -> None:
        u, v = GaussianCopula.sample(Decimal("0.5"), 200, seed=42)
        for ui, vi in zip(u, v):
            assert ZERO < ui < ONE
            assert ZERO < vi < ONE

    def test_sample_invalid_rho_raises(self) -> None:
        with pytest.raises(ValueError, match="rho"):
            GaussianCopula.sample(Decimal("1.5"), 10)

    def test_sample_invalid_n_raises(self) -> None:
        with pytest.raises(ValueError, match="n must be"):
            GaussianCopula.sample(Decimal("0.5"), 0)

    def test_sample_deterministic_seed(self) -> None:
        u1, v1 = GaussianCopula.sample(Decimal("0.5"), 50, seed=99)
        u2, v2 = GaussianCopula.sample(Decimal("0.5"), 50, seed=99)
        assert u1 == u2
        assert v1 == v2

    # --- joint_cdf tests ---

    def test_joint_cdf_independent(self) -> None:
        u, v = Decimal("0.3"), Decimal("0.7")
        result = GaussianCopula.joint_cdf(u, v, ZERO)
        expected = u * v
        assert abs(result - expected) < Decimal("0.001")

    def test_joint_cdf_perfect_positive(self) -> None:
        u, v = Decimal("0.3"), Decimal("0.7")
        result = GaussianCopula.joint_cdf(u, v, ONE)
        assert result == min(u, v)

    def test_joint_cdf_perfect_negative(self) -> None:
        u, v = Decimal("0.3"), Decimal("0.7")
        result = GaussianCopula.joint_cdf(u, v, -ONE)
        expected = max(u + v - ONE, ZERO)
        assert result == expected

    def test_joint_cdf_invalid_u_raises(self) -> None:
        with pytest.raises(ValueError, match="u must be"):
            GaussianCopula.joint_cdf(ZERO, Decimal("0.5"), ZERO)

    def test_joint_cdf_in_valid_range(self) -> None:
        result = GaussianCopula.joint_cdf(Decimal("0.5"), Decimal("0.5"), Decimal("0.3"))
        assert ZERO <= result <= ONE


# ---------------------------------------------------------------------------
# TestDependencyAnalyzer
# ---------------------------------------------------------------------------


class TestDependencyAnalyzer:
    """Tests for the DependencyAnalyzer class."""

    def test_window_too_small_raises(self) -> None:
        with pytest.raises(ValueError, match="at least 30"):
            DependencyAnalyzer(window=10)

    def test_none_before_full(self) -> None:
        analyzer = DependencyAnalyzer(window=30)
        for i in range(29):
            result = analyzer.update(Decimal(str(i)), Decimal(str(i * 2)))
        assert result is None

    def test_dict_when_full(self) -> None:
        analyzer = DependencyAnalyzer(window=30)
        x, y = _raw_correlated_pair(n=30, rho=0.8, seed=42)
        result = None
        for xi, yi in zip(x, y):
            result = analyzer.update(xi, yi)
        assert result is not None
        assert isinstance(result, dict)

    def test_all_keys_present(self) -> None:
        analyzer = DependencyAnalyzer(window=30)
        x, y = _raw_correlated_pair(n=30, rho=0.5, seed=42)
        result = None
        for xi, yi in zip(x, y):
            result = analyzer.update(xi, yi)
        expected_keys = {
            "pearson",
            "rank_correlation",
            "copula_rho",
            "tail_dep_lower",
            "tail_dep_upper",
            "is_tail_dependent",
        }
        assert set(result.keys()) == expected_keys

    def test_correlated_positive_pearson(self) -> None:
        analyzer = DependencyAnalyzer(window=50)
        x, y = _raw_correlated_pair(n=50, rho=0.8, seed=42)
        result = None
        for xi, yi in zip(x, y):
            result = analyzer.update(xi, yi)
        assert result["pearson"] > Decimal("0.3")

    def test_pearson_in_range(self) -> None:
        analyzer = DependencyAnalyzer(window=50)
        x, y = _raw_correlated_pair(n=50, rho=0.5, seed=42)
        result = None
        for xi, yi in zip(x, y):
            result = analyzer.update(xi, yi)
        assert -ONE <= result["pearson"] <= ONE
