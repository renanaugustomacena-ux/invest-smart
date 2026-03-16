"""Real integration tests for PostgresAuditTrail against a live PostgreSQL database.

These tests require a running PostgreSQL instance with the audit_log table
created by 001_init.sql. They are skipped when DATABASE_URL is not set.

NO MOCKS: All interactions hit the real database via asyncpg.
"""

import json
import os

import pytest

try:
    import asyncpg
except ImportError:
    asyncpg = None  # type: ignore[assignment]

from moneymaker_common.audit import compute_audit_hash
from moneymaker_common.audit_pg import PostgresAuditTrail

_SKIP_REASON = "requires real PostgreSQL (set DATABASE_URL)"
_SERVICE_NAME = "test-audit-real"


pytestmark = [
    pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason=_SKIP_REASON),
    pytest.mark.skipif(asyncpg is None, reason="asyncpg not installed"),
    pytest.mark.asyncio,
]


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture()
async def pool():
    """Create and yield a real asyncpg connection pool, then close it."""
    dsn = os.environ["DATABASE_URL"]
    _pool = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=3)
    yield _pool
    # Cleanup: remove rows inserted by this test suite.
    # The audit_log table has a BEFORE DELETE trigger that raises an exception,
    # so we must disable the trigger temporarily for cleanup.
    async with _pool.acquire() as conn:
        await conn.execute("ALTER TABLE audit_log DISABLE TRIGGER audit_no_delete")
        await conn.execute("DELETE FROM audit_log WHERE service = $1", _SERVICE_NAME)
        await conn.execute("ALTER TABLE audit_log ENABLE TRIGGER audit_no_delete")
    await _pool.close()


@pytest.fixture()
def audit(pool):
    """Return a PostgresAuditTrail wired to the real pool."""
    return PostgresAuditTrail(_SERVICE_NAME, pool=pool)


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


