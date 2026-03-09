"""Mock/stub implementations for external dependencies.

Used in integration tests to avoid real API calls.
All mocks return deterministic data.
"""

from decimal import Decimal
from datetime import datetime, timezone


class MockRedisClient:
    """In-memory Redis mock with async-compatible interface."""

    def __init__(self):
        self._store: dict[str, str] = {}
        self._expiry: dict[str, float] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._store[key] = value
        if ex:
            self._expiry[key] = ex

    async def delete(self, *keys: str) -> int:
        count = 0
        for key in keys:
            if key in self._store:
                del self._store[key]
                count += 1
        return count

    async def exists(self, key: str) -> bool:
        return key in self._store

    async def incr(self, key: str) -> int:
        val = int(self._store.get(key, "0")) + 1
        self._store[key] = str(val)
        return val

    async def ping(self) -> bool:
        return True

    def clear(self) -> None:
        self._store.clear()
        self._expiry.clear()


class MockPostgresPool:
    """Mock database connection pool for testing.

    Records queries for assertion without executing real SQL.
    """

    def __init__(self):
        self.queries: list[tuple[str, tuple]] = []
        self._mock_results: dict[str, list[dict]] = {}

    def set_mock_result(self, query_prefix: str, rows: list[dict]) -> None:
        """Pre-configure results for queries starting with given prefix."""
        self._mock_results[query_prefix] = rows

    async def fetch(self, query: str, *args) -> list[dict]:
        self.queries.append((query, args))
        for prefix, rows in self._mock_results.items():
            if query.strip().upper().startswith(prefix.upper()):
                return rows
        return []

    async def fetchrow(self, query: str, *args) -> dict | None:
        rows = await self.fetch(query, *args)
        return rows[0] if rows else None

    async def execute(self, query: str, *args) -> str:
        self.queries.append((query, args))
        return "DONE"

    async def close(self) -> None:
        pass


class MockMT5Terminal:
    """Mock MetaTrader5 terminal for testing without Windows/MT5."""

    def __init__(self):
        self.connected = True
        self.orders_sent: list[dict] = []
        self.positions: list[dict] = [
            {
                "ticket": 100001,
                "symbol": "XAUUSD",
                "type": 0,  # BUY
                "volume": 0.05,
                "price_open": Decimal("2650.00"),
                "sl": Decimal("2645.00"),
                "tp": Decimal("2665.00"),
                "profit": Decimal("12.50"),
                "time": int(datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc).timestamp()),
            }
        ]

    def initialize(self) -> bool:
        return self.connected

    def shutdown(self) -> None:
        self.connected = False

    def positions_get(self, symbol: str = None) -> list[dict]:
        if symbol:
            return [p for p in self.positions if p["symbol"] == symbol]
        return self.positions

    def order_send(self, request: dict) -> dict:
        self.orders_sent.append(request)
        return {
            "retcode": 10009,  # TRADE_RETCODE_DONE
            "deal": 200001 + len(self.orders_sent),
            "order": 300001 + len(self.orders_sent),
            "volume": request.get("volume", 0.01),
            "price": request.get("price", Decimal("2650.00")),
        }

    def account_info(self) -> dict:
        return {
            "balance": Decimal("10000.00"),
            "equity": Decimal("10012.50"),
            "margin": Decimal("325.00"),
            "margin_free": Decimal("9687.50"),
            "margin_level": Decimal("3081.54"),
            "currency": "USD",
        }
