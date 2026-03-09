"""Integration test fixtures — real components, no mocks.

Builds a complete AlgoEngine with all core components using their real
constructors and default parameters. Only KillSwitch runs in local-only
mode (no Redis) with fail-closed behavior deactivated at startup.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest

from algo_engine.analytics.attribution import StrategyAttribution
from algo_engine.engine import AlgoEngine
from algo_engine.features.data_quality import DataQualityChecker
from algo_engine.features.mtf_analyzer import MultiTimeframeAnalyzer
from algo_engine.features.pipeline import FeaturePipeline, OHLCVBar
from algo_engine.features.regime import RegimeClassifier
from algo_engine.features.sessions import SessionClassifier
from algo_engine.kill_switch import KillSwitch
from algo_engine.portfolio import PortfolioStateManager
from algo_engine.signals.generator import SignalGenerator
from algo_engine.signals.position_sizer import PositionSizer
from algo_engine.signals.rate_limiter import SignalRateLimiter
from algo_engine.signals.spiral_protection import SpiralProtection
from algo_engine.signals.validator import SignalValidator
from algo_engine.strategies.regime_router import RegimeRouter
from algo_engine.zmq_adapter import BarBuffer


def _make_xauusd_bars(
    count: int = 60,
    start_price: Decimal = Decimal("2340.00"),
    trend: Decimal = Decimal("0.30"),
) -> list[OHLCVBar]:
    """Generate a deterministic XAU/USD bar series.

    Prices follow a steady upward trend with realistic intra-bar ranges.
    Based on typical XAU/USD M5 candle characteristics:
    - Average range: ~$2-3 per bar
    - Spread between open/close: ~$0.50-1.50
    - Volume: 800-1500 contracts per bar
    """
    bars: list[OHLCVBar] = []
    for i in range(count):
        price = start_price + trend * Decimal(str(i))
        # Deterministic oscillation to create varying regimes
        cycle = Decimal(str((i % 11) - 5)) * Decimal("0.25")
        close = price + cycle
        open_price = close - Decimal("0.60")
        high = max(open_price, close) + Decimal("1.20")
        low = min(open_price, close) - Decimal("1.10")
        volume = Decimal("900") + Decimal(str((i % 13) * 50))

        bars.append(
            OHLCVBar(
                timestamp=1700000000000 + i * 300_000,  # 5-minute bars
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=volume,
            )
        )
    return bars


@pytest.fixture
def xauusd_trending_bars() -> list[OHLCVBar]:
    """60 XAU/USD bars with a clear upward trend (~$0.30/bar)."""
    return _make_xauusd_bars(count=60, trend=Decimal("0.30"))


@pytest.fixture
def xauusd_ranging_bars() -> list[OHLCVBar]:
    """60 XAU/USD bars with no trend (flat market, oscillating)."""
    return _make_xauusd_bars(count=60, trend=Decimal("0.00"))


@pytest.fixture
def xauusd_declining_bars() -> list[OHLCVBar]:
    """60 XAU/USD bars with a clear downward trend."""
    return _make_xauusd_bars(count=60, trend=Decimal("-0.35"))


def build_engine(
    *,
    kill_switch: KillSwitch | None = None,
    spiral_protection: SpiralProtection | None = None,
    portfolio_manager: PortfolioStateManager | None = None,
    min_confidence: Decimal = Decimal("0.50"),
    max_signals_per_hour: int = 100,
    min_bars: int = 50,
) -> AlgoEngine:
    """Build a real AlgoEngine with all core components.

    No mocks. Every component is instantiated via its real constructor.
    KillSwitch runs in local-only mode (no Redis).
    """
    if kill_switch is None:
        kill_switch = KillSwitch(redis_url="redis://nonexistent:6379")

    if spiral_protection is None:
        spiral_protection = SpiralProtection(
            consecutive_loss_threshold=3,
            max_consecutive_loss=5,
            cooldown_minutes=60,
        )

    if portfolio_manager is None:
        portfolio_manager = PortfolioStateManager()

    session_classifier = SessionClassifier()

    return AlgoEngine(
        feature_pipeline=FeaturePipeline(),
        regime_classifier=RegimeClassifier(),
        router=RegimeRouter(),
        signal_gen=SignalGenerator(),
        position_sizer=PositionSizer(
            risk_per_trade_pct=Decimal("1.0"),
            default_equity=Decimal("10000"),
            min_lots=Decimal("0.01"),
            max_lots=Decimal("0.10"),
        ),
        validator=SignalValidator(
            min_confidence=min_confidence,
            session_classifier=session_classifier,
        ),
        spiral_protection=spiral_protection,
        rate_limiter=SignalRateLimiter(max_per_hour=max_signals_per_hour),
        data_quality=DataQualityChecker(),
        session_classifier=session_classifier,
        mtf_analyzer=MultiTimeframeAnalyzer(),
        bar_buffer=BarBuffer(window_size=250, min_bars=min_bars),
        attribution=StrategyAttribution(),
        portfolio_manager=portfolio_manager,
        kill_switch=kill_switch,
    )


@pytest.fixture
def engine() -> AlgoEngine:
    """A fully wired AlgoEngine in local-only mode (no external deps)."""
    return build_engine()
