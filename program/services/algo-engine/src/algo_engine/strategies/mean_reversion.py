# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Strategia di mean-reversion — "aspetta il rimbalzo".

Come un elastico tirato troppo: quando il prezzo si allontana troppo
dalla media, prima o poi ritorna. Attivata per regimi RANGING (laterali).

Usa le Bande di Bollinger %B e l'RSI per rilevare condizioni di prezzo
troppo estese all'interno di un trading range — come un pendolo che
ha raggiunto il punto massimo e sta per tornare indietro.

Condizioni d'ingresso:
- BUY:  BB %B < 0.10 E RSI < 30 — l'elastico è tirato al massimo verso il basso
- SELL: BB %B > 0.90 E RSI > 70 — l'elastico è tirato al massimo verso l'alto

La conferma dello Stocastico aumenta la confidenza.
In condizioni ambigue → HOLD — non tirare l'elastico tu stesso.

Rif: Doc 07, Sezione 5.2 — Strategia Mean-Reversion.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from moneymaker_common.enums import Direction

from algo_engine.strategies.base import SignalSuggestion, TradingStrategy

_BB_LOW_THRESHOLD = Decimal("0.10")
_BB_HIGH_THRESHOLD = Decimal("0.90")
_RSI_OVERSOLD = Decimal("30")
_RSI_OVERBOUGHT = Decimal("70")
_STOCH_OVERSOLD = Decimal("20")
_STOCH_OVERBOUGHT = Decimal("80")


class MeanReversionStrategy(TradingStrategy):
    """Strategia mean-reversion con Bollinger %B + RSI — come un "elastico"."""

    @property
    def name(self) -> str:
        return "mean_reversion_v1"

    def analyze(self, features: dict[str, Any]) -> SignalSuggestion:
        """Analizza gli indicatori per segnali di mean-reversion.

        Cerca il prezzo agli estremi delle Bande di Bollinger confermato
        dall'RSI — l'elastico è al massimo, il rimbalzo è imminente.
        Lo Stocastico fornisce ulteriore confidenza.

        Args:
            features: Dizionario indicatori dalla FeaturePipeline.

        Returns:
            SignalSuggestion con direzione, confidenza e motivazione.
        """
        bb_pct_b = features.get("bb_pct_b", Decimal("0.5"))
        rsi = features.get("rsi", Decimal("50"))
        stoch_k = features.get("stoch_k", Decimal("50"))

        reasons: list[str] = []

        # Condizione BUY: prezzo all'estremo inferiore — elastico tirato in basso
        if bb_pct_b < _BB_LOW_THRESHOLD and rsi < _RSI_OVERSOLD:
            confidence = Decimal("0.65")
            reasons.append(f"BB %B={bb_pct_b:.3f} < 0.10")
            reasons.append(f"RSI={rsi:.1f} < 30")

            # Conferma stocastica — rinforza la tesi del rimbalzo
            if stoch_k < _STOCH_OVERSOLD:
                confidence += Decimal("0.10")
                reasons.append(f"Stoch %K={stoch_k:.1f} conferma ipervenduto")

            return SignalSuggestion(
                direction=Direction.BUY,
                confidence=min(confidence, Decimal("0.85")),
                reasoning=f"Mean-reversion BUY: {', '.join(reasons)}",
                metadata={
                    "bb_pct_b": str(bb_pct_b),
                    "rsi": str(rsi),
                    "stoch_k": str(stoch_k),
                },
            )

        # Condizione SELL: prezzo all'estremo superiore — elastico tirato in alto
        if bb_pct_b > _BB_HIGH_THRESHOLD and rsi > _RSI_OVERBOUGHT:
            confidence = Decimal("0.65")
            reasons.append(f"BB %B={bb_pct_b:.3f} > 0.90")
            reasons.append(f"RSI={rsi:.1f} > 70")

            # Conferma stocastica — rinforza la tesi del ritracciamento
            if stoch_k > _STOCH_OVERBOUGHT:
                confidence += Decimal("0.10")
                reasons.append(f"Stoch %K={stoch_k:.1f} conferma ipercomprato")

            return SignalSuggestion(
                direction=Direction.SELL,
                confidence=min(confidence, Decimal("0.85")),
                reasoning=f"Mean-reversion SELL: {', '.join(reasons)}",
                metadata={
                    "bb_pct_b": str(bb_pct_b),
                    "rsi": str(rsi),
                    "stoch_k": str(stoch_k),
                },
            )

        # Condizioni ambigue → HOLD — l'elastico non è abbastanza teso
        return SignalSuggestion(
            direction=Direction.HOLD,
            confidence=Decimal("0.40"),
            reasoning=(
                f"Nessun segnale mean-reversion: BB %B={bb_pct_b:.3f}, RSI={rsi:.1f} "
                f"(serve %B < 0.10 + RSI < 30 oppure %B > 0.90 + RSI > 70)"
            ),
        )
