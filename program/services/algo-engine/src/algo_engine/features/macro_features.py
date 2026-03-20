# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Macro Feature Provider — "i sensori macroeconomici".

Fornisce feature macro-economiche quantitative per il vettore di input 60-dim.
Dati provenienti dal servizio external-data via Redis cache.

Feature Macro (indici 40-49 del vettore):
- 40: vix_spot - VIX index value
- 41: vix_regime - 0=calm, 1=elevated, 2=panic
- 42: vix_contango - 1 se contango (normale), 0 se backwardation
- 43: yield_slope_2s10s - Spread 10Y-2Y Treasury
- 44: curve_inverted - 1 se curva invertita
- 45: recession_prob - Probabilità recessione a 12 mesi
- 46: dxy_change_1h_pct - Variazione % DXY ultima ora
- 47: real_rate_10y - Tasso reale 10Y (nominale - inflazione attesa)
- 48: cot_asset_mgr_pct_oi - % Open Interest gestori Gold
- 49: cot_sentiment - Sentiment COT: -1/0/1

Principi di design:
- Solo dati quantitativi, deterministici, verificabili
- Nessun sentiment soggettivo o derivato da news
- Fallback sicuro a valori neutri se dati non disponibili
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from moneymaker_common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MacroFeatures:
    """Container per le feature macro."""

    # VIX
    vix_spot: float = 15.0  # Default: calm market
    vix_regime: int = 0  # 0=calm, 1=elevated, 2=panic
    vix_contango: int = 1  # 1=contango (normale)

    # Yield Curve
    yield_slope_2s10s: float = 0.5  # Default: normal positive slope
    curve_inverted: int = 0  # 0=not inverted

    # Recession
    recession_prob: float = 0.15  # Default: low probability

    # DXY
    dxy_change_1h_pct: float = 0.0  # Default: no change

    # Real Rates
    real_rate_10y: float = 0.5  # Default: slightly positive

    # COT
    cot_asset_mgr_pct_oi: float = 10.0  # Default: moderate
    cot_sentiment: int = 0  # -1=bearish, 0=neutral, 1=bullish

    # Metadata
    data_age_seconds: float = 0.0
    data_stale: bool = False

    def to_vector(self) -> list[float]:
        """Converte in vettore per input ML.

        Returns:
            Lista di 10 valori float normalizzati
        """
        return [
            self._normalize_vix(self.vix_spot),
            float(self.vix_regime) / 2.0,  # 0-1 range
            float(self.vix_contango),
            self._normalize_spread(self.yield_slope_2s10s),
            float(self.curve_inverted),
            self._normalize_prob(self.recession_prob),
            self._normalize_pct_change(self.dxy_change_1h_pct),
            self._normalize_rate(self.real_rate_10y),
            self._normalize_pct_oi(self.cot_asset_mgr_pct_oi),
            (float(self.cot_sentiment) + 1.0) / 2.0,  # -1,0,1 -> 0,0.5,1
        ]

    def _normalize_vix(self, vix: float) -> float:
        """Normalizza VIX a range 0-1.

        VIX range tipico: 10-80
        """
        return min(max((vix - 10) / 70, 0.0), 1.0)

    def _normalize_spread(self, spread: float) -> float:
        """Normalizza spread yield curve.

        Range tipico: -1.0 a +3.0
        """
        return min(max((spread + 1.0) / 4.0, 0.0), 1.0)

    def _normalize_prob(self, prob: float) -> float:
        """Normalizza probabilità (già 0-100)."""
        return min(max(prob / 100.0, 0.0), 1.0)

    def _normalize_pct_change(self, pct: float) -> float:
        """Normalizza variazione percentuale.

        Range tipico: -2% a +2%
        """
        return min(max((pct + 2.0) / 4.0, 0.0), 1.0)

    def _normalize_rate(self, rate: float) -> float:
        """Normalizza tasso reale.

        Range tipico: -2% a +3%
        """
        return min(max((rate + 2.0) / 5.0, 0.0), 1.0)

    def _normalize_pct_oi(self, pct_oi: float) -> float:
        """Normalizza % open interest.

        Range tipico: 0-30%
        """
        return min(max(pct_oi / 30.0, 0.0), 1.0)


