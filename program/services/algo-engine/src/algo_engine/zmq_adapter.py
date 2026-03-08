"""Adattatore ZMQ — ponte tra il formato Go data-ingestion e la pipeline Algo Engine.

Come un traduttore simultaneo all'ONU: il servizio Go pubblica dati in un
formato, e questo modulo li traduce nel linguaggio che la pipeline del
Cervello AI sa leggere. Fornisce:

- ``parse_bar_message`` — traduce un singolo JSON bar dal formato Go in OHLCVBar
- ``determine_message_type`` — classifica un topic ZMQ come bar / tick / sconosciuto
- ``BarBuffer`` — finestra scorrevole per simbolo che accumula le candele
"""

from __future__ import annotations

import json
from collections import deque
from datetime import datetime, timezone
from decimal import Decimal

from moneymaker_common.logging import get_logger

from algo_engine.features.pipeline import OHLCVBar

logger = get_logger(__name__)


def determine_message_type(topic: str) -> str:
    """Classifica un topic ZMQ — come leggere l'etichetta su un pacco.

    Returns:
        ``"bar"`` per candele OHLCV completate (prefisso ``bar.``),
        ``"tick"`` per tick grezzi (prefisso ``trade.``),
        oppure ``"unknown"`` per tutto il resto.
    """
    if topic.startswith("bar."):
        return "bar"
    if topic.startswith("trade."):
        return "tick"
    return "unknown"


def parse_bar_message(payload: bytes) -> tuple[str, str, OHLCVBar]:
    """Traduce un singolo JSON bar pubblicato dal Go data-ingestion.

    Come decifrare un telegramma: prende il messaggio grezzo e lo
    converte in un oggetto strutturato che la pipeline sa elaborare.

    JSON atteso (dal Go ``aggregator.Bar``):

    .. code-block:: json

        {
            "symbol": "XAUUSD",
            "timeframe": "M1",
            "open_time": "2024-02-21T12:00:00Z",
            "close_time": "2024-02-21T12:01:00Z",
            "open": "2050.30",
            "high": "2051.10",
            "low": "2049.80",
            "close": "2050.90",
            "volume": "145.20",
            "tick_count": 47
        }

    Returns:
        Tupla di (simbolo, timeframe, OHLCVBar).

    Raises:
        KeyError: Se mancano campi obbligatori.
        json.JSONDecodeError: Se il payload non è JSON valido.
    """
    data = json.loads(payload)
    symbol = data["symbol"]
    timeframe = data.get("timeframe", "M5")

    # Converte il timestamp ISO 8601 in millisecondi Unix
    open_time_str = data["open_time"]
    dt = datetime.fromisoformat(open_time_str.replace("Z", "+00:00"))
    timestamp_ms = int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)

    bar = OHLCVBar(
        timestamp=timestamp_ms,
        open=Decimal(str(data["open"])),
        high=Decimal(str(data["high"])),
        low=Decimal(str(data["low"])),
        close=Decimal(str(data["close"])),
        volume=Decimal(str(data["volume"])),
    )
    return symbol, timeframe, bar


class BarBuffer:
    """Buffer a finestra scorrevole per candele OHLCV — come un nastro trasportatore.

    Accumula le candele una alla volta finché non raggiunge ``min_bars``,
    poi restituisce l'intera finestra ad ogni nuova candela. Come una
    catena di montaggio: il nastro si riempie, e quando è pieno ogni
    nuovo pezzo fa scorrere via il più vecchio.

    Args:
        window_size: Numero massimo di candele da mantenere per simbolo.
        min_bars: Candele minime prima che la pipeline si attivi.
    """

    def __init__(self, window_size: int = 250, min_bars: int = 50) -> None:
        self._window_size = window_size
        self._min_bars = min_bars
        self._buffers: dict[str, deque[OHLCVBar]] = {}

    def add_bar(self, symbol: str, bar: OHLCVBar) -> list[OHLCVBar] | None:
        """Aggiunge una candela al buffer per *symbol*.

        Returns:
            Lista di candele (copia della finestra corrente) se il buffer
            ha accumulato almeno ``min_bars``, altrimenti ``None``.
        """
        if symbol not in self._buffers:
            self._buffers[symbol] = deque(maxlen=self._window_size)
        buf = self._buffers[symbol]
        buf.append(bar)
        if len(buf) >= self._min_bars:
            return list(buf)
        return None

    @property
    def symbols(self) -> list[str]:
        """Restituisce la lista dei simboli attualmente nel buffer."""
        return list(self._buffers.keys())

    def bar_count(self, symbol: str) -> int:
        """Restituisce il numero di candele nel buffer per *symbol*."""
        buf = self._buffers.get(symbol)
        return len(buf) if buf else 0
