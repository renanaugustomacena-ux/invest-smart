# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Controllo correlazione esposizione — evita di scommettere tutto sullo stesso cavallo.

Decompone le posizioni aperte nelle valute componenti e verifica che
l'esposizione netta per singola valuta non sia eccessiva. Come un
investitore prudente che non mette tutte le uova nello stesso paniere.

Utilizzo:
    checker = CorrelationChecker(max_correlated_positions=2)
    allowed, reason = checker.check("EURUSD", "BUY", open_positions)
"""

from __future__ import annotations

from moneymaker_common.logging import get_logger

logger = get_logger(__name__)

# Mappa simbolo → (valuta_base, valuta_quote)
CURRENCY_PAIRS: dict[str, tuple[str, str]] = {
    "EURUSD": ("EUR", "USD"),
    "GBPUSD": ("GBP", "USD"),
    "USDJPY": ("USD", "JPY"),
    "USDCHF": ("USD", "CHF"),
    "AUDUSD": ("AUD", "USD"),
    "NZDUSD": ("NZD", "USD"),
    "USDCAD": ("USD", "CAD"),
    "EURGBP": ("EUR", "GBP"),
    "EURJPY": ("EUR", "JPY"),
    "GBPJPY": ("GBP", "JPY"),
    "XAUUSD": ("XAU", "USD"),
    "XAGUSD": ("XAG", "USD"),
}


def _decompose_exposure(symbol: str, direction: str) -> dict[str, float]:
    """Decompone una posizione nelle valute componenti.

    BUY EURUSD = +1 EUR, -1 USD
    SELL EURUSD = -1 EUR, +1 USD
    """
    pair = CURRENCY_PAIRS.get(symbol)
    if pair is None:
        logger.warning(
            "correlation_symbol_unmapped",
            symbol=symbol,
            direction=direction,
        )
        return {}

    base, quote = pair
    sign = 1.0 if direction == "BUY" else -1.0

    return {base: sign, quote: -sign}


class CorrelationChecker:
    """Controlla l'esposizione correlata prima di aprire nuove posizioni."""

    def __init__(self, max_exposure_per_currency: float = 3.0) -> None:
        """
        Args:
            max_exposure_per_currency: Esposizione netta massima per valuta
                (in unità di posizione). Es. 3.0 = max 3 posizioni nette
                nella stessa direzione per la stessa valuta.
        """
        self._max_exposure = max_exposure_per_currency

    def check(
        self,
        symbol: str,
        direction: str,
        open_positions: list[dict],
    ) -> tuple[bool, str]:
        """Verifica se aprire una nuova posizione supererebbe il limite di correlazione.

        Args:
            symbol: Simbolo della nuova posizione (es. "EURUSD").
            direction: Direzione ("BUY" o "SELL").
            open_positions: Lista di posizioni aperte, ogni dict con
                chiavi "symbol" e "direction".

        Returns:
            Tupla (è_permesso, motivo).
        """
        # Calcola esposizione netta corrente per valuta
        net_exposure: dict[str, float] = {}

        for pos in open_positions:
            decomp = _decompose_exposure(pos.get("symbol", ""), pos.get("direction", ""))
            for currency, amount in decomp.items():
                net_exposure[currency] = net_exposure.get(currency, 0.0) + amount

        # Aggiungi la nuova posizione proposta
        new_decomp = _decompose_exposure(symbol, direction)
        if not new_decomp:
            return True, ""  # Simbolo non mappato, permetti

        for currency, amount in new_decomp.items():
            projected = abs(net_exposure.get(currency, 0.0) + amount)
            if projected > self._max_exposure:
                reason = (
                    f"Esposizione {currency} eccessiva: "
                    f"{projected:.1f} > {self._max_exposure:.1f} "
                    f"(aggiungendo {direction} {symbol})"
                )
                logger.info(
                    "Correlazione bloccata",
                    symbol=symbol,
                    direction=direction,
                    currency=currency,
                    projected_exposure=f"{projected:.1f}",
                )
                return False, reason

        return True, ""
