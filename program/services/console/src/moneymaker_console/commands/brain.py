"""Algo Engine control commands — lifecycle, status, regime, maturity, coaching."""

from __future__ import annotations

from moneymaker_console.clients import ClientFactory
from moneymaker_console.registry import CommandRegistry


def _unavail() -> str:
    return "[warning] Algo Engine service not available. Start with: svc up algo-engine"


def _brain_start(*args: str) -> str:
    """Start the Algo Engine event loop."""
    mode = "rule-based"
    for i, a in enumerate(args):
        if a == "--mode" and i + 1 < len(args):
            mode = args[i + 1]
    docker = ClientFactory.get_docker()
    result = docker.restart("algo-engine")
    return f"[success] Algo Engine starting in '{mode}' mode.\n{result}"


def _brain_stop(*args: str) -> str:
    """Graceful stop of the Algo Engine."""
    force = "--force" in args
    docker = ClientFactory.get_docker()
    if force:
        from moneymaker_console.runner import run_tool, _PROJECT_ROOT, _DOCKER_COMPOSE
        return run_tool(
            ["docker", "compose", "-f", str(_DOCKER_COMPOSE), "kill", "algo-engine"],
            cwd=_PROJECT_ROOT,
        )
    return docker.restart("algo-engine")


def _brain_pause(*args: str) -> str:
    """Pause signal generation."""
    redis = ClientFactory.get_redis()
    if redis.set("moneymaker:brain:paused", "true"):
        return "[success] Algo Engine signal generation PAUSED."
    return "[warning] Could not pause — Redis not available."


def _brain_resume(*args: str) -> str:
    """Resume signal generation."""
    redis = ClientFactory.get_redis()
    if redis.delete("moneymaker:brain:paused"):
        return "[success] Algo Engine signal generation RESUMED."
    return "[warning] Could not resume — Redis not available."


def _brain_status(*args: str) -> str:
    """Comprehensive Algo Engine status."""
    brain = ClientFactory.get_brain()
    health = brain.get_health()

    if health:
        lines = [
            "Algo Engine Status",
            "=" * 40,
            f"  State:       {health.get('status', 'UNKNOWN')}",
            f"  Uptime:      {health.get('uptime_seconds', 'N/A')}s",
        ]
        details = health.get("details", {})
        for k, v in details.items():
            lines.append(f"  {k:<12}  {v}")
        return "\n".join(lines)

    # Fallback: query database
    db = ClientFactory.get_postgres()
    if not db.ping():
        return _unavail()

    lines = ["Algo Engine Status (from DB — REST unreachable)", "=" * 40]

    # Latest model from registry
    row = db.query_one(
        "SELECT model_name, model_version, is_active, created_at "
        "FROM model_registry ORDER BY created_at DESC LIMIT 1"
    )
    if row:
        lines.append(f"  Model:       {row[0]} v{row[1]}")
        lines.append(f"  Active:      {row[2]}")
        lines.append(f"  Created:     {row[3]}")
    else:
        lines.append("  Model:       No models registered")

    # Latest signal
    row = db.query_one(
        "SELECT symbol, direction, confidence, created_at "
        "FROM trading_signals ORDER BY created_at DESC LIMIT 1"
    )
    if row:
        lines.append(f"\n  Last Signal: {row[0]} {row[1]} (conf={row[2]:.2f})")
        lines.append(f"  Signal Time: {row[3]}")

    return "\n".join(lines)


def _brain_regime(*args: str) -> str:
    """Display current market regime classification."""
    redis = ClientFactory.get_redis()
    regime = redis.get_json("moneymaker:regime_cache")
    if regime:
        lines = [
            "Market Regime",
            "=" * 40,
            f"  Regime:      {regime.get('regime', 'UNKNOWN')}",
            f"  Confidence:  {regime.get('confidence', 'N/A')}",
        ]
        votes = regime.get("votes", {})
        for classifier, vote in votes.items():
            lines.append(f"  {classifier:<12}  {vote}")
        return "\n".join(lines)

    # DB fallback
    db = ClientFactory.get_postgres()
    row = db.query_one(
        "SELECT regime, confidence, classified_at "
        "FROM regime_classifications ORDER BY classified_at DESC LIMIT 1"
    )
    if row:
        return (
            f"Market Regime (from DB)\n"
            f"  Regime:      {row[0]}\n"
            f"  Confidence:  {row[1]}\n"
            f"  Classified:  {row[2]}"
        )
    return "[info] No regime data available."


