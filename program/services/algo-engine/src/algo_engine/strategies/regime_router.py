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

        logger.info(
            "Analisi strategica completata",
            regime=regime,
            strategy=strategy.name,
            direction=suggestion.direction,
            confidence=str(suggestion.confidence),
            reasoning=suggestion.reasoning,
        )

        return suggestion
