"""Enum di dominio per MONEYMAKER V1.

Come i "segnali stradali" del sistema: ogni modulo del progetto
riconosce questi valori e sa cosa significano. Rispecchiano le
definizioni enum nei file protobuf e le estendono con classificazioni
di regime e trend lato Python.

L'ereditarietà (str, Enum) garantisce la retrocompatibilità con
i confronti stringa esistenti: Direction.BUY == "BUY"  # True
"""

from __future__ import annotations

from enum import Enum


class Direction(str, Enum):
    """Direzione del trade — il "semaforo" del segnale. Rispecchia l'enum proto Direction."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class MarketRegime(str, Enum):
    """Classificazione del regime di mercato — le "condizioni meteo".

    Rif: Doc 07, Sezione 4.1 — I Quattro Regimi.
    """

    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    HIGH_VOLATILITY = "high_volatility"
    REVERSAL = "reversal"


class TrendDirection(str, Enum):
    """Classificazione del trend basata su EMA — la "bussola" della pipeline indicatori."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


class SourceTier(str, Enum):
    """Livello della fonte decisionale — la "gerarchia" delle fonti. Rispecchia l'enum proto."""

    STATISTICAL_PRIMARY = "statistical_primary"
    TECHNICAL = "technical"
    SENTIMENT = "sentiment"
    RULE_BASED = "rule_based"