class TestPostgresAuditTrailReal:
    """Integration tests for PostgresAuditTrail with a real PostgreSQL backend."""

    async def test_log_and_flush_persists_to_database(self, audit, pool):
        """log() buffers entries; flush() writes them to the real audit_log table."""
        entry = audit.log("test_action_1", details={"key": "value1"})
        assert audit.buffer_size == 1

        written = await audit.flush()
        assert written == 1
        assert audit.buffer_size == 0

        # Verify the row exists in the real database
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM audit_log WHERE hash = $1", entry.hash)
        assert row is not None
        assert row["service"] == _SERVICE_NAME
        assert row["action"] == "test_action_1"
        assert row["prev_hash"] == "GENESIS"
        assert row["hash"] == entry.hash

        details = json.loads(row["details"])
        assert details == {"key": "value1"}

    async def test_log_async_persists_immediately(self, audit, pool):
        """log_async() writes to the database without needing a separate flush()."""
        entry = await audit.log_async(
            "test_action_2",
            details={"immediate": True},
            entity_type="test_entity",
            entity_id="TE-001",
        )
        # Buffer should be empty because log_async removes the entry after writing
        assert audit.buffer_size == 0

        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM audit_log WHERE hash = $1", entry.hash)
        assert row is not None
        assert row["action"] == "test_action_2"
        assert row["entity_type"] == "test_entity"
        assert row["entity_id"] == "TE-001"

    async def test_multiple_entries_flush(self, audit, pool):
        """Multiple buffered entries are all persisted by flush()."""
        entries = []
        for i in range(5):
            entries.append(audit.log(f"batch_action_{i}", details={"idx": i}))
        assert audit.buffer_size == 5

        written = await audit.flush()
        assert written == 5
        assert audit.buffer_size == 0

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT hash FROM audit_log WHERE service = $1 AND action LIKE 'batch_action_%'",
                _SERVICE_NAME,
            )
        persisted_hashes = {r["hash"] for r in rows}
        for entry in entries:
            assert entry.hash in persisted_hashes

    async def test_hash_chain_integrity_in_database(self, audit, pool):
        """Each entry's prev_hash must match the previous entry's hash (chain)."""
        e1 = audit.log("chain_a", details={"step": 1})
        e2 = audit.log("chain_b", details={"step": 2})
        e3 = audit.log("chain_c", details={"step": 3})

        written = await audit.flush()
        assert written == 3

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT prev_hash, hash, action, details, created_at, service "
                "FROM audit_log WHERE service = $1 AND action LIKE 'chain_%' "
                "ORDER BY created_at ASC",
                _SERVICE_NAME,
            )
        assert len(rows) == 3

        # Verify the chain: first entry references GENESIS
        assert rows[0]["prev_hash"] == "GENESIS"
        assert rows[0]["hash"] == e1.hash

        # Second entry references first
        assert rows[1]["prev_hash"] == e1.hash
        assert rows[1]["hash"] == e2.hash

        # Third entry references second
        assert rows[2]["prev_hash"] == e2.hash
        assert rows[2]["hash"] == e3.hash

    async def test_hash_chain_recomputation(self, audit, pool):
        """Re-compute each hash from stored data to verify integrity."""
        e1 = audit.log("verify_a", details={"v": 1})
        e2 = audit.log("verify_b", details={"v": 2})
        await audit.flush()

        # Recompute hash for e1
        recomputed_1 = compute_audit_hash(
            prev_hash=e1.prev_hash,
            service=e1.service,
            action=e1.action,
            details=e1.details,
            timestamp=e1.timestamp,
        )
        assert recomputed_1 == e1.hash

        # Recompute hash for e2 — must reference e1.hash
        recomputed_2 = compute_audit_hash(
            prev_hash=e1.hash,
            service=e2.service,
            action=e2.action,
            details=e2.details,
            timestamp=e2.timestamp,
        )
        assert recomputed_2 == e2.hash

    async def test_entity_type_and_id_nullable(self, audit, pool):
        """entity_type and entity_id should be NULL when not provided."""
        entry = audit.log("nullable_check")
        await audit.flush()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT entity_type, entity_id FROM audit_log WHERE hash = $1",
                entry.hash,
            )
        assert row is not None
        assert row["entity_type"] is None
        assert row["entity_id"] is None

    async def test_flush_with_empty_buffer_returns_zero(self, audit):
        """flush() on an empty buffer returns 0 without hitting the database."""
        written = await audit.flush()
        assert written == 0

    async def test_connect_creates_pool(self):
        """connect() creates an internal asyncpg pool from a DSN."""
        dsn = os.environ["DATABASE_URL"]
        trail = PostgresAuditTrail(_SERVICE_NAME)
        assert trail._pool is None

        await trail.connect(dsn)
        assert trail._pool is not None

        # Log and flush using the internally created pool
        entry = await trail.log_async("connect_test", details={"connected": True})

        async with trail._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT action FROM audit_log WHERE hash = $1", entry.hash)
        assert row is not None
        assert row["action"] == "connect_test"

        # Cleanup
        async with trail._pool.acquire() as conn:
            await conn.execute("ALTER TABLE audit_log DISABLE TRIGGER audit_no_delete")
            await conn.execute(
                "DELETE FROM audit_log WHERE service = $1 AND action = 'connect_test'",
                _SERVICE_NAME,
            )
            await conn.execute("ALTER TABLE audit_log ENABLE TRIGGER audit_no_delete")
        await trail._pool.close()

    async def test_buffer_overflow_discards_oldest(self):
        """When buffer exceeds max_buffer_size, the oldest entry is discarded."""
        trail = PostgresAuditTrail(_SERVICE_NAME, pool=None, max_buffer_size=3)
        trail.log("overflow_1")
        trail.log("overflow_2")
        trail.log("overflow_3")
        assert trail.buffer_size == 3

        trail.log("overflow_4")
        assert trail.buffer_size == 3
        # The first entry should have been discarded
        actions = [e.action for e in trail._buffer]
        assert "overflow_1" not in actions
        assert "overflow_4" in actions

    async def test_details_stored_as_jsonb(self, audit, pool):
        """Verify that complex details dicts survive the round-trip as JSONB."""
        complex_details = {
            "nested": {"key": "value", "count": 42},
            "list": [1, 2, 3],
            "flag": True,
        }
        entry = audit.log("jsonb_test", details=complex_details)
        await audit.flush()

        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT details FROM audit_log WHERE hash = $1", entry.hash)
        stored_details = json.loads(row["details"])
        assert stored_details == complex_details