def _brain_maturity(*args: str) -> str:
    """Display maturity gating status."""
    db = ClientFactory.get_postgres()
    row = db.query_one(
        "SELECT maturity_state, trading_mode, sizing_multiplier, updated_at "
        "FROM maturity_state ORDER BY updated_at DESC LIMIT 1"
    )
    if row:
        return (
            f"Maturity Gating\n"
            f"{'=' * 40}\n"
            f"  State:       {row[0]}\n"
            f"  Mode:        {row[1]}\n"
            f"  Multiplier:  {row[2]}x\n"
            f"  Updated:     {row[3]}"
        )
    return "[info] No maturity data available."


def _brain_drift(*args: str) -> str:
    """Display drift monitor Z-scores."""
    db = ClientFactory.get_postgres()
    rows = db.query(
        "SELECT feature_name, z_score, is_drifted, checked_at "
        "FROM feature_drift_logs ORDER BY checked_at DESC LIMIT 10"
    )
    if not rows:
        return "[info] No drift data available."

    lines = ["Drift Monitor", "=" * 40]
    for name, z, drifted, ts in rows:
        flag = "[!!]" if drifted else "[OK]"
        lines.append(f"  {flag} {name:<25} z={z:+.3f}  {ts}")
    return "\n".join(lines)


def _brain_spiral(*args: str) -> str:
    """Display spiral protection status."""
    redis = ClientFactory.get_redis()
    data = redis.get_json("moneymaker:spiral_protection")
    if data:
        return (
            f"Spiral Protection\n"
            f"{'=' * 40}\n"
            f"  Active:          {data.get('active', False)}\n"
            f"  Consec Losses:   {data.get('consecutive_losses', 0)}\n"
            f"  Cooldown Timer:  {data.get('cooldown_remaining', 0)}s\n"
            f"  Lot Reduction:   {data.get('lot_reduction_factor', 1.0)}x"
        )
    return (
        "Spiral Protection\n"
        f"{'=' * 40}\n"
        "  Status:  INACTIVE (no data in Redis)"
    )


def _brain_confidence(*args: str) -> str:
    """Show signal confidence distribution."""
    symbol = args[0] if args else None
    db = ClientFactory.get_postgres()

    where = "WHERE created_at > NOW() - INTERVAL '7 days'"
    params: tuple = ()
    if symbol:
        where += " AND symbol = %s"
        params = (symbol.upper(),)

    rows = db.query(
        f"SELECT width_bucket(confidence, 0, 1, 10) AS bucket, count(*) "
        f"FROM trading_signals {where} GROUP BY bucket ORDER BY bucket",
        params,
    )
    if not rows:
        return "[info] No signal data in last 7 days."

    lines = ["Confidence Distribution (last 7 days)", "=" * 40]
    for bucket, count in rows:
        lo = (bucket - 1) * 0.1
        hi = bucket * 0.1
        bar = "#" * min(count, 50)
        lines.append(f"  {lo:.1f}-{hi:.1f}  {count:4d}  {bar}")
    return "\n".join(lines)


def _brain_features(*args: str) -> str:
    """Display current feature vector for a symbol."""
    if not args:
        return "[error] Usage: brain features <SYMBOL>"
    symbol = args[0].upper()
    db = ClientFactory.get_postgres()

    rows = db.query(
        "SELECT feature_name, feature_value, computed_at "
        "FROM feature_vectors "
        "WHERE symbol = %s ORDER BY computed_at DESC LIMIT 60",
        (symbol,),
    )
    if not rows:
        return f"[info] No feature data for {symbol}."

    lines = [f"Feature Vector: {symbol}", "=" * 40]
    for name, value, ts in rows:
        lines.append(f"  {name:<25} {value}")
    return "\n".join(lines)


def _brain_coaching(*args: str) -> str:
    """Display coaching system status."""
    db = ClientFactory.get_postgres()
    rows = db.query(
        "SELECT component, status, last_run, insight "
        "FROM coaching_status ORDER BY last_run DESC LIMIT 5"
    )
    if not rows:
        return "[info] No coaching data available."

    lines = ["Coaching System", "=" * 40]
    for component, status, last_run, insight in rows:
        lines.append(f"  {component:<20} {status:<10} {last_run}")
        if insight:
            lines.append(f"    -> {insight[:80]}")
    return "\n".join(lines)


def _brain_coaching_history(*args: str) -> str:
    """Display historical coaching corrections."""
    days = 7
    for i, a in enumerate(args):
        if a == "--days" and i + 1 < len(args):
            try:
                days = int(args[i + 1])
            except ValueError:
                pass

    db = ClientFactory.get_postgres()
    rows = db.query(
        "SELECT correction_type, message, created_at "
        "FROM coaching_corrections "
        "WHERE created_at > NOW() - INTERVAL '%s days' "
        "ORDER BY created_at DESC LIMIT 20",
        (days,),
    )
    if not rows:
        return f"[info] No coaching corrections in last {days} days."

    lines = [f"Coaching History (last {days} days)", "=" * 40]
    for ctype, msg, ts in rows:
        lines.append(f"  {ts}  [{ctype}] {msg[:70]}")
    return "\n".join(lines)


