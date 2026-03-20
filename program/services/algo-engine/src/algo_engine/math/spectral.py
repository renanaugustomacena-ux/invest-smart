# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Spectral analysis for cycle detection and signal denoising.

Provides Fourier-based cycle detection, wavelet denoising, and
spectral regime feature extraction for market data analysis.
"""

from __future__ import annotations

import math
from collections import deque
from decimal import Decimal

import numpy as np
import pywt
from scipy import fft as scipy_fft

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.logging import get_logger

logger = get_logger(__name__)


class FourierCycleDetector:
    """Detect dominant cycles in a price series using FFT."""

    def detect_cycles(
        self,
        series: list[Decimal],
        min_period: int = 5,
        max_period: int = 100,
        top_n: int = 3,
    ) -> list[tuple[int, Decimal]]:
        """Compute FFT of detrended series and find dominant cycle periods.

        Parameters
        ----------
        series:
            Price or return series as Decimal values.
        min_period:
            Minimum cycle period in bars to consider.
        max_period:
            Maximum cycle period in bars to consider.
        top_n:
            Number of top cycles to return.

        Returns
        -------
        list[tuple[int, Decimal]]
            List of ``(period_in_bars, power)`` sorted by power descending.
            Empty list if the series is too short or constant.
        """
        n = len(series)
        min_length = 2 * max_period

        if n < min_length:
            logger.warning(
                "Series length %d < minimum required %d for cycle detection",
                n,
                min_length,
            )
            return []

        arr = np.array([float(v) for v in series], dtype=np.float64)

        # Check for constant series
        if np.ptp(arr) == 0.0:
            logger.warning("Constant series, no cycles detectable")
            return []

        # Remove linear trend
        x = np.arange(n, dtype=np.float64)
        slope, intercept = np.polyfit(x, arr, 1)
        detrended = arr - (slope * x + intercept)

        # Compute one-sided FFT power spectrum
        fft_vals = scipy_fft.rfft(detrended)
        power = np.abs(fft_vals) ** 2
        freqs = scipy_fft.rfftfreq(n)

        # Convert frequencies to periods; skip DC component (index 0)
        results: list[tuple[int, float]] = []
        for i in range(1, len(freqs)):
            if freqs[i] == 0.0:
                continue
            period = round(1.0 / freqs[i])
            if min_period <= period <= max_period:
                results.append((period, float(power[i])))

        if not results:
            return []

        # If multiple FFT bins map to the same period, keep the max power
        period_power: dict[int, float] = {}
        for period, pwr in results:
            if period not in period_power or pwr > period_power[period]:
                period_power[period] = pwr

        sorted_cycles = sorted(period_power.items(), key=lambda t: t[1], reverse=True)
        top_cycles = sorted_cycles[:top_n]

        return [(period, Decimal(str(pwr))) for period, pwr in top_cycles]

    def dominant_cycle(
        self,
        series: list[Decimal],
        min_period: int = 5,
        max_period: int = 100,
    ) -> int:
        """Return the period of the strongest cycle.

        A cycle is considered significant only when its power exceeds
        twice the median power across the spectrum.

        Returns
        -------
        int
            Dominant cycle period in bars, or ``0`` if no significant
            cycle is found.
        """
        n = len(series)
        min_length = 2 * max_period

        if n < min_length:
            return 0

        arr = np.array([float(v) for v in series], dtype=np.float64)

        if np.ptp(arr) == 0.0:
            return 0

        # Remove linear trend
        x = np.arange(n, dtype=np.float64)
        slope, intercept = np.polyfit(x, arr, 1)
        detrended = arr - (slope * x + intercept)

        fft_vals = scipy_fft.rfft(detrended)
        power = np.abs(fft_vals) ** 2

        # Exclude DC for significance test
        spectrum_power = power[1:]
        if len(spectrum_power) == 0:
            return 0

        median_power = float(np.median(spectrum_power))

        freqs = scipy_fft.rfftfreq(n)

        best_period = 0
        best_power = 0.0

        for i in range(1, len(freqs)):
            if freqs[i] == 0.0:
                continue
            period = round(1.0 / freqs[i])
            if min_period <= period <= max_period:
                pwr = float(power[i])
                if pwr > best_power:
                    best_power = pwr
                    best_period = period

        # Significance: dominant peak must exceed 2x median power
        if best_period > 0 and best_power > 2.0 * median_power:
            return best_period

        return 0


class WaveletDenoiser:
    """Wavelet-based signal denoising using VisuShrink thresholding."""

    def __init__(self, wavelet: str = "db4", level: int = 3) -> None:
        self.wavelet = wavelet
        self.level = level

    def denoise(
        self,
        series: list[Decimal],
        threshold_mode: str = "soft",
    ) -> list[Decimal]:
        """Denoise a series via multi-level wavelet decomposition.

        Parameters
        ----------
        series:
            Input signal as Decimal values.
        threshold_mode:
            ``"soft"`` or ``"hard"`` thresholding.

        Returns
        -------
        list[Decimal]
            Denoised signal with the same length as input.
        """
        n = len(series)
        if n < 2:
            return list(series)

        arr = np.array([float(v) for v in series], dtype=np.float64)

        # Clamp decomposition level to the maximum allowed
        max_level = pywt.dwt_max_level(n, pywt.Wavelet(self.wavelet).dec_len)
        actual_level = min(self.level, max_level)

        if actual_level < 1:
            return list(series)

        # Multi-level wavelet decomposition
        coeffs = pywt.wavedec(arr, self.wavelet, level=actual_level)

        # Estimate noise sigma from finest detail coefficients (d1)
        d1 = coeffs[-1]
        sigma = float(np.median(np.abs(d1))) / 0.6745

        if sigma == 0.0:
            # Signal has no noise at the finest scale
            return list(series)

        # Universal threshold (VisuShrink)
        threshold = sigma * math.sqrt(2.0 * math.log(n))

        # Apply threshold to all detail coefficients (keep approximation intact)
        denoised_coeffs = [coeffs[0]]
        for detail in coeffs[1:]:
            denoised_coeffs.append(pywt.threshold(detail, value=threshold, mode=threshold_mode))

        # Reconstruct
        reconstructed = pywt.waverec(denoised_coeffs, self.wavelet)

        # pywt may return an array one element longer due to padding
        reconstructed = reconstructed[:n]

        return [Decimal(str(round(float(v), 10))) for v in reconstructed]


class SpectralRegimeDetector:
    """Extract spectral features from a rolling window of values."""

    def __init__(self, window: int = 100) -> None:
        self.window = window
        self._buffer: deque[Decimal] = deque(maxlen=window)
        self._cycle_detector = FourierCycleDetector()

    def update(self, value: Decimal) -> dict:
        """Append a value and compute spectral regime features.

        Returns
        -------
        dict
            ``dominant_cycle`` – strongest cycle period (int, 0 if none).
            ``spectral_entropy`` – entropy of normalised power spectrum
            (higher means noisier, lower means more cyclical).
            ``spectral_slope`` – slope of log-power vs log-frequency
            (steeper negative slope indicates stronger trending behaviour).
            Returns zeros if the buffer is not yet full.
        """
        self._buffer.append(value)

        if len(self._buffer) < self.window:
            return {
                "dominant_cycle": 0,
                "spectral_entropy": ZERO,
                "spectral_slope": ZERO,
            }

        arr = np.array([float(v) for v in self._buffer], dtype=np.float64)
        n = len(arr)

        # Check constant series
        if np.ptp(arr) == 0.0:
            return {
                "dominant_cycle": 0,
                "spectral_entropy": ZERO,
                "spectral_slope": ZERO,
            }

        # Remove linear trend
        x = np.arange(n, dtype=np.float64)
        slope, intercept = np.polyfit(x, arr, 1)
        detrended = arr - (slope * x + intercept)

        fft_vals = scipy_fft.rfft(detrended)
        power = np.abs(fft_vals[1:]) ** 2  # exclude DC
        freqs = scipy_fft.rfftfreq(n)[1:]

        if len(power) == 0 or np.sum(power) == 0.0:
            return {
                "dominant_cycle": 0,
                "spectral_entropy": ZERO,
                "spectral_slope": ZERO,
            }

        # --- Dominant cycle ---
        max_period = n // 2
        dominant_cycle = 0
        best_power = 0.0
        median_power = float(np.median(power))

        for i, freq in enumerate(freqs):
            if freq == 0.0:
                continue
            period = round(1.0 / freq)
            if 5 <= period <= max_period:
                pwr = float(power[i])
                if pwr > best_power:
                    best_power = pwr
                    dominant_cycle = period

        if median_power > 0.0 and best_power <= 2.0 * median_power:
            dominant_cycle = 0

        # --- Spectral entropy ---
        normalised = power / np.sum(power)
        # Avoid log(0)
        normalised = normalised[normalised > 0]
        entropy = -float(np.sum(normalised * np.log(normalised)))
        # Normalise to [0, 1] by dividing by max possible entropy
        max_entropy = math.log(len(power)) if len(power) > 1 else 1.0
        spectral_entropy = entropy / max_entropy if max_entropy > 0.0 else 0.0

        # --- Spectral slope ---
        # Linear regression of log-power vs log-frequency
        pos_mask = (freqs > 0) & (power > 0)
        if np.sum(pos_mask) >= 2:
            log_freq = np.log(freqs[pos_mask])
            log_power = np.log(power[pos_mask])
            spectral_slope_val, _ = np.polyfit(log_freq, log_power, 1)
        else:
            spectral_slope_val = 0.0

        return {
            "dominant_cycle": dominant_cycle,
            "spectral_entropy": Decimal(str(round(spectral_entropy, 10))),
            "spectral_slope": Decimal(str(round(float(spectral_slope_val), 10))),
        }
