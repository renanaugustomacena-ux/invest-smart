"""Client gRPC per inviare segnali di trading validati al MT5 Bridge.

Funziona come un servizio postale: prende il segnale (la lettera),
lo converte nel formato corretto (protobuf = busta standard),
e lo consegna al bridge. Se il destinatario non è raggiungibile,
registra un avviso e prosegue — meglio perdere un segnale che crashare.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from moneymaker_common.grpc_credentials import (
    create_async_client_channel,
    get_tls_config_from_env,
)
from moneymaker_common.logging import get_logger

logger = get_logger(__name__)

# Mappa direzione stringa → valore enum protobuf.
# Come un traduttore: converte le parole interne ("BUY") in codici numerici (1)
# Valori enum da trading_signal.proto:
#   DIRECTION_UNSPECIFIED = 0, BUY = 1, SELL = 2, HOLD = 3
_DIRECTION_MAP: dict[str, int] = {
    "BUY": 1,
    "SELL": 2,
    "HOLD": 3,
}

# Mappa codici di stato della risposta di esecuzione.
# Come decifrare i codici di risposta di una spedizione:
# "consegnato", "in transito", "rifiutato", ecc.
_STATUS_MAP: dict[int, str] = {
    0: "UNSPECIFIED",
    1: "PENDING",
    2: "FILLED",
    3: "PARTIALLY_FILLED",
    4: "REJECTED",
    5: "CANCELLED",
    6: "EXPIRED",
}


def signal_to_proto(signal: dict[str, Any]) -> Any:
    """Converte un segnale interno (dict) in un messaggio protobuf TradingSignal.

    Come mettere una lettera nella busta giusta: prende i dati dal
    dizionario e li organizza nel formato che il bridge sa leggere.

    Args:
        signal: Dizionario prodotto da ``SignalGenerator.generate_signal()``.

    Returns:
        Un messaggio protobuf ``trading_signal_pb2.TradingSignal``.
    """
    from moneymaker_proto import trading_signal_pb2

    raw_dir = signal.get("direction", "HOLD")
    direction_str = raw_dir.value if hasattr(raw_dir, "value") else str(raw_dir)
    direction_enum = _DIRECTION_MAP.get(direction_str, 0)

    # Converte il timestamp da millisecondi a nanosecondi
    ts_ms = signal.get("timestamp_ms", 0)
    ts_ns = int(ts_ms) * 1_000_000

    return trading_signal_pb2.TradingSignal(
        signal_id=str(signal.get("signal_id", "")),
        symbol=str(signal.get("symbol", "")),
        direction=direction_enum,
        confidence=str(signal.get("confidence", "0")),
        suggested_lots=str(signal.get("suggested_lots", "0.01")),
        stop_loss=str(signal.get("stop_loss", "0")),
        take_profit=str(signal.get("take_profit", "0")),
        timestamp=ts_ns,
        model_version=str(signal.get("model_version", "")),
        regime=str(signal.get("regime", "")),
        source_tier=signal.get("source_tier", 0),
        reasoning=str(signal.get("reasoning", "")),
        risk_reward_ratio=str(signal.get("risk_reward_ratio", "0")),
    )


def execution_to_dict(response: Any) -> dict[str, Any]:
    """Converte una risposta protobuf TradeExecution in un dizionario semplice.

    Come aprire il pacco di ritorno e leggere la ricevuta:
    estrae tutti i dettagli dell'esecuzione in formato leggibile.

    Args:
        response: Messaggio ``execution_pb2.TradeExecution``.

    Returns:
        Dizionario con i dettagli dell'esecuzione.
    """
    return {
        "order_id": response.order_id,
        "signal_id": response.signal_id,
        "symbol": response.symbol,
        "executed_price": response.executed_price,
        "quantity": response.quantity,
        "stop_loss": response.stop_loss,
        "take_profit": response.take_profit,
        "status": _STATUS_MAP.get(response.status, "UNKNOWN"),
        "slippage_pips": response.slippage_pips,
        "commission": response.commission,
        "swap": response.swap,
        "executed_at": response.executed_at,
        "rejection_reason": response.rejection_reason,
    }


class BridgeClient:
    """Client gRPC asincrono per il servizio MT5 Bridge — il "postino" dei segnali.

    Non-fatale se il bridge è irraggiungibile: si connette pigramente
    e registra avvisi in caso di errore, senza bloccare il servizio.

    Include retry con backoff esponenziale e circuit breaker per
    evitare di sovraccaricare un bridge degradato.
    """

    # Circuit breaker settings
    _CB_FAILURE_THRESHOLD = 5
    _CB_RECOVERY_TIMEOUT = 30.0  # seconds before trying again

    # Retry settings
    _MAX_RETRIES = 3
    _INITIAL_BACKOFF = 0.25  # seconds
    _MAX_BACKOFF = 4.0  # seconds
    _RPC_TIMEOUT = 10  # seconds per attempt

    def __init__(self, target: str) -> None:
        self._target = target
        self._channel: Any | None = None
        self._stub: Any | None = None
        self._available = False
        self._closed_trades_buffer: list[dict[str, Any]] = []

        # Circuit breaker state
        self._cb_failures = 0
        self._cb_open_since: float = 0.0

    @property
    def available(self) -> bool:
        """Indica se il canale verso il bridge è stato stabilito."""
        return self._available

    def _circuit_open(self) -> bool:
        """Check if circuit breaker is open (blocking calls)."""
        if self._cb_failures < self._CB_FAILURE_THRESHOLD:
            return False
        elapsed = time.monotonic() - self._cb_open_since
        if elapsed >= self._CB_RECOVERY_TIMEOUT:
            # Half-open: allow one attempt through
            return False
        return True

    def _record_success(self) -> None:
        """Reset circuit breaker on success."""
        self._cb_failures = 0

    def _record_failure(self) -> None:
        """Track failure for circuit breaker."""
        self._cb_failures += 1
        if self._cb_failures >= self._CB_FAILURE_THRESHOLD:
            self._cb_open_since = time.monotonic()
            logger.warning(
                "Circuit breaker aperto: troppe chiamate gRPC fallite",
                failures=self._cb_failures,
                recovery_timeout=self._CB_RECOVERY_TIMEOUT,
            )

    async def connect(self) -> None:
        """Apre un canale gRPC verso il MT5 Bridge.

        Non-fatale: se grpcio non è installato o il target è
        irraggiungibile, il client si segna come non disponibile.

        Supporta TLS/mTLS quando MONEYMAKER_TLS_ENABLED=true.
        """
        try:
            from moneymaker_proto import execution_pb2_grpc

            # Ottieni configurazione TLS
            tls_config = get_tls_config_from_env()

            # Crea canale (sicuro o insecure in base alla configurazione)
            self._channel = create_async_client_channel(
                target=self._target,
                tls_enabled=tls_config["enabled"],
                ca_cert=tls_config["ca_cert"],
                client_cert=tls_config["client_cert"],
                client_key=tls_config["client_key"],
            )
            self._stub = execution_pb2_grpc.ExecutionBridgeServiceStub(self._channel)
            self._available = True

            if tls_config["enabled"]:
                logger.info("Bridge client connesso con TLS", target=self._target)
            else:
                logger.info("Bridge client connesso", target=self._target)

        except Exception as exc:
            self._available = False
            logger.warning(
                "Bridge client non disponibile",
                target=self._target,
                error=str(exc),
            )

    async def get_closed_trades(self) -> list[dict[str, Any]]:
        """Recupera i trade chiusi dal bridge via StreamTradeUpdates.

        Svuota il buffer interno e restituisce i trade con status
        FILLED che sono arrivati dall'ultimo polling.
        """
        if not self._available or self._stub is None:
            return []
        trades = list(self._closed_trades_buffer)
        self._closed_trades_buffer.clear()
        return trades

    async def send_signal(self, signal: dict[str, Any]) -> dict[str, Any]:
        """Invia un segnale validato al MT5 Bridge con retry e circuit breaker.

        Args:
            signal: Dizionario segnale da ``SignalGenerator``.

        Returns:
            Dizionario con il risultato dell'esecuzione.

        Raises:
            RuntimeError: Se il client non è connesso o circuit breaker è aperto.
        """
        if not self._available or self._stub is None:
            raise RuntimeError("Bridge client non connesso")

        if self._circuit_open():
            raise RuntimeError(
                f"Circuit breaker aperto ({self._cb_failures} failures), "
                f"riprova tra {self._CB_RECOVERY_TIMEOUT:.0f}s"
            )

        proto_signal = signal_to_proto(signal)
        last_exc: Exception | None = None
        backoff = self._INITIAL_BACKOFF

        for attempt in range(1, self._MAX_RETRIES + 1):
            try:
                start = time.monotonic()
                response = await self._stub.ExecuteTrade(
                    proto_signal,
                    timeout=self._RPC_TIMEOUT,
                )
                elapsed_ms = (time.monotonic() - start) * 1000

                result = execution_to_dict(response)
                self._record_success()
                logger.debug(
                    "Risposta dal bridge",
                    signal_id=signal.get("signal_id"),
                    status=result["status"],
                    elapsed_ms=f"{elapsed_ms:.1f}",
                    attempt=attempt,
                )
                return result

            except Exception as exc:
                last_exc = exc
                self._record_failure()
                if attempt < self._MAX_RETRIES:
                    logger.warning(
                        "gRPC tentativo fallito, retry",
                        signal_id=signal.get("signal_id"),
                        attempt=attempt,
                        max_retries=self._MAX_RETRIES,
                        backoff_s=f"{backoff:.2f}",
                        error=str(exc),
                    )
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, self._MAX_BACKOFF)

        logger.error(
            "gRPC tutti i tentativi esauriti",
            signal_id=signal.get("signal_id"),
            attempts=self._MAX_RETRIES,
            error=str(last_exc),
        )
        raise last_exc  # type: ignore[misc]

    async def close(self) -> None:
        """Chiude il canale gRPC — come riagganciare il telefono."""
        if self._channel is not None:
            await self._channel.close()
            self._available = False
            logger.info("Bridge client chiuso")
