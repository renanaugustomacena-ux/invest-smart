"""Tests for CorrelationChecker and _decompose_exposure.

All tests use real class instances — no unittest.mock.
"""

from __future__ import annotations

import pytest

from algo_engine.signals.correlation import CorrelationChecker, _decompose_exposure

# ---------------------------------------------------------------------------
# _decompose_exposure() tests
# ---------------------------------------------------------------------------


class TestDecomposeExposure:
    """Test currency decomposition for known and unknown symbols."""

    def test_buy_eurusd(self) -> None:
        result = _decompose_exposure("EURUSD", "BUY")
        assert result == {"EUR": 1.0, "USD": -1.0}

    def test_sell_eurusd(self) -> None:
        result = _decompose_exposure("EURUSD", "SELL")
        assert result == {"EUR": -1.0, "USD": 1.0}

    def test_buy_gbpusd(self) -> None:
        result = _decompose_exposure("GBPUSD", "BUY")
        assert result == {"GBP": 1.0, "USD": -1.0}

    def test_sell_gbpusd(self) -> None:
        result = _decompose_exposure("GBPUSD", "SELL")
        assert result == {"GBP": -1.0, "USD": 1.0}

    def test_buy_usdjpy(self) -> None:
        result = _decompose_exposure("USDJPY", "BUY")
        assert result == {"USD": 1.0, "JPY": -1.0}

    def test_unknown_symbol_returns_empty(self) -> None:
        result = _decompose_exposure("ZZZZZ", "BUY")
        assert result == {}


# ---------------------------------------------------------------------------
# CorrelationChecker.check() tests
# ---------------------------------------------------------------------------


class TestCorrelationCheckerCheck:
    """Test the check() method with various position scenarios."""

    def test_empty_positions_always_passes(self) -> None:
        checker = CorrelationChecker(max_exposure_per_currency=3.0)
        allowed, reason = checker.check("EURUSD", "BUY", [])
        assert allowed is True
        assert reason == ""

    def test_positions_near_limit_passes(self) -> None:
        """2 BUY EURUSD open → EUR exposure = 2. Adding 1 more → 3.0 = limit."""
        checker = CorrelationChecker(max_exposure_per_currency=3.0)
        open_positions = [
            {"symbol": "EURUSD", "direction": "BUY"},
            {"symbol": "EURUSD", "direction": "BUY"},
        ]
        allowed, reason = checker.check("EURUSD", "BUY", open_positions)
        assert allowed is True
        assert reason == ""

    def test_positions_exceed_limit_rejected(self) -> None:
        """3 BUY EURUSD open → EUR exposure = 3. Adding 1 more → 4.0 > 3.0."""
        checker = CorrelationChecker(max_exposure_per_currency=3.0)
        open_positions = [
            {"symbol": "EURUSD", "direction": "BUY"},
            {"symbol": "EURUSD", "direction": "BUY"},
            {"symbol": "EURUSD", "direction": "BUY"},
        ]
        allowed, reason = checker.check("EURUSD", "BUY", open_positions)
        assert allowed is False
        assert "EUR" in reason

    def test_opposing_positions_cancel_out(self) -> None:
        """BUY + SELL same pair cancel: net EUR = 0. Adding BUY → EUR = 1."""
        checker = CorrelationChecker(max_exposure_per_currency=3.0)
        open_positions = [
            {"symbol": "EURUSD", "direction": "BUY"},
            {"symbol": "EURUSD", "direction": "SELL"},
        ]
        allowed, reason = checker.check("EURUSD", "BUY", open_positions)
        assert allowed is True
        assert reason == ""

    def test_cross_pair_eur_exposure(self) -> None:
        """EURUSD BUY + EURJPY BUY both add +1 EUR. 3 of them → EUR = 3.
        Adding EURGBP BUY → EUR = 4 > 3."""
        checker = CorrelationChecker(max_exposure_per_currency=3.0)
        open_positions = [
            {"symbol": "EURUSD", "direction": "BUY"},
            {"symbol": "EURJPY", "direction": "BUY"},
            {"symbol": "EURGBP", "direction": "BUY"},
        ]
        allowed, reason = checker.check("EURUSD", "BUY", open_positions)
        assert allowed is False
        assert "EUR" in reason

    def test_cross_pair_eur_within_limit(self) -> None:
        """EURUSD BUY + EURJPY BUY = EUR exposure 2. Adding EURGBP BUY → 3.0 = limit."""
        checker = CorrelationChecker(max_exposure_per_currency=3.0)
        open_positions = [
            {"symbol": "EURUSD", "direction": "BUY"},
            {"symbol": "EURJPY", "direction": "BUY"},
        ]
        allowed, reason = checker.check("EURGBP", "BUY", open_positions)
        assert allowed is True
        assert reason == ""

    def test_unmapped_symbol_passes(self) -> None:
        """An unknown symbol should pass (decomposition returns {})."""
        checker = CorrelationChecker(max_exposure_per_currency=1.0)
        open_positions = [
            {"symbol": "EURUSD", "direction": "BUY"},
            {"symbol": "EURUSD", "direction": "BUY"},
        ]
        allowed, reason = checker.check("BTCUSD", "BUY", open_positions)
        assert allowed is True
        assert reason == ""

    def test_usd_exposure_across_pairs(self) -> None:
        """BUY EURUSD = -1 USD, BUY GBPUSD = -1 USD, BUY AUDUSD = -1 USD.
        Adding BUY NZDUSD → USD = -4 → abs = 4 > 3."""
        checker = CorrelationChecker(max_exposure_per_currency=3.0)
        open_positions = [
            {"symbol": "EURUSD", "direction": "BUY"},
            {"symbol": "GBPUSD", "direction": "BUY"},
            {"symbol": "AUDUSD", "direction": "BUY"},
        ]
        allowed, reason = checker.check("NZDUSD", "BUY", open_positions)
        assert allowed is False
        assert "USD" in reason

    def test_custom_max_exposure(self) -> None:
        """With max_exposure=1.0, even a single existing position blocks same currency."""
        checker = CorrelationChecker(max_exposure_per_currency=1.0)
        open_positions = [
            {"symbol": "EURUSD", "direction": "BUY"},
        ]
        allowed, reason = checker.check("EURJPY", "BUY", open_positions)
        assert allowed is False
        assert "EUR" in reason

    def test_sell_reduces_positive_exposure(self) -> None:
        """3 BUY EURUSD = EUR 3. Adding SELL EURJPY reduces EUR by 1 → net 2. Passes."""
        checker = CorrelationChecker(max_exposure_per_currency=3.0)
        open_positions = [
            {"symbol": "EURUSD", "direction": "BUY"},
            {"symbol": "EURUSD", "direction": "BUY"},
            {"symbol": "EURUSD", "direction": "BUY"},
        ]
        allowed, reason = checker.check("EURJPY", "SELL", open_positions)
        assert allowed is True
        assert reason == ""
