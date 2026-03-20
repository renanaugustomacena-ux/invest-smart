# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Trade Recorder — persiste i trade chiusi nel database per il feedback loop.

Come l'"archivista" della filiale: registra ogni operazione completata
nel grande libro contabile (database) cosicché il Laboratorio ML possa
imparare dai risultati e migliorare le predizioni future.

Responsabilità:
    - Ricevere i dati delle posizioni chiuse da PositionTracker
    - Trasformarli in record TradeRecord
    - Persistere nel database trade_records (hypertable TimescaleDB)
    - Calcolare l'outcome (WIN/LOSS/BREAKEVEN)
    - Pubblicare evento su Redis per i consumer downstream
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import asyncpg
from prometheus_client import Counter, Histogram

from moneymaker_common.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Metriche Prometheus
# ---------------------------------------------------------------------------

TRADES_RECORDED = Counter(
    "moneymaker_mt5_trades_recorded_total",
    "Numero totale di trade registrati nel database",
    labelnames=["symbol", "outcome"],
)
RECORD_LATENCY = Histogram(
    "moneymaker_mt5_trade_record_latency_seconds",
    "Latenza della registrazione trade nel database",
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)


class TradeRecorder:
    """Registra i trade chiusi nel database per il ciclo di feedback ML.

    Ogni trade chiuso viene persistito nella tabella ``trade_records`` con
    tutti i dettagli necessari per l'addestramento del modello ML.

    Args:
        database_url: URL di connessione PostgreSQL (asyncpg).
        redis_client: Client Redis opzionale per pubblicare eventi.
    """

    _INSERT_SQL = """
        INSERT INTO trade_records (
            signal_id, symbol, timeframe, direction, lots,
            entry_price, exit_price, stop_loss, take_profit,
            spread_at_entry, outcome, pnl, pnl_pips,
            regime, session_type, strategy, advisor_mode,
            confidence, maturity_state, model_version,
            opened_at, closed_at, dataset_split
        ) VALUES (
            $1, $2, $3, $4, $5,
            $6, $7, $8, $9,
            $10, $11, $12, $13,
            $14, $15, $16, $17,
            $18, $19, $20,
            $21, $22, $23
        ) RETURNING id
    """

    def __init__(
        self,
        database_url: str,
        redis_client: Any = None,
        breakeven_threshold: Decimal = Decimal("0.50"),
    ) -> None:
        self._database_url = database_url
        self._redis = redis_client
        self._pool: asyncpg.Pool | None = None
        self._connected = False
        self._breakeven_threshold = breakeven_threshold

    async def connect(self) -> None:
        """Inizializza il pool di connessioni al database."""
        if self._pool is not None:
            return

        try:
            self._pool = await asyncpg.create_pool(
                self._database_url,
                min_size=1,
                max_size=5,
                command_timeout=30,
            )
            self._connected = True
            logger.info("trade_recorder_connected", pool_size=5)
        except Exception:
            logger.exception("trade_recorder_connection_failed")
            raise

    async def close(self) -> None:
        """Chiude il pool di connessioni."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            self._connected = False
            logger.info("trade_recorder_closed")

    @property
    def is_connected(self) -> bool:
        """Verifica se il recorder è connesso al database."""
        return self._connected and self._pool is not None

    async def record_closed_trade(
        self,
        trade_result: dict[str, Any],
        market_context: dict[str, Any] | None = None,
    ) -> int | None:
        """Registra un trade chiuso nel database.

        Args:
            trade_result: Dati del trade da PositionTracker.build_trade_result().
            market_context: Contesto di mercato opzionale (regime, session, etc.).

        Returns:
            ID del record inserito, o None in caso di errore.
        """
        if not self.is_connected:
            logger.warning("trade_recorder_not_connected")
            return None

        with RECORD_LATENCY.time():
            try:
                record_id = await self._insert_trade_record(trade_result, market_context)

                # Aggiorna metriche
                outcome = self._determine_outcome(trade_result)
                symbol = trade_result.get("symbol", "UNKNOWN")
                TRADES_RECORDED.labels(symbol=symbol, outcome=outcome).inc()

                # Pubblica evento su Redis se disponibile
                if self._redis:
                    await self._publish_trade_event(record_id, trade_result, outcome)

                logger.info(
                    "trade_recorded",
                    record_id=record_id,
                    ticket=trade_result.get("ticket"),
                    symbol=symbol,
                    outcome=outcome,
                    pnl=trade_result.get("profit"),
                )

                return record_id

            except Exception:
                logger.exception(
                    "trade_record_failed",
                    ticket=trade_result.get("ticket"),
                )
                return None

    async def _insert_trade_record(
        self,
        trade_result: dict[str, Any],
        market_context: dict[str, Any] | None,
    ) -> int:
        """Inserisce il record nel database e ritorna l'ID."""
        ctx = market_context or {}

        # Calcola outcome e PnL in pips
        outcome = self._determine_outcome(trade_result)
        pnl = Decimal(str(trade_result.get("profit", "0")))
        pnl_pips = self._calculate_pnl_pips(trade_result)

        # Genera signal_id dal ticket MT5 se non presente
        signal_id = trade_result.get("signal_id") or f"mt5_{trade_result.get('ticket', 0)}"

        # Converti timestamp Unix in datetime
        open_time = trade_result.get("open_time", 0)
        close_time = trade_result.get("close_time", 0)
        opened_at = (
            datetime.fromtimestamp(open_time, tz=timezone.utc)
            if open_time
            else datetime.now(timezone.utc)
        )
        closed_at = (
            datetime.fromtimestamp(close_time, tz=timezone.utc)
            if close_time
            else datetime.now(timezone.utc)
        )

        # Normalizza direzione
        direction = trade_result.get("direction", "BUY").lower()
        if direction not in ("buy", "sell"):
            direction = "buy"

        async with self._pool.acquire() as conn:
            result = await conn.fetchval(
                self._INSERT_SQL,
                signal_id,  # $1
                trade_result.get("symbol", ""),  # $2
                ctx.get("timeframe", "M5"),  # $3
                direction,  # $4
                Decimal(str(trade_result.get("volume", "0.01"))),  # $5
                Decimal(str(trade_result.get("price_open", "0"))),  # $6
                Decimal(str(trade_result.get("price_close", "0"))),  # $7
                Decimal(str(trade_result.get("stop_loss", "0"))),  # $8
                Decimal(str(trade_result.get("take_profit", "0"))),  # $9
                ctx.get("spread_at_entry"),  # $10
                outcome,  # $11
                pnl,  # $12
                pnl_pips,  # $13
                ctx.get("regime", "unknown"),  # $14
                ctx.get("session_type", "unknown"),  # $15
                ctx.get("strategy", "conservative"),  # $16
                ctx.get("advisor_mode", "conservative"),  # $17
                Decimal(str(ctx.get("confidence", "0.0"))),  # $18
                ctx.get("maturity_state", "doubt"),  # $19
                ctx.get("model_version", ""),  # $20
                opened_at,  # $21
                closed_at,  # $22
                "unassigned",  # $23 - dataset_split
            )
            return result

    def _determine_outcome(self, trade_result: dict[str, Any]) -> str:
        """Determina l'esito del trade basandosi sul profitto."""
        profit_str = str(trade_result.get("profit", "0"))
        try:
            profit = Decimal(profit_str)
        except Exception:
            profit = Decimal("0")

        if profit > self._breakeven_threshold:
            return "win"
        elif profit < -self._breakeven_threshold:
            return "loss"
        else:
            return "breakeven"

    def _calculate_pnl_pips(self, trade_result: dict[str, Any]) -> Decimal | None:
        """Calcola il PnL in pips dalla differenza di prezzo."""
        try:
            price_open = Decimal(str(trade_result.get("price_open", "0")))
            price_close = Decimal(str(trade_result.get("price_close", "0")))

            if price_open == 0:
                return None

            symbol = trade_result.get("symbol", "")
            direction = trade_result.get("direction", "BUY").upper()

            # Determina pip size
            if "JPY" in symbol:
                pip_size = Decimal("0.01")
            elif "XAU" in symbol or "GOLD" in symbol:
                pip_size = Decimal("0.01")
            else:
                pip_size = Decimal("0.0001")

            # Calcola pips in base alla direzione
            if direction == "BUY":
                pips = (price_close - price_open) / pip_size
            else:
                pips = (price_open - price_close) / pip_size

            return pips.quantize(Decimal("0.01"))

        except Exception:
            return None

    async def _publish_trade_event(
        self,
        record_id: int,
        trade_result: dict[str, Any],
        outcome: str,
    ) -> None:
        """Pubblica l'evento di trade chiuso su Redis per i consumer downstream."""
        try:
            event = {
                "type": "trade_closed",
                "record_id": record_id,
                "ticket": trade_result.get("ticket"),
                "symbol": trade_result.get("symbol"),
                "direction": trade_result.get("direction"),
                "profit": str(trade_result.get("profit", "0")),
                "outcome": outcome,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await self._redis.publish(
                "moneymaker:mt5:trade_closed",
                json.dumps(event),
            )
            logger.debug("trade_event_published", record_id=record_id)
        except Exception:
            logger.warning("trade_event_publish_failed", record_id=record_id)

    async def get_recent_trades(
        self,
        limit: int = 100,
        symbol: str | None = None,
    ) -> list[dict[str, Any]]:
        """Recupera i trade recenti dal database.

        Utile per debug e verifiche del feedback loop.
        """
        if not self.is_connected:
            return []

        query = """
            SELECT id, signal_id, symbol, direction, lots,
                   entry_price, exit_price, outcome, pnl, pnl_pips,
                   opened_at, closed_at
            FROM trade_records
            WHERE closed_at IS NOT NULL
        """
        params: list[Any] = []

        if symbol:
            query += " AND symbol = $1"
            params.append(symbol)

        query += f" ORDER BY closed_at DESC LIMIT {limit}"

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Factory e Singleton
# ---------------------------------------------------------------------------

_recorder_instance: TradeRecorder | None = None


async def init_trade_recorder(
    database_url: str,
    redis_client: Any = None,
) -> TradeRecorder:
    """Inizializza e connette il TradeRecorder singleton.

    Args:
        database_url: URL connessione PostgreSQL.
        redis_client: Client Redis opzionale.

    Returns:
        Istanza connessa di TradeRecorder.
    """
    global _recorder_instance

    _recorder_instance = TradeRecorder(
        database_url=database_url,
        redis_client=redis_client,
    )
    await _recorder_instance.connect()

    logger.info(
        "trade_recorder_initialized",
        connected=_recorder_instance.is_connected,
    )

    return _recorder_instance


def get_trade_recorder() -> TradeRecorder | None:
    """Ritorna l'istanza singleton del TradeRecorder, se inizializzata."""
    return _recorder_instance


__all__ = [
    "TradeRecorder",
    "init_trade_recorder",
    "get_trade_recorder",
]
