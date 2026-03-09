"""Calcolo indicatori tecnici con aritmetica Decimal.

VINCOLO ARCHITETTURALE: Tutti i calcoli su prezzi e indicatori usano
decimal.Decimal per evitare errori di precisione IEEE 754 dei float.
Come un farmacista che pesa i grammi con la bilancia di precisione
invece di "a occhio" — nei calcoli finanziari gli errori di
arrotondamento accumulati possono causare decisioni di trading errate.

Ogni funzione accetta liste di Decimal e restituisce risultati Decimal.
"""

from __future__ import annotations

import functools
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from moneymaker_common.decimal_utils import ONE, ZERO, to_decimal


def _has_invalid_decimals(values: list[Decimal]) -> bool:
    """Check if any Decimal in the list is NaN or Infinite."""
    for v in values:
        if isinstance(v, Decimal):
            if v.is_nan() or v.is_infinite():
                return True
    return False


def validate_decimal_inputs(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that validates all list[Decimal] arguments for NaN/Inf.

    Returns ZERO (or tuple of ZEROs matching return type) if invalid data found.
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        for arg in args:
            if isinstance(arg, list) and arg and isinstance(arg[0], Decimal):
                if _has_invalid_decimals(arg):
                    return ZERO
        for arg in kwargs.values():
            if isinstance(arg, list) and arg and isinstance(arg[0], Decimal):
                if _has_invalid_decimals(arg):
                    return ZERO
        try:
            return func(*args, **kwargs)
        except (InvalidOperation, ZeroDivisionError):
            return ZERO
    return wrapper


@validate_decimal_inputs
def calculate_sma(values: list[Decimal], period: int) -> Decimal:
    """Calcola la Media Mobile Semplice (SMA) — come la media dei voti scolastici.

    SMA = somma(ultimi N valori) / N

    Args:
        values: Lista di prezzi Decimal (dal più vecchio al più recente).
        period: Numero di periodi su cui mediare.

    Returns:
        SMA come Decimal. Restituisce ZERO se i dati sono insufficienti.
    """
    if len(values) < period or period <= 0:
        return ZERO

    window = values[-period:]
    total = sum(window, ZERO)
    return total / Decimal(str(period))


@validate_decimal_inputs
def calculate_ema(values: list[Decimal], period: int) -> Decimal:
    """Calcola la Media Mobile Esponenziale (EMA) — come una media che dà più peso ai voti recenti.

    Usa un moltiplicatore di lisciatura: k = 2 / (periodo + 1).
    Il primo valore EMA viene seminato con la SMA dei primi `period` valori,
    poi ogni valore successivo applica: EMA = valore * k + EMA_prec * (1 - k).

    Args:
        values: Lista di prezzi Decimal (dal più vecchio al più recente).
        period: Numero di periodi di lookback.

    Returns:
        EMA corrente come Decimal. Restituisce ZERO se i dati sono insufficienti.
    """
    if len(values) < period or period <= 0:
        return ZERO

    two = Decimal("2")
    multiplier = two / (Decimal(str(period)) + ONE)

    # Semina con SMA dei primi `period` valori — il punto di partenza
    ema = calculate_sma(values[:period], period)

    # Applica la formula EMA ai valori rimanenti — lisciatura progressiva
    for value in values[period:]:
        ema = (value * multiplier) + (ema * (ONE - multiplier))

    return ema


@validate_decimal_inputs
def calculate_rsi(closes: list[Decimal], period: int = 14) -> Decimal:
    """Calcola il Relative Strength Index — il "termometro" della forza del prezzo.

    RSI = 100 - (100 / (1 + RS))
    dove RS = guadagno_medio / perdita_media su `period` candele.
    Come misurare la febbre al mercato: sopra 70 è "surriscaldato" (ipercomprato),
    sotto 30 è "ipotermia" (ipervenduto).

    Usa il metodo lisciato di Wilder: dopo il seme SMA iniziale,
    i valori successivi usano lisciatura esponenziale con alpha = 1/period.

    Args:
        closes: Lista prezzi di chiusura Decimal (dal più vecchio).
        period: Periodo di lookback RSI (default 14).

    Returns:
        Valore RSI come Decimal in [0, 100]. ZERO se dati insufficienti.
    """
    if len(closes) < period + 1 or period <= 0:
        return ZERO

    hundred = Decimal("100")
    period_d = Decimal(str(period))

    # Calcola le variazioni di prezzo — le "oscillazioni" giornaliere
    changes: list[Decimal] = []
    for i in range(1, len(closes)):
        changes.append(closes[i] - closes[i - 1])

    # Media iniziale di guadagni e perdite (SMA sui primi `period` cambiamenti)
    gains = [c if c > ZERO else ZERO for c in changes[:period]]
    losses = [abs(c) if c < ZERO else ZERO for c in changes[:period]]

    avg_gain = sum(gains, ZERO) / period_d
    avg_loss = sum(losses, ZERO) / period_d

    # RSI lisciato (metodo di Wilder) per i cambiamenti rimanenti
    for change in changes[period:]:
        if change > ZERO:
            current_gain = change
            current_loss = ZERO
        else:
            current_gain = ZERO
            current_loss = abs(change)

        avg_gain = (avg_gain * (period_d - ONE) + current_gain) / period_d
        avg_loss = (avg_loss * (period_d - ONE) + current_loss) / period_d

    if avg_loss == ZERO:
        return hundred  # Nessuna perdita → RSI = 100

    rs = avg_gain / avg_loss
    rsi = hundred - (hundred / (ONE + rs))
    return rsi


@validate_decimal_inputs
def calculate_macd(
    closes: list[Decimal],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> tuple[Decimal, Decimal, Decimal]:
    """Calcola il MACD — il "radar" di convergenza/divergenza delle medie mobili.

    Linea MACD = EMA(veloce) - EMA(lenta)
    Linea Segnale = EMA(Linea MACD, periodo_segnale)
    Istogramma = Linea MACD - Linea Segnale

    Come due auto su una strada: quando la veloce supera la lenta
    (incrocio rialzista), il mercato accelera verso l'alto.

    Args:
        closes: Lista prezzi di chiusura Decimal (dal più vecchio).
        fast_period: Periodo EMA veloce (default 12).
        slow_period: Periodo EMA lenta (default 26).
        signal_period: Periodo EMA linea segnale (default 9).

    Returns:
        Tupla (macd_line, signal_line, istogramma) come Decimal.
        Restituisce (ZERO, ZERO, ZERO) se dati insufficienti.
    """
    if len(closes) < slow_period + signal_period:
        return ZERO, ZERO, ZERO

    # Calcola la serie MACD nel tempo per alimentare l'EMA del segnale
    two = Decimal("2")
    fast_mult = two / (Decimal(str(fast_period)) + ONE)
    slow_mult = two / (Decimal(str(slow_period)) + ONE)

    # Semina entrambe le EMA con le rispettive SMA
    fast_ema = calculate_sma(closes[:fast_period], fast_period)
    slow_ema = calculate_sma(closes[:slow_period], slow_period)

    # Costruisce la serie MACD: avanza dal punto di semina della EMA lenta,
    # aggiornando entrambe le EMA simultaneamente
    # Risemina la EMA veloce correttamente dall'inizio
    fast_ema = calculate_sma(closes[:fast_period], fast_period)
    for value in closes[fast_period:slow_period]:
        fast_ema = (value * fast_mult) + (fast_ema * (ONE - fast_mult))

    # Ora entrambe le EMA sono seminate; calcola la linea MACD da slow_period in poi
    macd_values: list[Decimal] = []

    # Primo valore MACD al confine del periodo lento
    macd_line = fast_ema - slow_ema
    macd_values.append(macd_line)

    for value in closes[slow_period:]:
        fast_ema = (value * fast_mult) + (fast_ema * (ONE - fast_mult))
        slow_ema = (value * slow_mult) + (slow_ema * (ONE - slow_mult))
        macd_line = fast_ema - slow_ema
        macd_values.append(macd_line)

    # Ultimo valore della linea MACD
    current_macd = macd_values[-1]

    # La linea segnale è l'EMA dei valori MACD
    if len(macd_values) < signal_period:
        return current_macd, ZERO, current_macd

    signal_line = calculate_ema(macd_values, signal_period)
    histogram = current_macd - signal_line

    return current_macd, signal_line, histogram


@validate_decimal_inputs
def calculate_bollinger_bands(
    closes: list[Decimal],
    period: int = 20,
    num_std: int = 2,
) -> tuple[Decimal, Decimal, Decimal]:
    """Calcola le Bande di Bollinger — i "guardrail" della volatilità.

    Banda Media = SMA(periodo)
    Banda Superiore = Media + num_std * DevStd
    Banda Inferiore = Media - num_std * DevStd

    Come i guardrail su un'autostrada: quando il prezzo li tocca,
    potrebbe "rimbalzare" verso il centro.

    La deviazione standard usa la formula della popolazione sugli
    ultimi `period` valori, tutta in aritmetica Decimal.

    Args:
        closes: Lista prezzi di chiusura Decimal (dal più vecchio).
        period: Periodo di lookback SMA (default 20).
        num_std: Numero di deviazioni standard per le bande (default 2).

    Returns:
        Tupla (banda_sup, banda_media, banda_inf) come Decimal.
        Restituisce (ZERO, ZERO, ZERO) se dati insufficienti.
    """
    if len(closes) < period or period <= 0:
        return ZERO, ZERO, ZERO

    window = closes[-period:]
    period_d = Decimal(str(period))
    num_std_d = Decimal(str(num_std))

    # Banda media (SMA) — il "centro strada"
    middle = sum(window, ZERO) / period_d

    # Deviazione standard della popolazione in Decimal
    variance = sum((v - middle) ** 2 for v in window) / period_d

    # Radice quadrata in Decimal con metodo di Newton
    std_dev = _decimal_sqrt(variance)

    upper = middle + (num_std_d * std_dev)
    lower = middle - (num_std_d * std_dev)

    return upper, middle, lower


@validate_decimal_inputs
def calculate_atr(
    highs: list[Decimal],
    lows: list[Decimal],
    closes: list[Decimal],
    period: int = 14,
) -> Decimal:
    """Calcola l'Average True Range — il "sismografo" della volatilità.

    True Range = max(
        massimo - minimo,
        |massimo - chiusura_prec|,
        |minimo - chiusura_prec|,
    )

    ATR è la media mobile lisciata del True Range con il metodo
    di Wilder (stesso dell'RSI). Misura quanto "trema" il prezzo.

    Args:
        highs: Lista prezzi massimi Decimal (dal più vecchio).
        lows: Lista prezzi minimi Decimal (dal più vecchio).
        closes: Lista prezzi chiusura Decimal (dal più vecchio).
        period: Periodo di lookback ATR (default 14).

    Returns:
        ATR come Decimal. Restituisce ZERO se dati insufficienti.
    """
    n = min(len(highs), len(lows), len(closes))
    if n < period + 1 or period <= 0:
        return ZERO

    period_d = Decimal(str(period))

    # Calcola la serie True Range (da indice 1, serve la chiusura precedente)
    true_ranges: list[Decimal] = []
    for i in range(1, n):
        high_low = highs[i] - lows[i]
        high_prev_close = abs(highs[i] - closes[i - 1])
        low_prev_close = abs(lows[i] - closes[i - 1])
        tr = max(high_low, high_prev_close, low_prev_close)
        true_ranges.append(tr)

    if len(true_ranges) < period:
        return ZERO

    # ATR iniziale = SMA dei primi `period` true range
    atr = sum(true_ranges[:period], ZERO) / period_d

    # Lisciatura di Wilder per i valori rimanenti
    for tr in true_ranges[period:]:
        atr = (atr * (period_d - ONE) + tr) / period_d

    return atr


@validate_decimal_inputs
def calculate_adx(
    highs: list[Decimal],
    lows: list[Decimal],
    closes: list[Decimal],
    period: int = 14,
) -> tuple[Decimal, Decimal, Decimal]:
    """Calcola l'Average Directional Index con +DI e -DI — il "misuratore di forza" del trend.

    ADX misura la forza del trend (non la direzione). Come un anemometro:
    sopra 25 il vento è forte (trend netto), sotto 20 è calmo (laterale).

    Args:
        highs: Lista prezzi massimi (dal più vecchio).
        lows: Lista prezzi minimi (dal più vecchio).
        closes: Lista prezzi chiusura (dal più vecchio).
        period: Periodo di lookback (default 14).

    Returns:
        Tupla (adx, plus_di, minus_di). Restituisce (ZERO, ZERO, ZERO)
        se dati insufficienti.
    """
    n = min(len(highs), len(lows), len(closes))
    # Servono almeno 2*period + 1 candele per un ADX significativo
    if n < 2 * period + 1 or period <= 0:
        return ZERO, ZERO, ZERO

    hundred = Decimal("100")
    period_d = Decimal(str(period))

    # Passo 1: Calcola +DM e -DM per ogni candela — movimenti direzionali
    plus_dm_list: list[Decimal] = []
    minus_dm_list: list[Decimal] = []
    tr_list: list[Decimal] = []

    for i in range(1, n):
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]

        plus_dm = up_move if (up_move > down_move and up_move > ZERO) else ZERO
        minus_dm = down_move if (down_move > up_move and down_move > ZERO) else ZERO

        plus_dm_list.append(plus_dm)
        minus_dm_list.append(minus_dm)

        # True Range — l'ampiezza effettiva del movimento
        high_low = highs[i] - lows[i]
        high_prev_close = abs(highs[i] - closes[i - 1])
        low_prev_close = abs(lows[i] - closes[i - 1])
        tr_list.append(max(high_low, high_prev_close, low_prev_close))

    # Passo 2: Liscia +DM, -DM e TR con Wilder sui primi `period`
    smoothed_plus_dm = sum(plus_dm_list[:period], ZERO)
    smoothed_minus_dm = sum(minus_dm_list[:period], ZERO)
    smoothed_tr = sum(tr_list[:period], ZERO)

    # Passo 3: Calcola i valori DI e DX per le candele rimanenti
    dx_values: list[Decimal] = []

    for i in range(period, len(plus_dm_list)):
        smoothed_plus_dm = (
            smoothed_plus_dm - (smoothed_plus_dm / period_d) + plus_dm_list[i]
        )
        smoothed_minus_dm = (
            smoothed_minus_dm - (smoothed_minus_dm / period_d) + minus_dm_list[i]
        )
        smoothed_tr = smoothed_tr - (smoothed_tr / period_d) + tr_list[i]

        if smoothed_tr == ZERO:
            continue

        plus_di = (smoothed_plus_dm / smoothed_tr) * hundred
        minus_di = (smoothed_minus_dm / smoothed_tr) * hundred

        di_sum = plus_di + minus_di
        if di_sum == ZERO:
            dx_values.append(ZERO)
        else:
            dx = (abs(plus_di - minus_di) / di_sum) * hundred
            dx_values.append(dx)

    if len(dx_values) < period:
        return ZERO, ZERO, ZERO

    # Passo 4: ADX = media lisciata di Wilder dei valori DX
    adx = sum(dx_values[:period], ZERO) / period_d
    for dx in dx_values[period:]:
        adx = (adx * (period_d - ONE) + dx) / period_d

    # +DI e -DI finali
    if smoothed_tr == ZERO:
        return adx, ZERO, ZERO

    final_plus_di = (smoothed_plus_dm / smoothed_tr) * hundred
    final_minus_di = (smoothed_minus_dm / smoothed_tr) * hundred

    return adx, final_plus_di, final_minus_di


@validate_decimal_inputs
def calculate_stochastic(
    highs: list[Decimal],
    lows: list[Decimal],
    closes: list[Decimal],
    k_period: int = 14,
    d_period: int = 3,
) -> tuple[Decimal, Decimal]:
    """Calcola l'Oscillatore Stocastico (%K e %D) — il "livello di benzina" del momentum.

    %K = (chiusura - minimo_più_basso) / (massimo_più_alto - minimo_più_basso) * 100
    %D = SMA(%K, d_period)

    Come il livello di benzina: vicino a 0 il serbatoio è vuoto (ipervenduto),
    vicino a 100 è pieno (ipercomprato).

    Args:
        highs: Prezzi massimi (dal più vecchio).
        lows: Prezzi minimi (dal più vecchio).
        closes: Prezzi di chiusura (dal più vecchio).
        k_period: Periodo lookback %K (default 14).
        d_period: Periodo lisciatura %D (default 3).

    Returns:
        Tupla (percent_k, percent_d). Restituisce (ZERO, ZERO) se
        dati insufficienti.
    """
    n = min(len(highs), len(lows), len(closes))
    if n < k_period + d_period - 1 or k_period <= 0 or d_period <= 0:
        return ZERO, ZERO

    hundred = Decimal("100")

    # Calcola %K per ogni posizione valida
    k_values: list[Decimal] = []
    for i in range(k_period - 1, n):
        window_highs = highs[i - k_period + 1 : i + 1]
        window_lows = lows[i - k_period + 1 : i + 1]
        highest = max(window_highs)
        lowest = min(window_lows)
        hl_range = highest - lowest

        if hl_range == ZERO:
            k_values.append(Decimal("50"))  # Punto medio quando non c'è escursione
        else:
            k = ((closes[i] - lowest) / hl_range) * hundred
            k_values.append(k)

    if len(k_values) < d_period:
        return ZERO, ZERO

    # %D = SMA degli ultimi d_period valori %K
    percent_k = k_values[-1]
    percent_d = calculate_sma(k_values, d_period)

    return percent_k, percent_d


@validate_decimal_inputs
def calculate_obv(closes: list[Decimal], volumes: list[Decimal]) -> Decimal:
    """Calcola l'On-Balance Volume — il "contatore di flusso" dei volumi.

    OBV accumula il volume nei giorni di rialzo e lo sottrae nei giorni
    di ribasso. Come il saldo di un conto corrente: depositi quando il
    prezzo sale, prelievi quando scende.

    Args:
        closes: Lista prezzi di chiusura (dal più vecchio).
        volumes: Lista volumi (dal più vecchio).

    Returns:
        Valore OBV corrente come Decimal. ZERO se dati insufficienti.
    """
    n = min(len(closes), len(volumes))
    if n < 2:
        return ZERO

    obv = ZERO
    for i in range(1, n):
        if closes[i] > closes[i - 1]:
            obv += volumes[i]
        elif closes[i] < closes[i - 1]:
            obv -= volumes[i]
        # Se chiusura == chiusura_prec, OBV invariato

    return obv


@validate_decimal_inputs
def calculate_donchian_channels(
    highs: list[Decimal],
    lows: list[Decimal],
    period: int = 20,
) -> tuple[Decimal, Decimal, Decimal]:
    """Calcola i Canali di Donchian — i "confini" di massimo e minimo.

    Superiore = massimo più alto nel periodo
    Inferiore = minimo più basso nel periodo
    Medio = (Superiore + Inferiore) / 2

    Come la temperatura max e min della settimana: definiscono
    il "campo di gioco" del prezzo.

    Args:
        highs: Lista prezzi massimi (dal più vecchio).
        lows: Lista prezzi minimi (dal più vecchio).
        period: Periodo di lookback (default 20).

    Returns:
        Tupla (superiore, medio, inferiore). Restituisce (ZERO, ZERO, ZERO)
        se dati insufficienti.
    """
    n = min(len(highs), len(lows))
    if n < period or period <= 0:
        return ZERO, ZERO, ZERO

    window_highs = highs[-period:]
    window_lows = lows[-period:]

    upper = max(window_highs)
    lower = min(window_lows)
    middle = (upper + lower) / Decimal("2")

    return upper, middle, lower


@validate_decimal_inputs
def calculate_williams_r(
    highs: list[Decimal],
    lows: list[Decimal],
    closes: list[Decimal],
    period: int = 14,
) -> Decimal:
    """Calcola il Williams %R — simile allo stocastico ma invertito.

    %R = (massimo_più_alto - chiusura) / (massimo_più_alto - minimo_più_basso) * -100
    Intervallo: da -100 a 0. Sotto -80 = ipervenduto, sopra -20 = ipercomprato.

    Args:
        highs: Lista prezzi massimi (dal più vecchio).
        lows: Lista prezzi minimi (dal più vecchio).
        closes: Lista prezzi chiusura (dal più vecchio).
        period: Periodo di lookback (default 14).

    Returns:
        Valore Williams %R. ZERO se dati insufficienti.
    """
    n = min(len(highs), len(lows), len(closes))
    if n < period or period <= 0:
        return ZERO

    hundred = Decimal("100")
    window_highs = highs[-period:]
    window_lows = lows[-period:]
    highest = max(window_highs)
    lowest = min(window_lows)
    hl_range = highest - lowest

    if hl_range == ZERO:
        return Decimal("-50")  # Punto medio quando non c'è escursione

    return ((highest - closes[-1]) / hl_range) * -hundred


@validate_decimal_inputs
def calculate_roc(closes: list[Decimal], period: int = 10) -> Decimal:
    """Calcola il Rate of Change (percentuale) — la "velocità" del prezzo.

    ROC = (chiusura - chiusura_N_periodi_fa) / chiusura_N_periodi_fa * 100

    Come il tachimetro di un'auto: misura quanto velocemente
    il prezzo si sta muovendo rispetto a N periodi fa.

    Args:
        closes: Lista prezzi di chiusura (dal più vecchio).
        period: Periodo di lookback (default 10).

    Returns:
        ROC come percentuale Decimal. ZERO se dati insufficienti.
    """
    if len(closes) < period + 1 or period <= 0:
        return ZERO

    hundred = Decimal("100")
    old_close = closes[-(period + 1)]

    if old_close == ZERO:
        return ZERO

    return ((closes[-1] - old_close) / old_close) * hundred


@validate_decimal_inputs
def calculate_cci(
    highs: list[Decimal],
    lows: list[Decimal],
    closes: list[Decimal],
    period: int = 20,
) -> Decimal:
    """Calcola il Commodity Channel Index — il "radar" delle deviazioni dal prezzo tipico.

    CCI = (Prezzo_Tipico - SMA(Prezzo_Tipico)) / (0.015 * Deviazione_Media)
    Prezzo_Tipico = (massimo + minimo + chiusura) / 3

    Come un radar meteorologico: valori estremi indicano "tempeste"
    (deviazioni significative dalla norma).

    Args:
        highs: Lista prezzi massimi (dal più vecchio).
        lows: Lista prezzi minimi (dal più vecchio).
        closes: Lista prezzi chiusura (dal più vecchio).
        period: Periodo di lookback (default 20).

    Returns:
        Valore CCI. ZERO se dati insufficienti.
    """
    n = min(len(highs), len(lows), len(closes))
    if n < period or period <= 0:
        return ZERO

    three = Decimal("3")
    period_d = Decimal(str(period))
    constant = Decimal("0.015")

    # Calcola i prezzi tipici per la finestra — il "baricentro" di ogni candela
    typical_prices: list[Decimal] = []
    for i in range(n - period, n):
        tp = (highs[i] + lows[i] + closes[i]) / three
        typical_prices.append(tp)

    # SMA dei prezzi tipici — la "norma"
    tp_sma = sum(typical_prices, ZERO) / period_d

    # Deviazione media — quanto i prezzi si "allontanano" dalla norma
    mean_dev = sum(abs(tp - tp_sma) for tp in typical_prices) / period_d

    if mean_dev == ZERO:
        return ZERO

    return (typical_prices[-1] - tp_sma) / (constant * mean_dev)


def _decimal_sqrt(value: Decimal, precision: int = 28) -> Decimal:
    """Calcola la radice quadrata di un Decimal con il metodo di Newton.

    Come un algoritmo che "converge" sulla risposta giusta: ad ogni
    iterazione si avvicina sempre di più al valore esatto.

    Args:
        value: Valore Decimal non negativo.
        precision: Numero di iterazioni per la convergenza.

    Returns:
        Radice quadrata come Decimal.
    """
    if value < ZERO:
        raise ValueError("Impossibile calcolare la radice quadrata di un numero negativo")
    if value == ZERO:
        return ZERO

    # Stima iniziale
    x = to_decimal(value)
    two = Decimal("2")

    for _ in range(precision):
        x = (x + value / x) / two

    return x


# ---------------------------------------------------------------------------
# Logaritmo naturale puro Decimal — Phase D helper
# ---------------------------------------------------------------------------

def _decimal_ln(value: Decimal, iterations: int = 50) -> Decimal:
    """Logaritmo naturale di un Decimal positivo via serie di Taylor arctanh.

    ln(x) = 2 * sum_{k=0}^{N} (1/(2k+1)) * ((x-1)/(x+1))^(2k+1)

    Usa riduzione di range: ln(x) = n*ln(2) + ln(x / 2^n) dove n
    è scelto per portare l'argomento vicino a 1.0 (convergenza rapida).

    Returns:
        ZERO se value <= 0.
    """
    if value <= ZERO:
        return ZERO

    # Riduzione di range: fattorizziamo potenze di 2
    n = 0
    reduced = value
    _TWO = Decimal("2")
    while reduced > _TWO:
        reduced /= _TWO
        n += 1
    _HALF = Decimal("0.5")
    while reduced < _HALF:
        reduced *= _TWO
        n -= 1

    # Serie arctanh: ln(reduced) = 2 * arctanh((reduced - 1) / (reduced + 1))
    y = (reduced - ONE) / (reduced + ONE)
    y_sq = y * y
    term = y
    result = term

    for k in range(1, iterations):
        term *= y_sq
        result += term / Decimal(str(2 * k + 1))

    ln_reduced = _TWO * result

    # Ricostruire: ln(value) = n * ln(2) + ln(reduced)
    return Decimal(str(n)) * _LN2 + ln_reduced


# Pre-calcolato ln(2) con precisione Decimal a 28 cifre
_LN2 = Decimal("0.6931471805599453094172321215")


def _calculate_rsi_series(closes: list[Decimal], period: int = 14) -> list[Decimal]:
    """Serie completa di valori RSI — necessaria per Stochastic RSI.

    Stesso algoritmo Wilder di calculate_rsi(), ma restituisce il valore
    RSI ad ogni barra dalla posizione `period` in poi.

    Returns:
        Lista di valori RSI Decimal, vuota se dati insufficienti.
    """
    if len(closes) < period + 1 or period <= 0:
        return []

    hundred = Decimal("100")
    period_d = Decimal(str(period))
    rsi_values: list[Decimal] = []

    # Variazioni di prezzo
    changes: list[Decimal] = []
    for i in range(1, len(closes)):
        changes.append(closes[i] - closes[i - 1])

    # Media iniziale (SMA) sui primi `period` cambiamenti
    gains = [c if c > ZERO else ZERO for c in changes[:period]]
    losses = [abs(c) if c < ZERO else ZERO for c in changes[:period]]

    avg_gain = sum(gains, ZERO) / period_d
    avg_loss = sum(losses, ZERO) / period_d

    # Primo RSI
    if avg_loss == ZERO:
        rsi_values.append(hundred)
    else:
        rs = avg_gain / avg_loss
        rsi_values.append(hundred - (hundred / (ONE + rs)))

    # RSI lisciato (Wilder) per ogni barra successiva
    for change in changes[period:]:
        if change > ZERO:
            current_gain = change
            current_loss = ZERO
        else:
            current_gain = ZERO
            current_loss = abs(change)

        avg_gain = (avg_gain * (period_d - ONE) + current_gain) / period_d
        avg_loss = (avg_loss * (period_d - ONE) + current_loss) / period_d

        if avg_loss == ZERO:
            rsi_values.append(hundred)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(hundred - (hundred / (ONE + rs)))

    return rsi_values
