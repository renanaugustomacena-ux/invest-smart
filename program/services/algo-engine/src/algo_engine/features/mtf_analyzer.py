# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Multi-Timeframe Analyzer — osservare il mercato da più angolazioni.

Come guardare una mappa a diversi livelli di zoom: M5 per i dettagli,
H1 per il contesto. Un segnale che allinea timeframe multipli è
significativamente più affidabile di uno basato su un singolo TF.

Il Data Ingestion (Go) pubblica barre su M1/M5/M15/H1 con topic
``bar.SYMBOL.TIMEFRAME``. Questo modulo mantiene buffer separati
per ogni timeframe e produce feature combinate quando il TF primario
ha abbastanza dati.

Utilizzo:
    mtf = MultiTimeframeAnalyzer(primary_tf="M5")
    features = mtf.add_bar(symbol, timeframe, bar)
    if features:
        # features contiene indicatori M5 + contesto H1/M15
        ...
"""

from __future__ import annotations

from collections import deque

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.logging import get_logger

from algo_engine.features.pipeline import FeaturePipeline, OHLCVBar

logger = get_logger(__name__)

# Barre minime per ogni timeframe prima che la pipeline si attivi
MIN_BARS: dict[str, int] = {
    "M1": 100,
    "M5": 50,
    "M15": 30,
    "H1": 20,
    "H4": 15,
    "D1": 10,
}

WINDOW_SIZES: dict[str, int] = {
    "M1": 500,
    "M5": 250,
    "M15": 150,
    "H1": 100,
    "H4": 60,
    "D1": 50,
}


class MultiTimeframeAnalyzer:
    """Mantiene buffer e pipeline per multipli timeframe."""

    def __init__(
        self,
        primary_tf: str = "M5",
        timeframes: list[str] | None = None,
        rsi_period: int = 14,
        ema_fast_period: int = 12,
        ema_slow_period: int = 26,
        bb_period: int = 20,
        atr_period: int = 14,
    ) -> None:
        self._primary_tf = primary_tf
        self._timeframes = timeframes or ["M5", "M15", "H1"]

        # Buffer separato per ogni (symbol, timeframe)
        self._buffers: dict[str, dict[str, deque]] = {}

        # Pipeline indicatori (condivisa, i parametri sono gli stessi)
        self._pipeline = FeaturePipeline(
            rsi_period=rsi_period,
            ema_fast_period=ema_fast_period,
            ema_slow_period=ema_slow_period,
            bb_period=bb_period,
            atr_period=atr_period,
        )

        # Cache delle ultime feature per TF superiori
        self._htf_features: dict[str, dict[str, dict]] = {}

    def add_bar(self, symbol: str, timeframe: str, bar: OHLCVBar) -> dict | None:
        """Aggiunge una barra al buffer del timeframe appropriato.

        Returns:
            Feature dict combinato (multi-TF) quando il TF primario ha
            abbastanza dati, altrimenti None.
        """
        if timeframe not in self._timeframes:
            return None

        # Assicura buffer per questo symbol
        if symbol not in self._buffers:
            self._buffers[symbol] = {}
            self._htf_features[symbol] = {}

        if timeframe not in self._buffers[symbol]:
            window = WINDOW_SIZES.get(timeframe, 250)
            self._buffers[symbol][timeframe] = deque(maxlen=window)

        self._buffers[symbol][timeframe].append(bar)
        buf = self._buffers[symbol][timeframe]
        min_needed = MIN_BARS.get(timeframe, 50)

        # Calcola feature per questo TF se ha abbastanza barre
        if len(buf) >= min_needed:
            features = self._pipeline.compute_features(f"{symbol}_{timeframe}", list(buf))
            if features and timeframe != self._primary_tf:
                # Salva feature HTF per arricchire il TF primario
                self._htf_features[symbol][timeframe] = features

        # Restituisci feature combinate solo quando arriva una barra del TF primario
        if timeframe != self._primary_tf:
            return None

        primary_buf = self._buffers[symbol].get(self._primary_tf)
        if primary_buf is None or len(primary_buf) < min_needed:
            return None

        # Calcola feature primarie
        primary_features = self._pipeline.compute_features(symbol, list(primary_buf))
        if not primary_features:
            return None

        # Arricchisci con contesto HTF
        return self._enrich_with_htf(symbol, primary_features)

    def _enrich_with_htf(self, symbol: str, primary: dict) -> dict:
        """Aggiunge feature dai timeframe superiori al dict primario."""
        htf_data = self._htf_features.get(symbol, {})

        for tf, features in htf_data.items():
            prefix = tf.lower()  # es. "h1", "m15"

            # Trend direction dal TF superiore
            ema_fast = features.get("ema_fast", ZERO)
            ema_slow = features.get("ema_slow", ZERO)
            if ema_fast > ZERO and ema_slow > ZERO:
                primary[f"{prefix}_trend"] = "bullish" if ema_fast > ema_slow else "bearish"
            else:
                primary[f"{prefix}_trend"] = "neutral"

            # ADX dal TF superiore (forza del trend)
            adx = features.get("adx", ZERO)
            primary[f"{prefix}_adx"] = adx

            # RSI dal TF superiore (contesto OB/OS)
            rsi = features.get("rsi", ZERO)
            primary[f"{prefix}_rsi"] = rsi

            # ATR dal TF superiore (volatilità macro)
            atr = features.get("atr", ZERO)
            primary[f"{prefix}_atr"] = atr

        # Flag di allineamento multi-TF
        h1_trend = primary.get("h1_trend", "neutral")
        primary_ema_fast = primary.get("ema_fast", ZERO)
        primary_ema_slow = primary.get("ema_slow", ZERO)
        primary_trend = "bullish" if primary_ema_fast > primary_ema_slow else "bearish"

        primary["mtf_aligned"] = h1_trend == primary_trend
        primary["primary_timeframe"] = self._primary_tf

        return primary

    def bar_count(self, symbol: str, timeframe: str) -> int:
        """Numero di barre nel buffer per symbol+timeframe."""
        buf = self._buffers.get(symbol, {}).get(timeframe)
        return len(buf) if buf else 0
