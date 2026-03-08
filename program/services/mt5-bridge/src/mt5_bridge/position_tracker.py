"""Tracciatore Posizioni — monitora le posizioni aperte in tempo reale.

Come il "direttore di filiale" che sorveglia tutte le operazioni in corso:
tiene traccia di ogni posizione aperta, sposta le protezioni (trailing stop)
quando conviene, e registra quando un'operazione viene chiusa per il
ciclo di feedback (apprendimento dai risultati).

Responsabilità:
- Tracciamento di tutte le posizioni aperte e il loro stato corrente
- Gestione trailing stop-loss — lo "scudo mobile"
- Rilevamento e registrazione delle chiusure posizioni
- Pubblicazione risultati trade per il ciclo di feedback
"""

from __future__ import annotations

import time
from decimal import Decimal
from typing import Any

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.logging import get_logger
from prometheus_client import Gauge

from mt5_bridge.connector import MT5Connector

logger = get_logger(__name__)

OPEN_POSITIONS = Gauge(
    "moneymaker_mt5_open_positions",
    "Numero di posizioni attualmente aperte",
)
UNREALIZED_PNL = Gauge(
    "moneymaker_mt5_unrealized_pnl",
    "Profitto/perdita non realizzato totale",
)


class PositionTracker:
    """Monitora e gestisce le posizioni di trading aperte — il "direttore di filiale"."""

    def __init__(
        self,
        connector: MT5Connector,
        trailing_stop_enabled: bool = True,
        trailing_stop_pips: Decimal = Decimal("50"),
        trailing_activation_pips: Decimal = Decimal("30"),
    ) -> None:
        self._connector = connector
        self._trailing_stop_enabled = trailing_stop_enabled
        self._trailing_stop_pips = trailing_stop_pips
        self._trailing_activation_pips = trailing_activation_pips
        self._known_positions: dict[int, dict[str, Any]] = {}  # ticket → dati posizione
        self._closed_positions: list[dict[str, Any]] = []

    def update(self) -> list[dict[str, Any]]:
        """Interroga MT5 per le posizioni correnti, rileva cambiamenti,
        restituisce le posizioni chiuse di recente.

        Returns:
            Lista di dizionari posizione chiuse dall'ultimo aggiornamento.
        """
        current_positions = self._connector.get_open_positions()
        current_tickets = {pos["ticket"] for pos in current_positions}

        # Rileva posizioni chiuse — "operazioni completate"
        newly_closed = []
        for ticket, prev_pos in list(self._known_positions.items()):
            if ticket not in current_tickets:
                # Recupera dettagli reali dalla deal history MT5
                try:
                    import MetaTrader5 as mt5
                    from moneymaker_common.decimal_utils import to_decimal

                    deals = mt5.history_deals_get(position=ticket)
                    if deals and len(deals) > 0:
                        close_deal = deals[-1]
                        prev_pos["profit"] = to_decimal(close_deal.profit)
                        prev_pos["price_current"] = to_decimal(close_deal.price)
                        prev_pos["commission"] = to_decimal(close_deal.commission)
                        prev_pos["swap"] = to_decimal(close_deal.swap)
                except Exception as exc:
                    logger.warning("Cannot fetch close details for ticket %d: %s", ticket, exc)
                prev_pos["closed_at"] = int(time.time())
                prev_pos["status"] = "CLOSED"
                newly_closed.append(prev_pos)
                self._closed_positions.append(prev_pos)
                logger.info(
                    "Posizione chiusa",
                    ticket=ticket,
                    symbol=prev_pos["symbol"],
                    profit=str(prev_pos.get("profit", "0")),
                )
                del self._known_positions[ticket]

        # Aggiorna le posizioni conosciute
        for pos in current_positions:
            self._known_positions[pos["ticket"]] = pos

        # Aggiorna trailing stop se abilitato — "sposta lo scudo mobile"
        if self._trailing_stop_enabled:
            self._update_trailing_stops(current_positions)

        # Aggiorna le metriche — i "contatori"
        OPEN_POSITIONS.set(len(current_positions))
        total_pnl = sum(
            (pos.get("profit", ZERO) for pos in current_positions),
            ZERO,
        )
        UNREALIZED_PNL.set(float(total_pnl))

        return newly_closed

    def _update_trailing_stops(self, positions: list[dict[str, Any]]) -> None:
        """Aggiusta i livelli di stop-loss per le posizioni in profitto — lo "scudo mobile"."""
        for pos in positions:
            profit = pos.get("profit", ZERO)
            if profit <= ZERO:
                continue

            ticket = pos["ticket"]
            direction = pos.get("type", "")
            price_open = Decimal(str(pos.get("price_open", "0")))
            price_current = Decimal(str(pos.get("price_current", "0")))
            current_sl = Decimal(str(pos.get("sl", "0")))

            if price_open == ZERO or price_current == ZERO:
                continue

            # Calcola pip size dal numero di cifre decimali del simbolo MT5
            symbol = pos.get("symbol", "")
            pip_size = self._get_pip_size(symbol)

            if direction == "BUY":
                profit_pips = (price_current - price_open) / pip_size
                if profit_pips < self._trailing_activation_pips:
                    continue
                new_sl = price_current - (self._trailing_stop_pips * pip_size)
                if new_sl > current_sl:
                    self._connector.modify_position_sl(ticket, float(new_sl))
            elif direction == "SELL":
                profit_pips = (price_open - price_current) / pip_size
                if profit_pips < self._trailing_activation_pips:
                    continue
                new_sl = price_current + (self._trailing_stop_pips * pip_size)
                if current_sl == ZERO or new_sl < current_sl:
                    self._connector.modify_position_sl(ticket, float(new_sl))

    def _get_pip_size(self, symbol: str) -> Decimal:
        """Determina il pip size interrogando MT5 per le cifre decimali del simbolo.

        Fallback a euristica se le info del simbolo non sono disponibili.
        Per strumenti a 3/5 cifre (es. EURUSD 5 digits), 1 pip = 10 points.
        Per strumenti a 2/4 cifre (es. USDJPY 3 digits), 1 pip = point.
        """
        try:
            info = self._connector.get_symbol_info(symbol)
            if info is not None:
                digits = info["digits"]
                # Standard forex: 5 digits → pip = 0.0001, 3 digits → pip = 0.01
                # Metals/indices may vary
                if digits <= 2:
                    return Decimal("0.01")
                elif digits == 3:
                    return Decimal("0.01")
                elif digits == 4:
                    return Decimal("0.0001")
                else:  # 5 digits (standard for most forex)
                    return Decimal("0.0001")
        except Exception:
            pass

        # Fallback euristica per quando MT5 non è disponibile
        if "JPY" in symbol or "XAU" in symbol or "XAG" in symbol:
            return Decimal("0.01")
        if "BTC" in symbol or "ETH" in symbol:
            return Decimal("0.01")
        return Decimal("0.0001")

    def get_open_positions(self) -> list[dict[str, Any]]:
        """Restituisce le posizioni aperte attualmente tracciate."""
        return list(self._known_positions.values())

    def get_recently_closed(self, since_seconds: float = 3600) -> list[dict[str, Any]]:
        """Restituisce le posizioni chiuse negli ultimi N secondi."""
        cutoff = time.time() - since_seconds
        return [p for p in self._closed_positions if p.get("closed_at", 0) >= cutoff]

    @property
    def position_count(self) -> int:
        return len(self._known_positions)

    def build_trade_result(self, closed_position: dict[str, Any]) -> dict[str, Any]:
        """Costruisce un record risultato per il ciclo di feedback.

        Questi dati vengono scritti nel database e usati dal Laboratorio
        di Addestramento ML per imparare dai risultati delle operazioni.
        """
        return {
            "ticket": closed_position["ticket"],
            "symbol": closed_position["symbol"],
            "direction": closed_position["type"],
            "volume": str(closed_position.get("volume", "0")),
            "price_open": str(closed_position.get("price_open", "0")),
            "price_close": str(closed_position.get("price_current", "0")),
            "stop_loss": str(closed_position.get("sl", "0")),
            "take_profit": str(closed_position.get("tp", "0")),
            "profit": str(closed_position.get("profit", "0")),
            "swap": str(closed_position.get("swap", "0")),
            "commission": str(closed_position.get("commission", "0")),
            "open_time": closed_position.get("time", 0),
            "close_time": closed_position.get("closed_at", 0),
            "magic": closed_position.get("magic", 0),
            "comment": closed_position.get("comment", ""),
        }
