# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Gestione connessione al terminale MetaTrader 5.

Come il "telefono diretto" con la banca: gestisce l'inizializzazione,
la connessione e la disconnessione dal terminale MT5.
Il pacchetto Python MT5 richiede un terminale MT5 in esecuzione
(Windows o Wine) — come il telefono che funziona solo se la banca è aperta.
"""

from __future__ import annotations

from typing import Any

from moneymaker_common.decimal_utils import to_decimal
from moneymaker_common.exceptions import BrokerError
from moneymaker_common.logging import get_logger

logger = get_logger(__name__)


class MT5Connector:
    """Gestisce la connessione al terminale MetaTrader 5 — il "telefono con la banca"."""

    def __init__(self, account: str, password: str, server: str, timeout_ms: int = 10000) -> None:
        self._account = account
        self._password = password
        self._server = server
        self._timeout_ms = timeout_ms
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Verifica connettivita' reale al terminale MT5, non solo flag locale."""
        if not self._connected:
            return False
        try:
            import MetaTrader5 as mt5

            info = mt5.terminal_info()
            if info is None:
                self._connected = False
                logger.warning("MT5 terminal non raggiungibile, flag resettato")
                return False
            return info.connected
        except Exception:
            self._connected = False
            return False

    def connect(self) -> None:
        """Inizializza e accede al terminale MT5 — "alza la cornetta e chiama la banca"."""
        try:
            import MetaTrader5 as mt5
        except ImportError:
            raise BrokerError(
                "Pacchetto MetaTrader5 non installato. "
                "Installa con: pip install MetaTrader5 (solo Windows)"
            )

        if not mt5.initialize(timeout=self._timeout_ms):
            error = mt5.last_error()
            raise BrokerError(f"Inizializzazione MT5 fallita: {error}")

        authorized = mt5.login(
            login=int(self._account),
            password=self._password,
            server=self._server,
            timeout=self._timeout_ms,
        )
        if not authorized:
            error = mt5.last_error()
            mt5.shutdown()
            raise BrokerError(f"Login MT5 fallito: {error}")

        self._connected = True
        logger.info("Connesso a MT5", server=self._server, account=self._account)

    def reconnect(
        self,
        max_retries: int = 5,
        initial_delay_sec: float = 1.0,
        max_delay_sec: float = 60.0,
    ) -> bool:
        """Tenta la riconnessione al terminale MT5 con backoff esponenziale."""
        import time as _time

        delay = initial_delay_sec
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    "Tentativo riconnessione MT5",
                    attempt=attempt,
                    max=max_retries,
                    delay_sec=delay,
                )
                self.disconnect()
                _time.sleep(delay)
                self.connect()
                logger.info("Riconnessione MT5 riuscita", attempt=attempt)
                return True
            except Exception as exc:
                logger.warning("Riconnessione fallita", attempt=attempt, error=str(exc))
                delay = min(delay * 2, max_delay_sec)
        logger.error("Riconnessione MT5 fallita dopo %d tentativi", max_retries)
        return False

    def disconnect(self) -> None:
        """Chiude la connessione al terminale MT5 — "riattacca il telefono"."""
        if self._connected:
            try:
                import MetaTrader5 as mt5

                mt5.shutdown()
            except Exception as e:
                logger.warning("Errore durante lo shutdown di MT5", error=str(e))
            finally:
                self._connected = False
                logger.info("Disconnesso da MT5")

    def get_account_info(self) -> dict[str, Any]:
        """Recupera le informazioni del conto corrente — l'"estratto conto"."""
        self._ensure_connected()
        import MetaTrader5 as mt5

        info = mt5.account_info()
        if info is None:
            raise BrokerError("Impossibile ottenere le info del conto")

        return {
            "balance": to_decimal(info.balance),
            "equity": to_decimal(info.equity),
            "margin": to_decimal(info.margin),
            "free_margin": to_decimal(info.margin_free),
            "profit": to_decimal(info.profit),
            "leverage": info.leverage,
            "currency": info.currency,
        }

    def get_symbol_info(self, symbol: str) -> dict[str, Any] | None:
        """Ottiene le informazioni di trading per un simbolo — la "scheda prodotto"."""
        self._ensure_connected()
        import MetaTrader5 as mt5

        info = mt5.symbol_info(symbol)
        if info is None:
            return None

        return {
            "name": info.name,
            "bid": to_decimal(info.bid),
            "ask": to_decimal(info.ask),
            "spread": info.spread,
            "digits": info.digits,
            "trade_contract_size": to_decimal(info.trade_contract_size),
            "volume_min": to_decimal(info.volume_min),
            "volume_max": to_decimal(info.volume_max),
            "volume_step": to_decimal(info.volume_step),
            "trade_mode": info.trade_mode,
        }

    def get_open_positions(self) -> list[dict[str, Any]]:
        """Ottiene tutte le posizioni attualmente aperte — le "operazioni in corso"."""
        self._ensure_connected()
        import MetaTrader5 as mt5

        positions = mt5.positions_get()
        if positions is None:
            return []

        result = []
        for pos in positions:
            result.append(
                {
                    "ticket": pos.ticket,
                    "symbol": pos.symbol,
                    "type": "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL",
                    "volume": to_decimal(pos.volume),
                    "price_open": to_decimal(pos.price_open),
                    "price_current": to_decimal(pos.price_current),
                    "sl": to_decimal(pos.sl),
                    "tp": to_decimal(pos.tp),
                    "profit": to_decimal(pos.profit),
                    "swap": to_decimal(pos.swap),
                    "commission": to_decimal(pos.commission),
                    "time": pos.time,
                    "magic": pos.magic,
                    "comment": pos.comment,
                }
            )
        return result

    def check_margin(self, symbol: str, direction: str, lots: float) -> dict[str, Any] | None:
        """Verifica il margine disponibile prima di aprire una posizione.

        Returns:
            Dict con margin_required e margin_free, oppure None se il calcolo fallisce.

        Raises:
            BrokerError: Se il margine libero è insufficiente.
        """
        self._ensure_connected()
        import MetaTrader5 as mt5

        order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return None

        price = tick.ask if direction == "BUY" else tick.bid
        margin = mt5.order_calc_margin(order_type, symbol, lots, price)
        if margin is None:
            return None

        account = mt5.account_info()
        if account is None:
            return None

        free_margin = account.margin_free
        if margin > free_margin:
            raise BrokerError(
                f"Margine insufficiente per {symbol}: richiesto={margin:.2f}, "
                f"disponibile={free_margin:.2f}"
            )

        return {
            "margin_required": to_decimal(margin),
            "margin_free": to_decimal(free_margin),
        }

    def modify_position_sl(self, ticket: int, new_sl: float) -> bool:
        """Modifica lo stop-loss di una posizione aperta (trailing stop).

        Args:
            ticket: Ticket della posizione da modificare.
            new_sl: Nuovo livello di stop-loss.

        Returns:
            True se la modifica è andata a buon fine.
        """
        self._ensure_connected()
        import MetaTrader5 as mt5

        position = mt5.positions_get(ticket=ticket)
        if not position:
            logger.warning("Posizione non trovata per trailing stop", ticket=ticket)
            return False

        pos = position[0]
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "symbol": pos.symbol,
            "sl": new_sl,
            "tp": float(pos.tp),
            "magic": pos.magic,
        }

        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            code = result.retcode if result else "None"
            logger.warning(
                "Modifica SL fallita",
                ticket=ticket,
                new_sl=new_sl,
                retcode=code,
            )
            return False

        logger.debug("Trailing stop aggiornato", ticket=ticket, new_sl=new_sl)
        return True

    def get_pending_orders(self) -> list[dict[str, Any]]:
        """Ottiene tutti gli ordini pendenti MONEYMAKER (magic=123456)."""
        self._ensure_connected()
        import MetaTrader5 as mt5

        orders = mt5.orders_get()
        if orders is None:
            return []

        return [
            {
                "ticket": o.ticket,
                "symbol": o.symbol,
                "type": o.type,
                "volume": to_decimal(o.volume_current),
                "price": to_decimal(o.price_open),
                "magic": o.magic,
            }
            for o in orders
            if o.magic == 123456
        ]

    def cancel_order(self, ticket: int) -> bool:
        """Cancella un ordine pendente per ticket."""
        self._ensure_connected()
        import MetaTrader5 as mt5

        request = {
            "action": mt5.TRADE_ACTION_REMOVE,
            "order": ticket,
        }
        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            code = result.retcode if result else "None"
            logger.warning("Cancellazione ordine fallita", ticket=ticket, retcode=code)
            return False

        logger.info("Ordine pendente cancellato", ticket=ticket)
        return True

    def send_heartbeat(self) -> bool:
        """Scrive il timestamp corrente nella GlobalVariable MT5 per il Guardian EA.

        Il Guardian EA legge MONEYMAKER_HEARTBEAT per sapere se il bridge Python
        è ancora vivo. Se il valore diventa stale (>30s), il Guardian entra
        in modalità difensiva e gestisce i trailing stop in autonomia.
        """
        if not self._connected:
            return False
        try:
            import MetaTrader5 as mt5
            import time as _time

            # GlobalVariableSet scrive un double — usiamo Unix timestamp
            result = mt5.global_variable_set("MONEYMAKER_HEARTBEAT", float(int(_time.time())))
            if result:
                return True
            logger.debug("Impossibile scrivere heartbeat GlobalVariable")
            return False
        except Exception as exc:
            logger.debug("Errore invio heartbeat: %s", exc)
            return False

    def _ensure_connected(self) -> None:
        """Verifica la connessione a MT5, altrimenti solleva eccezione."""
        if not self._connected:
            raise BrokerError("Non connesso al terminale MT5")
