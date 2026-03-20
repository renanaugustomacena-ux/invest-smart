# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Algo Engine — Async entry point.

Maps to algo-engine/main.py run_brain() (lines 172-380 init, lines 494+ loop)
with all ML/intelligence modules removed.

Pipeline: ZMQ subscriber -> AlgoEngine.process_bar() -> gRPC dispatch to MT5 Bridge
"""

from __future__ import annotations

import asyncio
import os
import signal
import sys
import time
from decimal import Decimal

from moneymaker_common.audit_pg import PostgresAuditTrail
from moneymaker_common.health import HealthChecker
from moneymaker_common.logging import get_logger, setup_logging
from moneymaker_common.metrics import (
    ERROR_COUNTER,
    PIPELINE_LATENCY,
    SERVICE_UP,
    start_metrics_server,
)

from algo_engine.alerting.dispatcher import AlertDispatcher, AlertLevel
from algo_engine.alerting.telegram import TelegramChannel
from algo_engine.analytics.attribution import StrategyAttribution
from algo_engine.features.data_quality import DataQualityChecker
from algo_engine.features.mtf_analyzer import MultiTimeframeAnalyzer
from algo_engine.features.pipeline import FeaturePipeline
from algo_engine.features.regime import RegimeClassifier
from algo_engine.features.sessions import SessionClassifier
from algo_engine.grpc_client import BridgeClient
from algo_engine.kill_switch import KillSwitch
from algo_engine.portfolio import PortfolioStateManager
from algo_engine.signals.correlation import CorrelationChecker
from algo_engine.signals.generator import SignalGenerator
from algo_engine.signals.position_sizer import PositionSizer
from algo_engine.signals.rate_limiter import SignalRateLimiter
from algo_engine.signals.spiral_protection import DrawdownEnforcer, SpiralProtection
from algo_engine.signals.validator import SignalValidator
from algo_engine.zmq_adapter import BarBuffer, determine_message_type, parse_bar_message

from algo_engine.config import AlgoEngineSettings
from algo_engine.engine import AlgoEngine
from algo_engine.strategies import build_algo_router

logger = get_logger(__name__)


async def run_engine(settings: AlgoEngineSettings) -> None:
    """Main async loop for the algo engine service."""

    # --- 1. Health checker (algo-engine line 176) ---
    health = HealthChecker(service_name=settings.algo_service_name)

    # --- 2. PostgreSQL audit trail (algo-engine lines 179-196) ---
    audit = PostgresAuditTrail(settings.algo_service_name)
    audit_db_url = os.environ.get("ALGO_DATABASE_URL")
    if audit_db_url:
        try:
            await audit.connect(audit_db_url)
            logger.info("Audit trail connected to database")
        except Exception as exc:
            logger.warning(
                "Audit trail: database unavailable, local log only",
                error=str(exc),
            )
    else:
        logger.info("Audit trail: ALGO_DATABASE_URL not set, in-memory only")

    audit.start_periodic_flush(interval_sec=30.0)

    # --- 3. Prometheus metrics server (algo-engine lines 198-201) ---
    start_metrics_server(port=settings.algo_metrics_port)
    SERVICE_UP.labels(service=settings.algo_service_name).set(1)
    logger.info("Metrics server started", port=settings.algo_metrics_port)

    # --- 4. Kill switch — Redis-backed emergency stop (algo-engine lines 204-206) ---
    kill_switch = KillSwitch(
        host=settings.moneymaker_redis_host,
        port=settings.moneymaker_redis_port,
        password=settings.moneymaker_redis_password,
    )
    await kill_switch.connect()
    logger.info("Kill Switch initialized")

    # --- 5. Spiral protection (algo-engine lines 209-213) ---
    spiral_protection = SpiralProtection(
        consecutive_loss_threshold=settings.algo_spiral_loss_threshold,
        max_consecutive_loss=settings.algo_spiral_max_losses,
        cooldown_minutes=settings.algo_spiral_cooldown_minutes,
    )
    logger.info("Spiral Protection initialized")

    # --- 6. Drawdown enforcer (algo-engine lines 217-223) ---
    drawdown_enforcer = DrawdownEnforcer(
        kill_switch=kill_switch,
        max_drawdown_pct=Decimal(str(settings.algo_max_drawdown_pct)),
    )
    logger.info(
        "Drawdown Enforcer initialized",
        max_pct=str(settings.algo_max_drawdown_pct),
    )

    # --- 7. Async Redis client (algo-engine lines 226-235) ---
    redis_client = None
    try:
        import redis.asyncio as aioredis

        redis_client = aioredis.Redis(
            host=settings.moneymaker_redis_host,
            port=settings.moneymaker_redis_port,
            password=settings.moneymaker_redis_password or None,
            db=0,
            decode_responses=True,
        )
        await redis_client.ping()
        logger.info("Redis connected for portfolio persistence (async)")
        _rc = redis_client
        assert _rc is not None
        health.register_check(
            "redis",
            lambda: _rc.connection_pool.get_encoding(),
        )
    except Exception as e:
        logger.warning("Redis unavailable for portfolio", error=str(e))
        redis_client = None

    # Inject Redis into spiral protection for state persistence (F-S2)
    if redis_client is not None:
        spiral_protection._redis = redis_client
        await spiral_protection.sync_from_redis()

    # --- 8. Feature pipeline (algo-engine lines 238-244) ---
    feature_pipeline = FeaturePipeline(
        rsi_period=settings.algo_default_rsi_period,
        ema_fast_period=settings.algo_default_ema_fast,
        ema_slow_period=settings.algo_default_ema_slow,
        bb_period=settings.algo_default_bb_period,
        atr_period=settings.algo_default_atr_period,
    )
    logger.info("Feature pipeline initialized")

    # --- 9. Regime classifier — single rule-based (algo-engine line 248) ---
    regime_classifier = RegimeClassifier()
    logger.info("Regime classifier initialized")

    # --- 10. Strategy router — algo-specific with breakout ---
    router = build_algo_router()
    logger.info(
        "Strategy router initialized",
        regimes=router.get_registered_regimes(),
    )

    # --- 11. Signal generator (algo-engine line 262) ---
    signal_gen = SignalGenerator()
    logger.info("Signal generator initialized")

    # --- 12. Position sizer (algo-engine lines 268-273) ---
    position_sizer = PositionSizer(
        risk_per_trade_pct=Decimal(str(settings.algo_risk_per_trade_pct)),
        default_equity=Decimal(str(settings.algo_default_equity)),
        min_lots=Decimal("0.01"),
        max_lots=Decimal(str(settings.algo_max_lots)),
    )
    logger.info(
        "Position Sizer initialized",
        risk_pct=str(settings.algo_risk_per_trade_pct),
    )

    # --- 13. Validation components (algo-engine lines 277-302) ---
    correlation_checker = CorrelationChecker(
        max_exposure_per_currency=settings.algo_max_exposure_per_currency,
    )
    session_classifier = SessionClassifier()

    calendar_filter = None
    if settings.algo_calendar_file:
        from algo_engine.features.economic_calendar import EconomicCalendarFilter

        calendar_filter = EconomicCalendarFilter(
            events_file=settings.algo_calendar_file,
            blackout_minutes_before=settings.algo_calendar_blackout_before_min,
            blackout_minutes_after=settings.algo_calendar_blackout_after_min,
        )
        logger.info("Economic calendar loaded", file=settings.algo_calendar_file)

    validator = SignalValidator(
        max_open_positions=settings.algo_max_open_positions,
        max_drawdown_pct=Decimal(str(settings.algo_max_drawdown_pct)),
        max_daily_loss_pct=Decimal(str(settings.algo_max_daily_loss_pct)),
        min_confidence=Decimal(str(settings.algo_confidence_threshold)),
        correlation_checker=correlation_checker,
        session_classifier=session_classifier,
        calendar_filter=calendar_filter,
    )
    logger.info("Signal validator initialized (11 checks)")

    # --- 14. Rate limiter (algo-engine line 306) ---
    rate_limiter = SignalRateLimiter(max_per_hour=settings.algo_max_signals_per_hour)
    logger.info(
        "Rate limiter initialized",
        max_per_hour=settings.algo_max_signals_per_hour,
    )

    # --- 15. Portfolio manager (algo-engine lines 310-312) ---
    portfolio_manager = PortfolioStateManager(redis_client=redis_client)
    await portfolio_manager.sync_from_redis()
    logger.info("Portfolio state manager initialized")

    # --- 16. MTF analyzer (algo-engine lines 315-316) ---
    primary_tf = settings.algo_primary_timeframe
    mtf_analyzer = MultiTimeframeAnalyzer(primary_tf=primary_tf)
    logger.info("Multi-Timeframe Analyzer initialized", primary=primary_tf)

    # --- 17. Data quality, bar buffer, attribution (algo-engine lines 320-329) ---
    data_quality = DataQualityChecker()
    logger.info("Data Quality Checker initialized")

    bar_buffer = BarBuffer(window_size=250, min_bars=50)
    logger.info("Bar buffer initialized", window_size=250, min_bars=50)

    attribution = StrategyAttribution()
    logger.info("Strategy Attribution initialized")

    # --- 18. Alert dispatcher with optional Telegram (algo-engine lines 332-340) ---
    alert_dispatcher = AlertDispatcher()
    if settings.algo_telegram_bot_token and settings.algo_telegram_chat_id:
        alert_dispatcher.add_channel(
            TelegramChannel(
                bot_token=settings.algo_telegram_bot_token,
                chat_id=settings.algo_telegram_chat_id,
            )
        )
        logger.info("Telegram alerting configured")

    # --- 19. ZMQ subscriber (algo-engine lines 343-356) ---
    zmq_sub = None
    try:
        import zmq
        import zmq.asyncio

        zmq_context = zmq.asyncio.Context()
        zmq_sub = zmq_context.socket(zmq.SUB)
        zmq_sub.setsockopt(zmq.RCVHWM, 1000)
        zmq_sub.connect(settings.algo_zmq_data_feed)
        zmq_sub.setsockopt_string(zmq.SUBSCRIBE, "bar.")
        logger.info("ZMQ subscriber connected", address=settings.algo_zmq_data_feed)
        health.register_check("zmq", lambda: True)
    except ImportError:
        logger.warning("ZMQ unavailable, running in standalone mode")

    # --- 20. gRPC bridge client (algo-engine lines 359-379) ---
    bridge_client: BridgeClient | None = None
    try:
        bridge_client = BridgeClient(settings.algo_mt5_bridge_target)
        await bridge_client.connect()
        if bridge_client.available:
            logger.info(
                "MT5 Bridge client connected",
                target=settings.algo_mt5_bridge_target,
            )
        else:
            logger.warning(
                "MT5 Bridge unavailable, signals will not be dispatched",
                target=settings.algo_mt5_bridge_target,
            )
    except Exception as exc:
        logger.warning(
            "MT5 Bridge client setup failed",
            target=settings.algo_mt5_bridge_target,
            error=str(exc),
        )
        bridge_client = None

    # --- Build AlgoEngine with all components ---
    engine = AlgoEngine(
        feature_pipeline=feature_pipeline,
        regime_classifier=regime_classifier,
        router=router,
        signal_gen=signal_gen,
        position_sizer=position_sizer,
        validator=validator,
        spiral_protection=spiral_protection,
        rate_limiter=rate_limiter,
        data_quality=data_quality,
        session_classifier=session_classifier,
        mtf_analyzer=mtf_analyzer,
        bar_buffer=bar_buffer,
        attribution=attribution,
        portfolio_manager=portfolio_manager,
        kill_switch=kill_switch,
    )

    health.set_ready()
    logger.info("Algo Engine ready — entering main loop")

    # --- Main loop (algo-engine lines 494-1133, ML sections removed) ---
    bar_counter: int = 0
    _loop_iter: int = 0

    while True:
        try:
            _loop_iter += 1

            # 0. Kill switch check first (algo-engine lines 497-501)
            _ks_active, _ks_reason = await kill_switch.is_active()
            if _ks_active:
                if _loop_iter <= 3 or _loop_iter % 100 == 0:
                    logger.warning(
                        "Kill switch ACTIVE — blocking bar processing",
                        reason=_ks_reason,
                        iteration=_loop_iter,
                    )
                await asyncio.sleep(5)
                continue

            if _loop_iter == 1:
                logger.info("Main loop: kill switch check passed, waiting for ZMQ bars")

            # ZMQ receive (algo-engine lines 503-513)
            if zmq_sub is not None:
                raw_message = await zmq_sub.recv_multipart()
                if len(raw_message) < 2:
                    continue
                topic = raw_message[0].decode("utf-8", errors="replace")
                payload = raw_message[1]
            else:
                await asyncio.sleep(1)
                continue

            # Message type filter (algo-engine lines 516-520)
            msg_type = determine_message_type(topic)
            if msg_type != "bar":
                continue

            bar_counter += 1
            loop_start = time.monotonic()

            if bar_counter <= 5 or bar_counter % 10 == 0:
                logger.info(
                    "Bar received",
                    topic=topic,
                    bar_count=bar_counter,
                )

            # Parse bar (algo-engine line 526)
            symbol, timeframe, bar = parse_bar_message(payload)

            # === CORE PIPELINE ===
            trading_signal = await engine.process_bar(symbol, timeframe, bar)

            if trading_signal is None:
                if bar_counter <= 5 or bar_counter % 10 == 0:
                    logger.info(
                        "Bar processed (no signal — warmup or no edge)",
                        symbol=symbol,
                        timeframe=timeframe,
                        bar_count=bar_counter,
                    )
                continue

            # Auto-check kill switch with current metrics (algo-engine lines 956-969)
            _state = portfolio_manager.get_state()
            await kill_switch.auto_check(
                daily_loss_pct=Decimal(str(_state["daily_loss_pct"])),
                max_daily_loss_pct=Decimal(str(settings.algo_max_daily_loss_pct)),
                drawdown_pct=Decimal(str(_state["current_drawdown_pct"])),
                max_drawdown_pct=Decimal(str(settings.algo_max_drawdown_pct)),
            )
            _ks_active, _ks_reason = await kill_switch.is_active()
            if _ks_active:
                await alert_dispatcher.send(
                    AlertLevel.CRITICAL,
                    "Kill Switch Activated",
                    "Kill switch auto-activated. Trading suspended.",
                )
                continue

            # Pipeline latency metric
            elapsed = time.monotonic() - loop_start
            PIPELINE_LATENCY.observe(elapsed)

            logger.info(
                "Signal validated and ready",
                signal_id=trading_signal["signal_id"],
                symbol=symbol,
                direction=trading_signal.get("direction", ""),
                source_tier=trading_signal.get("source_tier", ""),
                pipeline_latency_ms=f"{elapsed * 1000:.1f}",
            )

            # Audit log
            audit.log(
                "signal_generated",
                details={
                    "signal_id": trading_signal["signal_id"],
                    "symbol": symbol,
                    "direction": trading_signal.get("direction", ""),
                    "confidence": str(trading_signal.get("confidence", "")),
                    "source_tier": trading_signal.get("source_tier", ""),
                },
                entity_type="signal",
                entity_id=trading_signal["signal_id"],
            )

            # Dispatch to MT5 Bridge (algo-engine lines 1006-1097)
            if bridge_client is not None and bridge_client.available:
                try:
                    result = await bridge_client.send_signal(trading_signal)
                    status = result.get("status", "UNKNOWN")
                    logger.info(
                        "Signal dispatched to MT5 Bridge",
                        signal_id=trading_signal["signal_id"],
                        status=status,
                        order_id=result.get("order_id", ""),
                    )
                    audit.log(
                        "signal_dispatched",
                        details={
                            "signal_id": trading_signal["signal_id"],
                            "status": status,
                            "order_id": result.get("order_id", ""),
                        },
                        entity_type="signal",
                        entity_id=trading_signal["signal_id"],
                    )
                    if status == "FILLED":
                        portfolio_manager.record_fill(
                            symbol=symbol,
                            lots=Decimal(str(trading_signal.get("suggested_lots", "0"))),
                            direction=trading_signal.get("direction", ""),
                        )
                        await portfolio_manager.persist_to_redis()

                        await alert_dispatcher.send(
                            AlertLevel.INFO,
                            f"Trade Opened: {symbol}",
                            f"Direction: {trading_signal.get('direction', '')}, "
                            f"Lots: {trading_signal.get('suggested_lots', '')}, "
                            f"Source: {trading_signal.get('source_tier', '')}",
                        )
                    elif status == "REJECTED":
                        logger.warning(
                            "Order rejected by bridge",
                            symbol=symbol,
                        )
                except Exception as exc:
                    ERROR_COUNTER.labels(
                        service=settings.algo_service_name,
                        error_type="grpc_dispatch",
                    ).inc()
                    logger.error(
                        "Signal dispatch to MT5 Bridge failed",
                        signal_id=trading_signal["signal_id"],
                        error=str(exc),
                    )
            else:
                logger.warning(
                    "Signal validated but Bridge unavailable",
                    signal_id=trading_signal["signal_id"],
                )

            # Periodic: closed trade polling (algo-engine lines 1100-1116)
            if bar_counter % 10 == 0 and bridge_client is not None and bridge_client.available:
                try:
                    closed_trades = await bridge_client.get_closed_trades()
                    for trade in closed_trades:
                        pnl = Decimal(str(trade.get("profit", "0")))
                        portfolio_manager.record_close(
                            symbol=trade.get("symbol", ""),
                            lots=Decimal(str(trade.get("quantity", "0"))),
                            profit=pnl,
                        )
                        spiral_protection.record_trade_result(is_win=(pnl > Decimal("0")))
                        await portfolio_manager.persist_to_redis()
                except Exception as exc:
                    logger.debug("Closed trade check error: %s", exc)

            # Periodic: drawdown enforcer (algo-engine lines 1118-1126)
            portfolio_state = portfolio_manager.get_state()
            try:
                await drawdown_enforcer.check(
                    current_equity=Decimal(str(portfolio_state.get("equity", "1000"))),
                    peak_equity=Decimal(str(portfolio_state.get("peak_equity", "1000"))),
                )
            except (ValueError, Exception) as exc:
                logger.debug("Drawdown enforcer error: %s", exc)

        except asyncio.CancelledError:
            break
        except Exception as exc:
            ERROR_COUNTER.labels(
                service=settings.algo_service_name,
                error_type="pipeline",
            ).inc()
            logger.error("Pipeline error", error=str(exc))
            await asyncio.sleep(1)

    # --- Graceful shutdown ---
    logger.info("Algo Engine shutting down")
    if zmq_sub is not None:
        zmq_sub.close()
    if bridge_client is not None:
        await bridge_client.close()
    await audit.close()
    SERVICE_UP.labels(service=settings.algo_service_name).set(0)


def main() -> None:
    """Entry point for the algo engine service."""
    setup_logging(service_name="algo-engine")
    settings = AlgoEngineSettings()
    logger.info("Algo Engine starting", settings=settings.safe_dump())

    loop = asyncio.new_event_loop()

    def _shutdown() -> None:
        for task in asyncio.all_tasks(loop):
            task.cancel()

    if sys.platform != "win32":
        loop.add_signal_handler(signal.SIGINT, _shutdown)
        loop.add_signal_handler(signal.SIGTERM, _shutdown)

    try:
        loop.run_until_complete(run_engine(settings))
    except KeyboardInterrupt:
        logger.info("Algo Engine interrupted")
    finally:
        loop.close()


if __name__ == "__main__":
    main()
