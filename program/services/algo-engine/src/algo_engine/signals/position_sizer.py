# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Position Sizer — calcola la dimensione ottimale del trade basata sul rischio.

Come un ingegnere strutturale che calcola il peso massimo che un ponte
può sopportare: questo modulo determina quanti lotti tradare per non
rischiare più di una percentuale configurata dell'equity.

Formula: lots = (equity × risk%) / (SL_pips × pip_value_per_lot)

Utilizzo:
    sizer = PositionSizer(risk_per_trade_pct=Decimal("1.0"))
    lots = sizer.calculate(
        equity=Decimal("10000"),
        entry_price=Decimal("1.0850"),
        stop_loss=Decimal("1.0820"),
        pip_size=Decimal("0.0001"),
        pip_value_per_lot=Decimal("10"),
    )
"""

from __future__ import annotations

from decimal import Decimal

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.logging import get_logger

logger = get_logger(__name__)

# Dimensione pip per tipo di strumento
PIP_SIZES: dict[str, Decimal] = {
    "EURUSD": Decimal("0.0001"),
    "GBPUSD": Decimal("0.0001"),
    "USDJPY": Decimal("0.01"),
    "USDCHF": Decimal("0.0001"),
    "AUDUSD": Decimal("0.0001"),
    "NZDUSD": Decimal("0.0001"),
    "USDCAD": Decimal("0.0001"),
    "EURGBP": Decimal("0.0001"),
    "EURJPY": Decimal("0.01"),
    "GBPJPY": Decimal("0.01"),
    "XAUUSD": Decimal("0.01"),
    "XAGUSD": Decimal("0.001"),
}

# Valore pip per lotto standard (1.0 lot) in USD
PIP_VALUES: dict[str, Decimal] = {
    "EURUSD": Decimal("10"),
    "GBPUSD": Decimal("10"),
    "USDJPY": Decimal("6.7"),
    "USDCHF": Decimal("10"),
    "AUDUSD": Decimal("10"),
    "NZDUSD": Decimal("10"),
    "USDCAD": Decimal("7.5"),
    "EURGBP": Decimal("12.5"),
    "EURJPY": Decimal("6.7"),
    "GBPJPY": Decimal("6.7"),
    "XAUUSD": Decimal("1"),  # $1 per 0.01 move per 1 lot (100 oz)
    "XAGUSD": Decimal("50"),
}


def infer_pip_size(symbol: str, digits: int | None = None) -> Decimal:
    """Inferisce pip_size dal numero di cifre decimali o dal nome del simbolo.

    Se *digits* (da MT5 symbol_info) viene fornito, il pip_size viene
    calcolato direttamente: 5-digit forex -> 0.0001, 3-digit JPY -> 0.01.
    Altrimenti si usa la tabella statica + fallback euristico.

    Args:
        symbol: Nome dello strumento (es. "EURUSD").
        digits: Cifre decimali dallo symbol_info MT5 (opzionale).
    """
    if digits is not None:
        if digits <= 3:
            return Decimal("0.01")
        return Decimal("0.0001")

    if symbol in PIP_SIZES:
        return PIP_SIZES[symbol]

    s = symbol.upper()
    if s.endswith("JPY") or "JPY" in s:
        return Decimal("0.01")
    if s.startswith("XAU"):
        return Decimal("0.01")
    if s.startswith("XAG"):
        return Decimal("0.001")
    if any(idx in s for idx in ("US30", "US500", "NAS", "DAX", "FTSE", "JP225")):
        return Decimal("1.0")
    if any(c in s for c in ("BTC", "ETH", "LTC", "XRP")):
        return Decimal("1.0")

    logger.error(
        "Simbolo sconosciuto nel pip_size registry — sizing potenzialmente errato",
        symbol=symbol,
    )
    raise ValueError(
        f"Simbolo '{symbol}' non trovato nel PIP_SIZES registry e nessun pattern euristico corrisponde. "
        f"Aggiungere il simbolo a PIP_SIZES per evitare errori di sizing."
    )


def infer_pip_value(symbol: str) -> Decimal:
    """Inferisce pip_value dal nome del simbolo se non presente nella tabella.

    Valori approssimativi per conto USD.
    """
    if symbol in PIP_VALUES:
        return PIP_VALUES[symbol]

    s = symbol.upper()
    if s.endswith("JPY") or "JPY" in s:
        return Decimal("6.7")
    if s.startswith("XAU"):
        return Decimal("1")
    if s.startswith("XAG"):
        return Decimal("50")
    if any(idx in s for idx in ("US30", "US500", "NAS", "DAX")):
        return Decimal("1")
    if any(c in s for c in ("BTC", "ETH")):
        return Decimal("1")

    logger.error(
        "Simbolo sconosciuto nel pip_value registry — sizing potenzialmente errato",
        symbol=symbol,
    )
    raise ValueError(
        f"Simbolo '{symbol}' non trovato nel PIP_VALUES registry e nessun pattern euristico corrisponde. "
        f"Aggiungere il simbolo a PIP_VALUES per evitare errori di sizing."
    )


class PositionSizer:
    """Calcola lot size basata sul rischio per trade."""

    def __init__(
        self,
        risk_per_trade_pct: Decimal = Decimal("1.0"),
        default_equity: Decimal = Decimal("1000"),
        min_lots: Decimal = Decimal("0.01"),
        max_lots: Decimal = Decimal("0.10"),
    ) -> None:
        self._risk_pct = risk_per_trade_pct
        self._default_equity = default_equity
        self._min_lots = min_lots
        self._max_lots = max_lots

    @staticmethod
    def _drawdown_scaling(drawdown_pct: Decimal) -> Decimal:
        """Scala il sizing in base al drawdown corrente.

        0-2% -> 1.0, 2-4% -> 0.5, 4-5% -> 0.25, >5% -> 0.0
        """
        if drawdown_pct < Decimal("2"):
            return Decimal("1.0")
        if drawdown_pct < Decimal("4"):
            return Decimal("0.5")
        if drawdown_pct < Decimal("5"):
            return Decimal("0.25")
        return ZERO

    def calculate(
        self,
        symbol: str,
        entry_price: Decimal,
        stop_loss: Decimal,
        equity: Decimal | None = None,
        drawdown_pct: Decimal = ZERO,
    ) -> Decimal:
        """Calcola la dimensione del lotto basata sul rischio.

        Returns:
            Decimal: Dimensione del lotto, clamped a [min_lots, max_lots].
        """
        equity = equity if equity is not None else self._default_equity
        try:
            pip_size = infer_pip_size(symbol)
            pip_value = infer_pip_value(symbol)
        except ValueError:
            logger.critical(
                "Position sizer: simbolo non registrato, uso lotto minimo per sicurezza",
                symbol=symbol,
            )
            return self._min_lots

        sl_distance = abs(entry_price - stop_loss)
        if sl_distance.is_nan() or sl_distance.is_infinite():
            logger.warning("Position sizer: SL distance NaN/Inf", symbol=symbol)
            return self._min_lots
        if sl_distance <= ZERO or pip_size <= ZERO or pip_value <= ZERO:
            logger.warning(
                "Position sizer: parametri invalidi, uso lotto minimo",
                symbol=symbol,
                sl_distance=str(sl_distance),
            )
            return self._min_lots

        sl_pips = sl_distance / pip_size
        risk_amount = equity * self._risk_pct / Decimal("100")

        # Applica scaling drawdown
        dd_factor = self._drawdown_scaling(drawdown_pct)
        if dd_factor == ZERO:
            return self._min_lots
        risk_amount = risk_amount * dd_factor

        lots = risk_amount / (sl_pips * pip_value)

        # Clamp
        if lots < self._min_lots:
            lots = self._min_lots
        elif lots > self._max_lots:
            lots = self._max_lots

        # Arrotonda a 2 decimali (lotti standard)
        lots = lots.quantize(Decimal("0.01"))

        logger.debug(
            "Position sizing calcolato",
            symbol=symbol,
            equity=str(equity),
            risk_pct=str(self._risk_pct),
            sl_pips=str(sl_pips),
            calculated_lots=str(lots),
        )

        return lots
