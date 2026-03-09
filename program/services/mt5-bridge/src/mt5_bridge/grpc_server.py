"""Server gRPC per il servizio di esecuzione MT5 Bridge.

Come la "reception dello sportello bancario": riceve i clienti (segnali)
dalla sala d'attesa (Algo Engine via gRPC), li smista al cassiere
(OrderManager) per l'esecuzione, e restituisce la ricevuta (risultato).

Implementa l'interfaccia ExecutionBridgeService definita in execution.proto.

Utilizzo:
    server = ExecutionServer(order_manager, port=50055)
    await server.start()
    await server.wait_for_termination()
"""

from __future__ import annotations

import time
from typing import Any, Optional, Union

from moneymaker_common.exceptions import BrokerError, SignalRejectedError
from moneymaker_common.grpc_credentials import get_tls_config_from_env, load_server_credentials
from moneymaker_common.logging import get_logger
from moneymaker_common.metrics import EXECUTION_LATENCY, TRADES_EXECUTED
from moneymaker_common.ratelimit import (
    InMemoryRateLimiter,
    RateLimitConfig,
    RateLimitExceededError,
    RateLimitPresets,
    RedisRateLimiter,
)

from mt5_bridge.order_manager import OrderManager

logger = get_logger(__name__)

# Tipo rate limiter (Redis o In-Memory)
RateLimiterType = Optional[Union[RedisRateLimiter, InMemoryRateLimiter]]


class ExecutionServicer:
    """Gestisce le chiamate RPC ExecutionBridgeService — la "reception".

    Traduce i dizionari segnale (deserializzati da proto) in chiamate
    all'OrderManager e restituisce i risultati dell'esecuzione.
    """

    def __init__(self, order_manager: OrderManager) -> None:
        self._order_manager = order_manager

    async def execute_trade(self, signal: dict[str, Any]) -> dict[str, Any]:
        """Esegue un segnale di trading ricevuto via gRPC — "serve il cliente".

        Args:
            signal: Dizionario con campi segnale (signal_id, symbol,
                    direction, entry_price, stop_loss, take_profit,
                    confidence, ecc.)

        Returns:
            Dizionario risultato esecuzione con order_id, status,
            executed_price, slippage, ecc.
        """
        signal_id = signal.get("signal_id", "unknown")
        symbol = signal.get("symbol", "")
        direction = signal.get("direction", "")

        logger.info(
            "Richiesta esecuzione trade ricevuta",
            signal_id=signal_id,
            symbol=symbol,
            direction=direction,
        )

        start_time = time.monotonic()

        try:
            # Aggiungi lotti suggeriti se non presenti (default 0.01 per sicurezza)
            if "suggested_lots" not in signal:
                signal["suggested_lots"] = "0.01"

            import asyncio
            result = await asyncio.get_event_loop().run_in_executor(
                None, self._order_manager.execute_signal, signal,
            )

            elapsed = time.monotonic() - start_time
            EXECUTION_LATENCY.observe(elapsed)

            status = result.get("status", "UNKNOWN")
            TRADES_EXECUTED.labels(
                symbol=symbol,
                direction=direction,
                status=status,
            ).inc()

            logger.info(
                "Trade eseguito",
                signal_id=signal_id,
                status=status,
                order_id=result.get("order_id", ""),
                latency_ms=f"{elapsed * 1000:.1f}",
            )

            return result

        except SignalRejectedError as e:
            logger.warning(
                "Segnale rifiutato dal livello di esecuzione",
                signal_id=signal_id,
                reason=str(e),
            )
            TRADES_EXECUTED.labels(
                symbol=symbol,
                direction=direction,
                status="REJECTED",
            ).inc()
            return {
                "status": "REJECTED",
                "order_id": "",
                "signal_id": signal_id,
                "rejection_reason": str(e),
            }

        except BrokerError as e:
            logger.error(
                "Errore broker durante l'esecuzione",
                signal_id=signal_id,
                error=str(e),
            )
            TRADES_EXECUTED.labels(
                symbol=symbol,
                direction=direction,
                status="ERROR",
            ).inc()
            return {
                "status": "ERROR",
                "order_id": "",
                "signal_id": signal_id,
                "rejection_reason": f"Errore broker: {e}",
            }


