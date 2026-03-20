# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Punto di ingresso per il servizio MONEYMAKER MT5 Bridge.

Il MT5 Bridge è lo "sportello bancario" — il livello di esecuzione.
Riceve segnali di trading validati dall'Algo Engine via gRPC e li
traduce in chiamate API MetaTrader 5.

Fail-safe per default: in caso di ambiguità o fallimento, non fare nulla.
Come un cassiere prudente che, nel dubbio, non processa l'operazione.

Sequenza di avvio — come "aprire la filiale al mattino":
1. Carica la configurazione dall'ambiente
2. Inizializza il connettore MT5 (connessione al terminale)
3. Crea il Gestore Ordini con i limiti di sicurezza
4. Crea il Tracciatore Posizioni per il monitoraggio
5. Avvia il server gRPC per la ricezione segnali
6. Avvia il server metriche
7. Entra nel ciclo eventi fino al segnale di spegnimento
"""

from __future__ import annotations

import asyncio
import signal

from moneymaker_common.decimal_utils import to_decimal
from moneymaker_common.health import HealthChecker
from moneymaker_common.logging import get_logger, setup_logging
from moneymaker_common.metrics import SERVICE_UP, start_metrics_server
from moneymaker_common.ratelimit import (
    RateLimitConfig,
    create_rate_limiter,
)

from mt5_bridge.config import MT5BridgeSettings
from mt5_bridge.connector import MT5Connector
from mt5_bridge.grpc_server import ExecutionServer, ExecutionServicer
from mt5_bridge.order_manager import OrderManager
from mt5_bridge.position_tracker import PositionTracker
from mt5_bridge.trade_recorder import TradeRecorder

logger = get_logger(__name__)


async def main() -> None:
    setup_logging("mt5_bridge")

    settings = MT5BridgeSettings()
    health = HealthChecker("mt5_bridge")

    logger.info(
        "Avvio MONEYMAKER MT5 Bridge",
        env=settings.moneymaker_env,
        grpc_port=settings.moneymaker_mt5_bridge_grpc_port,
    )

    # --- Metriche — i "contatori" dello sportello ---
    start_metrics_server(settings.moneymaker_mt5_bridge_metrics_port)
    SERVICE_UP.labels(service="mt5_bridge").set(1)

    # --- Connettore MT5 — il "telefono con la banca" ---
    connector = MT5Connector(
        account=settings.mt5_account,
        password=settings.mt5_password,
        server=settings.mt5_server,
        timeout_ms=settings.mt5_timeout_ms,
    )

    # Tentativo di connessione MT5 (non-fatale se non disponibile — es. dev/Docker)
    try:
        connector.connect()
        health.register_check("mt5", lambda: connector.is_connected)
        logger.info("Terminale MT5 connesso")
    except Exception as e:
        logger.warning(
            "Connessione MT5 fallita, in esecuzione in modalità degradata",
            error=str(e),
        )

    # --- Gestore Ordini — il "cassiere" ---
    order_manager = OrderManager(
        connector=connector,
        max_lot_size=to_decimal(settings.max_lot_size),
        max_position_count=settings.max_position_count,
        dedup_window_sec=settings.signal_dedup_window_sec,
        max_spread_points=settings.max_spread_points,
        signal_max_age_sec=settings.signal_max_age_sec,
        max_daily_loss_pct=to_decimal(settings.max_daily_loss_pct),
        max_drawdown_pct=to_decimal(settings.max_drawdown_pct),
    )
    logger.info(
        "Gestore ordini inizializzato",
        max_lot=settings.max_lot_size,
        max_positions=settings.max_position_count,
    )

    # --- Tracciatore Posizioni — il "guardiano delle operazioni" ---
    tracker = PositionTracker(
        connector=connector,
        trailing_stop_enabled=settings.trailing_stop_enabled,
        trailing_stop_pips=to_decimal(settings.trailing_stop_pips),
        trailing_activation_pips=to_decimal(settings.trailing_activation_pips),
    )
    logger.info(
        "Tracciatore posizioni inizializzato",
        trailing_enabled=settings.trailing_stop_enabled,
        trailing_pips=settings.trailing_stop_pips,
    )

    # --- Trade Recorder — l'"archivista" per il feedback loop ---
    trade_recorder: TradeRecorder | None = None
    try:
        database_url = (
            f"postgresql://{settings.moneymaker_db_user}:{settings.moneymaker_db_password}"
            f"@{settings.moneymaker_db_host}:{settings.moneymaker_db_port}/{settings.moneymaker_db_name}"
        )
        trade_recorder = TradeRecorder(database_url=database_url)
        await trade_recorder.connect()
        logger.info("Trade recorder inizializzato per feedback loop")
    except Exception as e:
        logger.warning(
            "Trade recorder non disponibile, feedback loop disabilitato",
            error=str(e),
        )

    # --- Rate Limiter — il "vigile urbano" che limita le richieste ---
    rate_limiter = None
    if settings.rate_limit_enabled:
        rate_config = RateLimitConfig(
            requests_per_window=settings.rate_limit_requests_per_minute,
            window_seconds=60,
            burst_size=settings.rate_limit_burst_size,
            key_prefix="ratelimit:mt5bridge",
        )
        rate_limiter = await create_rate_limiter(
            redis_url=settings.redis_url,
            config=rate_config,
            service_name="mt5_bridge",
        )
        logger.info(
            "Rate limiter inizializzato",
            requests_per_minute=settings.rate_limit_requests_per_minute,
            burst_size=settings.rate_limit_burst_size,
        )

    # --- Server gRPC — lo "sportello" aperto ai clienti ---
    servicer = ExecutionServicer(order_manager)
    grpc_server = ExecutionServer(
        servicer=servicer,
        port=settings.moneymaker_mt5_bridge_grpc_port,
        rate_limiter=rate_limiter,
    )
    await grpc_server.start()

    # --- Pronto — "sportello aperto al pubblico" ---
    health.set_ready()
    logger.info("MT5 Bridge pronto")

    # --- Gestione spegnimento ---
    shutdown_event = asyncio.Event()

    def handle_signal(sig: int) -> None:
        logger.info("Segnale di spegnimento ricevuto", signal=sig)
        shutdown_event.set()

    loop = asyncio.get_event_loop()
    import sys

    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, handle_signal, sig)
    else:
        signal.signal(signal.SIGINT, lambda s, f: handle_signal(s))
        signal.signal(signal.SIGTERM, lambda s, f: handle_signal(s))

    async def position_monitor_loop() -> None:
        """Ciclo di monitoraggio posizioni: trailing stop e rilevamento chiusure."""
        while not shutdown_event.is_set():
            if not connector.is_connected:
                logger.warning("MT5 disconnesso, tentativo riconnessione...")
                connector.reconnect()
                await asyncio.sleep(10)
                continue
            if connector.is_connected:
                # Invia heartbeat al Guardian EA dentro MT5
                connector.send_heartbeat()
                try:
                    closed = tracker.update()
                    for pos in closed:
                        logger.info(
                            "Trade chiuso rilevato",
                            ticket=pos.get("ticket"),
                            symbol=pos.get("symbol"),
                            profit=str(pos.get("profit", "0")),
                        )
                        # Registra il trade chiuso per il feedback loop
                        if trade_recorder and trade_recorder.is_connected:
                            trade_result = tracker.build_trade_result(pos)
                            record_id = await trade_recorder.record_closed_trade(trade_result)
                            if record_id:
                                logger.info(
                                    "Trade registrato per feedback loop",
                                    record_id=record_id,
                                    ticket=pos.get("ticket"),
                                )
                except Exception as e:
                    logger.warning("Errore nel monitor posizioni", error=str(e))
            await asyncio.sleep(5)

    monitor_task = asyncio.create_task(position_monitor_loop())

    await shutdown_event.wait()

    monitor_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass

    # --- Spegnimento graduale — "chiusura serale della filiale" ---
    logger.info("Spegnimento - cancellazione ordini pendenti e controllo posizioni...")

    # Cancella tutti gli ordini pendenti MONEYMAKER per evitare fill non gestiti
    if connector.is_connected:
        try:
            pending = connector.get_pending_orders()
            if pending:
                logger.warning(
                    "Cancellazione ordini pendenti allo spegnimento",
                    count=len(pending),
                )
                for order in pending:
                    cancelled = connector.cancel_order(order["ticket"])
                    if cancelled:
                        logger.info(
                            "Ordine pendente cancellato",
                            ticket=order["ticket"],
                            symbol=order["symbol"],
                        )
                    else:
                        logger.error(
                            "Impossibile cancellare ordine pendente",
                            ticket=order["ticket"],
                        )
        except Exception as e:
            logger.warning("Errore durante cancellazione ordini pendenti", error=str(e))

    # Rapporto stato finale delle posizioni
    if connector.is_connected:
        try:
            positions = connector.get_open_positions()
            logger.info("Posizioni aperte allo spegnimento", count=len(positions))
            for pos in positions:
                logger.info(
                    "Posizione aperta",
                    symbol=pos["symbol"],
                    type=pos["type"],
                    volume=str(pos["volume"]),
                    profit=str(pos["profit"]),
                )
        except Exception as e:
            logger.warning("Impossibile recuperare posizioni allo spegnimento", error=str(e))

    # Ferma il server gRPC
    await grpc_server.stop()

    # Chiudi il trade recorder
    if trade_recorder:
        await trade_recorder.close()

    # Disconnetti da MT5
    connector.disconnect()

    SERVICE_UP.labels(service="mt5_bridge").set(0)
    logger.info("Spegnimento MT5 Bridge completato")


if __name__ == "__main__":
    asyncio.run(main())
