"""Maturity Gate — paper-to-live progression state machine.

Controls position sizing multiplier based on system maturity. A new
strategy (or fresh deployment) starts in DOUBT with tiny sizing and
must demonstrate consistent performance to graduate through states.

States and sizing multipliers:
    DOUBT      → 0.05x  (paper-equivalent, near-zero risk)
    LEARNING   → 0.35x  (small live exposure)
    CONVICTION → 0.80x  (growing confidence)
    MATURE     → 1.00x  (full sizing)

Transitions use hysteresis to prevent oscillation:
    Promotion:  3 consecutive positive conviction checks
    Demotion:   2 consecutive negative conviction checks

The ConvictionIndex scorer evaluates system health:
    conviction = 0.35*win_rate + 0.30*sharpe_norm + 0.20*pf_norm + 0.15*(1 - dd_pct/100)

All math uses Decimal for financial precision.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal
from enum import Enum


class MaturityState(str, Enum):
    """System maturity progression states."""

    DOUBT = "DOUBT"
    LEARNING = "LEARNING"
    CONVICTION = "CONVICTION"
    MATURE = "MATURE"


# Sizing multiplier per state
STATE_MULTIPLIERS: dict[MaturityState, Decimal] = {
    MaturityState.DOUBT: Decimal("0.05"),
    MaturityState.LEARNING: Decimal("0.35"),
    MaturityState.CONVICTION: Decimal("0.80"),
    MaturityState.MATURE: Decimal("1.00"),
}

# Ordered for promotion/demotion traversal
_STATE_ORDER = [
    MaturityState.DOUBT,
    MaturityState.LEARNING,
    MaturityState.CONVICTION,
    MaturityState.MATURE,
]

_ONE = Decimal("1")
_ZERO = Decimal("0")


def _clamp_01(value: Decimal) -> Decimal:
    """Clamp value to [0, 1]."""
    if value < _ZERO:
        return _ZERO
    if value > _ONE:
        return _ONE
    return value


@dataclass(frozen=True)
class ConvictionSnapshot:
    """Point-in-time conviction index calculation."""

    win_rate: Decimal         # [0, 1]
    sharpe_norm: Decimal      # [0, 1] — normalized Sharpe
    profit_factor_norm: Decimal  # [0, 1] — normalized PF
    drawdown_health: Decimal  # [0, 1] — (1 - dd_pct/100)
    conviction_index: Decimal  # [0, 1] weighted composite


class ConvictionIndex:
    """Calculate system conviction from performance metrics.

    Formula:
        conviction = 0.35*wr + 0.30*sharpe_norm + 0.20*pf_norm + 0.15*(1 - dd/100)

    Normalization:
        - Sharpe: clamp(sharpe / 3.0, 0, 1) — Sharpe of 3.0 maps to 1.0
        - Profit Factor: clamp((pf - 1.0) / 2.0, 0, 1) — PF of 3.0 maps to 1.0
        - Drawdown: clamp(1 - dd_pct/100, 0, 1) — 0% DD = 1.0, 100% DD = 0.0
    """

    W_WR = Decimal("0.35")
    W_SHARPE = Decimal("0.30")
    W_PF = Decimal("0.20")
    W_DD = Decimal("0.15")

    SHARPE_CAP = Decimal("3.0")
    PF_OFFSET = Decimal("1.0")
    PF_RANGE = Decimal("2.0")
    DD_DIVISOR = Decimal("100")

    def compute(
        self,
        win_rate: Decimal,
        sharpe_ratio: Decimal,
        profit_factor: Decimal,
        drawdown_pct: Decimal,
    ) -> ConvictionSnapshot:
        """Compute conviction index from performance metrics.

        Args:
            win_rate: Win rate [0, 1].
            sharpe_ratio: Annualized Sharpe ratio (unbounded).
            profit_factor: Gross profit / gross loss (>= 0).
            drawdown_pct: Current drawdown as percentage [0, 100].
        """
        wr = _clamp_01(win_rate)
        sharpe_norm = _clamp_01(sharpe_ratio / self.SHARPE_CAP)
        pf_norm = _clamp_01((profit_factor - self.PF_OFFSET) / self.PF_RANGE)
        dd_health = _clamp_01(_ONE - drawdown_pct / self.DD_DIVISOR)

        conviction = (
            self.W_WR * wr
            + self.W_SHARPE * sharpe_norm
            + self.W_PF * pf_norm
            + self.W_DD * dd_health
        ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)

        return ConvictionSnapshot(
            win_rate=wr,
            sharpe_norm=sharpe_norm,
            profit_factor_norm=pf_norm,
            drawdown_health=dd_health,
            conviction_index=conviction,
        )


class MaturityGate:
    """State machine controlling position sizing based on system maturity.

    Transitions require consecutive conviction checks above/below threshold:
        - Promotion: 3 consecutive checks with conviction >= promote_threshold
        - Demotion: 2 consecutive checks with conviction < demote_threshold
    """

    def __init__(
        self,
        *,
        promote_threshold: Decimal = Decimal("0.60"),
        demote_threshold: Decimal = Decimal("0.35"),
        promote_count: int = 3,
        demote_count: int = 2,
        initial_state: MaturityState = MaturityState.DOUBT,
    ) -> None:
        self._state = initial_state
        self._promote_threshold = promote_threshold
        self._demote_threshold = demote_threshold
        self._promote_count = promote_count
        self._demote_count = demote_count

        self._consecutive_positive = 0
        self._consecutive_negative = 0
        self._check_count = 0

    @property
    def state(self) -> MaturityState:
        return self._state

    @property
    def sizing_multiplier(self) -> Decimal:
        return STATE_MULTIPLIERS[self._state]

    @property
    def check_count(self) -> int:
        return self._check_count

    def evaluate(self, conviction: Decimal) -> MaturityState:
        """Evaluate conviction and potentially transition state.

        Args:
            conviction: Conviction index [0, 1] from ConvictionIndex.compute().

        Returns:
            Current MaturityState after evaluation.
        """
        self._check_count += 1

        if conviction >= self._promote_threshold:
            self._consecutive_positive += 1
            self._consecutive_negative = 0
        elif conviction < self._demote_threshold:
            self._consecutive_negative += 1
            self._consecutive_positive = 0
        else:
            # In the neutral zone — reset both counters
            self._consecutive_positive = 0
            self._consecutive_negative = 0

        # Check for promotion
        if self._consecutive_positive >= self._promote_count:
            self._promote()
            self._consecutive_positive = 0

        # Check for demotion
        if self._consecutive_negative >= self._demote_count:
            self._demote()
            self._consecutive_negative = 0

        return self._state

    def _promote(self) -> None:
        """Move to next higher state (if not already MATURE)."""
        idx = _STATE_ORDER.index(self._state)
        if idx < len(_STATE_ORDER) - 1:
            self._state = _STATE_ORDER[idx + 1]

    def _demote(self) -> None:
        """Move to next lower state (if not already DOUBT)."""
        idx = _STATE_ORDER.index(self._state)
        if idx > 0:
            self._state = _STATE_ORDER[idx - 1]

    def force_state(self, state: MaturityState) -> None:
        """Override state manually (for admin/emergency use)."""
        self._state = state
        self._consecutive_positive = 0
        self._consecutive_negative = 0