# Mappatura enum direzione proto → stringa — la "tabella di conversione"
_PROTO_DIRECTION_TO_STR: dict[int, str] = {
    0: "HOLD",  # DIRECTION_UNSPECIFIED
    1: "BUY",   # DIRECTION_BUY
    2: "SELL",  # DIRECTION_SELL
    3: "HOLD",  # DIRECTION_HOLD
}

# Mappatura stato esecuzione stringa → valore enum proto
_STATUS_STR_TO_PROTO: dict[str, int] = {
    "PENDING": 1,
    "FILLED": 2,
    "PARTIALLY_FILLED": 3,
    "REJECTED": 4,
    "CANCELLED": 5,
    "EXPIRED": 6,
    "ERROR": 7,     # STATUS_ERROR, distinct from REJECTED (4)
    "UNKNOWN": 0,
}


class GRPCExecutionServicer:
    """Servicer gRPC che fa da ponte tra messaggi proto e l'ExecutionServicer — il "traduttore".

    Implementa l'interfaccia ``ExecutionBridgeService`` definita in
    ``execution.proto`` traducendo tra protobuf e l'ExecutionServicer
    basato su dizionari.

    Integra rate limiting per proteggere da abusi e DoS.
    """

    def __init__(
        self,
        servicer: ExecutionServicer,
        rate_limiter: RateLimiterType = None,
    ) -> None:
        self._servicer = servicer
        self._rate_limiter = rate_limiter

    def _extract_client_id(self, context: Any) -> str:
        """Estrae l'identificatore del client dal contesto gRPC."""
        try:
            peer = context.peer()
            if peer:
                # Formato: ipv4:IP:PORT o ipv6:[IP]:PORT
                if peer.startswith("ipv4:"):
                    return peer.split(":")[1]
                elif peer.startswith("ipv6:"):
                    return peer.split("[")[1].split("]")[0]
        except Exception:
            pass
        return "unknown"

    async def ExecuteTrade(self, request: Any, context: Any) -> Any:
        """Gestisce una chiamata RPC ExecuteTrade — "traduce e smista".

        Converte il proto TradingSignal in dizionario, delega
        all'ExecutionServicer, e riconverte il risultato in proto.

        Include rate limiting per proteggere da abusi.
        """
        import grpc
        from moneymaker_proto import execution_pb2

        # --- Rate Limiting Check ---
        if self._rate_limiter is not None:
            client_id = self._extract_client_id(context)
            try:
                await self._rate_limiter.check_or_raise(client_id, "ExecuteTrade")
            except RateLimitExceededError as e:
                logger.warning(
                    "Rate limit superato per ExecuteTrade",
                    client_id=client_id,
                    retry_after=e.retry_after,
                )
                context.abort(
                    grpc.StatusCode.RESOURCE_EXHAUSTED,
                    f"Rate limit exceeded. Retry after {e.retry_after:.1f}s",
                )

        # Proto TradingSignal → dizionario
        signal: dict[str, Any] = {
            "signal_id": request.signal_id,
            "symbol": request.symbol,
            "direction": _PROTO_DIRECTION_TO_STR.get(request.direction, "HOLD"),
            "confidence": request.confidence,
            "suggested_lots": request.suggested_lots or "0.01",
            "stop_loss": request.stop_loss,
            "take_profit": request.take_profit,
            "reasoning": request.reasoning,
            "regime": request.regime,
            "model_version": request.model_version,
            "risk_reward_ratio": request.risk_reward_ratio,
        }

        result = await self._servicer.execute_trade(signal)

        # Dizionario → proto TradeExecution
        status_str = result.get("status", "UNKNOWN")
        return execution_pb2.TradeExecution(
            order_id=str(result.get("order_id", "")),
            signal_id=str(result.get("signal_id", signal["signal_id"])),
            symbol=signal["symbol"],
            executed_price=str(result.get("executed_price", "0")),
            quantity=str(result.get("volume", "0")),
            stop_loss=signal["stop_loss"],
            take_profit=signal["take_profit"],
            status=_STATUS_STR_TO_PROTO.get(status_str, 0),
            slippage_pips=str(result.get("slippage", "0")),
            rejection_reason=str(result.get("rejection_reason", "")),
        )

    async def StreamTradeUpdates(self, request: Any, context: Any) -> None:
        """Placeholder per streaming aggiornamenti trade."""
        pass

    async def CheckHealth(self, request: Any, context: Any) -> Any:
        """Restituisce una risposta di controllo salute basata su stato reale del connettore."""
        from moneymaker_proto import health_pb2

        try:
            connected = self._order_manager._connector.is_connected
        except Exception:
            connected = False

        if connected:
            return health_pb2.HealthCheckResponse(
                status=health_pb2.HealthCheckResponse.HEALTHY,
                message="MT5 Bridge operativo — connesso al terminale",
            )
        return health_pb2.HealthCheckResponse(
            status=health_pb2.HealthCheckResponse.UNHEALTHY,
            message="MT5 Bridge disconnesso dal terminale",
        )


