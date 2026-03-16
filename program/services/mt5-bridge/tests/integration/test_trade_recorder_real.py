"""Integration tests for TradeRecorder against a real PostgreSQL database.

Requires a running PostgreSQL instance and DATABASE_URL environment variable.
The trade_records table is created on-the-fly since it is not part of the
standard 001_init.sql (the TradeRecorder uses its own table schema).

NO MOCKS: every interaction hits a real asyncpg pool and real database.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import asyncpg
import pytest

from mt5_bridge.trade_recorder import TradeRecorder

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="requires real PostgreSQL (set DATABASE_URL)",
)

# DDL for the trade_records table used by TradeRecorder._INSERT_SQL
_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS trade_records (
    id              BIGSERIAL       PRIMARY KEY,
    signal_id       TEXT            NOT NULL,
    symbol          TEXT            NOT NULL,
    timeframe       TEXT            NOT NULL DEFAULT 'M5',
    direction       TEXT            NOT NULL,
    lots            NUMERIC(10,4)  NOT NULL,
    entry_price     NUMERIC(20,8)  NOT NULL,
    exit_price      NUMERIC(20,8)  NOT NULL,
    stop_loss       NUMERIC(20,8)  NOT NULL DEFAULT 0,
    take_profit     NUMERIC(20,8)  NOT NULL DEFAULT 0,
    spread_at_entry INTEGER,
    outcome         TEXT            NOT NULL,
    pnl             NUMERIC(20,8)  NOT NULL DEFAULT 0,
    pnl_pips        NUMERIC(20,4),
    regime          TEXT            DEFAULT 'unknown',
    session_type    TEXT            DEFAULT 'unknown',
    strategy        TEXT            DEFAULT 'conservative',
    advisor_mode    TEXT            DEFAULT 'conservative',
    confidence      NUMERIC(5,4)   DEFAULT 0.0,
    maturity_state  TEXT            DEFAULT 'doubt',
    model_version   TEXT            DEFAULT '',
    opened_at       TIMESTAMPTZ    NOT NULL,
    closed_at       TIMESTAMPTZ    NOT NULL,
    dataset_split   TEXT            DEFAULT 'unassigned'
);
"""


@pytest.fixture
async def db_pool():
    """Create a real asyncpg connection pool and ensure the table exists."""
    database_url = os.environ["DATABASE_URL"]
    pool = await asyncpg.create_pool(database_url, min_size=1, max_size=3)
    async with pool.acquire() as conn:
        await conn.execute(_CREATE_TABLE_SQL)
    yield pool
    await pool.close()


@pytest.fixture
async def recorder(db_pool):
    """Create a TradeRecorder connected to the real database."""
    database_url = os.environ["DATABASE_URL"]
    rec = TradeRecorder(database_url=database_url)
    await rec.connect()
    yield rec
    await rec.close()


@pytest.fixture
def trade_result():
    """A realistic trade result dict, as produced by PositionTracker."""
    unique_id = uuid.uuid4().hex[:12]
    return {
        "ticket": int(unique_id[:8], 16),
        "signal_id": f"test_{unique_id}",
        "symbol": "XAUUSD",
        "direction": "BUY",
        "volume": "0.10",
        "price_open": "2050.50",
        "price_close": "2055.75",
        "stop_loss": "2045.00",
        "take_profit": "2060.00",
        "profit": "52.50",
        "open_time": 1700000000,
        "close_time": 1700003600,
    }


async def _cleanup_signal(pool: asyncpg.Pool, signal_id: str) -> None:
    """Remove a test trade record by signal_id."""
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM trade_records WHERE signal_id = $1", signal_id)


# -------------------------------------------------------------------------
# Tests
# -------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_closed_trade_inserts_row(db_pool, recorder, trade_result):
    """record_closed_trade() should insert a row and return the record id."""
    signal_id = trade_result["signal_id"]
    try:
        record_id = await recorder.record_closed_trade(trade_result)

        assert record_id is not None
        assert isinstance(record_id, int)

        # Verify the row exists in the real database
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM trade_records WHERE id = $1", record_id)

        assert row is not None
        assert row["signal_id"] == signal_id
        assert row["symbol"] == "XAUUSD"
        assert row["direction"] == "buy"
        assert row["outcome"] == "win"
        assert row["pnl"] == Decimal("52.50")
    finally:
        await _cleanup_signal(db_pool, signal_id)


@pytest.mark.asyncio
async def test_record_closed_trade_win_outcome(db_pool, recorder, trade_result):
    """A trade with profit > breakeven_threshold should be recorded as 'win'."""
    trade_result["profit"] = "10.00"
    signal_id = trade_result["signal_id"]
    try:
        record_id = await recorder.record_closed_trade(trade_result)

        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT outcome FROM trade_records WHERE id = $1", record_id)
        assert row["outcome"] == "win"
    finally:
        await _cleanup_signal(db_pool, signal_id)


@pytest.mark.asyncio
async def test_record_closed_trade_loss_outcome(db_pool, recorder, trade_result):
    """A trade with profit < -breakeven_threshold should be recorded as 'loss'."""
    trade_result["profit"] = "-15.30"
    signal_id = trade_result["signal_id"]
    try:
        record_id = await recorder.record_closed_trade(trade_result)

        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT outcome FROM trade_records WHERE id = $1", record_id)
        assert row["outcome"] == "loss"
    finally:
        await _cleanup_signal(db_pool, signal_id)


