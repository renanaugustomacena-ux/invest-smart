"""Shared pytest fixtures for the Algo Engine test suite."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from algo_engine.config import AlgoEngineSettings
from algo_engine.features.pipeline import OHLCVBar
from algo_engine.strategies.base import SignalSuggestion, TradingStrategy

# ---------------------------------------------------------------------------
# Configuration fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def algo_settings() -> AlgoEngineSettings:
    """Return an AlgoEngineSettings instance with test defaults."""
    return AlgoEngineSettings(
        moneymaker_env="test",
        algo_metrics_port=0,  # disable metrics server in tests
        algo_confidence_threshold=0.65,
        algo_max_signals_per_hour=100,
        algo_max_open_positions=5,
        algo_max_daily_loss_pct=2.0,
        algo_max_drawdown_pct=5.0,
    )


# ---------------------------------------------------------------------------
# Market data fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_ohlcv_bars() -> list[OHLCVBar]:
    """Return a list of 50 synthetic OHLCV bars for testing.

    Generates a simple upward-trending price series starting at 1900.00
    with small random-like deviations (deterministic).
    """
    bars: list[OHLCVBar] = []
    base_price = Decimal("1900.00")

    for i in range(50):
        # Deterministic price pattern: gradual uptrend with oscillation
        offset = Decimal(str(i)) * Decimal("0.50")
        oscillation = Decimal(str((i % 7) - 3)) * Decimal("0.30")

        close = base_price + offset + oscillation
        open_price = close - Decimal("0.20")
        high = close + Decimal("1.50")
        low = close - Decimal("1.50")
        volume = Decimal("1000") + Decimal(str(i * 10))

        bars.append(
            OHLCVBar(
                timestamp=1700000000000 + i * 60000,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=volume,
            )
        )

    return bars


@pytest.fixture
def sample_closes(sample_ohlcv_bars: list[OHLCVBar]) -> list[Decimal]:
    """Extract closing prices from the sample OHLCV bars."""
    return [bar.close for bar in sample_ohlcv_bars]


@pytest.fixture
def sample_highs(sample_ohlcv_bars: list[OHLCVBar]) -> list[Decimal]:
    """Extract high prices from the sample OHLCV bars."""
    return [bar.high for bar in sample_ohlcv_bars]


@pytest.fixture
def sample_lows(sample_ohlcv_bars: list[OHLCVBar]) -> list[Decimal]:
    """Extract low prices from the sample OHLCV bars."""
    return [bar.low for bar in sample_ohlcv_bars]


# ---------------------------------------------------------------------------
# Strategy fixtures
# ---------------------------------------------------------------------------


class StubStrategy(TradingStrategy):
    """A simple stub strategy for testing the router and signal generator."""

    def __init__(
        self,
        name: str = "stub_strategy",
        direction: str = "BUY",
        confidence: Decimal = Decimal("0.80"),
        reasoning: str = "Stub strategy signal",
    ) -> None:
        self._name = name
        self._direction = direction
        self._confidence = confidence
        self._reasoning = reasoning

    @property
    def name(self) -> str:
        return self._name

    def analyze(self, features: dict[str, Any]) -> SignalSuggestion:
        return SignalSuggestion(
            direction=self._direction,
            confidence=self._confidence,
            reasoning=self._reasoning,
        )


@pytest.fixture
def stub_buy_strategy() -> StubStrategy:
    """Return a stub strategy that always suggests BUY."""
    return StubStrategy(name="stub_buy", direction="BUY", confidence=Decimal("0.80"))


@pytest.fixture
def stub_sell_strategy() -> StubStrategy:
    """Return a stub strategy that always suggests SELL."""
    return StubStrategy(name="stub_sell", direction="SELL", confidence=Decimal("0.75"))


@pytest.fixture
def stub_hold_strategy() -> StubStrategy:
    """Return a stub strategy that always suggests HOLD."""
    return StubStrategy(
        name="stub_hold",
        direction="HOLD",
        confidence=Decimal("0.30"),
        reasoning="No clear signal",
    )


# ---------------------------------------------------------------------------
# Portfolio state fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def healthy_portfolio_state() -> dict[str, Any]:
    """Return a portfolio state with no risk limit violations."""
    return {
        "open_position_count": 2,
        "current_drawdown_pct": "1.5",
        "daily_loss_pct": "0.5",
        "equity": "100000.00",
    }


@pytest.fixture
def maxed_out_portfolio_state() -> dict[str, Any]:
    """Return a portfolio state that has hit maximum open positions."""
    return {
        "open_position_count": 5,
        "current_drawdown_pct": "1.0",
        "daily_loss_pct": "0.3",
        "equity": "100000.00",
    }


@pytest.fixture
def high_drawdown_portfolio_state() -> dict[str, Any]:
    """Return a portfolio state with drawdown exceeding the limit."""
    return {
        "open_position_count": 1,
        "current_drawdown_pct": "6.0",
        "daily_loss_pct": "0.5",
        "equity": "94000.00",
    }
