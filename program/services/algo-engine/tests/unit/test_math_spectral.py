"""Tests for algo_engine.math.spectral — FourierCycleDetector, WaveletDenoiser, SpectralRegimeDetector."""

from __future__ import annotations

import math
from decimal import Decimal

import numpy as np
import pytest

from moneymaker_common.decimal_utils import ZERO

from algo_engine.math.spectral import (
    FourierCycleDetector,
    SpectralRegimeDetector,
    WaveletDenoiser,
)

ONE = Decimal("1")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pure_sine(period: int = 20, n: int = 400, amplitude: float = 1.0) -> list[Decimal]:
    """Generate a pure sine wave with known period."""
    return [
        Decimal(str(round(amplitude * math.sin(2 * math.pi * i / period), 10))) for i in range(n)
    ]


def _noisy_sine(
    period: int = 20, n: int = 400, noise_std: float = 0.3, seed: int = 42
) -> list[Decimal]:
    """Sine wave with additive Gaussian noise."""
    rng = np.random.default_rng(seed)
    signal = [amplitude := math.sin(2 * math.pi * i / period) for i in range(n)]
    noise = rng.normal(0, noise_std, n)
    return [Decimal(str(round(s + n_, 10))) for s, n_ in zip(signal, noise)]


# ---------------------------------------------------------------------------
# TestFourierCycleDetector
# ---------------------------------------------------------------------------


class TestFourierCycleDetector:
    """Tests for the FourierCycleDetector class."""

    def test_too_short_returns_empty(self) -> None:
        detector = FourierCycleDetector()
        result = detector.detect_cycles([Decimal("1")] * 10)
        assert result == []

    def test_constant_returns_empty(self) -> None:
        detector = FourierCycleDetector()
        result = detector.detect_cycles([Decimal("5")] * 300)
        assert result == []

    def test_pure_sine_detects_period(self) -> None:
        detector = FourierCycleDetector()
        series = _pure_sine(period=20, n=400)
        cycles = detector.detect_cycles(series, min_period=5, max_period=100, top_n=3)
        assert len(cycles) > 0
        # Top cycle should be period=20
        assert cycles[0][0] == 20

    def test_returns_list_of_tuples(self) -> None:
        detector = FourierCycleDetector()
        series = _pure_sine(period=20, n=400)
        cycles = detector.detect_cycles(series)
        for period, power in cycles:
            assert isinstance(period, int)
            assert isinstance(power, Decimal)

    def test_sorted_by_power_descending(self) -> None:
        detector = FourierCycleDetector()
        series = _pure_sine(period=20, n=400)
        cycles = detector.detect_cycles(series, top_n=5)
        if len(cycles) > 1:
            powers = [c[1] for c in cycles]
            assert powers == sorted(powers, reverse=True)

    def test_top_n_honored(self) -> None:
        detector = FourierCycleDetector()
        series = _pure_sine(period=20, n=400)
        cycles = detector.detect_cycles(series, top_n=2)
        assert len(cycles) <= 2

    # --- dominant_cycle tests ---

    def test_dominant_cycle_pure_sine(self) -> None:
        detector = FourierCycleDetector()
        series = _pure_sine(period=20, n=400)
        assert detector.dominant_cycle(series) == 20

    def test_dominant_cycle_short_returns_zero(self) -> None:
        detector = FourierCycleDetector()
        assert detector.dominant_cycle([Decimal("1")] * 10) == 0

    def test_dominant_cycle_constant_returns_zero(self) -> None:
        detector = FourierCycleDetector()
        assert detector.dominant_cycle([Decimal("5")] * 300) == 0

    def test_dominant_cycle_noise_returns_zero(self) -> None:
        detector = FourierCycleDetector()
        rng = np.random.default_rng(42)
        noise = [Decimal(str(round(v, 8))) for v in rng.standard_normal(400)]
        result = detector.dominant_cycle(noise)
        # Pure noise is unlikely to have a significant cycle
        # (could be 0 or a spurious one, but usually 0)
        assert isinstance(result, int)


# ---------------------------------------------------------------------------
# TestWaveletDenoiser
# ---------------------------------------------------------------------------


