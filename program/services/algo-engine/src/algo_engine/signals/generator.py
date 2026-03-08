"""Generatore di segnali di trading.

Converte un SignalSuggestion da una strategia in un segnale TradingSignal
completo — come un operaio che prende il progetto dell'ingegnere (suggerimento)
e costruisce il pezzo finito (segnale) con tutti i dettagli:
ID univoco, timestamps, stop-loss, take-profit e metadati.

Tutti i calcoli sui prezzi usano aritmetica Decimal.
"""

from __future__ import annotations

import time
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.enums import Direction
from moneymaker_common.logging import get_logger

if TYPE_CHECKING:
    from algo_engine.strategies.base import SignalSuggestion

logger = get_logger(__name__)


class SignalGenerator:
    """Genera segnali di trading completi dai suggerimenti strategici.

    Come un artigiano che dal semplice schizzo (suggerimento) crea
    l'opera finita (segnale) aggiungendo:
    - ID univoco del segnale (UUID4) — la "targa" del segnale
    - Timestamps — quando è stato creato
    - Stop-loss e take-profit basati sull'ATR — le "reti di sicurezza"
    - Metadati del segnale — la "carta d'identità" per l'audit trail

    Utilizzo:
        generator = SignalGenerator()
        signal = generator.generate_signal("XAUUSD", suggestion, current_price, atr)
    """

    def __init__(
        self,
        default_sl_atr_multiplier: Decimal = Decimal("1.5"),
        default_tp_atr_multiplier: Decimal = Decimal("2.5"),
    ) -> None:
        """Inizializza il generatore di segnali.

        Args:
            default_sl_atr_multiplier: Moltiplicatore ATR per la distanza dello stop-loss.
            default_tp_atr_multiplier: Moltiplicatore ATR per la distanza del take-profit.
        """
        self.default_sl_atr_multiplier = default_sl_atr_multiplier
        self.default_tp_atr_multiplier = default_tp_atr_multiplier

    def generate_signal(
        self,
        symbol: str,
        suggestion: SignalSuggestion,
        current_price: Decimal,
        atr: Decimal = ZERO,
    ) -> dict[str, Any] | None:
        """Genera un segnale di trading da un suggerimento strategico.

        Se l'ATR è fornito e diverso da zero, stop-loss e take-profit
        vengono calcolati come multipli dell'ATR dal prezzo corrente.
        Se l'ATR è zero per segnali non-HOLD, ritorna None (rifiutato).

        Args:
            symbol: Simbolo dello strumento (es. "XAUUSD").
            suggestion: Il SignalSuggestion dalla strategia.
            current_price: Prezzo di mercato corrente come Decimal.
            atr: Valore ATR corrente per il calcolo SL/TP.

        Returns:
            Dizionario del segnale di trading, o None se ATR invalido.
        """
        signal_id = str(uuid.uuid4())
        timestamp_ms = int(time.time() * 1000)

        # Rifiuta segnali senza ATR valido per direzioni non-HOLD
        # (un segnale senza stop-loss è troppo pericoloso da eseguire)
        if suggestion.direction != Direction.HOLD and atr <= ZERO:
            logger.warning(
                "Segnale rifiutato: ATR zero o negativo, impossibile calcolare SL/TP",
                symbol=symbol,
                direction=suggestion.direction,
                atr=str(atr),
            )
            return None

        # Calcola stop-loss e take-profit — le "reti di sicurezza" del trade
        stop_loss = ZERO
        take_profit = ZERO

        if atr > ZERO and suggestion.direction != Direction.HOLD:
            sl_distance = atr * self.default_sl_atr_multiplier
            tp_distance = atr * self.default_tp_atr_multiplier

            if suggestion.direction == Direction.BUY:
                stop_loss = current_price - sl_distance
                take_profit = current_price + tp_distance
            elif suggestion.direction == Direction.SELL:
                stop_loss = current_price + sl_distance
                take_profit = current_price - tp_distance

        # Rapporto rischio/rendimento — quanto guadagni per ogni euro rischiato
        risk_reward = ZERO
        if stop_loss != ZERO and take_profit != ZERO:
            risk = abs(current_price - stop_loss)
            reward = abs(take_profit - current_price)
            if risk > ZERO:
                risk_reward = reward / risk

        # Tipo ordine (MARKET o LIMIT) dal metadata della strategia
        order_type = "MARKET"
        if suggestion.metadata:
            order_type = suggestion.metadata.get("order_type", "MARKET")

        signal: dict[str, Any] = {
            "signal_id": signal_id,
            "symbol": symbol,
            "direction": suggestion.direction,
            "confidence": suggestion.confidence,
            "entry_price": current_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_reward_ratio": risk_reward,
            "order_type": order_type,
            "reasoning": suggestion.reasoning,
            "timestamp_ms": timestamp_ms,
            "metadata": suggestion.metadata or {},
        }

        logger.info(
            "Segnale generato",
            signal_id=signal_id,
            symbol=symbol,
            direction=suggestion.direction,
            confidence=str(suggestion.confidence),
            entry_price=str(current_price),
            stop_loss=str(stop_loss),
            take_profit=str(take_profit),
            risk_reward=str(risk_reward),
        )

        return signal
