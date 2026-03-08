"""AlgoEngine — Pure algorithmic trading engine with 9-step deterministic pipeline.

Maps to algo-engine/main.py lines 525-900 with all ML sections removed.
Pipeline: Data Quality -> MTF -> Features -> Regime -> Strategy -> Signal -> Sizing -> Validation
"""

from __future__ import annotations

import asyncio
from decimal import Decimal

from moneymaker_common.enums import Direction, SourceTier
from moneymaker_common.logging import get_logger
from moneymaker_common.metrics import (
    FEATURES_COMPUTED,
    PIPELINE_TIMEOUTS,
    REGIME_CLASSIFIED,
    SIGNAL_CONFIDENCE,
    SIGNALS_GENERATED,
    SIGNALS_REJECTED,
)

from algo_engine.analytics.attribution import StrategyAttribution
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

logger = get_logger(__name__)


class AlgoEngine:
    """Pure algorithmic trading engine — 9-step deterministic pipeline.

    Reuses 22 pure-algorithmic modules from algo-engine with zero ML dependencies.
    Single method: process_bar() -> validated trading signal or None.
    """

    def __init__(
        self,
        *,
        feature_pipeline: FeaturePipeline,
        regime_classifier: RegimeClassifier,
        router: RegimeRouter,
        signal_gen: SignalGenerator,
        position_sizer: PositionSizer,
        validator: SignalValidator,
        spiral_protection: SpiralProtection,
        rate_limiter: SignalRateLimiter,
        data_quality: DataQualityChecker,
        session_classifier: SessionClassifier,
        mtf_analyzer: MultiTimeframeAnalyzer,
        bar_buffer: BarBuffer,
        attribution: StrategyAttribution,
        portfolio_manager: PortfolioStateManager,
        kill_switch: KillSwitch,
    ) -> None:
        self._feature_pipeline = feature_pipeline
        self._regime_classifier = regime_classifier
        self._router = router
        self._signal_gen = signal_gen
        self._position_sizer = position_sizer
        self._validator = validator
        self._spiral_protection = spiral_protection
        self._rate_limiter = rate_limiter
        self._data_quality = data_quality
        self._session_classifier = session_classifier
        self._mtf_analyzer = mtf_analyzer
        self._bar_buffer = bar_buffer
        self._attribution = attribution
        self._portfolio_manager = portfolio_manager
        self._kill_switch = kill_switch
        self._bar_counter: int = 0
        self._pipeline_timeout: float = 5.0

    @property
    def bar_counter(self) -> int:
        return self._bar_counter

    async def process_bar(
        self, symbol: str, timeframe: str, bar: OHLCVBar
    ) -> dict | None:
        """Process a single OHLCV bar through the deterministic pipeline.

        Returns a validated trading signal dict ready for dispatch, or None.
        Enforces a 5-second timeout to prevent pipeline stalls.
        """
        try:
            return await asyncio.wait_for(
                self._process_bar_inner(symbol, timeframe, bar),
                timeout=self._pipeline_timeout,
            )
        except asyncio.TimeoutError:
            PIPELINE_TIMEOUTS.labels(symbol=symbol).inc()
            logger.error(
                "Pipeline timeout exceeded",
                symbol=symbol,
                timeframe=timeframe,
                timeout_seconds=self._pipeline_timeout,
            )
            return None

    async def _process_bar_inner(
        self, symbol: str, timeframe: str, bar: OHLCVBar
    ) -> dict | None:
        """Internal pipeline logic wrapped by process_bar timeout."""
        self._bar_counter += 1

        # --- Step 1: Data quality check (algo-engine lines 529-539) ---
        is_quality_ok, quality_reason = self._data_quality.validate_bar(
            bar_open=bar.open,
            bar_high=bar.high,
            bar_low=bar.low,
            bar_close=bar.close,
            bar_volume=bar.volume,
            bar_timestamp_ms=bar.timestamp,
        )
        if not is_quality_ok:
            logger.debug(
                "Bar rejected for quality", symbol=symbol, reason=quality_reason
            )
            return None

        # --- Step 2: MTF accumulation + bar buffer (algo-engine lines 563-566) ---
        mtf_features = self._mtf_analyzer.add_bar(symbol, timeframe, bar)
        bars = self._bar_buffer.add_bar(symbol, bar)
        if bars is None:
            return None  # Not enough bars yet

        # --- Step 3: Feature computation (algo-engine lines 569-576) ---
        features = self._feature_pipeline.compute_features(symbol, bars)
        if not features:
            return None

        # Enrich with multi-timeframe features if available
        if mtf_features:
            features.update(mtf_features)

        FEATURES_COMPUTED.labels(symbol=symbol).inc()

        # --- Step 4: Regime classification — single rule-based (algo-engine lines 643-644) ---
        # Skips: ensemble, vectorizer, drift monitoring
        classification = self._regime_classifier.classify(features)
        regime = classification.regime

        REGIME_CLASSIFIED.labels(regime=regime.value).inc()

        logger.debug(
            "Regime classified",
            symbol=symbol,
            regime=regime.value,
            confidence=str(classification.confidence),
            adx=str(classification.adx),
        )

        # --- Step 5: Session classification (algo-engine lines 657-660) ---
        session_name = self._session_classifier.classify(
            bar.timestamp // 3_600_000 % 24
        )

        # --- Step 6: Strategy routing — direct (algo-engine line 782) ---
        # Skips: advisor cascade, ML proxy, A/B testing
        suggestion = self._router.route(regime.value, features)
        source_tier = SourceTier.TECHNICAL

        # Record attribution (algo-engine lines 847-854)
        strategy_name = (
            suggestion.metadata.get("strategy", regime.value)
            if suggestion.metadata
            else regime.value
        )
        self._attribution.record_signal(
            strategy_name, str(suggestion.direction), suggestion.confidence
        )

        # --- Step 7: Signal generation — skip HOLD (algo-engine lines 867-874) ---
        if suggestion.direction == Direction.HOLD:
            return None

        current_price = features["latest_close"]
        atr = features.get("atr", Decimal("0"))
        trading_signal = self._signal_gen.generate_signal(
            symbol, suggestion, current_price, atr
        )
        if trading_signal is None:
            return None

        # --- Step 8: Position sizing (algo-engine lines 877-885) ---
        portfolio_state = self._portfolio_manager.get_state()
        sized_lots = self._position_sizer.calculate(
            symbol=symbol,
            entry_price=current_price,
            stop_loss=Decimal(str(trading_signal["stop_loss"])),
            equity=portfolio_state.get("equity", Decimal("1000")),
            drawdown_pct=portfolio_state.get("current_drawdown_pct", Decimal("0")),
        )
        trading_signal["suggested_lots"] = sized_lots
        trading_signal["source_tier"] = source_tier.value

        SIGNAL_CONFIDENCE.observe(float(suggestion.confidence))
        SIGNALS_GENERATED.labels(
            symbol=symbol, direction=str(suggestion.direction)
        ).inc()

        # Step 8a: Spiral protection — cooldown check (algo-engine lines 902-920)
        if self._spiral_protection.is_in_cooldown():
            logger.info("Signal blocked: spiral cooldown active")
            SIGNALS_REJECTED.labels(reason="spiral_cooldown").inc()
            return None

        spiral_mult = self._spiral_protection.get_sizing_multiplier()
        if spiral_mult < Decimal("1"):
            old_lots = Decimal(str(trading_signal.get("suggested_lots", "0")))
            new_lots = (old_lots * spiral_mult).quantize(Decimal("0.01"))
            if new_lots < Decimal("0.01"):
                new_lots = Decimal("0.01")
            trading_signal["suggested_lots"] = new_lots
            logger.info(
                "Spiral protection: lots reduced",
                old_lots=str(old_lots),
                new_lots=str(new_lots),
                multiplier=str(spiral_mult),
            )

        # --- Step 9: Signal validation — 11 checks (algo-engine lines 923-953) ---
        is_valid, rejection_reason = self._validator.validate(
            trading_signal, self._portfolio_manager.get_state()
        )
        if not is_valid:
            SIGNALS_REJECTED.labels(reason=rejection_reason).inc()
            logger.info(
                "Signal rejected",
                signal_id=trading_signal["signal_id"],
                reason=rejection_reason,
            )
            return None

        # Rate limiter (algo-engine lines 946-953)
        if not self._rate_limiter.allow():
            SIGNALS_REJECTED.labels(reason="rate_limit").inc()
            logger.info(
                "Signal rejected: rate limit",
                signal_id=trading_signal["signal_id"],
            )
            return None
        self._rate_limiter.record()

        logger.info(
            "Signal validated",
            signal_id=trading_signal["signal_id"],
            symbol=symbol,
            direction=str(suggestion.direction),
            confidence=str(suggestion.confidence),
            regime=regime.value,
            lots=str(trading_signal["suggested_lots"]),
        )

        return trading_signal
