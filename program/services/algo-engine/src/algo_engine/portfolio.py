"""Gestore dello stato del portafoglio per il motore algoritmico.

Funziona come un cruscotto in tempo reale: tiene traccia delle posizioni
aperte e delle metriche di rischio in memoria. I nomi delle chiavi
in ``get_state()`` corrispondono a quelli attesi da ``SignalValidator.validate()``:
``open_position_count``, ``current_drawdown_pct``, ``daily_loss_pct``.

I campi aggiuntivi (exposure, win rate, last trade) forniscono
contesto per le decisioni algoritmiche e il monitoraggio.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.logging import get_logger

logger = get_logger(__name__)


class PortfolioStateManager:
    """Cruscotto del portafoglio — come il contachilometri di un'auto.

    Viene aggiornato dopo ogni esecuzione di segnale (fill) e
    chiusura di posizione. Fornisce il dizionario di stato
    consumato da ``SignalValidator.validate()``.
    """

    def __init__(self, redis_client: Any = None) -> None:
        self._redis = redis_client
        self._open_position_count: int = 0
        self._current_drawdown_pct: Decimal = ZERO
        self._daily_loss_pct: Decimal = ZERO
        self._last_reset_date: str = datetime.datetime.now(datetime.timezone.utc).date().isoformat()

        # Campi aggiuntivi per contesto algoritmico
        self._total_exposure: Decimal = ZERO
        self._unrealized_pnl: Decimal = ZERO
        self._symbols_exposed: set[str] = set()
        self._win_count: int = 0
        self._loss_count: int = 0
        self._last_trade_result: str = ""

        # Dettaglio posizioni per il correlation checker
        self._positions_detail: list[dict[str, str]] = []

        # Equity e margine per il margin check del validatore
        self._equity: Decimal = Decimal("1000")  # Default $1k
        self._used_margin: Decimal = ZERO

    def _check_daily_reset(self) -> None:
        """Resetta metriche giornaliere se il giorno è cambiato."""
        today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
        if today != self._last_reset_date:
            logger.info(
                "Reset giornaliero metriche",
                old_date=self._last_reset_date,
                new_date=today,
            )
            self._daily_loss_pct = ZERO
            self._last_reset_date = today

    def get_state(self) -> dict[str, object]:
        """Restituisce lo stato del portafoglio nel formato atteso dal validatore."""
        self._check_daily_reset()
        return {
            "open_position_count": self._open_position_count,
            "current_drawdown_pct": self._current_drawdown_pct,
            "daily_loss_pct": self._daily_loss_pct,
            "total_exposure": self._total_exposure,
            "unrealized_pnl": self._unrealized_pnl,
            "symbols_exposed": sorted(self._symbols_exposed),
            "win_rate": self.win_rate,
            "last_trade_result": self._last_trade_result,
            "positions_detail": list(self._positions_detail),
            "equity": self._equity,
            "used_margin": self._used_margin,
        }

    def record_fill(
        self, symbol: str = "", lots: Decimal = ZERO, direction: str = ""
    ) -> None:
        """Registra l'apertura di una nuova posizione — come aggiungere un'auto al parcheggio."""
        self._open_position_count += 1
        self._total_exposure += lots
        if symbol:
            self._symbols_exposed.add(symbol)
        if symbol and direction:
            self._positions_detail.append({"symbol": symbol, "direction": direction})

    def record_close(
        self, symbol: str = "", lots: Decimal = ZERO, profit: Decimal = ZERO, direction: str = "",
    ) -> None:
        """Registra la chiusura di una posizione — un'auto esce dal parcheggio."""
        self._open_position_count = max(0, self._open_position_count - 1)
        self._total_exposure = max(ZERO, self._total_exposure - lots)
        if symbol and self._open_position_count == 0:
            self._symbols_exposed.discard(symbol)
        # Rimuovi prima occorrenza dal dettaglio posizioni (match per direction se fornita)
        for i, p in enumerate(self._positions_detail):
            if p.get("symbol") == symbol and (not direction or p.get("direction") == direction):
                self._positions_detail.pop(i)
                break
        self.record_trade_result(profit)

    def record_trade_result(self, profit: Decimal) -> None:
        """Registra l'esito di un trade chiuso (win/loss) per il calcolo del win rate."""
        if profit > ZERO:
            self._win_count += 1
            self._last_trade_result = "win"
        elif profit < ZERO:
            self._loss_count += 1
            self._last_trade_result = "loss"

    def update_drawdown(self, pct: Decimal) -> None:
        """Aggiorna la percentuale di drawdown corrente."""
        self._current_drawdown_pct = pct

    def update_daily_loss(self, pct: Decimal) -> None:
        """Aggiorna la percentuale di perdita giornaliera."""
        self._check_daily_reset()
        self._daily_loss_pct = pct

    def update_unrealized_pnl(self, pnl: Decimal) -> None:
        """Aggiorna il P&L non realizzato complessivo."""
        self._unrealized_pnl = pnl

    def update_equity(self, equity: Decimal) -> None:
        """Aggiorna l'equity corrente."""
        self._equity = equity

    def update_used_margin(self, margin: Decimal) -> None:
        """Aggiorna il margine utilizzato."""
        self._used_margin = margin

    @property
    def open_position_count(self) -> int:
        """Numero attuale di posizioni aperte."""
        return self._open_position_count

    @property
    def win_rate(self) -> Decimal:
        """Tasso di vittoria delle posizioni chiuse (0.50 se nessun trade)."""
        total = self._win_count + self._loss_count
        if total == 0:
            return Decimal("0.50")
        return Decimal(str(self._win_count)) / Decimal(str(total))

    async def sync_from_redis(self) -> None:
        """Recupera la daily loss da Redis all'avvio (persistenza tra riavvii)."""
        if self._redis is None:
            return
        try:
            today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
            key = f"moneymaker:daily_loss:{today}"
            val = await self._redis.get(key)
            if val is not None:
                self._daily_loss_pct = Decimal(val.decode() if isinstance(val, bytes) else str(val))
                logger.info("Daily loss recuperata da Redis", daily_loss=str(self._daily_loss_pct))
        except Exception as e:
            logger.warning("Sync daily loss da Redis fallita", error=str(e))

    async def persist_to_redis(self) -> None:
        """Salva la daily loss corrente in Redis con scadenza a mezzanotte."""
        if self._redis is None:
            return
        try:
            today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
            key = f"moneymaker:daily_loss:{today}"
            await self._redis.set(key, str(self._daily_loss_pct), ex=86400)
        except Exception as e:
            logger.warning("Persist daily loss su Redis fallita", error=str(e))
