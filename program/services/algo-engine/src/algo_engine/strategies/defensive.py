"""Strategia difensiva — "nel dubbio, fermati".

Come un capitano prudente che ormeggia la nave quando vede la tempesta
in avvicinamento: attivata per i regimi ALTA_VOLATILITÀ e INVERSIONE.
Implementa il principio fondamentale di MONEYMAKER: "Quando hai dubbi, HOLD."

Questa strategia restituisce quasi sempre HOLD. Genera un segnale solo
in condizioni estremamente rare e non ambigue (intenzionalmente difficili
da raggiungere) — la sicurezza prima di tutto.

Rif: Doc 07, Sezione 5.3 — Strategia Difensiva / Principio Fail-Safe.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from moneymaker_common.enums import Direction

from algo_engine.strategies.base import SignalSuggestion, TradingStrategy


class DefensiveStrategy(TradingStrategy):
    """Strategia difensiva che sceglie HOLD in condizioni incerte — il "capitano prudente"."""

    @property
    def name(self) -> str:
        return "defensive_v1"

    def analyze(self, features: dict[str, Any]) -> SignalSuggestion:
        """Analisi difensiva — restituisce quasi sempre HOLD.

        In condizioni di alta volatilità o inversione, l'azione più
        sicura è l'inazione. Come una nave che resta al porto durante
        la tempesta anziché rischiare di affondare.

        Args:
            features: Dizionario indicatori dalla FeaturePipeline.

        Returns:
            SignalSuggestion — HOLD in praticamente tutti i casi.
        """
        adx = features.get("adx", Decimal("0"))
        atr = features.get("atr", Decimal("0"))
        rsi = features.get("rsi", Decimal("50"))

        return SignalSuggestion(
            direction=Direction.HOLD,
            confidence=Decimal("0.80"),
            reasoning=(
                f"Difensiva HOLD: regime volatile/inversione "
                f"(ADX={adx:.1f}, ATR={atr:.2f}, RSI={rsi:.1f})"
            ),
            metadata={"strategy": "defensive", "reason": "fail_safe"},
        )
