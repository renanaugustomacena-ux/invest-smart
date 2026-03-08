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

    def classify(self, features: dict[str, Any]) -> RegimeClassification:
        """Classifica il regime di mercato corrente dagli indicatori.

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

        # --- Catena di priorità della classificazione ---

        # 1. ALTA VOLATILITÀ: ATR > 2× ATR medio — tempesta in arrivo
        if avg_atr > ZERO and atr > _ATR_VOLATILITY_MULTIPLIER * avg_atr:
            confidence = min(
                Decimal("0.50") + (atr_ratio - _TWO) * Decimal("0.25"),
                Decimal("0.95"),
            )
            result = RegimeClassification(
                regime=MarketRegime.HIGH_VOLATILITY,
                confidence=max(confidence, Decimal("0.50")),
                reasoning=f"Rapporto ATR {atr_ratio:.2f}x supera la soglia 2x",
                adx=adx,
                atr_ratio=atr_ratio,
            )
            self._prev_adx = adx
            logger.info(
                "Regime classificato",
                regime=result.regime,
                confidence=str(result.confidence),
            )
            return result

        # 2. TREND RIALZISTA: ADX > 25 E EMA veloce > EMA lenta — vento forte da sud
        if adx > _ADX_TRENDING_THRESHOLD and ema_fast > ema_slow and ema_slow > ZERO:
            confidence = min(_TREND_CONFIDENCE_BASE + adx / _TREND_CONFIDENCE_DIVISOR, _TREND_CONFIDENCE_CAP)
            result = RegimeClassification(
                regime=MarketRegime.TRENDING_UP,
                confidence=confidence,
                reasoning=f"ADX={adx:.1f} > 25, EMA veloce > EMA lenta",
                adx=adx,
                atr_ratio=atr_ratio,
            )
            self._prev_adx = adx
            logger.info(
                "Regime classificato",
                regime=result.regime,
                confidence=str(result.confidence),
            )
            return result

        # 3. TREND RIBASSISTA: ADX > 25 E EMA veloce < EMA lenta — vento forte da nord
        if adx > _ADX_TRENDING_THRESHOLD and ema_fast < ema_slow and ema_slow > ZERO:
            confidence = min(_TREND_CONFIDENCE_BASE + adx / _TREND_CONFIDENCE_DIVISOR, _TREND_CONFIDENCE_CAP)
            result = RegimeClassification(
                regime=MarketRegime.TRENDING_DOWN,
                confidence=confidence,
                reasoning=f"ADX={adx:.1f} > 25, EMA veloce < EMA lenta",
                adx=adx,
                atr_ratio=atr_ratio,
            )
            self._prev_adx = adx
            logger.info(
                "Regime classificato",
                regime=result.regime,
                confidence=str(result.confidence),
            )
            return result

        # 4. INVERSIONE: ADX in calo da trend forte + RSI estremo — cambio di stagione
        if (
            self._prev_adx > _ADX_STRONG_TREND_THRESHOLD
            and adx < self._prev_adx
            and (rsi > _RSI_OVERBOUGHT or rsi < _RSI_OVERSOLD)
        ):
            confidence = Decimal("0.55")
            result = RegimeClassification(
                regime=MarketRegime.REVERSAL,
                confidence=confidence,
                reasoning=(
                    f"ADX in calo da {self._prev_adx:.1f} a {adx:.1f}, "
                    f"RSI={rsi:.1f} a livello estremo"
                ),
                adx=adx,
                atr_ratio=atr_ratio,
            )
            self._prev_adx = adx
            logger.info(
                "Regime classificato",
                regime=result.regime,
                confidence=str(result.confidence),
            )
            return result

        # 5. LATERALE: default — calma piatta, il mercato si muove di lato
        confidence = Decimal("0.60")
        if adx < _ADX_RANGING_THRESHOLD:
            confidence = Decimal("0.70")

        result = RegimeClassification(
            regime=MarketRegime.RANGING,
            confidence=confidence,
            reasoning=f"ADX={adx:.1f} sotto la soglia di trend, nessun picco di volatilità",
            adx=adx,
            atr_ratio=atr_ratio,
        )
        self._prev_adx = adx
        logger.info(
            "Regime classificato", regime=result.regime, confidence=str(result.confidence)
        )
        return result
