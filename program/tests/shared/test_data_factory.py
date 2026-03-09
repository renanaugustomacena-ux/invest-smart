"""Deterministic test data factory for MONEYMAKER.

All data is synthetic. No external API calls ever.
All values use Decimal for financial precision.
Patterns are deterministic — same call always returns same data.
"""

from decimal import Decimal
from datetime import datetime, timezone, timedelta


class BarFactory:
    """Generate deterministic OHLCV bar series."""

    @staticmethod
    def trending_up(
        count: int = 50,
        symbol: str = "XAUUSD",
        base_price: Decimal = Decimal("2650.00"),
        step: Decimal = Decimal("1.50"),
        timeframe: str = "M1",
        start_time: datetime | None = None,
    ) -> list[dict]:
        """Generate an uptrending bar series with deterministic oscillation."""
        if start_time is None:
            start_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        bars = []
        for i in range(count):
            mid = base_price + step * i
            noise = Decimal("0.50") * (1 if i % 3 == 0 else -1)
            bars.append({
                "symbol": symbol,
                "timeframe": timeframe,
                "time": start_time + timedelta(minutes=i),
                "open": mid - Decimal("0.30"),
                "high": mid + Decimal("1.00") + abs(noise),
                "low": mid - Decimal("0.80") - abs(noise),
                "close": mid + noise,
                "volume": Decimal(str(1000 + i * 10)),
                "tick_count": 30 + i,
                "complete": True,
            })
        return bars

    @staticmethod
    def trending_down(
        count: int = 50,
        symbol: str = "XAUUSD",
        base_price: Decimal = Decimal("2700.00"),
        step: Decimal = Decimal("1.50"),
        timeframe: str = "M1",
        start_time: datetime | None = None,
    ) -> list[dict]:
        """Generate a downtrending bar series."""
        if start_time is None:
            start_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        bars = []
        for i in range(count):
            mid = base_price - step * i
            noise = Decimal("0.40") * (1 if i % 2 == 0 else -1)
            bars.append({
                "symbol": symbol,
                "timeframe": timeframe,
                "time": start_time + timedelta(minutes=i),
                "open": mid + Decimal("0.20"),
                "high": mid + Decimal("0.80") + abs(noise),
                "low": mid - Decimal("1.00") - abs(noise),
                "close": mid + noise,
                "volume": Decimal(str(1200 + i * 8)),
                "tick_count": 28 + i,
                "complete": True,
            })
        return bars

    @staticmethod
    def ranging(
        count: int = 50,
        symbol: str = "XAUUSD",
        center: Decimal = Decimal("2660.00"),
        amplitude: Decimal = Decimal("3.00"),
        timeframe: str = "M1",
        start_time: datetime | None = None,
    ) -> list[dict]:
        """Generate a ranging (sideways) bar series oscillating around center."""
        if start_time is None:
            start_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        bars = []
        for i in range(count):
            # Deterministic sine-like oscillation using modular arithmetic
            phase = i % 8
            offsets = [0, 1, 2, 1, 0, -1, -2, -1]
            offset = Decimal(str(offsets[phase])) * amplitude / 2
            mid = center + offset

            bars.append({
                "symbol": symbol,
                "timeframe": timeframe,
                "time": start_time + timedelta(minutes=i),
                "open": mid - Decimal("0.20"),
                "high": mid + Decimal("0.60"),
                "low": mid - Decimal("0.60"),
                "close": mid + Decimal("0.10"),
                "volume": Decimal(str(900 + (i % 5) * 100)),
                "tick_count": 25 + (i % 10),
                "complete": True,
            })
        return bars


class SignalFactory:
    """Generate deterministic trading signals."""

    @staticmethod
    def valid_buy(
        symbol: str = "XAUUSD",
        confidence: Decimal = Decimal("0.72"),
        lots: Decimal = Decimal("0.05"),
    ) -> dict:
        return {
            "signal_id": "test-buy-001",
            "symbol": symbol,
            "direction": "BUY",
            "confidence": confidence,
            "suggested_lots": lots,
            "stop_loss": Decimal("2645.00"),
            "take_profit": Decimal("2665.00"),
            "regime": "trending_up",
            "source_tier": "TECHNICAL",
            "reasoning": "Test buy signal",
        }

    @staticmethod
    def valid_sell(
        symbol: str = "XAUUSD",
        confidence: Decimal = Decimal("0.68"),
        lots: Decimal = Decimal("0.03"),
    ) -> dict:
        return {
            "signal_id": "test-sell-001",
            "symbol": symbol,
            "direction": "SELL",
            "confidence": confidence,
            "suggested_lots": lots,
            "stop_loss": Decimal("2670.00"),
            "take_profit": Decimal("2640.00"),
            "regime": "trending_down",
            "source_tier": "TECHNICAL",
            "reasoning": "Test sell signal",
        }

    @staticmethod
    def hold(symbol: str = "XAUUSD") -> dict:
        return {
            "signal_id": "test-hold-001",
            "symbol": symbol,
            "direction": "HOLD",
            "confidence": Decimal("0.45"),
            "suggested_lots": Decimal("0"),
            "stop_loss": None,
            "take_profit": None,
            "regime": "ranging",
            "source_tier": "TECHNICAL",
            "reasoning": "No clear signal",
        }
