# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Kill switch commands — emergency trading halt via Redis."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone

_logger = logging.getLogger(__name__)

from moneymaker_console.clients import ClientFactory
from moneymaker_console.console_logging import log_event
from moneymaker_console.registry import CommandRegistry

_KILL_KEY = "moneymaker:kill_switch"
_ALERT_CHANNEL = "moneymaker:alerts"
_SERVICE_NAME = "console"


def _persist_to_audit_log(action: str, details: dict | None = None) -> None:
    """Write a kill switch event to the PostgreSQL audit_log table.

    Maintains the SHA-256 hash chain.  Silently skips if PostgreSQL is
    unavailable — the file-based log_event() call remains the fallback.
    """
    try:
        from moneymaker_common.audit import compute_audit_hash
    except ImportError:
        return

    try:
        db = ClientFactory.get_postgres()
        if not db.ping():
            return

        details = details or {}
        now = datetime.now(timezone.utc)

        # Fetch the last hash to continue the chain
        row = db.query_one("SELECT hash FROM audit_log ORDER BY id DESC LIMIT 1")
        prev_hash = row[0] if row else "GENESIS"

        entry_hash = compute_audit_hash(
            prev_hash=prev_hash,
            service=_SERVICE_NAME,
            action=action,
            details=details,
            timestamp=now,
        )

        db.execute(
            "INSERT INTO audit_log "
            "(created_at, service, action, entity_type, entity_id, details, prev_hash, hash) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (
                now,
                _SERVICE_NAME,
                action,
                "kill_switch",
                None,
                json.dumps(details, sort_keys=True, default=str),
                prev_hash,
                entry_hash,
            ),
        )
    except Exception:
        _logger.error(
            "Kill switch audit persistence to PostgreSQL failed "
            "(file-based log_event already captured the event)",
            exc_info=True,
        )


def _kill_status(*args: str) -> str:
    """Check the current kill switch state."""
    redis = ClientFactory.get_redis()
    if not redis.ping():
        return "[warning] Redis not connected. Kill switch state unknown."

    data = redis.get_json(_KILL_KEY)
    if data and data.get("active"):
        reason = data.get("reason", "No reason provided")
        activated_at = data.get("activated_at", "unknown")
        return (
            f"[error] KILL SWITCH ACTIVE\n"
            f"  Reason:       {reason}\n"
            f"  Activated at: {activated_at}\n"
            f"  Auto-close:   {data.get('auto_close_positions', True)}\n\n"
            f"  Deactivate with: kill deactivate"
        )
    return "[success] Kill switch INACTIVE. Trading allowed."


def _kill_activate(*args: str) -> str:
    """Activate the global kill switch."""
    reason = " ".join(args) if args else "Manual activation from console"

    redis = ClientFactory.get_redis()
    if not redis.ping():
        return "[error] Redis not connected. Cannot activate kill switch."

    payload = {
        "active": True,
        "reason": reason,
        "activated_at": time.time(),
        "activated_by": "console_operator",
        "auto_close_positions": True,
    }

    redis.set_json(_KILL_KEY, payload)
    redis.publish(
        _ALERT_CHANNEL,
        json.dumps(
            {
                "severity": "CRITICAL",
                "message": f"Kill switch ACTIVATED: {reason}",
                "timestamp": time.time(),
            }
        ),
    )

    log_event("kill_switch_activated", reason=reason)
    _persist_to_audit_log("kill_switch_activated", {"reason": reason})
    return (
        f"[error] KILL SWITCH ACTIVATED\n"
        f"  Reason: {reason}\n"
        f"  All trading halted. Positions will be closed.\n"
        f"  Deactivate with: kill deactivate"
    )


def _kill_deactivate(*args: str) -> str:
    """Deactivate the kill switch."""
    redis = ClientFactory.get_redis()
    if not redis.ping():
        return "[error] Redis not connected. Cannot deactivate kill switch."

    redis.delete(_KILL_KEY)
    redis.publish(
        _ALERT_CHANNEL,
        json.dumps(
            {
                "severity": "INFO",
                "message": "Kill switch DEACTIVATED. Trading restored.",
                "timestamp": time.time(),
            }
        ),
    )

    log_event("kill_switch_deactivated")
    _persist_to_audit_log("kill_switch_deactivated")
    return "[success] Kill switch deactivated. Trading restored."


