# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Classe base astratta per le strategie di trading.

Come il "contratto" che ogni operaio della fabbrica deve rispettare:
ogni strategia di MONEYMAKER implementa questa interfaccia. Il Router
di Regime invia i dizionari di indicatori alla strategia appropriata
in base al regime di mercato rilevato.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from moneymaker_common.enums import Direction


@dataclass
class SignalSuggestion:
    """Un suggerimento di segnale prodotto da una strategia — la "bozza" dell'ordine.

    Output intermedio prima di diventare un TradingSignal completo.
    Il Generatore di Segnali aggiunge prezzo, dimensionamento e parametri di rischio.

    Attributi:
        direction: BUY, SELL o HOLD — la direzione del trade.
        confidence: Decimal in [0, 1] — quanto è sicura la strategia.
        reasoning: Spiegazione leggibile del perché il segnale è stato generato.
        metadata: Dizionario opzionale per dati specifici della strategia.
    """

    direction: str | Direction
    confidence: Decimal
    reasoning: str
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        # Converte stringhe grezze nell'enum Direction per sicurezza dei tipi
        if isinstance(self.direction, str) and not isinstance(self.direction, Direction):
            try:
                self.direction = Direction(self.direction)
            except ValueError as err:
                raise ValueError(
                    f"Direzione non valida '{self.direction}', "
                    f"deve essere una di {[d.value for d in Direction]}"
                ) from err
        if not (Decimal("0") <= self.confidence <= Decimal("1")):
            raise ValueError(f"La confidenza deve essere tra 0 e 1, ricevuto {self.confidence}")


class TradingStrategy(ABC):
    """Classe base astratta per tutte le strategie di trading — il "contratto".

    Le sotto-classi devono implementare:
    - name: Un identificatore univoco per la strategia.
    - analyze: Accetta un dizionario di indicatori e restituisce un SignalSuggestion.

    Esempio:
        class StrategiaMomentum(TradingStrategy):
            @property
            def name(self) -> str:
                return "momentum_v1"

            def analyze(self, features: dict[str, Any]) -> SignalSuggestion:
                rsi = features.get("rsi", Decimal("50"))
                if rsi > Decimal("70"):
                    return SignalSuggestion("SELL", Decimal("0.7"), "RSI ipercomprato")
                elif rsi < Decimal("30"):
                    return SignalSuggestion("BUY", Decimal("0.7"), "RSI ipervenduto")
                return SignalSuggestion("HOLD", Decimal("0.3"), "RSI neutro")
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Identificatore univoco per questa strategia."""
        ...

    @abstractmethod
    def analyze(self, features: dict[str, Any]) -> SignalSuggestion:
        """Analizza gli indicatori e produce un suggerimento di segnale.

        Args:
            features: Dizionario di indicatori tecnici calcolati dalla FeaturePipeline.

        Returns:
            Un SignalSuggestion con direzione, confidenza e motivazione.
        """
        ...
