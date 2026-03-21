# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Validatore di rischio per i segnali di trading.

L'ultimo cancello prima che un segnale raggiunga il MT5 Bridge — come
il controllore qualità alla fine della catena di montaggio. Ogni segnale
deve superare tutti i controlli di rischio prima di essere "spedito".

Controlli di rischio:
1. Numero massimo di posizioni aperte — non sovraccaricare il parcheggio
2. Drawdown massimo del portafoglio — il "freno d'emergenza" delle perdite
3. Limite perdita giornaliera — il budget giornaliero di rischio
4. Soglia minima di confidenza — non agire se non sei abbastanza sicuro
5. Posizionamento valido dello stop-loss — la rete di sicurezza deve essere al posto giusto
6-7. Rapporto rischio/rendimento minimo
8. Margine sufficiente — hai abbastanza soldi in garanzia?
9. Correlazione esposizione valutaria
10. Sessione di trading
11. Calendario economico
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.enums import Direction
from moneymaker_common.logging import get_logger

logger = get_logger(__name__)


class SignalValidator:
    """Valida i segnali di trading contro i vincoli di rischio — il "controllore qualità".

    Tutte le soglie sono configurabili. Il validatore controlla
    diverse dimensioni di rischio e restituisce un risultato
    passa/non-passa con spiegazione.

    Utilizzo:
        validator = SignalValidator(
            max_open_positions=5,
            max_drawdown_pct=Decimal("5.0"),
            max_daily_loss_pct=Decimal("2.0"),
            min_confidence=Decimal("0.65"),
        )

        valid, reason = validator.validate(signal, portfolio_state)
        if valid:
            # Invia il segnale al MT5 Bridge
            ...
    """

    def __init__(
        self,
        max_open_positions: int = 5,
        max_drawdown_pct: Decimal = Decimal("5.0"),
        max_daily_loss_pct: Decimal = Decimal("2.0"),
        min_confidence: Decimal = Decimal("0.65"),
        min_risk_reward_ratio: Decimal = Decimal("1.0"),
        correlation_checker: Any = None,
        session_classifier: Any = None,
        calendar_filter: Any = None,
        spread_tracker: Any = None,
        default_leverage: int = 100,
        margin_buffer_pct: Decimal = Decimal("0.80"),
    ) -> None:
        """Inizializza il validatore con le soglie di rischio.

        Args:
            max_open_positions: Numero massimo di posizioni aperte simultanee.
            max_drawdown_pct: Percentuale massima di drawdown del portafoglio.
            max_daily_loss_pct: Perdita giornaliera massima come % del capitale.
            min_confidence: Confidenza minima del segnale per permettere l'esecuzione.
            min_risk_reward_ratio: Rapporto rischio/rendimento minimo per il trade.
            correlation_checker: CorrelationChecker per esposizione valutaria.
            session_classifier: SessionClassifier per awareness sessione di trading.
            calendar_filter: EconomicCalendarFilter per blackout eventi.
            default_leverage: Leva predefinita per il calcolo del margine.
            margin_buffer_pct: Frazione del margine disponibile utilizzabile (0.80 = 80%).
        """
        self.max_open_positions = max_open_positions
        self.max_drawdown_pct = max_drawdown_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.min_confidence = min_confidence
        self.min_risk_reward_ratio = min_risk_reward_ratio
        self._correlation_checker = correlation_checker
        self._session_classifier = session_classifier
        self._calendar_filter = calendar_filter
        self._spread_tracker = spread_tracker
        self._default_leverage = default_leverage
        self._margin_buffer_pct = margin_buffer_pct

    def validate(
        self,
        signal: dict[str, Any],
        portfolio_state: dict[str, Any],
    ) -> tuple[bool, str]:
        """Valida un segnale di trading contro i vincoli di rischio.

        Esegue tutti i controlli in sequenza. Si ferma al primo
        "difetto" trovato (fail-fast) — come un controllore che
        scarta il pezzo al primo problema.

        Args:
            signal: Dizionario segnale da SignalGenerator.
                Chiavi attese: direction, confidence, stop_loss, entry_price,
                take_profit, risk_reward_ratio, symbol.
            portfolio_state: Dizionario stato portafoglio corrente.
                Chiavi attese: open_position_count, current_drawdown_pct,
                daily_loss_pct, equity.

        Returns:
            Tupla (è_valido, motivo). Se valido, motivo = "tutti i controlli superati".
            Se non valido, motivo descrive quale controllo è fallito.
        """
        # Controllo 1: I segnali HOLD non vengono mai eseguiti — stai fermo
        direction = signal.get("direction", Direction.HOLD)
        # Normalizza: accetta sia stringa che enum
        if isinstance(direction, str):
            try:
                direction = Direction(direction)
            except ValueError:
                direction = Direction.HOLD
        if direction == Direction.HOLD:
            logger.debug("Segnale rifiutato: direzione HOLD", signal_id=signal.get("signal_id"))
            return False, "I segnali HOLD non vengono eseguiti"

        # Controllo 2: Posizioni aperte massime — il parcheggio è pieno
        open_positions = portfolio_state.get("open_position_count", 0)
        if open_positions >= self.max_open_positions:
            reason = (
                f"Posizioni aperte massime raggiunte: {open_positions}/{self.max_open_positions}"
            )
            logger.warning(
                "Segnale rifiutato: max posizioni",
                signal_id=signal.get("signal_id"),
                open_positions=open_positions,
                max_positions=self.max_open_positions,
            )
            return False, reason

        # Controllo 3: Drawdown massimo — il freno d'emergenza
        current_drawdown = Decimal(str(portfolio_state.get("current_drawdown_pct", "0")))
        if current_drawdown >= self.max_drawdown_pct:
            reason = f"Drawdown massimo superato: {current_drawdown}% >= {self.max_drawdown_pct}%"
            logger.warning(
                "Segnale rifiutato: max drawdown",
                signal_id=signal.get("signal_id"),
                current_drawdown=str(current_drawdown),
                max_drawdown=str(self.max_drawdown_pct),
            )
            return False, reason

        # Controllo 4: Limite perdita giornaliera — il budget è esaurito
        daily_loss = Decimal(str(portfolio_state.get("daily_loss_pct", "0")))
        if daily_loss >= self.max_daily_loss_pct:
            reason = (
                f"Limite perdita giornaliera superato: {daily_loss}% >= {self.max_daily_loss_pct}%"
            )
            logger.warning(
                "Segnale rifiutato: limite perdita giornaliera",
                signal_id=signal.get("signal_id"),
                daily_loss=str(daily_loss),
                max_daily_loss=str(self.max_daily_loss_pct),
            )
            return False, reason

        # Controllo 5: Soglia minima di confidenza — non abbastanza sicuro
        confidence = Decimal(str(signal.get("confidence", "0")))
        if confidence.is_nan() or confidence.is_infinite():
            return False, f"Confidenza non valida: {confidence}"
        if confidence < self.min_confidence:
            reason = f"Confidenza sotto la soglia: {confidence} < {self.min_confidence}"
            logger.info(
                "Segnale rifiutato: confidenza bassa",
                signal_id=signal.get("signal_id"),
                confidence=str(confidence),
                min_confidence=str(self.min_confidence),
            )
            return False, reason

        # Controllo 5b: Spread percentile — spread anomalo rispetto alla storia
        if self._spread_tracker is not None:
            symbol = signal.get("symbol", "")
            current_spread = Decimal(str(signal.get("spread", "0")))
            if current_spread > ZERO:
                spread_ok, spread_reason = self._spread_tracker.check(symbol, current_spread)
                if not spread_ok:
                    logger.warning(
                        "Segnale rifiutato: spread anomalo",
                        signal_id=signal.get("signal_id"),
                        spread=str(current_spread),
                        reason=spread_reason,
                    )
                    return False, spread_reason

        # Controllo 6: Posizionamento valido dello stop-loss — la rete è al posto giusto?
        stop_loss = Decimal(str(signal.get("stop_loss", "0")))
        entry_price = Decimal(str(signal.get("entry_price", "0")))

        # Controllo NaN/Inf su entry_price e stop_loss
        if entry_price.is_nan() or entry_price.is_infinite():
            return False, f"Prezzo d'ingresso non valido: {entry_price}"
        if stop_loss.is_nan() or stop_loss.is_infinite():
            return False, f"Stop-loss non valido: {stop_loss}"

        if stop_loss == ZERO:
            reason = "Stop-loss non impostato (zero)"
            logger.warning(
                "Segnale rifiutato: stop-loss assente",
                signal_id=signal.get("signal_id"),
            )
            return False, reason

        # Verifica che lo stop-loss sia dal lato corretto del prezzo d'ingresso
        if direction == Direction.BUY and stop_loss >= entry_price:
            reason = f"Stop-loss BUY ({stop_loss}) deve essere sotto il prezzo d'ingresso ({entry_price})"
            logger.warning(
                "Segnale rifiutato: SL posizionato male",
                signal_id=signal.get("signal_id"),
                direction=direction,
                stop_loss=str(stop_loss),
                entry_price=str(entry_price),
            )
            return False, reason

        if direction == Direction.SELL and stop_loss <= entry_price:
            reason = f"Stop-loss SELL ({stop_loss}) deve essere sopra il prezzo d'ingresso ({entry_price})"
            logger.warning(
                "Segnale rifiutato: SL posizionato male",
                signal_id=signal.get("signal_id"),
                direction=direction,
                stop_loss=str(stop_loss),
                entry_price=str(entry_price),
            )
            return False, reason

        # Controllo 7: Rapporto rischio/rendimento minimo — il gioco deve valere la candela
        risk_reward = Decimal(str(signal.get("risk_reward_ratio", "0")))
        if risk_reward < self.min_risk_reward_ratio and self.min_risk_reward_ratio > ZERO:
            reason = f"Rapporto rischio/rendimento troppo basso: {risk_reward} < {self.min_risk_reward_ratio}"
            logger.info(
                "Segnale rifiutato: rischio/rendimento basso",
                signal_id=signal.get("signal_id"),
                risk_reward=str(risk_reward),
                min_risk_reward=str(self.min_risk_reward_ratio),
            )
            return False, reason

        # Controllo 8: Margine sufficiente — hai abbastanza soldi in garanzia?
        equity_str = str(portfolio_state.get("equity", "0"))
        used_margin_str = str(portfolio_state.get("used_margin", "0"))
        suggested_lots_str = str(signal.get("suggested_lots", "0"))
        equity = Decimal(equity_str)
        used_margin = Decimal(used_margin_str)
        suggested_lots = Decimal(suggested_lots_str)
        if equity > ZERO and suggested_lots > ZERO:
            symbol = signal.get("symbol", "")
            if "XAU" in symbol:
                contract_size = Decimal("100")  # 1 lot = 100 oz gold
            elif "XAG" in symbol:
                contract_size = Decimal("5000")  # 1 lot = 5000 oz silver
            else:
                contract_size = Decimal("100000")  # 1 lot = 100k units (forex)
            # Usa la leva reale dal contesto account, fallback al default configurato
            account_leverage = int(portfolio_state.get("leverage", self._default_leverage))
            if account_leverage <= 0:
                account_leverage = self._default_leverage
            estimated_margin = (suggested_lots * contract_size * entry_price) / Decimal(
                str(account_leverage)
            )
            available_margin = equity - used_margin
            margin_buffer = available_margin * self._margin_buffer_pct
            if estimated_margin > margin_buffer:
                buffer_pct_display = int(self._margin_buffer_pct * 100)
                reason = (
                    f"Margine insufficiente: richiesto {estimated_margin:.2f}, "
                    f"disponibile {available_margin:.2f} ({buffer_pct_display}% buffer: {margin_buffer:.2f})"
                )
                logger.warning(
                    "Segnale rifiutato: margine insufficiente",
                    signal_id=signal.get("signal_id"),
                    estimated_margin=str(estimated_margin),
                    available_margin=str(available_margin),
                )
                return False, reason

        # Controllo 9: Correlazione esposizione valutaria — non sbilanciare il portafoglio
        if self._correlation_checker is None:
            logger.debug(
                "Controllo correlazione disabilitato (correlation_checker non configurato)",
                signal_id=signal.get("signal_id"),
            )
        if self._correlation_checker is not None:
            symbol = signal.get("symbol", "")
            dir_str = direction.value
            positions_detail = portfolio_state.get("positions_detail", [])
            is_ok, corr_reason = self._correlation_checker.check(symbol, dir_str, positions_detail)
            if not is_ok:
                logger.warning(
                    "Segnale rifiutato: correlazione esposizione",
                    signal_id=signal.get("signal_id"),
                    reason=corr_reason,
                )
                return False, corr_reason

        # Controllo 10: Sessione di trading — OFF_HOURS richiede confidenza extra
        if self._session_classifier is not None:
            from datetime import datetime, timezone

            utc_hour = datetime.now(timezone.utc).hour
            session = self._session_classifier.classify(utc_hour)
            boost = self._session_classifier.get_confidence_boost(session)
            adjusted_threshold = max(Decimal("0.30"), self.min_confidence - Decimal(str(boost)))
            if confidence < adjusted_threshold:
                reason = (
                    f"Confidenza insufficiente per sessione {session.value}: "
                    f"{confidence} < {adjusted_threshold}"
                )
                logger.info(
                    "Segnale rifiutato: confidenza sessione",
                    signal_id=signal.get("signal_id"),
                    session=session.value,
                    confidence=str(confidence),
                    threshold=str(adjusted_threshold),
                )
                return False, reason

        # Controllo 11: Calendario economico — blackout durante eventi high-impact
        if self._calendar_filter is not None:
            from datetime import datetime, timezone

            symbol = signal.get("symbol", "")
            utc_now = datetime.now(timezone.utc)
            is_blocked, _cal_desc = self._calendar_filter.is_blackout(symbol, utc_now)
            if is_blocked:
                reason = f"Blackout calendario economico per {symbol}"
                logger.warning(
                    "Segnale rifiutato: blackout economico",
                    signal_id=signal.get("signal_id"),
                    symbol=symbol,
                )
                return False, reason

        logger.info(
            "Segnale validato con successo",
            signal_id=signal.get("signal_id"),
            symbol=signal.get("symbol"),
            direction=direction,
            confidence=str(confidence),
        )
        return True, "tutti i controlli superati"