class ExecutionServer:
    """Gestisce il ciclo di vita del server gRPC per il MT5 Bridge — il "portiere".

    Gestisce creazione, avvio e spegnimento graduale del server.
    Se grpcio non è disponibile, salta l'avvio del server gRPC.

    Supporta rate limiting opzionale per protezione da DoS.
    """

    def __init__(
        self,
        servicer: ExecutionServicer,
        port: int = 50055,
        rate_limiter: RateLimiterType = None,
    ) -> None:
        self._servicer = servicer
        self._port = port
        self._rate_limiter = rate_limiter
        self._server = None

    async def start(self) -> None:
        """Avvia il server gRPC — "apre lo sportello".

        Supporta mTLS quando MONEYMAKER_TLS_ENABLED=true e i certificati sono configurati.
        In caso contrario, avvia in modalità insecure per retrocompatibilità.
        """
        try:
            import grpc
            from moneymaker_proto import execution_pb2_grpc

            self._server = grpc.aio.server()
            grpc_servicer = GRPCExecutionServicer(
                self._servicer,
                rate_limiter=self._rate_limiter,
            )
            execution_pb2_grpc.add_ExecutionBridgeServiceServicer_to_server(
                grpc_servicer, self._server
            )

            # Verifica se TLS è abilitato
            tls_config = get_tls_config_from_env()

            if (
                tls_config["enabled"]
                and tls_config["server_cert"]
                and tls_config["server_key"]
            ):
                try:
                    credentials = load_server_credentials(
                        ca_cert_path=tls_config["ca_cert"],
                        server_cert_path=tls_config["server_cert"],
                        server_key_path=tls_config["server_key"],
                        require_client_cert=True,  # mTLS: richiede cert client
                    )
                    self._server.add_secure_port(f"[::]:{self._port}", credentials)
                    await self._server.start()
                    logger.info(
                        "Server gRPC avviato con mTLS",
                        port=self._port,
                        server_cert=tls_config["server_cert"],
                    )
                except FileNotFoundError as e:
                    logger.warning(
                        "Certificati TLS non trovati, avvio in modalità insecure",
                        error=str(e),
                    )
                    self._server.add_insecure_port(f"[::]:{self._port}")
                    await self._server.start()
                    logger.warning(
                        "Server gRPC avviato SENZA TLS (certificati mancanti)",
                        port=self._port,
                    )
            else:
                self._server.add_insecure_port(f"[::]:{self._port}")
                await self._server.start()
                logger.info(
                    "Server gRPC avviato (TLS disabilitato)",
                    port=self._port,
                )

        except ImportError:
            logger.warning(
                "grpcio non disponibile, server gRPC non avviato. "
                "I segnali devono essere consegnati tramite meccanismo alternativo."
            )

    async def stop(self) -> None:
        """Spegne gradualmente il server gRPC — "chiude lo sportello"."""
        if self._server is not None:
            await self._server.stop(grace=5)
            logger.info("Server gRPC fermato")

    async def wait_for_termination(self) -> None:
        """Blocca fino alla terminazione del server."""
        if self._server is not None:
            await self._server.wait_for_termination()
