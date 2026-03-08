"""Validazione Qualità Dati — il "laboratorio di analisi" delle candele.

Prima di processare una candela attraverso la pipeline, verifica che
i dati siano sensati. Come un controllore qualità che scarta i pezzi
difettosi prima che entrino nella catena di montaggio.

Controlli:
1. Relazione OHLC valida (high >= max(open, close), low <= min(open, close))
2. Spike detection (movimento > 3x ATR medio)
3. Volume zero (segnale di dati mancanti)
4. Timestamp stale (gap > 2x durata timeframe)

Utilizzo:
    checker = DataQualityChecker()
    is_valid, reason = checker.validate_bar(bar, prev_bar)
"""

from __future__ import annotations

from decimal import Decimal

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.logging import get_logger

logger = get_logger(__name__)


class DataQualityChecker:
    """Valida le candele OHLCV prima dell'elaborazione."""

    def __init__(
        self,
        max_spike_atr_multiple: Decimal = Decimal("5.0"),
        max_gap_multiple: float = 3.0,
    ) -> None:
        """
        Args:
            max_spike_atr_multiple: Rifiuta barre con range > N volte l'ATR medio.
            max_gap_multiple: Rifiuta se il gap temporale > N volte la durata timeframe.
        """
        self._max_spike = max_spike_atr_multiple
        self._max_gap = max_gap_multiple
        self._avg_range: Decimal = ZERO
        self._bar_count: int = 0

    def validate_bar(
        self,
        bar_open: Decimal,
        bar_high: Decimal,
        bar_low: Decimal,
        bar_close: Decimal,
        bar_volume: Decimal,
        bar_timestamp_ms: int,
        prev_close: Decimal | None = None,
        prev_timestamp_ms: int | None = None,
        expected_interval_ms: int = 60_000,
    ) -> tuple[bool, str]:
        """Valida una singola candela OHLCV.

        Returns:
            Tupla (è_valida, motivo). Se valida, motivo è stringa vuota.
        """
        # 1. Relazione OHLC — high deve essere il massimo, low il minimo
        if bar_high < bar_open or bar_high < bar_close:
            return False, f"OHLC invalido: high ({bar_high}) < open ({bar_open}) o close ({bar_close})"

        if bar_low > bar_open or bar_low > bar_close:
            return False, f"OHLC invalido: low ({bar_low}) > open ({bar_open}) o close ({bar_close})"

        if bar_high < bar_low:
            return False, f"OHLC invalido: high ({bar_high}) < low ({bar_low})"

        # 2. Volume zero — probabile dato mancante
        if bar_volume <= ZERO:
            logger.debug("Barra con volume zero, potrebbe essere dato mancante")
            # Non rifiutiamo, ma logghiamo (nel forex i volumi possono essere tick count)

        # 3. Spike detection — movimento anomalo rispetto alla media
        bar_range = bar_high - bar_low
        if bar_range > ZERO:
            self._bar_count += 1
            # Media mobile esponenziale del range
            if self._avg_range == ZERO:
                self._avg_range = bar_range
            else:
                alpha = Decimal("0.05")
                self._avg_range = alpha * bar_range + (1 - alpha) * self._avg_range

            if self._bar_count > 20 and self._avg_range > ZERO:
                spike_ratio = bar_range / self._avg_range
                if spike_ratio > self._max_spike:
                    return False, (
                        f"Spike rilevato: range {bar_range} = "
                        f"{spike_ratio:.1f}x media ({self._avg_range:.5f})"
                    )

        # 4. Gap detection — se il timestamp è troppo lontano dal precedente
        if prev_timestamp_ms is not None and expected_interval_ms > 0:
            gap_ms = bar_timestamp_ms - prev_timestamp_ms
            max_gap_ms = expected_interval_ms * self._max_gap
            if gap_ms > max_gap_ms and gap_ms > 0:
                logger.warning(
                    "Gap temporale rilevato",
                    gap_seconds=gap_ms / 1000,
                    expected_seconds=expected_interval_ms / 1000,
                )
                # Non rifiutiamo (i gap sono normali nel forex), ma logghiamo

        # 5. Price continuity — salto eccessivo dal close precedente
        if prev_close is not None and prev_close > ZERO and self._avg_range > ZERO:
            gap = abs(bar_open - prev_close)
            if gap > self._avg_range * self._max_spike:
                return False, (
                    f"Gap di prezzo anomalo: {gap:.5f} "
                    f"(prev close: {prev_close}, open: {bar_open})"
                )

        return True, ""
