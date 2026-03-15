"""Calendario Economico — il "calendario degli eventi pericolosi".

Previene il trading durante rilasci di dati macroeconomici ad alto impatto
(NFP, CPI, decisioni banche centrali) dove spread e volatilità esplodono.

Opera con un file JSON statico di eventi settimanali che può essere
aggiornato manualmente o via script. Non dipende da API esterne in
tempo reale per affidabilità.

Utilizzo:
    calendar = EconomicCalendarFilter(blackout_minutes=15)
    is_blocked, reason = calendar.is_blackout("EURUSD", utc_now)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from moneymaker_common.logging import get_logger

logger = get_logger(__name__)

# Valute impattate per tipo di evento
EVENT_CURRENCY_MAP: dict[str, list[str]] = {
    "USD": ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD", "XAUUSD"],
    "EUR": ["EURUSD", "EURGBP", "EURJPY"],
    "GBP": ["GBPUSD", "EURGBP", "GBPJPY"],
    "JPY": ["USDJPY", "EURJPY", "GBPJPY"],
    "AUD": ["AUDUSD"],
    "NZD": ["NZDUSD"],
    "CAD": ["USDCAD"],
    "CHF": ["USDCHF"],
}

# Eventi ad alto impatto ricorrenti (giorno della settimana, ora UTC, valuta)
# Questi sono i più importanti e ricorrenti mensilmente
RECURRING_HIGH_IMPACT: list[dict] = [
    # NFP — primo venerdì del mese (approssimato: ogni venerdì in prima settimana)
    {
        "name": "US Non-Farm Payrolls",
        "currency": "USD",
        "hour_utc": 13,
        "minute": 30,
        "weekday": 4,
        "week_of_month": 1,
    },
    # FOMC — ogni 6 settimane circa (gestito via JSON eventi)
    # ECB Rate Decision — gestito via JSON
    # CPI releases — gestito via JSON
]


class EconomicCalendarFilter:
    """Filtra il trading durante eventi economici ad alto impatto."""

    def __init__(
        self,
        blackout_minutes_before: int = 15,
        blackout_minutes_after: int = 15,
        events_file: str | None = None,
    ) -> None:
        self._blackout_before = blackout_minutes_before
        self._blackout_after = blackout_minutes_after
        self._events: list[dict] = []

        if events_file:
            self._load_events(events_file)

    def _load_events(self, filepath: str) -> None:
        """Carica eventi da file JSON."""
        path = Path(filepath)
        if not path.exists():
            logger.warning("File calendario economico non trovato", path=filepath)
            return

        try:
            with path.open() as f:
                self._events = json.load(f)
            logger.info(
                "Calendario economico caricato",
                events_count=len(self._events),
            )
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Errore caricamento calendario", error=str(exc))

    def is_blackout(self, symbol: str, utc_now: datetime | None = None) -> tuple[bool, str]:
        """Controlla se siamo in periodo di blackout per il simbolo dato.

        Returns:
            Tupla (è_blackout, descrizione_evento).
        """
        if utc_now is None:
            utc_now = datetime.now(timezone.utc)

        # 1. Controlla eventi dal file JSON
        for event in self._events:
            event_time = datetime.fromisoformat(event["datetime"]).replace(tzinfo=timezone.utc)
            event_currency = event.get("currency", "")
            event_impact = event.get("impact", "low")

            if event_impact not in ("high", "critical"):
                continue

            affected_symbols = EVENT_CURRENCY_MAP.get(event_currency, [])
            if symbol not in affected_symbols:
                continue

            minutes_diff = (utc_now - event_time).total_seconds() / 60

            if -self._blackout_before <= minutes_diff <= self._blackout_after:
                return True, (
                    f"Blackout: {event.get('name', 'evento')} "
                    f"({event_currency}, {event_impact})"
                )

        # 2. Controlla pattern ricorrenti noti
        weekday = utc_now.weekday()
        hour = utc_now.hour
        minute = utc_now.minute
        day = utc_now.day

        # NFP check semplificato: primo venerdì del mese, 13:30 UTC
        if (
            weekday == 4  # Venerdì
            and day <= 7  # Prima settimana
            and symbol in EVENT_CURRENCY_MAP.get("USD", [])
        ):
            nfp_minute = 13 * 60 + 30
            current_minute = hour * 60 + minute
            diff = current_minute - nfp_minute

            if -self._blackout_before <= diff <= self._blackout_after:
                return True, "Blackout: probabile NFP (primo venerdì del mese)"

        return False, ""
