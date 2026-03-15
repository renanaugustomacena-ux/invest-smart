"""Session-Aware Trading — il "fuso orario" del mercato forex.

Il mercato forex ha personalità diverse in base all'ora del giorno:
- Asian session: calmo, laterale, spread ampi
- London session: volatile, trend, spread stretti
- US session: alta liquidità, movimenti direzionali
- Overlap London/US: massima liquidità, miglior momento per tradare

Utilizzo:
    classifier = SessionClassifier()
    session = classifier.classify(utc_hour=14)
    # → TradingSession.LONDON_US_OVERLAP
"""

from __future__ import annotations

from enum import Enum


class TradingSession(str, Enum):
    """Sessioni di trading del mercato forex."""

    ASIAN = "asian"
    LONDON = "london"
    US = "us"
    LONDON_US_OVERLAP = "london_us_overlap"
    OFF_HOURS = "off_hours"


# Caratteristiche per sessione: aggiustamento confidenza e limiti
SESSION_CONFIGS: dict[TradingSession, dict] = {
    TradingSession.ASIAN: {
        "confidence_boost": -0.05,  # Richiedi +5% confidenza (mercato tranquillo, falsi segnali)
        "description": "00:00-08:00 UTC — sessione calma, range trading",
    },
    TradingSession.LONDON: {
        "confidence_boost": 0.0,  # Nessun aggiustamento
        "description": "08:00-13:00 UTC — alta volatilità, trend forti",
    },
    TradingSession.LONDON_US_OVERLAP: {
        "confidence_boost": 0.05,  # Permetti -5% confidenza (alta liquidità)
        "description": "13:00-16:00 UTC — massima liquidità, spread minimi",
    },
    TradingSession.US: {
        "confidence_boost": 0.0,  # Nessun aggiustamento
        "description": "16:00-21:00 UTC — buona liquidità, movimenti direzionali",
    },
    TradingSession.OFF_HOURS: {
        "confidence_boost": -0.10,  # Richiedi +10% confidenza (poca liquidità)
        "description": "21:00-00:00 UTC — bassa liquidità, evitare se possibile",
    },
}


class SessionClassifier:
    """Classifica l'ora corrente in una sessione di trading."""

    def classify(self, utc_hour: int) -> TradingSession:
        """Determina la sessione di trading dall'ora UTC.

        Args:
            utc_hour: Ora UTC corrente (0-23).

        Returns:
            La sessione di trading attiva.
        """
        if 0 <= utc_hour < 8:
            return TradingSession.ASIAN
        if 8 <= utc_hour < 13:
            return TradingSession.LONDON
        if 13 <= utc_hour < 16:
            return TradingSession.LONDON_US_OVERLAP
        if 16 <= utc_hour < 21:
            return TradingSession.US
        return TradingSession.OFF_HOURS

    def get_confidence_boost(self, session: TradingSession) -> float:
        """Restituisce l'aggiustamento di confidenza per la sessione."""
        config = SESSION_CONFIGS.get(session, {})
        return config.get("confidence_boost", 0.0)