def _brain_skill_progress(*args: str) -> str:
    """Display RAP Coach skill progression."""
    db = ClientFactory.get_postgres()
    rows = db.query(
        "SELECT skill_name, level, score, updated_at "
        "FROM skill_progress ORDER BY updated_at DESC LIMIT 10"
    )
    if not rows:
        return "[info] No skill progression data."

    lines = ["Trader Skill Progress (RAP Coach)", "=" * 40]
    for skill, level, score, ts in rows:
        lines.append(f"  {skill:<25} Level {level}  Score: {score:.2f}")
    return "\n".join(lines)


def _brain_sentry(*args: str) -> str:
    """Display Sentry error tracking status."""
    import os
    dsn = os.environ.get("SENTRY_DSN", "")
    if not dsn:
        return "[info] Sentry DSN not configured."

    lines = [
        "Sentry Integration",
        "=" * 40,
        f"  DSN:     ****{dsn[-20:]}",
        "  Status:  Configured (check Sentry dashboard for details)",
    ]
    return "\n".join(lines)


def _brain_model_info(*args: str) -> str:
    """Display current model architecture details."""
    db = ClientFactory.get_postgres()
    row = db.query_one(
        "SELECT model_name, model_version, model_type, is_active, "
        "training_samples, validation_accuracy, checkpoint_path, created_at "
        "FROM model_registry WHERE is_active = true "
        "ORDER BY created_at DESC LIMIT 1"
    )
    if not row:
        return "[info] No active model in registry."

    return (
        f"Active Model\n"
        f"{'=' * 40}\n"
        f"  Name:       {row[0]}\n"
        f"  Version:    {row[1]}\n"
        f"  Type:       {row[2]}\n"
        f"  Samples:    {row[4]}\n"
        f"  Val Acc:    {row[5]}\n"
        f"  Checkpoint: {row[6]}\n"
        f"  Created:    {row[7]}"
    )


def _brain_checkpoint(*args: str) -> str:
    """Force an immediate state checkpoint save."""
    redis = ClientFactory.get_redis()
    if redis.publish("moneymaker:brain:commands", "checkpoint"):
        return "[success] Checkpoint command sent to Algo Engine."
    return "[warning] Could not send checkpoint command — Redis not available."


def _brain_eval(*args: str) -> str:
    """Trigger evaluation on test dataset."""
    redis = ClientFactory.get_redis()
    if redis.publish("moneymaker:brain:commands", "eval"):
        return "[success] Evaluation command sent to Algo Engine."
    return "[warning] Could not send eval command — Redis not available."


def register(registry: CommandRegistry) -> None:
    registry.register("brain", "start", _brain_start,
                       "Start Algo Engine [--mode MODE]")
    registry.register("brain", "stop", _brain_stop,
                       "Graceful stop [--force]")
    registry.register("brain", "pause", _brain_pause,
                       "Pause signal generation")
    registry.register("brain", "resume", _brain_resume,
                       "Resume signal generation")
    registry.register("brain", "status", _brain_status,
                       "Comprehensive status")
    registry.register("brain", "eval", _brain_eval,
                       "Trigger evaluation cycle")
    registry.register("brain", "checkpoint", _brain_checkpoint,
                       "Force checkpoint save")
    registry.register("brain", "model-info", _brain_model_info,
                       "Model architecture details")
    registry.register("brain", "regime", _brain_regime,
                       "Market regime classification")
    registry.register("brain", "drift", _brain_drift,
                       "Drift monitor Z-scores")
    registry.register("brain", "maturity", _brain_maturity,
                       "Maturity gating status")
    registry.register("brain", "spiral", _brain_spiral,
                       "Spiral protection status")
    registry.register("brain", "confidence", _brain_confidence,
                       "Confidence distribution [SYMBOL]")
    registry.register("brain", "features", _brain_features,
                       "Feature vector for SYMBOL")
    registry.register("brain", "coaching", _brain_coaching,
                       "Coaching system status")
    registry.register("brain", "coaching-history", _brain_coaching_history,
                       "Coaching correction history [--days N]")
    registry.register("brain", "skill-progress", _brain_skill_progress,
                       "RAP Coach skill progression")
    registry.register("brain", "sentry", _brain_sentry,
                       "Sentry error tracking status")
