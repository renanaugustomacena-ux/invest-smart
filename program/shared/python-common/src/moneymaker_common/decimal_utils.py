"""Utilità di precisione Decimal per MONEYMAKER.

Come un orologiaio svizzero: nella finanza, ogni centesimo conta.
I calcoli finanziari non devono MAI usare l'aritmetica a virgola
mobile IEEE 754. La classica dimostrazione:

    0.1 + 0.2 = 0.30000000000000004 in float

Un errore che si accumula su milioni di calcoli — come un orologio
che perde un millesimo di secondo ogni tick, dopo anni è fuori fase.

VINCOLO ARCHITETTURALE: Tutti i valori finanziari usano decimal.Decimal
in Python, e stringhe codificate nei messaggi protobuf.
"""

from __future__ import annotations

import decimal
from decimal import Decimal
from typing import Union

# Contesto Decimal globale per calcoli finanziari
FINANCIAL_CONTEXT = decimal.Context(
    prec=28,
    rounding=decimal.ROUND_HALF_EVEN,  # Arrotondamento del banchiere
)

# Costanti usate di frequente — le "unità di misura" base
ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")


def to_decimal(value: Union[str, int, float, Decimal]) -> Decimal:
    """Converte un valore in Decimal in modo sicuro.

    Per i float, converte via stringa per evitare artefatti di precisione.
    Meglio passare direttamente stringhe o interi.
    """
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        # Converte float → str → Decimal per evitare perdita di precisione
        return Decimal(str(value))
    return Decimal(str(value))


def decimal_to_str(value: Decimal, places: int = 8) -> str:
    """Converte Decimal in stringa con precisione fissa per codifica protobuf."""
    quantize_str = "0." + "0" * places
    return str(value.quantize(Decimal(quantize_str), rounding=decimal.ROUND_HALF_EVEN))


def calculate_pips(price_diff: Decimal, pip_size: Decimal) -> Decimal:
    """Calcola il numero di pips da una differenza di prezzo."""
    if pip_size == ZERO:
        return ZERO
    return price_diff / pip_size


def position_value(lots: Decimal, price: Decimal, contract_size: Decimal) -> Decimal:
    """Calcola il valore nozionale di una posizione."""
    return lots * price * contract_size


def calculate_lot_size(
    risk_amount: Decimal,
    stop_loss_pips: Decimal,
    pip_value: Decimal,
) -> Decimal:
    """Calcola la dimensione della posizione dal rischio e dalla distanza dello stop-loss."""
    if stop_loss_pips == ZERO or pip_value == ZERO:
        return ZERO
    return risk_amount / (stop_loss_pips * pip_value)


def pct_change(old_value: Decimal, new_value: Decimal) -> Decimal:
    """Calcola la variazione percentuale tra due valori."""
    if old_value == ZERO:
        return ZERO
    return ((new_value - old_value) / old_value) * HUNDRED
