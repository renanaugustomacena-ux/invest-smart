"""Pipeline di calcolo indicatori tecnici per l'Algo Engine di Trading.

Come un laboratorio di analisi: prende le candele OHLCV grezze
(i "campioni di sangue" del mercato) e produce un dizionario di
indicatori tecnici ("i risultati delle analisi") che vengono
consumati dal Router Strategia.

Tutti i calcoli sui prezzi usano Decimal per evitare errori
di arrotondamento IEEE 754 — precisione chirurgica nei calcoli finanziari.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.enums import TrendDirection
from moneymaker_common.logging import get_logger

from algo_engine.features.technical import (
    calculate_adx,
    calculate_atr,
    calculate_bollinger_bands,
    calculate_cci,
    calculate_cmf,
    calculate_dema,
    calculate_donchian_channels,
    calculate_ema,
    calculate_force_index,
    calculate_historical_volatility,
    calculate_keltner_channels,
    calculate_macd,
    calculate_obv,
    calculate_parabolic_sar,
    calculate_parkinson_volatility,
    calculate_roc,
    calculate_rsi,
    calculate_sma,
    calculate_stochastic,
    calculate_stochastic_rsi,
    calculate_ultimate_oscillator,
    calculate_vwap,
    calculate_williams_r,
)

# Import opzionale per macro features (può fallire se Redis non disponibile)
try:
    from algo_engine.features.macro_features import MacroFeatureProvider, MacroFeatures
    MACRO_FEATURES_AVAILABLE = True
except ImportError:
    MACRO_FEATURES_AVAILABLE = False
    MacroFeatureProvider = None
    MacroFeatures = None

logger = get_logger(__name__)


@dataclass
class OHLCVBar:
    """Una singola candela OHLCV (Apertura, Massimo, Minimo, Chiusura, Volume)."""

    timestamp: int  # Timestamp Unix in millisecondi
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


class FeaturePipeline:
    """Calcola gli indicatori tecnici dalle candele OHLCV grezze.

    Come una catena di test in laboratorio: estrae i prezzi di chiusura,
    massimi e minimi, poi esegue ogni calcolo di indicatore tecnico.
    I risultati vengono restituiti in un dizionario piatto, pronto
    per l'uso da parte dei moduli a valle.

    Utilizzo:
        pipeline = FeaturePipeline()
        features = pipeline.compute_features("XAUUSD", bars)
    """

    def __init__(
        self,
        rsi_period: int = 14,
        ema_fast_period: int = 12,
        ema_slow_period: int = 26,
        sma_period: int = 20,
        bb_period: int = 20,
        atr_period: int = 14,
        adx_period: int = 14,
        stoch_k_period: int = 14,
        stoch_d_period: int = 3,
        donchian_period: int = 20,
        cci_period: int = 20,
        volume_sma_period: int = 20,
        sma_long_period: int = 200,
        dema_period: int = 20,
        keltner_ema_period: int = 20,
        keltner_atr_period: int = 14,
        keltner_multiplier: int = 2,
        cmf_period: int = 20,
        stoch_rsi_period: int = 14,
        uo_period1: int = 7,
        uo_period2: int = 14,
        uo_period3: int = 28,
        hist_vol_period: int = 20,
        parkinson_vol_period: int = 20,
        force_index_period: int = 13,
        redis_client: Any = None,
    ) -> None:
        self.rsi_period = rsi_period
        self.ema_fast_period = ema_fast_period
        self.ema_slow_period = ema_slow_period
        self.sma_period = sma_period
        self.bb_period = bb_period
        self.atr_period = atr_period
        self.adx_period = adx_period
        self.stoch_k_period = stoch_k_period
        self.stoch_d_period = stoch_d_period
        self.donchian_period = donchian_period
        self.cci_period = cci_period
        self.volume_sma_period = volume_sma_period
        self.sma_long_period = sma_long_period
        self.dema_period = dema_period
        self.keltner_ema_period = keltner_ema_period
        self.keltner_atr_period = keltner_atr_period
        self.keltner_multiplier = keltner_multiplier
        self.cmf_period = cmf_period
        self.stoch_rsi_period = stoch_rsi_period
        self.uo_period1 = uo_period1
        self.uo_period2 = uo_period2
        self.uo_period3 = uo_period3
        self.hist_vol_period = hist_vol_period
        self.parkinson_vol_period = parkinson_vol_period
        self.force_index_period = force_index_period

        # ATR history per symbol for ATR SMA computation (breakout strategy needs this)
        self._atr_history: dict[str, deque[Decimal]] = {}

        # Macro feature provider (opzionale)
        self._macro_provider: Any = None
        if MACRO_FEATURES_AVAILABLE and redis_client is not None:
            self._macro_provider = MacroFeatureProvider(redis_client)

    def compute_features(
        self,
        symbol: str,
        ohlcv_bars: list[OHLCVBar],
    ) -> dict[str, Any]:
        """Calcola tutti gli indicatori tecnici dalle candele OHLCV.

        Args:
            symbol: Simbolo dello strumento (es. "XAUUSD").
            ohlcv_bars: Lista di OHLCVBar, dalla più vecchia alla più recente.

        Returns:
            Dizionario di indicatori con chiavi stringa e valori Decimal.
            Restituisce un dict vuoto se i dati sono insufficienti.
        """
        if not ohlcv_bars:
            logger.warning(
                "Nessuna candela OHLCV fornita per il calcolo", symbol=symbol
            )
            return {}

        closes = [bar.close for bar in ohlcv_bars]
        highs = [bar.high for bar in ohlcv_bars]
        lows = [bar.low for bar in ohlcv_bars]
        volumes = [bar.volume for bar in ohlcv_bars]

        features: dict[str, Any] = {
            "symbol": symbol,
            "bar_count": len(ohlcv_bars),
            "latest_close": closes[-1],
            "latest_high": highs[-1],
            "latest_low": lows[-1],
            "latest_timestamp": ohlcv_bars[-1].timestamp,
        }

        # RSI — termometro della forza relativa del prezzo
        rsi = calculate_rsi(closes, period=self.rsi_period)
        features["rsi"] = rsi

        # Medie mobili — la "bussola" del trend
        features["ema_fast"] = calculate_ema(closes, period=self.ema_fast_period)
        features["ema_slow"] = calculate_ema(closes, period=self.ema_slow_period)
        features["sma"] = calculate_sma(closes, period=self.sma_period)

        # MACD — il "radar" di convergenza/divergenza delle medie mobili
        macd_line, signal_line, histogram = calculate_macd(
            closes,
            fast_period=self.ema_fast_period,
            slow_period=self.ema_slow_period,
        )
        features["macd_line"] = macd_line
        features["macd_signal"] = signal_line
        features["macd_histogram"] = histogram

        # Bande di Bollinger — i "guardrail" della volatilità
        bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(
            closes,
            period=self.bb_period,
        )
        features["bb_upper"] = bb_upper
        features["bb_middle"] = bb_middle
        features["bb_lower"] = bb_lower

        # Larghezza Bollinger e %B — quanto sono larghi i guardrail
        if bb_upper != ZERO and bb_lower != ZERO and bb_middle != ZERO:
            features["bb_width"] = (bb_upper - bb_lower) / bb_middle
            bb_range = bb_upper - bb_lower
            if bb_range != ZERO:
                features["bb_pct_b"] = (closes[-1] - bb_lower) / bb_range
            else:
                features["bb_pct_b"] = ZERO
        else:
            features["bb_width"] = ZERO
            features["bb_pct_b"] = ZERO

        # ATR — il "sismografo" della volatilità (escursione media reale)
        features["atr"] = calculate_atr(
            highs,
            lows,
            closes,
            period=self.atr_period,
        )

        # ATR SMA — media mobile dell'ATR per rilevamento espansione volatilità
        if features["atr"] > ZERO:
            if symbol not in self._atr_history:
                self._atr_history[symbol] = deque(maxlen=20)
            self._atr_history[symbol].append(features["atr"])
            atr_hist = self._atr_history[symbol]
            features["atr_sma"] = sum(atr_hist) / Decimal(str(len(atr_hist)))
        else:
            features["atr_sma"] = ZERO

        # ATR percentuale — volatilità relativa al prezzo
        if features["atr"] != ZERO:
            features["atr_pct"] = (features["atr"] / closes[-1]) * Decimal("100")
        else:
            features["atr_pct"] = ZERO

        # ADX — il "misuratore di forza" del trend (non la direzione)
        adx, plus_di, minus_di = calculate_adx(
            highs,
            lows,
            closes,
            period=self.adx_period,
        )
        features["adx"] = adx
        features["plus_di"] = plus_di
        features["minus_di"] = minus_di

        # Oscillatore Stocastico — il "livello di benzina" del momentum
        stoch_k, stoch_d = calculate_stochastic(
            highs,
            lows,
            closes,
            k_period=self.stoch_k_period,
            d_period=self.stoch_d_period,
        )
        features["stoch_k"] = stoch_k
        features["stoch_d"] = stoch_d

        # On-Balance Volume — il "contatore di flusso" dei volumi
        features["obv"] = calculate_obv(closes, volumes)

        # Canali di Donchian — i "confini" di massimo e minimo
        don_upper, don_middle, don_lower = calculate_donchian_channels(
            highs,
            lows,
            period=self.donchian_period,
        )
        features["donchian_upper"] = don_upper
        features["donchian_middle"] = don_middle
        features["donchian_lower"] = don_lower

        # Williams %R — simile allo stocastico ma invertito
        features["williams_r"] = calculate_williams_r(highs, lows, closes)

        # Tasso di Variazione (ROC) — la "velocità" del cambiamento di prezzo
        features["roc"] = calculate_roc(closes, period=10)

        # CCI — il "radar" delle deviazioni dal prezzo tipico
        features["cci"] = calculate_cci(highs, lows, closes, period=self.cci_period)

        # --- Phase D indicators ---

        # DEMA — media mobile a doppia esponenziale (più reattiva)
        features["dema"] = calculate_dema(closes, period=self.dema_period)

        # Keltner Channels — canali basati su volatilità ATR
        kelt_upper, kelt_middle, kelt_lower = calculate_keltner_channels(
            highs, lows, closes,
            ema_period=self.keltner_ema_period,
            atr_period=self.keltner_atr_period,
            multiplier=self.keltner_multiplier,
        )
        features["keltner_upper"] = kelt_upper
        features["keltner_middle"] = kelt_middle
        features["keltner_lower"] = kelt_lower

        # Parabolic SAR — trailing stop dinamico
        sar_value, sar_trend = calculate_parabolic_sar(highs, lows)
        features["parabolic_sar"] = sar_value
        features["parabolic_sar_trend"] = sar_trend

        # VWAP — prezzo medio ponderato per volume
        features["vwap"] = calculate_vwap(highs, lows, closes, volumes)

        # CMF — Chaikin Money Flow
        features["cmf"] = calculate_cmf(
            highs, lows, closes, volumes, period=self.cmf_period,
        )

        # Stochastic RSI — oscillatore stocastico applicato all'RSI
        stoch_rsi_k, stoch_rsi_d = calculate_stochastic_rsi(
            closes, rsi_period=self.rsi_period, stoch_period=self.stoch_rsi_period,
        )
        features["stoch_rsi_k"] = stoch_rsi_k
        features["stoch_rsi_d"] = stoch_rsi_d

        # Ultimate Oscillator — pressione di acquisto multi-periodo
        features["ultimate_osc"] = calculate_ultimate_oscillator(
            highs, lows, closes,
            period1=self.uo_period1,
            period2=self.uo_period2,
            period3=self.uo_period3,
        )

        # Volatilità storica close-to-close
        features["hist_vol"] = calculate_historical_volatility(
            closes, period=self.hist_vol_period,
        )

        # Volatilità di Parkinson (range high-low)
        features["parkinson_vol"] = calculate_parkinson_volatility(
            highs, lows, period=self.parkinson_vol_period,
        )

        # Force Index — forza del movimento ponderata per volume
        features["force_index"] = calculate_force_index(
            closes, volumes, period=self.force_index_period,
        )

        # SMA 200 — il "faro" del trend di lungo periodo
        features["sma_200"] = calculate_sma(closes, period=self.sma_long_period)

        # Rapporto volume — volume attuale vs media (il "rumore" del mercato)
        vol_sma = calculate_sma(volumes, period=self.volume_sma_period)
        if vol_sma != ZERO:
            features["volume_ratio"] = volumes[-1] / vol_sma
        else:
            features["volume_ratio"] = ZERO

        # Euristica di direzione del trend — incrocio EMA come indicatore di rotta
        if features["ema_fast"] != ZERO and features["ema_slow"] != ZERO:
            if features["ema_fast"] > features["ema_slow"]:
                features["ema_trend"] = TrendDirection.BULLISH
            elif features["ema_fast"] < features["ema_slow"]:
                features["ema_trend"] = TrendDirection.BEARISH
            else:
                features["ema_trend"] = TrendDirection.NEUTRAL
        else:
            features["ema_trend"] = TrendDirection.UNKNOWN

        logger.debug(
            "Indicatori calcolati",
            symbol=symbol,
            bar_count=len(ohlcv_bars),
            rsi=str(rsi),
            ema_trend=features["ema_trend"],
        )

        return features

    async def compute_features_with_macro(
        self,
        symbol: str,
        ohlcv_bars: list[OHLCVBar],
    ) -> dict[str, Any]:
        """Calcola indicatori tecnici + feature macro.

        Versione asincrona che include anche le macro features
        da Redis (VIX, yield curve, COT, etc.).

        Args:
            symbol: Simbolo dello strumento
            ohlcv_bars: Lista di OHLCVBar

        Returns:
            Dizionario con indicatori tecnici e macro features
        """
        # Calcola indicatori tecnici standard
        features = self.compute_features(symbol, ohlcv_bars)

        # Aggiungi macro features se disponibili
        if self._macro_provider is not None:
            try:
                macro = await self._macro_provider.get_features(symbol)

                # Aggiungi feature macro al dict (prefisso "macro_")
                features["macro_vix_spot"] = macro.vix_spot
                features["macro_vix_regime"] = macro.vix_regime
                features["macro_vix_contango"] = macro.vix_contango
                features["macro_yield_slope_2s10s"] = macro.yield_slope_2s10s
                features["macro_curve_inverted"] = macro.curve_inverted
                features["macro_recession_prob"] = macro.recession_prob
                features["macro_dxy_change_1h_pct"] = macro.dxy_change_1h_pct
                features["macro_real_rate_10y"] = macro.real_rate_10y
                features["macro_cot_asset_mgr_pct_oi"] = macro.cot_asset_mgr_pct_oi
                features["macro_cot_sentiment"] = macro.cot_sentiment
                features["macro_data_stale"] = macro.data_stale

                # Aggiungi vettore normalizzato
                features["macro_vector"] = macro.to_vector()

                # Valutazioni ambiente
                features["macro_gold_bullish"] = self._macro_provider.is_gold_bullish_environment(macro)
                features["macro_high_risk"] = self._macro_provider.is_high_risk_environment(macro)

                logger.debug(
                    "Macro features aggiunte",
                    symbol=symbol,
                    vix=macro.vix_spot,
                    vix_regime=macro.vix_regime,
                    gold_bullish=features["macro_gold_bullish"],
                )

            except Exception as e:
                logger.warning("Errore fetch macro features", error=str(e))
                # Continua senza macro features
                features["macro_available"] = False
        else:
            features["macro_available"] = False

        return features
