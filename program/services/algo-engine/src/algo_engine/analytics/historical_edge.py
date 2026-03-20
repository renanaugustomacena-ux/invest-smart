# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Historical Edge Tracker — rendimento storico per contesto di trading.

Traccia win rate, profitto medio, e expected value per ogni combinazione
di (symbol, regime, session). Un segnale in un contesto con edge storico
positivo merita più fiducia; uno senza edge storico è più rischioso.

Il tracker richiede un minimo di 30 trade (configurabile) prima di
considerare le statistiche affidabili — sotto questa soglia restituisce
edge "unknown" per evitare decisioni basate su campioni troppo piccoli.

Utilizzo:
    tracker = HistoricalEdgeTracker(min_trades=30)
    tracker.record_outcome("XAUUSD", "trending", "london", Decimal("50.00"))
    edge = tracker.get_edge("XAUUSD", "trending", "london")
    if edge.is_reliable:
        print(f"Win rate: {edge.win_rate}, EV: {edge.expected_value}")
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal

from moneymaker_common.decimal_utils import ZERO
from moneymaker_common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class EdgeStats:
    """Statistiche di edge per un singolo contesto (symbol, regime, session)."""

    wins: int = 0
    losses: int = 0
    total_profit: Decimal = ZERO
    total_loss: Decimal = ZERO

    @property
    def trade_count(self) -> int:
        return self.wins + self.losses

    @property
    def win_rate(self) -> Decimal:
        if self.trade_count == 0:
            return ZERO
        return (Decimal(str(self.wins)) / Decimal(str(self.trade_count))).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_EVEN
        )

    @property
    def avg_win(self) -> Decimal:
        if self.wins == 0:
            return ZERO
        return self.total_profit / Decimal(str(self.wins))

    @property
    def avg_loss(self) -> Decimal:
        if self.losses == 0:
            return ZERO
        return self.total_loss / Decimal(str(self.losses))

    @property
    def expected_value(self) -> Decimal:
        """EV = win_rate * avg_win + (1 - win_rate) * avg_loss."""
        if self.trade_count == 0:
            return ZERO
        wr = self.win_rate
        return (wr * self.avg_win + (Decimal("1") - wr) * self.avg_loss).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_EVEN
        )

    @property
    def profit_factor(self) -> Decimal:
        if self.total_loss == ZERO:
            return Decimal("Infinity") if self.total_profit > ZERO else ZERO
        return abs(self.total_profit / self.total_loss)


@dataclass(frozen=True)
class EdgeSnapshot:
    """Immutable snapshot of edge for a specific context."""

    symbol: str
    regime: str
    session: str
    win_rate: Decimal
    avg_win: Decimal
    avg_loss: Decimal
    expected_value: Decimal
    profit_factor: Decimal
    trade_count: int
    is_reliable: bool  # True if trade_count >= min_trades


class HistoricalEdgeTracker:
    """Track per-context trading edge from closed outcomes.

    Context key = (symbol, regime, session). Each combination gets
    its own EdgeStats accumulator.
    """

    def __init__(self, min_trades: int = 30) -> None:
        self._min_trades = min_trades
        self._edges: dict[tuple[str, str, str], EdgeStats] = {}

    @staticmethod
    def _key(symbol: str, regime: str, session: str) -> tuple[str, str, str]:
        return (symbol.upper(), regime.lower(), session.lower())

    def record_outcome(
        self,
        symbol: str,
        regime: str,
        session: str,
        profit: Decimal,
    ) -> None:
        """Record a closed trade outcome in the given context."""
        key = self._key(symbol, regime, session)
        if key not in self._edges:
            self._edges[key] = EdgeStats()
        stats = self._edges[key]

        if profit > ZERO:
            stats.wins += 1
            stats.total_profit += profit
        elif profit < ZERO:
            stats.losses += 1
            stats.total_loss += profit  # negative

    def get_edge(self, symbol: str, regime: str, session: str) -> EdgeSnapshot:
        """Get the edge snapshot for a specific context."""
        key = self._key(symbol, regime, session)
        stats = self._edges.get(key, EdgeStats())

        return EdgeSnapshot(
            symbol=symbol.upper(),
            regime=regime.lower(),
            session=session.lower(),
            win_rate=stats.win_rate,
            avg_win=stats.avg_win,
            avg_loss=stats.avg_loss,
            expected_value=stats.expected_value,
            profit_factor=stats.profit_factor,
            trade_count=stats.trade_count,
            is_reliable=stats.trade_count >= self._min_trades,
        )

    def get_all_edges(self) -> list[EdgeSnapshot]:
        """Get snapshots for all tracked contexts."""
        results = []
        for (sym, reg, ses), stats in self._edges.items():
            results.append(
                EdgeSnapshot(
                    symbol=sym,
                    regime=reg,
                    session=ses,
                    win_rate=stats.win_rate,
                    avg_win=stats.avg_win,
                    avg_loss=stats.avg_loss,
                    expected_value=stats.expected_value,
                    profit_factor=stats.profit_factor,
                    trade_count=stats.trade_count,
                    is_reliable=stats.trade_count >= self._min_trades,
                )
            )
        return results

    def get_report(self) -> dict[str, dict]:
        """Serialize all edges to a flat report dict."""
        report = {}
        for (sym, reg, ses), stats in self._edges.items():
            label = f"{sym}|{reg}|{ses}"
            report[label] = {
                "trades": stats.trade_count,
                "win_rate": str(stats.win_rate),
                "avg_win": str(stats.avg_win),
                "avg_loss": str(stats.avg_loss),
                "expected_value": str(stats.expected_value),
                "profit_factor": str(stats.profit_factor),
                "reliable": stats.trade_count >= self._min_trades,
            }
        return report
