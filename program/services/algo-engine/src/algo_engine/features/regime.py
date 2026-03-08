"""Classificatore di regime di mercato basato su regole.

Come un meteorologo che guarda gli strumenti e dice "oggi piove" o
"oggi c'è il sole": analizza gli indicatori tecnici e classifica
le condizioni di mercato in uno dei cinque regimi. L'etichetta del
regime guida la selezione della strategia tramite il RegimeRouter.

Priorità di classificazione (dalla più alta):
1. ALTA_VOLATILITÀ — ATR > 2× media mobile ATR (tempesta)
2. TREND_RIALZISTA — ADX > 25 E EMA veloce > EMA lenta (vento forte da sud)
3. TREND_RIBASSISTA — ADX > 25 E EMA veloce < EMA lenta (vento forte da nord)
4. INVERSIONE — ADX in calo da >40 E RSI estremo (cambio di stagione)
5. LATERALE — default (ADX < 20, bande strette, calma piatta)

Rif: Doc 07, Sezione 4.2 — Euristiche di Rilevamento Regime.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.enums import MarketRegime
from moneymaker_common.logging import get_logger

logger = get_logger(__name__)

# Soglie — le "tacche" sugli strumenti del meteorologo
_ADX_TRENDING_THRESHOLD = Decimal("25")
_ADX_STRONG_TREND_THRESHOLD = Decimal("40")
_ADX_RANGING_THRESHOLD = Decimal("20")
_ATR_VOLATILITY_MULTIPLIER = Decimal("2")
_RSI_OVERBOUGHT = Decimal("70")
_RSI_OVERSOLD = Decimal("30")
_TWO = Decimal("2")

# Hysteresis thresholds — prevent regime flip-flopping
_ADX_ENTER_TREND = Decimal("27")    # ADX must exceed this to enter trending
_ADX_EXIT_TREND = Decimal("23")     # ADX must drop below this to exit trending
_ATR_ENTER_VOLATILITY = Decimal("2.0")   # ATR ratio to enter high volatility
_ATR_EXIT_VOLATILITY = Decimal("1.5")    # ATR ratio to exit high volatility
_HYSTERESIS_BARS = 3  # Consecutive bars required to confirm regime change

# Confidence formula constants for trending regimes.
# Formula: conf = clamp(BASE + ADX/DIVISOR, BASE, CAP)
# Rationale: ADX measures trend strength on a 0-100 scale.
#   - ADX=25 (threshold) → conf = 0.50 + 0.25 = 0.75
#   - ADX=40 (strong)    → conf = 0.50 + 0.40 = 0.90 (capped)
# Base 0.50 ensures minimum confidence when trend is just detected.
# Cap 0.90 prevents overconfidence — even strong ADX can reverse.
_TREND_CONFIDENCE_BASE = Decimal("0.50")
_TREND_CONFIDENCE_DIVISOR = Decimal("100")
_TREND_CONFIDENCE_CAP = Decimal("0.90")


@dataclass
class RegimeClassification:
    """Risultato della classificazione del regime — il "bollettino meteo" del mercato.

    Attributi:
        regime: Il regime di mercato rilevato.
        confidence: Fiducia nella classificazione [0, 1].
        reasoning: Spiegazione leggibile.
        adx: Valore ADX usato per la classificazione.
        atr_ratio: Rapporto ATR attuale / ATR medio.
    """

    regime: MarketRegime
    confidence: Decimal
    reasoning: str
    adx: Decimal
    atr_ratio: Decimal


class RegimeClassifier:
    """Classifica il regime di mercato dai dizionari di indicatori — il "meteorologo".

    Mantiene una finestra mobile di valori ATR per calcolare l'ATR
    medio necessario al rilevamento della volatilità.

    Utilizzo:
        classifier = RegimeClassifier()
        classification = classifier.classify(features)
    """

    def __init__(self, atr_window: int = 50) -> None:
        """Inizializza il classificatore di regime.

        Args:
            atr_window: Numero di osservazioni ATR da mediare per
                        il rilevamento della volatilità.
        """
        self._atr_history: deque[Decimal] = deque(maxlen=atr_window)
        self._prev_adx: Decimal = ZERO
        # Hysteresis state
        self._current_regime: MarketRegime = MarketRegime.RANGING
        self._candidate_regime: MarketRegime | None = None
        self._candidate_count: int = 0

    def classify(self, features: dict[str, Any]) -> RegimeClassification:
        """Classifica il regime di mercato corrente dagli indicatori.

        Uses hysteresis to prevent regime flip-flopping:
        - ADX must exceed 27 to enter trend, drop below 23 to exit
        - ATR ratio must exceed 2.0 to enter high vol, drop below 1.5 to exit
        - Requires 3 consecutive bars confirming a new regime before switching

        Args:
            features: Dizionario indicatori da FeaturePipeline.compute_features().
                      Chiavi attese: adx, atr, ema_fast, ema_slow, rsi,
                      bb_width (opzionale).

        Returns:
            Un RegimeClassification con regime, fiducia e motivazione.
        """
        adx = features.get("adx", ZERO)
        atr = features.get("atr", ZERO)
        rsi = features.get("rsi", ZERO)
        ema_fast = features.get("ema_fast", ZERO)
        ema_slow = features.get("ema_slow", ZERO)

        # Calcola l'ATR medio dalla cronologia PRIMA di aggiungere il valore corrente
        avg_atr = ZERO
        if self._atr_history:
            avg_atr = sum(self._atr_history) / Decimal(str(len(self._atr_history)))

        # Aggiorna la cronologia ATR dopo aver calcolato la media
        if atr > ZERO:
            self._atr_history.append(atr)

        # Rapporto ATR — quanto è "agitato" il mercato rispetto alla norma
        atr_ratio = ZERO
        if avg_atr > ZERO:
            atr_ratio = atr / avg_atr

        # --- Determine raw regime with hysteresis thresholds ---
        raw_regime, confidence, reasoning = self._classify_raw(
            adx, atr, atr_ratio, avg_atr, rsi, ema_fast, ema_slow
        )

        # --- Apply hysteresis: require consecutive confirmations ---
        final_regime = self._apply_hysteresis(raw_regime)

        # Recompute confidence/reasoning if hysteresis overrides
        if final_regime != raw_regime:
            _, confidence, reasoning = self._classify_raw_for_regime(
                final_regime, adx, atr_ratio, rsi, ema_fast, ema_slow
            )

        self._prev_adx = adx

        result = RegimeClassification(
            regime=final_regime,
            confidence=confidence,
            reasoning=reasoning,
            adx=adx,
            atr_ratio=atr_ratio,
        )
        logger.info(
            "Regime classificato",
            regime=result.regime,
            confidence=str(result.confidence),
        )
        return result

    def _apply_hysteresis(self, raw_regime: MarketRegime) -> MarketRegime:
        """Apply hysteresis: require N consecutive bars to confirm regime change."""
        if raw_regime == self._current_regime:
            # Same regime — reset candidate counter
            self._candidate_regime = None
            self._candidate_count = 0
            return self._current_regime

        # Different regime detected
        if raw_regime == self._candidate_regime:
            self._candidate_count += 1
        else:
            self._candidate_regime = raw_regime
            self._candidate_count = 1

        if self._candidate_count >= _HYSTERESIS_BARS:
            # Confirmed: switch regime
            self._current_regime = raw_regime
            self._candidate_regime = None
            self._candidate_count = 0
            return raw_regime

        # Not yet confirmed — stay in current regime
        return self._current_regime

    def _classify_raw(
        self,
        adx: Decimal,
        atr: Decimal,
        atr_ratio: Decimal,
        avg_atr: Decimal,
        rsi: Decimal,
        ema_fast: Decimal,
        ema_slow: Decimal,
    ) -> tuple[MarketRegime, Decimal, str]:
        """Determine raw regime using hysteresis-aware thresholds.

        Returns (regime, confidence, reasoning).
        """
        currently_in = self._current_regime

        # 1. HIGH VOLATILITY — with entry/exit hysteresis
        if avg_atr > ZERO:
            if currently_in == MarketRegime.HIGH_VOLATILITY:
                in_vol = atr_ratio > _ATR_EXIT_VOLATILITY
            else:
                in_vol = atr_ratio > _ATR_ENTER_VOLATILITY
            if in_vol:
                confidence = min(
                    Decimal("0.50") + (atr_ratio - _TWO) * Decimal("0.25"),
                    Decimal("0.95"),
                )
                return (
                    MarketRegime.HIGH_VOLATILITY,
                    max(confidence, Decimal("0.50")),
                    f"Rapporto ATR {atr_ratio:.2f}x supera la soglia",
                )

        # 2/3. TRENDING — with entry/exit hysteresis on ADX
        if ema_slow > ZERO:
            if currently_in in (MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN):
                adx_threshold = _ADX_EXIT_TREND
            else:
                adx_threshold = _ADX_ENTER_TREND

            if adx > adx_threshold:
                confidence = min(
                    _TREND_CONFIDENCE_BASE + adx / _TREND_CONFIDENCE_DIVISOR,
                    _TREND_CONFIDENCE_CAP,
                )
                if ema_fast > ema_slow:
                    return (
                        MarketRegime.TRENDING_UP,
                        confidence,
                        f"ADX={adx:.1f} > {adx_threshold}, EMA veloce > EMA lenta",
                    )
                elif ema_fast < ema_slow:
                    return (
                        MarketRegime.TRENDING_DOWN,
                        confidence,
                        f"ADX={adx:.1f} > {adx_threshold}, EMA veloce < EMA lenta",
                    )

        # 4. REVERSAL — ADX declining from strong + extreme RSI
        if (
            self._prev_adx > _ADX_STRONG_TREND_THRESHOLD
            and adx < self._prev_adx
            and (rsi > _RSI_OVERBOUGHT or rsi < _RSI_OVERSOLD)
        ):
            return (
                MarketRegime.REVERSAL,
                Decimal("0.55"),
                f"ADX in calo da {self._prev_adx:.1f} a {adx:.1f}, RSI={rsi:.1f} estremo",
            )

        # 5. RANGING — default
        confidence = Decimal("0.70") if adx < _ADX_RANGING_THRESHOLD else Decimal("0.60")
        return (
            MarketRegime.RANGING,
            confidence,
            f"ADX={adx:.1f} sotto la soglia di trend, nessun picco di volatilità",
        )

    def _classify_raw_for_regime(
        self,
        regime: MarketRegime,
        adx: Decimal,
        atr_ratio: Decimal,
        rsi: Decimal,
        ema_fast: Decimal,
        ema_slow: Decimal,
    ) -> tuple[MarketRegime, Decimal, str]:
        """Get confidence/reasoning for a specific regime (used when hysteresis overrides)."""
        if regime == MarketRegime.HIGH_VOLATILITY:
            confidence = min(
                Decimal("0.50") + (atr_ratio - _TWO) * Decimal("0.25"),
                Decimal("0.95"),
            )
            return regime, max(confidence, Decimal("0.50")), f"ATR ratio {atr_ratio:.2f}x (stabile)"
        if regime in (MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN):
            confidence = min(
                _TREND_CONFIDENCE_BASE + adx / _TREND_CONFIDENCE_DIVISOR,
                _TREND_CONFIDENCE_CAP,
            )
            direction = "rialzista" if regime == MarketRegime.TRENDING_UP else "ribassista"
            return regime, confidence, f"Trend {direction} stabile (ADX={adx:.1f})"
        if regime == MarketRegime.REVERSAL:
            return regime, Decimal("0.55"), f"Inversione in corso (RSI={rsi:.1f})"
        # RANGING
        confidence = Decimal("0.70") if adx < _ADX_RANGING_THRESHOLD else Decimal("0.60")
        return regime, confidence, f"Laterale stabile (ADX={adx:.1f})"
