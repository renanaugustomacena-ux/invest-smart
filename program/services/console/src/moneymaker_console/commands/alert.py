# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""Alerting and notification system commands."""

from __future__ import annotations

import os

from moneymaker_console.registry import CommandRegistry


def _alert_status(*args: str) -> str:
    """Display alerting system status."""
    lines = ["Alerting System Status", "=" * 40]
    # Telegram
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if bot_token and chat_id:
        lines.append("  Telegram:  CONFIGURED")
    else:
        lines.append("  Telegram:  NOT CONFIGURED")

    # Redis pub/sub
    try:
        from moneymaker_console.clients import ClientFactory

        redis = ClientFactory.get_redis()
        if redis.ping():
            lines.append("  Redis:     CONNECTED (pub/sub available)")
        else:
            lines.append("  Redis:     NOT CONNECTED")
    except Exception:
        lines.append("  Redis:     NOT AVAILABLE")

    # Sentry
    sentry_dsn = os.environ.get("SENTRY_DSN", "")
    lines.append(f"  Sentry:    {'CONFIGURED' if sentry_dsn else 'NOT CONFIGURED'}")

    return "\n".join(lines)


def _alert_channels(*args: str) -> str:
    """List notification channels."""
    lines = ["Notification Channels", "=" * 40]
    channels = {
        "telegram": bool(os.environ.get("TELEGRAM_BOT_TOKEN")),
        "redis_pubsub": True,
        "console_log": True,
        "sentry": bool(os.environ.get("SENTRY_DSN")),
    }
    for name, active in channels.items():
        status = "ACTIVE" if active else "INACTIVE"
        lines.append(f"  {name:20s}: {status}")
    return "\n".join(lines)


def _alert_test(*args: str) -> str:
    """Send a test alert."""
    channel = args[0] if args else "all"
    lines = [f"Testing alert channel: {channel}", "=" * 40]

    if channel in ("all", "redis"):
        try:
            from moneymaker_console.clients import ClientFactory

            redis = ClientFactory.get_redis()
            redis.publish(
                "moneymaker:alerts", '{"level":"INFO","message":"Test alert from console"}'
            )
            lines.append("  Redis pub/sub: SENT")
        except Exception as exc:
            lines.append(f"  Redis pub/sub: FAILED ({exc})")

    if channel in ("all", "telegram"):
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
        if token and chat_id:
            try:
                import httpx

                resp = httpx.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": chat_id, "text": "MONEYMAKER Test Alert"},
                    timeout=10,
                )
                if resp.status_code == 200:
                    lines.append("  Telegram: SENT")
                else:
                    lines.append(f"  Telegram: HTTP {resp.status_code}")
            except Exception as exc:
                lines.append(f"  Telegram: FAILED ({exc})")
        else:
            lines.append("  Telegram: NOT CONFIGURED")

    return "\n".join(lines)


def _alert_rules(*args: str) -> str:
    """List alert rules."""
    return (
        "Alert Rules\n"
        "=" * 50 + "\n"
        "  1. Kill switch activation → CRITICAL → all channels\n"
        "  2. Max drawdown breach    → CRITICAL → all channels\n"
        "  3. Spiral protection      → WARNING  → telegram, redis\n"
        "  4. Service down           → WARNING  → telegram, redis\n"
        "  5. Trade execution        → INFO     → redis, console\n"
        "  6. Model drift detected   → WARNING  → telegram, redis\n"
        "\n  Custom rules managed via configuration."
    )


def _alert_add_rule(*args: str) -> str:
    """Add a new alert rule."""
    if len(args) < 2:
        return 'Usage: alert add-rule "CONDITION" SEVERITY [--channel CHANNEL]'
    return f"[info] Rule creation requires config file support. Condition: {args[0]}, Severity: {args[1]}"


def _alert_remove_rule(*args: str) -> str:
    """Remove an alert rule."""
    if not args:
        return "Usage: alert remove-rule RULE_ID"
    return f"[info] Rule removal requires config file support. Rule ID: {args[0]}"


def _alert_history(*args: str) -> str:
    """Display alert history."""
    days = 7
    for i, a in enumerate(args):
        if a == "--days" and i + 1 < len(args):
            days = int(args[i + 1])
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        rows = db.query(
            "SELECT created_at, level, message, channel "
            "FROM alert_history "
            f"WHERE created_at > NOW() - INTERVAL '{days} days' "
            "ORDER BY created_at DESC LIMIT 30"
        )
        if not rows:
            return f"No alerts in the last {days} days."
        lines = [f"Alert History (last {days} days)", "=" * 70]
        for r in rows:
            lines.append(f"  [{r[1]:8s}] {r[0]}  {r[2][:60]}  via={r[3]}")
        return "\n".join(lines)
    except Exception:
        return "[info] Alert history table not available. Check console logs."


def _alert_mute(*args: str) -> str:
    """Mute non-critical alerts."""
    minutes = int(args[0]) if args else 60
    try:
        from moneymaker_console.clients import ClientFactory
        import time

        redis = ClientFactory.get_redis()
        redis.set_json(
            "moneymaker:alert_mute",
            {
                "muted_until": time.time() + (minutes * 60),
                "muted_at": time.time(),
            },
        )
        return f"[success] Non-critical alerts muted for {minutes} minutes."
    except Exception as exc:
        return f"[error] {exc}"


def _alert_unmute(*args: str) -> str:
    """Unmute alerts."""
    try:
        from moneymaker_console.clients import ClientFactory

        redis = ClientFactory.get_redis()
        redis.delete("moneymaker:alert_mute")
        return "[success] Alerts unmuted."
    except Exception as exc:
        return f"[error] {exc}"


def _alert_telegram(*args: str) -> str:
    """Configure or test Telegram."""
    if not args:
        return _alert_test("telegram")
    # Parse --bot-token and --chat-id
    token = chat_id = None
    for i, a in enumerate(args):
        if a == "--bot-token" and i + 1 < len(args):
            token = args[i + 1]
        if a == "--chat-id" and i + 1 < len(args):
            chat_id = args[i + 1]
    if token and chat_id:
        from moneymaker_console.commands.config import _config_set

        _config_set("TELEGRAM_BOT_TOKEN", token)
        _config_set("TELEGRAM_CHAT_ID", chat_id)
        return "[success] Telegram configured. Run 'alert test telegram' to verify."
    return "Usage: alert telegram --bot-token TOKEN --chat-id ID"


def register(registry: CommandRegistry) -> None:
    registry.register("alert", "status", _alert_status, "Alerting system status")
    registry.register("alert", "channels", _alert_channels, "List notification channels")
    registry.register("alert", "test", _alert_test, "Send test alert")
    registry.register("alert", "rules", _alert_rules, "List alert rules")
    registry.register("alert", "add-rule", _alert_add_rule, "Add an alert rule")
    registry.register("alert", "remove-rule", _alert_remove_rule, "Remove an alert rule")
    registry.register("alert", "history", _alert_history, "Alert history")
    registry.register("alert", "mute", _alert_mute, "Mute non-critical alerts")
    registry.register("alert", "unmute", _alert_unmute, "Unmute alerts")
    registry.register("alert", "telegram", _alert_telegram, "Configure Telegram")
