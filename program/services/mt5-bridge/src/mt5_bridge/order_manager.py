"""Gestore Ordini — traduce i segnali di trading in ordini MT5.

Come il "cassiere dello sportello bancario": riceve l'ordine di pagamento
(segnale), verifica che tutto sia in regola (validazione), calcola
l'importo corretto (lotti), e lo processa allo sportello (MT5 API).

Responsabilità:
- Calcolo lotti appropriati dalle raccomandazioni del segnale
- Impostazione livelli stop-loss e take-profit
- Invio ordini a mercato o limit tramite API MT5
- Validazione ordini prima dell'invio (limiti lotti, verifica margine)
"""

from __future__ import annotations

import time
from decimal import Decimal
from typing import Any

from moneymaker_common.decimal_utils import ZERO, to_decimal
from moneymaker_common.exceptions import BrokerError, SignalRejectedError
from moneymaker_common.logging import get_logger
from prometheus_client import Counter, Histogram

from mt5_bridge.connector import MT5Connector

logger = get_logger(__name__)

ORDERS_SUBMITTED = Counter(
    "moneymaker_mt5_orders_submitted_total",
    "Ordini totali inviati a MT5",
    ["symbol", "direction"],
)
ORDERS_FILLED = Counter(
    "moneymaker_mt5_orders_filled_total",
    "Ordini totali eseguiti da MT5",
    ["symbol", "direction"],
)
ORDER_LATENCY = Histogram(
    "moneymaker_mt5_order_execution_seconds",
    "Latenza esecuzione ordine in secondi",
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)


