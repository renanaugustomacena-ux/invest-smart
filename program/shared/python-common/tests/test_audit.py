"""Tests for moneymaker_common.audit."""

from datetime import datetime, timezone

from moneymaker_common.audit import AuditTrail, compute_audit_hash


class TestComputeAuditHash:
    def test_deterministic(self):
        ts = datetime(2025, 1, 1, tzinfo=timezone.utc)
        h1 = compute_audit_hash("GENESIS", "brain", "SIGNAL", {"id": "1"}, ts)
        h2 = compute_audit_hash("GENESIS", "brain", "SIGNAL", {"id": "1"}, ts)
        assert h1 == h2

    def test_is_hex_sha256(self):
        ts = datetime(2025, 1, 1, tzinfo=timezone.utc)
        h = compute_audit_hash("GENESIS", "test", "ACTION", {}, ts)
        assert len(h) == 64  # SHA-256 hex length
        assert all(c in "0123456789abcdef" for c in h)

    def test_different_inputs_different_hash(self):
        ts = datetime(2025, 1, 1, tzinfo=timezone.utc)
        h1 = compute_audit_hash("GENESIS", "brain", "SIGNAL", {"id": "1"}, ts)
        h2 = compute_audit_hash("GENESIS", "brain", "SIGNAL", {"id": "2"}, ts)
        assert h1 != h2

    def test_different_prev_hash_changes_output(self):
        ts = datetime(2025, 1, 1, tzinfo=timezone.utc)
        h1 = compute_audit_hash("GENESIS", "brain", "SIGNAL", {}, ts)
        h2 = compute_audit_hash("other_hash", "brain", "SIGNAL", {}, ts)
        assert h1 != h2


class TestAuditTrail:
    def test_first_entry_uses_genesis(self):
        trail = AuditTrail("test-service")
        entry = trail.log("ACTION_1", {"key": "val"})
        assert entry.prev_hash == "GENESIS"

    def test_chain_integrity(self):
        trail = AuditTrail("test-service")
        entry1 = trail.log("ACTION_1", {"key": "val1"})
        entry2 = trail.log("ACTION_2", {"key": "val2"})
        assert entry2.prev_hash == entry1.hash
        assert entry1.hash != entry2.hash

    def test_three_entry_chain(self):
        trail = AuditTrail("test-service")
        e1 = trail.log("A")
        e2 = trail.log("B")
        e3 = trail.log("C")
        assert e1.prev_hash == "GENESIS"
        assert e2.prev_hash == e1.hash
        assert e3.prev_hash == e2.hash

    def test_entry_fields(self):
        trail = AuditTrail("my-service")
        entry = trail.log(
            "TRADE_OPENED",
            details={"symbol": "XAUUSD"},
            entity_type="trade",
            entity_id="T-001",
        )
        assert entry.service == "my-service"
        assert entry.action == "TRADE_OPENED"
        assert entry.entity_type == "trade"
        assert entry.entity_id == "T-001"
        assert entry.details == {"symbol": "XAUUSD"}
        assert entry.timestamp.tzinfo == timezone.utc