def _kill_history_from_db() -> list[str] | None:
    """Try to read kill switch history from the audit_log table.

    Returns formatted lines on success, or None if PostgreSQL is unavailable.
    """
    try:
        db = ClientFactory.get_postgres()
        if not db.ping():
            return None

        rows = db.query(
            "SELECT created_at, action, details "
            "FROM audit_log "
            "WHERE action IN ('kill_switch_activated', 'kill_switch_deactivated') "
            "ORDER BY created_at DESC "
            "LIMIT 20"
        )
        if not rows:
            return None

        entries: list[str] = []
        for row in rows:
            ts = str(row[0])[:19]
            event = str(row[1]).replace("kill_switch_", "").upper()
            details = row[2] if isinstance(row[2], dict) else {}
            reason = details.get("reason", "")
            entries.append(f"  {ts}  {event:12s}  {reason}")
        return entries
    except Exception:
        return None


def _kill_history_from_files() -> list[str]:
    """Read kill switch history from console JSON log files (fallback)."""
    from pathlib import Path

    log_dir = Path(__file__).resolve().parent.parent.parent.parent / "logs"
    if not log_dir.exists():
        return []

    entries: list[str] = []
    for log_file in sorted(log_dir.glob("console_*.json"), reverse=True)[:7]:
        try:
            with open(log_file, encoding="utf-8") as f:
                for line in f:
                    data = json.loads(line)
                    if data.get("event") in (
                        "kill_switch_activated",
                        "kill_switch_deactivated",
                    ):
                        ts = data.get("ts", "?")[:19]
                        event = data["event"].replace("kill_switch_", "").upper()
                        reason = data.get("reason", "")
                        entries.append(f"  {ts}  {event:12s}  {reason}")
        except (json.JSONDecodeError, OSError):
            continue
    return entries


def _kill_history(*args: str) -> str:
    """Display kill switch activation history.

    Primary source: PostgreSQL audit_log table (persistent, survives log rotation).
    Fallback: console JSON log files (last 7 days).
    """
    # Try audit_log first
    db_entries = _kill_history_from_db()
    if db_entries:
        return "Kill Switch History (from audit_log):\n" + "\n".join(db_entries[:20])

    # Fallback to file-based history
    file_entries = _kill_history_from_files()
    if file_entries:
        return "Kill Switch History (from console logs — last 7 days):\n" + "\n".join(
            file_entries[:20]
        )

    return "[info] No kill switch events found."


def _kill_test(*args: str) -> str:
    """Test the kill switch mechanism without activating it."""
    redis = ClientFactory.get_redis()
    results: list[str] = ["Kill Switch Test Report:"]

    # 1. Redis connectivity
    if redis.ping():
        results.append("  [OK] Redis connection")
    else:
        results.append("  [FAIL] Redis not connected")
        return "\n".join(results)

    # 2. Write/read test key
    test_key = "moneymaker:kill_switch_test"
    redis.set(test_key, "test", ex=5)
    val = redis.get(test_key)
    if val == "test":
        results.append("  [OK] Redis write/read")
    else:
        results.append("  [FAIL] Redis write/read failed")

    redis.delete(test_key)

    # 3. Pub/sub test
    ok = redis.publish(
        _ALERT_CHANNEL,
        json.dumps(
            {
                "severity": "TEST",
                "message": "Kill switch test — ignore this alert",
                "timestamp": time.time(),
            }
        ),
    )
    if ok:
        results.append("  [OK] Pub/sub delivery")
    else:
        results.append("  [FAIL] Pub/sub delivery failed")

    # 4. Current state
    data = redis.get_json(_KILL_KEY)
    if data and data.get("active"):
        results.append("  [WARN] Kill switch is currently ACTIVE")
    else:
        results.append("  [OK] Kill switch is currently INACTIVE")

    return "\n".join(results)


def register(registry: CommandRegistry) -> None:
    registry.register("kill", "status", _kill_status, "Kill switch state", aliases=["k status"])
    registry.register(
        "kill",
        "activate",
        _kill_activate,
        "Activate kill switch (+ reason)",
        requires_confirmation=True,
        dangerous=True,
    )
    registry.register(
        "kill", "deactivate", _kill_deactivate, "Deactivate kill switch", requires_confirmation=True
    )
    registry.register("kill", "history", _kill_history, "Activation/deactivation history")
    registry.register("kill", "test", _kill_test, "Test kill switch mechanism")
