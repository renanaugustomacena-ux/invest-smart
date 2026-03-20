# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Router di strategie basato sul regime di mercato.

Come uno scambio ferroviario: quando il classificatore di regime identifica
le condizioni di mercato (sole, pioggia, tempesta), il router indirizza
il treno (dati) sul binario giusto (strategia appropriata).

Regimi supportati:
- "trending_up":   Trend rialzista forte — binario del trend-following
- "trending_down": Trend ribassista forte — binario del trend-following
- "ranging":       Mercato laterale — binario della mean-reversion
- "volatile":      Alta volatilità — binario difensivo
- "default":       Fallback quando nessun regime è rilevato
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from moneymaker_common.enums import Direction
from moneymaker_common.logging import get_logger

from algo_engine.strategies.base import SignalSuggestion, TradingStrategy

logger = get_logger(__name__)


class RegimeRouter:
    """Instrada i dizionari di indicatori alle strategie specifiche per regime.

    Come il capostazione che decide su quale binario mandare ogni treno.

    Utilizzo:
        router = RegimeRouter()
        router.register_strategy("trending_up", strategia_momentum)
        router.register_strategy("ranging", strategia_mean_reversion)

        suggerimento = router.route("trending_up", features)
    """

    def __init__(self) -> None:
        self._strategies: dict[str, TradingStrategy] = {}
        self._default_strategy: TradingStrategy | None = None

    def register_strategy(self, regime: str, strategy: TradingStrategy) -> None:
        """Registra una strategia per un regime di mercato specifico.

        Args:
            regime: L'etichetta del regime (es. "trending_up", "ranging").
            strategy: L'istanza TradingStrategy da usare per questo regime.
        """
        self._strategies[regime] = strategy
        logger.info(
            "Strategia registrata",
            regime=regime,
            strategy=strategy.name,
        )

    def set_default_strategy(self, strategy: TradingStrategy) -> None:
        """Imposta la strategia di ripiego per regimi non riconosciuti.

        Args:
            strategy: L'istanza TradingStrategy da usare come fallback.
        """
        self._default_strategy = strategy
        logger.info("Strategia predefinita impostata", strategy=strategy.name)

    def get_registered_regimes(self) -> list[str]:
        """Restituisce l'elenco di tutti i regimi registrati."""
        return list(self._strategies.keys())

    def route(self, regime: str, features: dict[str, Any]) -> SignalSuggestion:
        """Instrada gli indicatori alla strategia appropriata in base al regime.

        Se nessuna strategia è registrata per il regime dato, usa la
        strategia predefinita. Se nemmeno quella è impostata, restituisce
        HOLD con confidenza zero — nel dubbio, fermati.

        Args:
            regime: L'etichetta del regime di mercato rilevato.
            features: Dizionario di indicatori tecnici calcolati.

        Returns:
            Un SignalSuggestion dalla strategia selezionata.
        """
        strategy = self._strategies.get(regime)

        if strategy is None:
            if self._default_strategy is not None:
                logger.warning(
                    "Nessuna strategia per il regime, uso il default",
                    regime=regime,
                    default_strategy=self._default_strategy.name,
                )
                strategy = self._default_strategy
            else:
                logger.warning(
                    "Nessuna strategia registrata e nessun default, restituisco HOLD",
                    regime=regime,
                )
                return SignalSuggestion(
                    direction=Direction.HOLD,
                    confidence=Decimal("0"),
                    reasoning=f"Nessuna strategia registrata per il regime '{regime}'",
                )

        logger.debug(
            "Instradamento alla strategia",
            regime=regime,
            strategy=strategy.name,
            symbol=features.get("symbol", "sconosciuto"),
        )

        suggestion = strategy.analyze(features)

        # Inject strategy name into metadata for attribution
        if suggestion.metadata is None:
            suggestion.metadata = {}
        suggestion.metadata.setdefault("strategy", strategy.name)

        logger.info(
            "Analisi strategica completata",
            regime=regime,
            strategy=strategy.name,
            direction=suggestion.direction,
            confidence=str(suggestion.confidence),
            reasoning=suggestion.reasoning,
        )

        return suggestion

    def route_probabilistic(
        self, regime_posteriors: dict[str, Decimal], features: dict[str, Any]
    ) -> SignalSuggestion:
        """Route using Bayesian regime posterior probabilities.

        Instead of hard-selecting one regime's strategy, queries all strategies
        whose regime has non-trivial posterior probability and produces a
        weighted consensus signal.

        Args:
            regime_posteriors: {regime_name: posterior_probability} from
                BayesianRegimeDetector. Probabilities should sum to ~1.
            features: Technical indicator dictionary.

        Returns:
            Weighted consensus SignalSuggestion.
        """
        _MIN_POSTERIOR = Decimal("0.10")

        # Collect suggestions from all regimes with meaningful probability
        weighted_suggestions: list[tuple[Decimal, SignalSuggestion]] = []
        for regime, posterior in regime_posteriors.items():
            if posterior < _MIN_POSTERIOR:
                continue
            strategy = self._strategies.get(regime)
            if strategy is None:
                continue
            suggestion = strategy.analyze(features)
            weighted_suggestions.append((posterior, suggestion))

        if not weighted_suggestions:
            # Fallback to default or HOLD
            if self._default_strategy:
                return self._default_strategy.analyze(features)
            return SignalSuggestion(
                direction=Direction.HOLD,
                confidence=Decimal("0"),
                reasoning="No regime has sufficient posterior probability",
            )

        # Compute weighted directional score: BUY=+1, SELL=-1, HOLD=0
        total_weight = Decimal("0")
        directional_score = Decimal("0")
        blended_confidence = Decimal("0")
        reasoning_parts: list[str] = []

        for weight, suggestion in weighted_suggestions:
            total_weight += weight
            if suggestion.direction == Direction.BUY:
                directional_score += weight * suggestion.confidence
            elif suggestion.direction == Direction.SELL:
                directional_score -= weight * suggestion.confidence
            blended_confidence += weight * suggestion.confidence

            strategy_name = (
                suggestion.metadata.get("strategy", "unknown") if suggestion.metadata else "unknown"
            )
            reasoning_parts.append(f"{strategy_name}({weight:.0%})→{suggestion.direction}")

        if total_weight > Decimal("0"):
            directional_score /= total_weight
            blended_confidence /= total_weight

        # Determine consensus direction
        if abs(directional_score) < Decimal("0.10"):
            direction = Direction.HOLD
            final_confidence = Decimal("0.30")
        elif directional_score > Decimal("0"):
            direction = Direction.BUY
            final_confidence = min(blended_confidence, Decimal("0.85"))
        else:
            direction = Direction.SELL
            final_confidence = min(blended_confidence, Decimal("0.85"))

        result = SignalSuggestion(
            direction=direction,
            confidence=final_confidence,
            reasoning=f"Probabilistic consensus: {', '.join(reasoning_parts)}",
            metadata={
                "strategy": "probabilistic_router",
                "directional_score": str(directional_score),
                "regime_posteriors": {k: str(v) for k, v in regime_posteriors.items()},
            },
        )

        logger.info(
            "Probabilistic routing completed",
            direction=str(direction),
            confidence=str(final_confidence),
            directional_score=str(directional_score),
            n_strategies=len(weighted_suggestions),
        )

        return result