class MacroFeatureProvider:
    """Provider per feature macroeconomiche da Redis cache."""

    # Keys Redis usate dal servizio external-data
    REDIS_KEYS = {
        "vix": "macro:vix",
        "yield_curve": "macro:yield_curve",
        "real_rates": "macro:real_rates",
        "recession": "macro:recession",
        "dxy": "macro:dxy",
        "cot_gold": "macro:cot:gold",
    }

    # Tempo massimo per considerare i dati freschi
    MAX_DATA_AGE_SECONDS = 600  # 10 minuti per VIX
    MAX_YIELD_AGE_SECONDS = 7200  # 2 ore per yield
    MAX_COT_AGE_SECONDS = 604800  # 7 giorni per COT (settimanale)

    def __init__(self, redis_client: Any | None = None) -> None:
        """Inizializza il provider.

        Args:
            redis_client: Client Redis asincrono opzionale
        """
        self.redis = redis_client
        self._cache: dict[str, tuple[dict, datetime]] = {}
        self._last_features: MacroFeatures | None = None

    async def get_features(self, symbol: str = "XAU/USD") -> MacroFeatures:
        """Recupera feature macro correnti.

        Args:
            symbol: Simbolo trading (per COT specifico)

        Returns:
            MacroFeatures con valori correnti o default
        """
        features = MacroFeatures()
        now = datetime.now(timezone.utc)
        oldest_update = now

        # Se Redis non disponibile, usa cache locale o default
        if self.redis is None:
            logger.debug("Redis non disponibile, usando default")
            return self._last_features or features

        try:
            # Fetch VIX
            vix_data = await self._get_redis_json("vix")
            if vix_data:
                features.vix_spot = float(vix_data.get("spot", 15.0))
                features.vix_regime = int(vix_data.get("regime", 0))
                features.vix_contango = 1 if vix_data.get("contango", True) else 0
                oldest_update = min(oldest_update, self._parse_timestamp(vix_data))

            # Fetch Yield Curve
            yield_data = await self._get_redis_json("yield_curve")
            if yield_data:
                spread = yield_data.get("spread_2s10s")
                if spread is not None:
                    features.yield_slope_2s10s = float(spread)
                features.curve_inverted = 1 if yield_data.get("inverted", False) else 0
                oldest_update = min(oldest_update, self._parse_timestamp(yield_data))

            # Fetch Real Rates
            rates_data = await self._get_redis_json("real_rates")
            if rates_data:
                real_rate = rates_data.get("real_rate_10y")
                if real_rate is not None:
                    features.real_rate_10y = float(real_rate)

            # Fetch Recession Probability
            recession_data = await self._get_redis_json("recession")
            if recession_data:
                prob = recession_data.get("probability_12m")
                if prob is not None:
                    features.recession_prob = float(prob)

            # Fetch DXY
            dxy_data = await self._get_redis_json("dxy")
            if dxy_data:
                change = dxy_data.get("change_1h_pct")
                if change is not None:
                    features.dxy_change_1h_pct = float(change)

            # Fetch COT (Gold specific)
            cot_data = await self._get_redis_json("cot_gold")
            if cot_data:
                pct_oi = cot_data.get("asset_mgr_pct_oi")
                if pct_oi is not None:
                    features.cot_asset_mgr_pct_oi = float(pct_oi)
                features.cot_sentiment = int(cot_data.get("sentiment", 0))

            # Calcola età dati
            features.data_age_seconds = (now - oldest_update).total_seconds()
            features.data_stale = features.data_age_seconds > self.MAX_DATA_AGE_SECONDS

            self._last_features = features

            logger.debug(
                "Macro features loaded",
                vix=features.vix_spot,
                vix_regime=features.vix_regime,
                yield_inverted=features.curve_inverted,
                data_age=features.data_age_seconds,
            )

        except Exception as e:
            logger.error("Error fetching macro features", error=str(e))
            # Return cached or default
            return self._last_features or features

        return features

    async def _get_redis_json(self, key_name: str) -> dict | None:
        """Recupera e parsa JSON da Redis.

        Args:
            key_name: Nome chiave (da REDIS_KEYS)

        Returns:
            Dict parsato o None
        """
        full_key = self.REDIS_KEYS.get(key_name)
        if not full_key or self.redis is None:
            return None

        try:
            data = await self.redis.get(full_key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.debug(f"Redis get failed for {key_name}", error=str(e))

        return None

    def _parse_timestamp(self, data: dict) -> datetime:
        """Parsa timestamp da dati Redis.

        Args:
            data: Dict con campo updated_at

        Returns:
            datetime parsed o now
        """
        updated_at = data.get("updated_at")
        if updated_at:
            try:
                return datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass
        return datetime.now(timezone.utc)

    def get_feature_names(self) -> list[str]:
        """Restituisce nomi delle feature macro.

        Returns:
            Lista di nomi feature
        """
        return [
            "vix_spot",
            "vix_regime",
            "vix_contango",
            "yield_slope_2s10s",
            "curve_inverted",
            "recession_prob",
            "dxy_change_1h_pct",
            "real_rate_10y",
            "cot_asset_mgr_pct_oi",
            "cot_sentiment",
        ]

    def is_gold_bullish_environment(self, features: MacroFeatures) -> bool:
        """Valuta se l'ambiente macro è bullish per Gold.

        Fattori bullish per Gold:
        - VIX alto (panico)
        - Curva yield invertita (recessione)
        - Tassi reali negativi
        - COT sentiment bullish

        Args:
            features: MacroFeatures correnti

        Returns:
            True se ambiente bullish per Gold
        """
        bullish_signals = 0

        # VIX panic
        if features.vix_regime >= 2:
            bullish_signals += 2
        elif features.vix_regime == 1:
            bullish_signals += 1

        # Curva invertita
        if features.curve_inverted:
            bullish_signals += 1

        # Tassi reali negativi
        if features.real_rate_10y < 0:
            bullish_signals += 2
        elif features.real_rate_10y < 0.5:
            bullish_signals += 1

        # DXY in calo
        if features.dxy_change_1h_pct < -0.2:
            bullish_signals += 1

        # COT bullish
        if features.cot_sentiment > 0:
            bullish_signals += 1

        # 4+ segnali = bullish
        return bullish_signals >= 4

    def is_high_risk_environment(self, features: MacroFeatures) -> bool:
        """Valuta se l'ambiente è ad alto rischio (volatilità).

        Args:
            features: MacroFeatures correnti

        Returns:
            True se ambiente ad alto rischio
        """
        # VIX panic mode
        if features.vix_regime >= 2:
            return True

        # Curva profondamente invertita
        if features.yield_slope_2s10s < -0.5:
            return True

        # Alta probabilità recessione
        if features.recession_prob > 40:
            return True

        return False