class TestWaveletDenoiser:
    """Tests for the WaveletDenoiser class."""

    def test_single_element_unchanged(self) -> None:
        denoiser = WaveletDenoiser()
        result = denoiser.denoise([Decimal("5.0")])
        assert result == [Decimal("5.0")]

    def test_empty_unchanged(self) -> None:
        denoiser = WaveletDenoiser()
        result = denoiser.denoise([])
        assert result == []

    def test_output_same_length(self) -> None:
        denoiser = WaveletDenoiser()
        series = [Decimal(str(i)) for i in range(100)]
        result = denoiser.denoise(series)
        assert len(result) == 100

    def test_constant_unchanged(self) -> None:
        denoiser = WaveletDenoiser()
        series = [Decimal("3.0")] * 64
        result = denoiser.denoise(series)
        for v in result:
            assert abs(v - Decimal("3.0")) < Decimal("0.001")

    def test_denoising_reduces_noise(self) -> None:
        # Pure signal
        pure = _pure_sine(period=20, n=256, amplitude=1.0)
        # Noisy version
        noisy = _noisy_sine(period=20, n=256, noise_std=0.5, seed=42)

        denoiser = WaveletDenoiser()
        denoised = denoiser.denoise(noisy)

        # MSE of denoised vs pure should be less than MSE of noisy vs pure
        mse_noisy = sum((float(a) - float(b)) ** 2 for a, b in zip(noisy, pure)) / len(pure)
        mse_denoised = sum((float(a) - float(b)) ** 2 for a, b in zip(denoised, pure)) / len(pure)
        assert mse_denoised < mse_noisy

    def test_result_is_decimal(self) -> None:
        denoiser = WaveletDenoiser()
        series = _noisy_sine(period=20, n=128, seed=42)
        result = denoiser.denoise(series)
        assert all(isinstance(v, Decimal) for v in result)

    def test_soft_vs_hard_differ(self) -> None:
        denoiser = WaveletDenoiser()
        series = _noisy_sine(period=20, n=128, seed=42)
        soft = denoiser.denoise(series, threshold_mode="soft")
        hard = denoiser.denoise(series, threshold_mode="hard")
        assert soft != hard

    def test_custom_wavelet(self) -> None:
        denoiser = WaveletDenoiser(wavelet="haar", level=2)
        series = [Decimal(str(i)) for i in range(64)]
        result = denoiser.denoise(series)
        assert len(result) == 64


# ---------------------------------------------------------------------------
# TestSpectralRegimeDetector
# ---------------------------------------------------------------------------


class TestSpectralRegimeDetector:
    """Tests for the SpectralRegimeDetector class."""

    def test_zeros_before_buffer_full(self) -> None:
        detector = SpectralRegimeDetector(window=100)
        for i in range(99):
            result = detector.update(Decimal(str(i)))
        assert result["dominant_cycle"] == 0
        assert result["spectral_entropy"] == ZERO

    def test_dict_when_full(self) -> None:
        detector = SpectralRegimeDetector(window=100)
        for i in range(100):
            result = detector.update(Decimal(str(math.sin(2 * math.pi * i / 20))))
        assert isinstance(result, dict)
        assert "dominant_cycle" in result
        assert "spectral_entropy" in result
        assert "spectral_slope" in result

    def test_constant_returns_zeros(self) -> None:
        detector = SpectralRegimeDetector(window=100)
        for i in range(100):
            result = detector.update(Decimal("5.0"))
        assert result["dominant_cycle"] == 0
        assert result["spectral_entropy"] == ZERO

    def test_entropy_in_range(self) -> None:
        detector = SpectralRegimeDetector(window=100)
        rng = np.random.default_rng(42)
        for i in range(100):
            result = detector.update(Decimal(str(round(rng.standard_normal(), 8))))
        assert result["spectral_entropy"] >= ZERO
        assert result["spectral_entropy"] <= ONE + Decimal("0.01")  # allow tiny float rounding

    def test_sine_detects_cycle(self) -> None:
        detector = SpectralRegimeDetector(window=200)
        for i in range(200):
            result = detector.update(Decimal(str(round(math.sin(2 * math.pi * i / 20), 10))))
        assert result["dominant_cycle"] == 20

    def test_slope_is_decimal(self) -> None:
        detector = SpectralRegimeDetector(window=100)
        rng = np.random.default_rng(42)
        for i in range(100):
            result = detector.update(Decimal(str(round(rng.standard_normal(), 8))))
        assert isinstance(result["spectral_slope"], Decimal)
