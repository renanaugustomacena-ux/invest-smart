"""Tests for algo_engine.math.bayesian — BayesianRegimeDetector, ThompsonSamplingSelector, BayesianParameterEstimator."""

from __future__ import annotations

from decimal import Decimal

import numpy as np
import pytest

from moneymaker_common.decimal_utils import ZERO

from algo_engine.math.bayesian import (
    BayesianParameterEstimator,
    BayesianRegimeDetector,
    ThompsonSamplingSelector,
)

ONE = Decimal("1")


# ---------------------------------------------------------------------------
# TestBayesianRegimeDetector
# ---------------------------------------------------------------------------


class TestBayesianRegimeDetector:
    """Tests for the BayesianRegimeDetector class."""

    def test_initial_uniform_posteriors(self) -> None:
        detector = BayesianRegimeDetector(n_regimes=5)
        posteriors = detector.get_posteriors()
        expected = Decimal("0.2")
        for prob in posteriors.values():
            assert abs(prob - expected) < Decimal("0.001")

    def test_posteriors_sum_to_one(self) -> None:
        detector = BayesianRegimeDetector(n_regimes=5)
        for i in range(50):
            detector.update(Decimal(str(i * 0.01)))
        posteriors = detector.get_posteriors()
        total = sum(posteriors.values())
        assert abs(total - ONE) < Decimal("0.001")

    def test_update_returns_dict(self) -> None:
        detector = BayesianRegimeDetector(n_regimes=3)
        result = detector.update(Decimal("0.01"))
        assert isinstance(result, dict)
        assert len(result) == 3

    def test_posteriors_evolve(self) -> None:
        detector = BayesianRegimeDetector(n_regimes=5)
        initial = detector.get_posteriors()
        for i in range(20):
            detector.update(Decimal(str(i * 0.1)))
        updated = detector.get_posteriors()
        # At least one posterior should have changed
        assert any(
            abs(initial[k] - updated[k]) > Decimal("0.001")
            for k in initial
        )

    def test_most_likely_regime_returns_tuple(self) -> None:
        detector = BayesianRegimeDetector(n_regimes=4)
        for i in range(10):
            detector.update(Decimal(str(i)))
        name, prob = detector.most_likely_regime()
        assert isinstance(name, str)
        assert isinstance(prob, Decimal)
        assert prob > ZERO

    def test_most_likely_regime_in_posteriors(self) -> None:
        detector = BayesianRegimeDetector(n_regimes=4)
        for i in range(10):
            detector.update(Decimal(str(i)))
        name, prob = detector.most_likely_regime()
        posteriors = detector.get_posteriors()
        assert name in posteriors
        assert posteriors[name] == prob

    def test_stable_series_stabilizes(self) -> None:
        detector = BayesianRegimeDetector(n_regimes=3, hazard_rate=Decimal("0.01"))
        # Feed constant data — posteriors should stabilize
        for i in range(100):
            detector.update(Decimal("5.0"))
        p1 = detector.get_posteriors()
        for i in range(10):
            detector.update(Decimal("5.0"))
        p2 = detector.get_posteriors()
        # Should be very similar after stable input
        for k in p1:
            assert abs(p1[k] - p2[k]) < Decimal("0.05")

    def test_changepoint_shifts_posteriors(self) -> None:
        detector = BayesianRegimeDetector(n_regimes=3, hazard_rate=Decimal("0.1"))
        # Stable period
        for i in range(50):
            detector.update(Decimal("1.0"))
        p_before = detector.get_posteriors()
        # Sudden regime change
        for i in range(20):
            detector.update(Decimal("100.0"))
        p_after = detector.get_posteriors()
        # At least one posterior should shift significantly
        assert any(
            abs(p_before[k] - p_after[k]) > Decimal("0.05")
            for k in p_before
        )


# ---------------------------------------------------------------------------
# TestThompsonSamplingSelector
# ---------------------------------------------------------------------------


