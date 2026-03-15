"""Performance Attribution per Strategia — il "pagelle" di ogni strategia.

Traccia le metriche di ogni strategia individualmente per capire quale
sta contribuendo ai profitti e quale sta causando perdite. Come un
allenatore che monitora le statistiche di ogni giocatore della squadra.

Utilizzo:
    attr = StrategyAttribution()
    attr.record_signal("trend_following", "BUY", Decimal("0.75"))
    attr.record_outcome("trend_following", Decimal("50.00"))
    report = attr.get_report()
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class StrategyStats:
    """Statistiche per una singola strategia."""

    signals_count: int = 0
    wins: int = 0
    losses: int = 0
    total_profit: Decimal = ZERO
    total_loss: Decimal = ZERO
    confidence_sum: Decimal = ZERO

    @property
    def win_rate(self) -> Decimal:
        total = self.wins + self.losses
        if total == 0:
            return ZERO
        return Decimal(str(self.wins)) / Decimal(str(total))

    @property
    def profit_factor(self) -> Decimal:
        if self.total_loss == ZERO:
            return Decimal("Infinity") if self.total_profit > ZERO else ZERO
        return abs(self.total_profit / self.total_loss)

    @property
    def net_profit(self) -> Decimal:
        return self.total_profit + self.total_loss  # loss è già negativo

    @property
    def avg_confidence(self) -> Decimal:
        if self.signals_count == 0:
            return ZERO
        return self.confidence_sum / Decimal(str(self.signals_count))


class StrategyAttribution:
    """Traccia le performance per strategia."""

    def __init__(self) -> None:
        self._stats: dict[str, StrategyStats] = {}

    def _ensure_stats(self, strategy_name: str) -> StrategyStats:
        if strategy_name not in self._stats:
            self._stats[strategy_name] = StrategyStats()
        return self._stats[strategy_name]

    def record_signal(self, strategy_name: str, direction: str, confidence: Decimal) -> None:
        """Registra l'emissione di un segnale da una strategia."""
        stats = self._ensure_stats(strategy_name)
        stats.signals_count += 1
        stats.confidence_sum += confidence

    def record_outcome(self, strategy_name: str, profit: Decimal) -> None:
        """Registra l'esito di un trade chiuso per una strategia."""
        stats = self._ensure_stats(strategy_name)
        if profit > ZERO:
            stats.wins += 1
            stats.total_profit += profit
        elif profit < ZERO:
            stats.losses += 1
            stats.total_loss += profit  # negativo

    def get_report(self) -> dict[str, dict]:
        """Genera il report di attribuzione per tutte le strategie."""
        report = {}
        for name, stats in self._stats.items():
            report[name] = {
                "signals": stats.signals_count,
                "wins": stats.wins,
                "losses": stats.losses,
                "win_rate": str(stats.win_rate),
                "net_profit": str(stats.net_profit),
                "profit_factor": str(stats.profit_factor),
                "avg_confidence": str(stats.avg_confidence),
            }
        return report

    def get_strategy_names(self) -> list[str]:
        """Lista delle strategie tracciate."""
        return list(self._stats.keys())
