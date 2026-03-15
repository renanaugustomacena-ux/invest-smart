"""Strategia di trend-following — "segui la corrente".

Come un surfista che cavalca l'onda: attivata per i regimi TRENDING_UP
e TRENDING_DOWN. Usa più indicatori di conferma per verificare che l'onda
(trend) sia vera e forte prima di salirci sopra.

Indicatori di conferma — le "prove" che il trend è reale:
1. Incrocio EMA (veloce > lenta per BUY, veloce < lenta per SELL)
2. Prezzo sopra/sotto la SMA(200) — la "linea di galleggiamento"
3. Istogramma MACD positivo/negativo — il "motore" del momentum
4. ADX > 25 — la "forza del vento" è sufficiente

Richiede >= 3 conferme per generare un segnale. Confidenza = 0.50 + ADX/100
(massimo 0.90). Meno di 3 conferme → HOLD — meglio aspettare la prossima onda.

Rif: Doc 07, Sezione 5.1 — Strategia Trend-Following.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.enums import Direction

from algo_engine.strategies.base import SignalSuggestion, TradingStrategy

_ADX_THRESHOLD = Decimal("25")
_MIN_CONFIRMATIONS = 3


class TrendFollowingStrategy(TradingStrategy):
    """Strategia trend-following con conferma multi-indicatore — il "surfista"."""

    @property
    def name(self) -> str:
        return "trend_following_v1"

    def analyze(self, features: dict[str, Any]) -> SignalSuggestion:
        """Analizza gli indicatori per segnali trend-following.

        Conta gli indicatori che confermano la direzione del trend dominante.
        Richiede almeno 3 conferme per generare un segnale BUY o SELL.

        Args:
            features: Dizionario indicatori dalla FeaturePipeline.

        Returns:
            SignalSuggestion con direzione, confidenza e motivazione.
        """
        ema_fast = features.get("ema_fast", ZERO)
        ema_slow = features.get("ema_slow", ZERO)
        sma_200 = features.get("sma_200", ZERO)
        latest_close = features.get("latest_close", ZERO)
        macd_histogram = features.get("macd_histogram", ZERO)
        adx = features.get("adx", ZERO)
        adx = max(ZERO, min(adx, Decimal("100")))

        # Conta le conferme per ciascuna direzione
        buy_confirmations: list[str] = []
        sell_confirmations: list[str] = []

        # 1. Incrocio EMA — le medie mobili si allineano
        if ema_fast > ZERO and ema_slow > ZERO:
            if ema_fast > ema_slow:
                buy_confirmations.append("EMA veloce > lenta")
            elif ema_fast < ema_slow:
                sell_confirmations.append("EMA veloce < lenta")

        # 2. Prezzo vs SMA(200) — sopra o sotto la linea di galleggiamento
        if sma_200 > ZERO and latest_close > ZERO:
            if latest_close > sma_200:
                buy_confirmations.append("Prezzo > SMA(200)")
            elif latest_close < sma_200:
                sell_confirmations.append("Prezzo < SMA(200)")

        # 3. Istogramma MACD — il motore del momentum
        if macd_histogram > ZERO:
            buy_confirmations.append("Istogramma MACD positivo")
        elif macd_histogram < ZERO:
            sell_confirmations.append("Istogramma MACD negativo")

        # 4. Forza del trend ADX — il vento è abbastanza forte?
        # ADX è non-direzionale: rafforza la direzione dominante, non entrambe.
        adx_strong = adx > _ADX_THRESHOLD
        if adx_strong:
            if len(buy_confirmations) > len(sell_confirmations):
                buy_confirmations.append("ADX > 25")
            elif len(sell_confirmations) > len(buy_confirmations):
                sell_confirmations.append("ADX > 25")

        # Determina la direzione in base al conteggio delle conferme
        buy_count = len(buy_confirmations)
        sell_count = len(sell_confirmations)

        if buy_count >= _MIN_CONFIRMATIONS and buy_count > sell_count:
            confidence = min(Decimal("0.50") + adx / Decimal("100"), Decimal("0.90"))
            return SignalSuggestion(
                direction=Direction.BUY,
                confidence=confidence,
                reasoning=f"Trend BUY: {buy_count} conferme — {', '.join(buy_confirmations)}",
                metadata={"confirmations": buy_count, "indicators": buy_confirmations},
            )

        if sell_count >= _MIN_CONFIRMATIONS and sell_count > buy_count:
            confidence = min(Decimal("0.50") + adx / Decimal("100"), Decimal("0.90"))
            return SignalSuggestion(
                direction=Direction.SELL,
                confidence=confidence,
                reasoning=(
                    f"Trend SELL: {sell_count} conferme" f" — {', '.join(sell_confirmations)}"
                ),
                metadata={
                    "confirmations": sell_count,
                    "indicators": sell_confirmations,
                },
            )

        return SignalSuggestion(
            direction=Direction.HOLD,
            confidence=Decimal("0.30"),
            reasoning=(
                f"Conferme insufficienti: BUY={buy_count}, SELL={sell_count}, "
                f"servono >= {_MIN_CONFIRMATIONS}"
            ),
        )