class TestThompsonSamplingSelector:
    """Tests for the ThompsonSamplingSelector class."""

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            ThompsonSamplingSelector([])

    def test_select_returns_known_strategy(self) -> None:
        strategies = ["A", "B", "C"]
        selector = ThompsonSamplingSelector(strategies)
        result = selector.select()
        assert result in strategies

    def test_unknown_update_raises(self) -> None:
        selector = ThompsonSamplingSelector(["A", "B"])
        with pytest.raises(ValueError, match="Unknown strategy"):
            selector.update("Z", ONE)

    def test_positive_reward_increments_alpha(self) -> None:
        selector = ThompsonSamplingSelector(["A"])
        stats_before = selector.get_statistics()["A"]["alpha"]
        selector.update("A", Decimal("1.0"))
        stats_after = selector.get_statistics()["A"]["alpha"]
        assert stats_after == stats_before + ONE

    def test_negative_reward_increments_beta(self) -> None:
        selector = ThompsonSamplingSelector(["A"])
        stats_before = selector.get_statistics()["A"]["beta"]
        selector.update("A", Decimal("-1.0"))
        stats_after = selector.get_statistics()["A"]["beta"]
        assert stats_after == stats_before + ONE

    def test_zero_reward_increments_beta(self) -> None:
        selector = ThompsonSamplingSelector(["A"])
        stats_before = selector.get_statistics()["A"]["beta"]
        selector.update("A", ZERO)
        stats_after = selector.get_statistics()["A"]["beta"]
        assert stats_after == stats_before + ONE

    def test_statistics_structure(self) -> None:
        selector = ThompsonSamplingSelector(["X", "Y"])
        stats = selector.get_statistics()
        assert set(stats.keys()) == {"X", "Y"}
        for s in stats.values():
            assert "alpha" in s
            assert "beta" in s
            assert "mean" in s
            assert "samples" in s

    def test_initial_mean_half(self) -> None:
        # Beta(1,1) has mean = 1/2
        selector = ThompsonSamplingSelector(["A"])
        stats = selector.get_statistics()
        assert stats["A"]["mean"] == Decimal("0.5")

    def test_winning_arm_selected_majority(self) -> None:
        # Seed numpy for reproducibility
        np.random.seed(42)
        selector = ThompsonSamplingSelector(["good", "bad"])
        # Give "good" many successes, "bad" many failures
        for _ in range(50):
            selector.update("good", ONE)
            selector.update("bad", Decimal("-1"))
        counts = {"good": 0, "bad": 0}
        for _ in range(100):
            counts[selector.select()] += 1
        assert counts["good"] > counts["bad"]

    def test_samples_counter(self) -> None:
        selector = ThompsonSamplingSelector(["A", "B"])
        selector.update("A", ONE)
        selector.update("A", Decimal("-1"))
        selector.update("B", ONE)
        stats = selector.get_statistics()
        assert stats["A"]["samples"] == 2
        assert stats["B"]["samples"] == 1


# ---------------------------------------------------------------------------
# TestBayesianParameterEstimator
# ---------------------------------------------------------------------------


class TestBayesianParameterEstimator:
    """Tests for the BayesianParameterEstimator class."""

    def test_initial_posterior_mean_equals_prior(self) -> None:
        est = BayesianParameterEstimator(prior_mu=Decimal("5.0"))
        assert est.posterior_mean() == Decimal("5.0")

    def test_initial_variance_zero(self) -> None:
        est = BayesianParameterEstimator()
        # alpha starts at 1, so alpha <= 1 -> returns ZERO
        assert est.posterior_variance() == ZERO

    def test_update_shifts_mean(self) -> None:
        est = BayesianParameterEstimator(prior_mu=ZERO)
        for _ in range(20):
            est.update(Decimal("10.0"))
        assert est.posterior_mean() > Decimal("5.0")

    def test_converges_to_data_mean(self) -> None:
        est = BayesianParameterEstimator(prior_mu=ZERO, prior_kappa=ONE)
        for _ in range(100):
            est.update(Decimal("42.0"))
        assert abs(est.posterior_mean() - Decimal("42")) < Decimal("1")

    def test_variance_positive_after_updates(self) -> None:
        est = BayesianParameterEstimator()
        for i in range(10):
            est.update(Decimal(str(i)))
        assert est.posterior_variance() > ZERO

    def test_credible_interval_degenerate_before_data(self) -> None:
        est = BayesianParameterEstimator(prior_mu=Decimal("5.0"))
        lower, upper = est.credible_interval()
        # No data: returns (mu, mu)
        assert lower == Decimal("5.0")
        assert upper == Decimal("5.0")

    def test_credible_interval_contains_mean(self) -> None:
        est = BayesianParameterEstimator(prior_mu=ZERO)
        for i in range(50):
            est.update(Decimal(str(i * 0.1)))
        lower, upper = est.credible_interval(alpha=Decimal("0.05"))
        mean = est.posterior_mean()
        assert lower <= mean <= upper

    def test_credible_interval_narrows_with_data(self) -> None:
        est = BayesianParameterEstimator(prior_mu=ZERO)
        for i in range(5):
            est.update(Decimal("10.0"))
        _, upper_5 = est.credible_interval()
        lower_5, _ = est.credible_interval()
        width_5 = upper_5 - lower_5

        for i in range(95):
            est.update(Decimal("10.0"))
        lower_100, upper_100 = est.credible_interval()
        width_100 = upper_100 - lower_100

        assert width_100 < width_5

    def test_credible_interval_wider_with_smaller_alpha(self) -> None:
        est = BayesianParameterEstimator(prior_mu=ZERO)
        for i in range(30):
            est.update(Decimal(str(i)))
        lower_95, upper_95 = est.credible_interval(alpha=Decimal("0.05"))
        lower_80, upper_80 = est.credible_interval(alpha=Decimal("0.20"))
        width_95 = upper_95 - lower_95
        width_80 = upper_80 - lower_80
        assert width_95 > width_80
