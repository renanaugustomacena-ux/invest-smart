"""Tests for moneymaker_common.audit_pg — PostgresAuditTrail.

These tests verify the buffering and interface behavior without
requiring a real PostgreSQL connection. Integration tests with a
real database belong in a separate integration test suite.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from moneymaker_common.audit_pg import PostgresAuditTrail


class TestPostgresAuditTrail:
    def test_inherits_from_audit_trail(self):
        """PostgresAuditTrail is a subclass of AuditTrail."""
        from moneymaker_common.audit import AuditTrail

        assert issubclass(PostgresAuditTrail, AuditTrail)

    def test_sync_log_buffers_entry(self):
        """Calling sync log() buffers the entry."""
        audit = PostgresAuditTrail("test-service")
        entry = audit.log("test_action", details={"key": "value"})

        assert audit.buffer_size == 1
        assert entry.service == "test-service"
        assert entry.action == "test_action"

    def test_chain_integrity_preserved(self):
        """Hash chain works correctly through PostgresAuditTrail."""
        audit = PostgresAuditTrail("test-service")
        e1 = audit.log("first")
        e2 = audit.log("second")

        assert e1.prev_hash == "GENESIS"
        assert e2.prev_hash == e1.hash
        assert e1.hash != e2.hash
        assert audit.buffer_size == 2

    def test_buffer_accumulates(self):
        """Multiple log calls accumulate in buffer."""
        audit = PostgresAuditTrail("test-service")
        for i in range(5):
            audit.log(f"action_{i}")
        assert audit.buffer_size == 5

    def test_set_pool(self):
        """set_pool updates the internal pool."""
        audit = PostgresAuditTrail("test-service")
        assert audit._pool is None
        mock_pool = MagicMock()
        audit.set_pool(mock_pool)
        assert audit._pool is mock_pool

    @pytest.mark.asyncio
    async def test_flush_without_pool_returns_zero(self):
        """flush() with no pool returns 0."""
        audit = PostgresAuditTrail("test-service")
        audit.log("action")
        result = await audit.flush()
        assert result == 0
        assert audit.buffer_size == 1

    @pytest.mark.asyncio
    async def test_flush_with_mock_pool(self):
        """flush() writes buffered entries via the pool."""
        mock_conn = AsyncMock()
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        audit = PostgresAuditTrail("test-service", pool=mock_pool)
        audit.log("action_1")
        audit.log("action_2")
        assert audit.buffer_size == 2

        written = await audit.flush()
        assert written == 2
        assert audit.buffer_size == 0
        assert mock_conn.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_log_async_writes_immediately(self):
        """log_async() writes directly without needing flush()."""
        mock_conn = AsyncMock()
        mock_pool = MagicMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        audit = PostgresAuditTrail("test-service", pool=mock_pool)
        entry = await audit.log_async("immediate_action", details={"fast": True})

        assert entry.action == "immediate_action"
        assert audit.buffer_size == 0  # Was written, then removed from buffer
        assert mock_conn.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_log_async_falls_back_to_buffer_on_error(self):
        """log_async() keeps entry in buffer if write fails."""
        mock_pool = MagicMock()
        mock_pool.acquire.side_effect = Exception("DB connection lost")

        audit = PostgresAuditTrail("test-service", pool=mock_pool)
        entry = await audit.log_async("failing_action")

        assert entry.action == "failing_action"
        assert audit.buffer_size == 1  # Stays buffered

    @pytest.mark.asyncio
    async def test_log_async_without_pool_buffers(self):
        """log_async() without pool just buffers."""
        audit = PostgresAuditTrail("test-service")
        entry = await audit.log_async("no_pool_action")

        assert entry.action == "no_pool_action"
        assert audit.buffer_size == 1