class OrderManager:
    """Traduce i segnali di trading validati in ordini MT5 — il "cassiere"."""

    def __init__(
        self,
        connector: MT5Connector,
        max_lot_size: Decimal,
        max_position_count: int,
        dedup_window_sec: int = 300,
        max_spread_points: int = 30,
        signal_max_age_sec: int = 30,
        max_daily_loss_pct: Decimal = Decimal("2.0"),
        max_drawdown_pct: Decimal = Decimal("10.0"),
    ) -> None:
        self._connector = connector
        self._max_lot_size = max_lot_size
        self._max_position_count = max_position_count
        self._dedup_window_sec = dedup_window_sec
        self._max_spread_points = max_spread_points
        self._signal_max_age_sec = signal_max_age_sec
        self._max_daily_loss_pct = max_daily_loss_pct
        self._max_drawdown_pct = max_drawdown_pct
        self._recent_signals: dict[str, float] = {}  # signal_id → timestamp
        import threading
        self._execution_lock = threading.Lock()

    def execute_signal(self, signal: dict[str, Any]) -> dict[str, Any]:
        """Esegue un segnale di trading tramite MT5 — "processa l'operazione".

        Args:
            signal: Dizionario con chiavi: signal_id, symbol, direction, suggested_lots,
                    stop_loss, take_profit, confidence

        Returns:
            Dizionario risultato con order_id, executed_price, slippage, status

        Raises:
            SignalRejectedError: Se il segnale non supera la validazione pre-esecuzione
            BrokerError: Se l'invio dell'ordine MT5 fallisce
        """
        with self._execution_lock:
            return self._execute_signal_locked(signal)

    def _execute_signal_locked(self, signal: dict[str, Any]) -> dict[str, Any]:
        """Corpo effettivo di execute_signal, protetto dal lock."""
        signal_id = signal["signal_id"]

        # Controllo de-duplicazione — "questo ordine è già stato processato?"
        if signal_id in self._recent_signals:
            raise SignalRejectedError(signal_id, "segnale duplicato")

        # Validazione pre-esecuzione — "verifica documenti"
        self._validate_signal(signal)

        # Registra segnale PRIMA dell'esecuzione per prevenire duplicati concorrenti
        self._recent_signals[signal_id] = time.time()

        symbol = signal["symbol"]
        direction = signal["direction"]
        lots = self._clamp_lot_size(to_decimal(signal["suggested_lots"]), symbol)
        stop_loss = to_decimal(signal["stop_loss"])
        take_profit = to_decimal(signal["take_profit"])

        logger.info(
            "Esecuzione segnale",
            signal_id=signal_id,
            symbol=symbol,
            direction=direction,
            lots=str(lots),
        )

        ORDERS_SUBMITTED.labels(symbol=symbol, direction=direction).inc()

        start_time = time.monotonic()

        order_type = signal.get("order_type", "MARKET")

        try:
            if order_type == "LIMIT":
                limit_price = to_decimal(signal.get("limit_price", signal.get("entry_price", "0")))
                result = self._submit_limit_order(
                    symbol=symbol,
                    direction=direction,
                    lots=lots,
                    price=limit_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    comment=f"MONEYMAKER:{signal_id[:8]}",
                )
            else:
                result = self._submit_order(
                    symbol=symbol,
                    direction=direction,
                    lots=lots,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    comment=f"MONEYMAKER:{signal_id[:8]}",
                )
        finally:
            elapsed = time.monotonic() - start_time
            ORDER_LATENCY.observe(elapsed)

        self._cleanup_old_signals()

        if result["status"] == "FILLED":
            ORDERS_FILLED.labels(symbol=symbol, direction=direction).inc()

        return result

    def _validate_signal(self, signal: dict[str, Any]) -> None:
        """Valida il segnale prima dell'esecuzione — il "controllo documenti"."""
        # Controlla l'età del segnale — rifiuta segnali troppo vecchi
        timestamp_ms = signal.get("timestamp_ms")
        if timestamp_ms is not None and self._signal_max_age_sec > 0:
            age_sec = time.time() - (int(timestamp_ms) / 1000)
            if age_sec > self._signal_max_age_sec:
                raise SignalRejectedError(
                    signal["signal_id"],
                    f"segnale troppo vecchio: {age_sec:.1f}s > {self._signal_max_age_sec}s",
                )

        # Controlla la direzione
        direction = signal.get("direction", "")
        if direction not in ("BUY", "SELL"):
            raise SignalRejectedError(
                signal["signal_id"], f"direzione non valida: {direction}"
            )

        # Controlla la dimensione dei lotti
        lots = to_decimal(signal.get("suggested_lots", "0"))
        if lots <= ZERO:
            raise SignalRejectedError(signal["signal_id"], "i lotti devono essere positivi")

        # Controlla che esista lo stop loss
        sl = to_decimal(signal.get("stop_loss", "0"))
        if sl <= ZERO:
            raise SignalRejectedError(signal["signal_id"], "lo stop loss è obbligatorio")

        # Controlla la coerenza direzionale SL/TP
        tp = to_decimal(signal.get("take_profit", "0"))
        direction = signal.get("direction", "")
        entry_price = to_decimal(signal.get("entry_price", "0"))
        if entry_price > ZERO and direction in ("BUY", "SELL"):
            if direction == "BUY":
                if sl >= entry_price:
                    raise SignalRejectedError(
                        signal["signal_id"],
                        f"BUY: stop loss ({sl}) deve essere sotto entry ({entry_price})",
                    )
                if tp > ZERO and tp <= entry_price:
                    raise SignalRejectedError(
                        signal["signal_id"],
                        f"BUY: take profit ({tp}) deve essere sopra entry ({entry_price})",
                    )
            else:  # SELL
                if sl <= entry_price:
                    raise SignalRejectedError(
                        signal["signal_id"],
                        f"SELL: stop loss ({sl}) deve essere sopra entry ({entry_price})",
                    )
                if tp > ZERO and tp >= entry_price:
                    raise SignalRejectedError(
                        signal["signal_id"],
                        f"SELL: take profit ({tp}) deve essere sotto entry ({entry_price})",
                    )

        # Controlla il limite di posizioni — "posti disponibili allo sportello"
        open_positions = self._connector.get_open_positions()
        if len(open_positions) >= self._max_position_count:
            raise SignalRejectedError(
                signal["signal_id"],
                f"limite posizioni ({self._max_position_count}) raggiunto",
            )

        # Controlla lo spread — protezione contro spread eccessivi
        symbol = signal.get("symbol", "")
        symbol_info = self._connector.get_symbol_info(symbol)
        if symbol_info is not None:
            current_spread = symbol_info["spread"]
            if current_spread > self._max_spread_points:
                raise SignalRejectedError(
                    signal["signal_id"],
                    f"spread troppo alto: {current_spread} > {self._max_spread_points} punti",
                )

        # Controlla il margine disponibile — "verifica fondi sufficienti"
        direction = signal.get("direction", "")
        lots_val = self._clamp_lot_size(to_decimal(signal.get("suggested_lots", "0")), symbol)
        if symbol and direction in ("BUY", "SELL") and lots_val > ZERO:
            try:
                self._connector.check_margin(symbol, direction, float(lots_val))
            except BrokerError as e:
                raise SignalRejectedError(signal["signal_id"], str(e))

        # Controlla limiti di perdita giornaliera e drawdown dal conto MT5
        try:
            account = self._connector.get_account_info()
            balance = account["balance"]
            equity = account["equity"]

            if balance > ZERO:
                # Drawdown = (balance - equity) / balance * 100
                drawdown_pct = ((balance - equity) / balance) * Decimal("100")
                if drawdown_pct >= self._max_drawdown_pct:
                    raise SignalRejectedError(
                        signal["signal_id"],
                        f"drawdown {drawdown_pct:.2f}% >= limite {self._max_drawdown_pct}%",
                    )

                # Perdita giornaliera approssimata dal P&L floating
                daily_loss_pct = (account["profit"] / balance) * Decimal("-100") if account["profit"] < ZERO else ZERO
                if daily_loss_pct >= self._max_daily_loss_pct:
                    raise SignalRejectedError(
                        signal["signal_id"],
                        f"perdita giornaliera {daily_loss_pct:.2f}% >= limite {self._max_daily_loss_pct}%",
                    )
        except SignalRejectedError:
            raise
        except Exception as e:
            logger.warning("Impossibile verificare limiti conto", error=str(e))

    def _clamp_lot_size(self, lots: Decimal, symbol: str) -> Decimal:
        """Limita i lotti al range consentito — il "limitatore di sicurezza"."""
        # Applica il massimo
        if lots > self._max_lot_size:
            logger.warning(
                "Lotti limitati al massimo",
                requested=str(lots),
                max=str(self._max_lot_size),
            )
            lots = self._max_lot_size

        # Applica i minimi del simbolo
        symbol_info = self._connector.get_symbol_info(symbol)
        if symbol_info:
            vol_min = symbol_info["volume_min"]
            vol_step = symbol_info["volume_step"]
            # Arrotonda allo step del volume PRIMA di clamp al minimo
            if vol_step > ZERO:
                lots = (lots // vol_step) * vol_step
            if lots < vol_min:
                lots = vol_min

        return lots

    def _submit_order(
        self,
        symbol: str,
        direction: str,
        lots: Decimal,
        stop_loss: Decimal,
        take_profit: Decimal,
        comment: str = "",
    ) -> dict[str, Any]:
        """Invia l'ordine a MT5 — "processa il pagamento". Restituisce il risultato."""
        try:
            import MetaTrader5 as mt5
        except ImportError:
            raise BrokerError("Pacchetto MetaTrader5 non disponibile")

        order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL

        # Ottieni il prezzo corrente
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise BrokerError(f"Impossibile ottenere il tick per {symbol}")

        price = tick.ask if direction == "BUY" else tick.bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(lots),
            "type": order_type,
            "price": price,
            "sl": float(stop_loss),
            "tp": float(take_profit),
            "deviation": 20,  # Slippage massimo consentito in punti
            "magic": 123456,  # Numero magico MONEYMAKER
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result is None:
            raise BrokerError("MT5 order_send ha restituito None")

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return {
                "status": "REJECTED",
                "order_id": "",
                "error_code": result.retcode,
                "error_message": result.comment,
                "executed_price": "0",
                "slippage": "0",
            }

        executed_price = to_decimal(result.price)
        requested_price = to_decimal(price)
        raw_slippage = executed_price - requested_price
        # Normalize: positive = unfavorable (paid more for BUY, received less for SELL)
        slippage = raw_slippage if direction == "BUY" else -raw_slippage

        return {
            "status": "FILLED",
            "order_id": str(result.order),
            "executed_price": str(executed_price),
            "requested_price": str(requested_price),
            "slippage": str(slippage),
            "volume": str(to_decimal(result.volume)),
        }

    def _submit_limit_order(
        self,
        symbol: str,
        direction: str,
        lots: Decimal,
        price: Decimal,
        stop_loss: Decimal,
        take_profit: Decimal,
        comment: str = "",
    ) -> dict[str, Any]:
        """Invia un ordine limit (pendente) a MT5."""
        try:
            import MetaTrader5 as mt5
        except ImportError:
            raise BrokerError("Pacchetto MetaTrader5 non disponibile")

        order_type = (
            mt5.ORDER_TYPE_BUY_LIMIT if direction == "BUY" else mt5.ORDER_TYPE_SELL_LIMIT
        )

        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": float(lots),
            "type": order_type,
            "price": float(price),
            "sl": float(stop_loss),
            "tp": float(take_profit),
            "deviation": 20,
            "magic": 123456,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result is None:
            raise BrokerError("MT5 order_send (limit) ha restituito None")

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return {
                "status": "REJECTED",
                "order_id": "",
                "error_code": result.retcode,
                "error_message": result.comment,
                "executed_price": "0",
                "slippage": "0",
            }

        return {
            "status": "PENDING",
            "order_id": str(result.order),
            "executed_price": "0",
            "requested_price": str(price),
            "slippage": "0",
            "volume": str(lots),
        }

    def _cleanup_old_signals(self) -> None:
        """Rimuove segnali più vecchi della finestra di de-duplicazione configurata."""
        now = time.time()
        expired = [
            sid for sid, ts in self._recent_signals.items()
            if now - ts > self._dedup_window_sec
        ]
        for sid in expired:
            del self._recent_signals[sid]