@pytest.mark.asyncio
async def test_record_closed_trade_breakeven_outcome(db_pool, recorder, trade_result):
    """A trade with profit within breakeven threshold should be 'breakeven'."""
    trade_result["profit"] = "0.10"
    signal_id = trade_result["signal_id"]
    try:
        record_id = await recorder.record_closed_trade(trade_result)

        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT outcome FROM trade_records WHERE id = $1", record_id)
        assert row["outcome"] == "breakeven"
    finally:
        await _cleanup_signal(db_pool, signal_id)


@pytest.mark.asyncio
async def test_record_closed_trade_with_market_context(db_pool, recorder, trade_result):
    """Market context fields should be stored in the database row."""
    signal_id = trade_result["signal_id"]
    context = {
        "timeframe": "H1",
        "regime": "trending_up",
        "session_type": "london",
        "strategy": "momentum",
        "advisor_mode": "aggressive",
        "confidence": "0.92",
        "maturity_state": "conviction",
        "model_version": "v2.1.0",
        "spread_at_entry": 12,
    }
    try:
        record_id = await recorder.record_closed_trade(trade_result, market_context=context)

        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT timeframe, regime, session_type, strategy, "
                "advisor_mode, confidence, maturity_state, model_version, "
                "spread_at_entry FROM trade_records WHERE id = $1",
                record_id,
            )

        assert row["timeframe"] == "H1"
        assert row["regime"] == "trending_up"
        assert row["session_type"] == "london"
        assert row["strategy"] == "momentum"
        assert row["advisor_mode"] == "aggressive"
        assert row["confidence"] == Decimal("0.9200")
        assert row["maturity_state"] == "conviction"
        assert row["model_version"] == "v2.1.0"
        assert row["spread_at_entry"] == 12
    finally:
        await _cleanup_signal(db_pool, signal_id)


@pytest.mark.asyncio
async def test_record_closed_trade_timestamps(db_pool, recorder, trade_result):
    """opened_at and closed_at should be correctly derived from Unix timestamps."""
    signal_id = trade_result["signal_id"]
    try:
        record_id = await recorder.record_closed_trade(trade_result)

        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT opened_at, closed_at FROM trade_records WHERE id = $1",
                record_id,
            )

        expected_open = datetime.fromtimestamp(1700000000, tz=timezone.utc)
        expected_close = datetime.fromtimestamp(1700003600, tz=timezone.utc)
        assert row["opened_at"] == expected_open
        assert row["closed_at"] == expected_close
    finally:
        await _cleanup_signal(db_pool, signal_id)


@pytest.mark.asyncio
async def test_record_closed_trade_pnl_pips(db_pool, recorder, trade_result):
    """PnL in pips should be calculated correctly for XAUUSD (pip = 0.01)."""
    signal_id = trade_result["signal_id"]
    try:
        record_id = await recorder.record_closed_trade(trade_result)

        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT pnl_pips FROM trade_records WHERE id = $1", record_id)

        # BUY XAUUSD: (2055.75 - 2050.50) / 0.01 = 525.00 pips
        assert row["pnl_pips"] == Decimal("525.00")
    finally:
        await _cleanup_signal(db_pool, signal_id)


@pytest.mark.asyncio
async def test_get_recent_trades(db_pool, recorder, trade_result):
    """get_recent_trades() should return the trade we just recorded."""
    signal_id = trade_result["signal_id"]
    try:
        await recorder.record_closed_trade(trade_result)

        trades = await recorder.get_recent_trades(limit=10, symbol="XAUUSD")
        assert len(trades) >= 1

        found = any(t["signal_id"] == signal_id for t in trades)
        assert found, f"Expected signal_id {signal_id} in recent trades"
    finally:
        await _cleanup_signal(db_pool, signal_id)


@pytest.mark.asyncio
async def test_not_connected_returns_none():
    """record_closed_trade() should return None when not connected."""
    recorder = TradeRecorder(database_url="postgresql://fake:5432/fake")
    # Do NOT call connect() — recorder is disconnected
    result = await recorder.record_closed_trade({"symbol": "TEST", "profit": "0"})
    assert result is None


@pytest.mark.asyncio
async def test_full_lifecycle(db_pool):
    """Full lifecycle: create, connect, record, query, close."""
    database_url = os.environ["DATABASE_URL"]
    rec = TradeRecorder(database_url=database_url)

    assert not rec.is_connected
    await rec.connect()
    assert rec.is_connected

    unique_id = uuid.uuid4().hex[:12]
    signal_id = f"lifecycle_{unique_id}"
    trade_data = {
        "ticket": 99999,
        "signal_id": signal_id,
        "symbol": "EURUSD",
        "direction": "SELL",
        "volume": "0.05",
        "price_open": "1.09500",
        "price_close": "1.09200",
        "stop_loss": "1.10000",
        "take_profit": "1.08500",
        "profit": "15.00",
        "open_time": 1700000000,
        "close_time": 1700001800,
    }

    try:
        record_id = await rec.record_closed_trade(trade_data)
        assert record_id is not None

        # Verify via direct DB query
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT symbol, direction, outcome, pnl FROM trade_records WHERE id = $1",
                record_id,
            )
        assert row["symbol"] == "EURUSD"
        assert row["direction"] == "sell"
        assert row["outcome"] == "win"
        assert row["pnl"] == Decimal("15.00")

        # Query via the recorder itself
        trades = await rec.get_recent_trades(limit=5, symbol="EURUSD")
        assert any(t["signal_id"] == signal_id for t in trades)
    finally:
        await _cleanup_signal(db_pool, signal_id)
        await rec.close()
        assert not rec.is_connected
