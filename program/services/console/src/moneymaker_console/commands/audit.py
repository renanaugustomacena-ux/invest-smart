"""Security and compliance audit commands."""

from __future__ import annotations

import os
from pathlib import Path

from moneymaker_console.registry import CommandRegistry
from moneymaker_console.runner import _PROJECT_ROOT, run_tool


def _audit_security(*args: str) -> str:
    """Run a full security audit."""
    lines = ["Security Audit", "=" * 50]

    # .env permissions
    env_file = _PROJECT_ROOT / ".env"
    if env_file.exists():
        mode = env_file.stat().st_mode & 0o777
        if mode <= 0o600:
            lines.append("  [OK]      .env permissions: restricted")
        else:
            lines.append(f"  [WARNING] .env permissions: {oct(mode)} (should be 0o600)")
    else:
        lines.append("  [INFO]    No .env file found")

    # Check for secrets in git
    result = run_tool(
        [
            "git",
            "log",
            "--all",
            "-p",
            "--diff-filter=A",
            "-S",
            "PASSWORD",
            "--format=%h %s",
            "--",
            "*.py",
            "*.yml",
            "*.yaml",
        ],
        cwd=str(_PROJECT_ROOT),
    )
    if result.strip():
        lines.append("  [WARNING] Potential secrets found in git history")
    else:
        lines.append("  [OK]      No PASSWORD strings in tracked Python/YAML files")

    # TLS config
    tls_enabled = os.environ.get("MONEYMAKER_TLS_ENABLED", "false")
    lines.append(f"  [INFO]    TLS enabled: {tls_enabled}")

    # Redis auth
    redis_pass = os.environ.get("MONEYMAKER_REDIS_PASSWORD", "")
    if redis_pass:
        lines.append("  [OK]      Redis password configured")
    else:
        lines.append("  [WARNING] Redis password not set")

    # Docker privileged check
    compose_file = _PROJECT_ROOT / "infra" / "docker" / "docker-compose.yml"
    if compose_file.exists():
        content = compose_file.read_text()
        if "privileged: true" in content:
            lines.append("  [WARNING] Docker: privileged containers detected")
        else:
            lines.append("  [OK]      Docker: no privileged containers")

    return "\n".join(lines)


def _audit_secrets(*args: str) -> str:
    """Scan for committed secrets."""
    deep = "--deep" in args
    patterns = [
        "PRIVATE.KEY",
        "BEGIN RSA",
        "BEGIN EC",
        "sk_live_",
        "sk_test_",
        "ghp_",
        "gho_",
    ]
    lines = ["Secret Scan", "=" * 50]

    for pattern in patterns:
        cmd = ["git", "grep", "-l", pattern, "--", "*.py", "*.yml", "*.yaml", "*.json"]
        if deep:
            cmd = ["git", "log", "--all", "-p", "-S", pattern, "--format=%h"]
        result = run_tool(cmd, cwd=str(_PROJECT_ROOT))
        if result.strip():
            lines.append(f"  [FOUND]   Pattern '{pattern}' in: {result.strip()[:80]}")
        else:
            lines.append(f"  [CLEAN]   No '{pattern}' matches")

    return "\n".join(lines)


def _audit_tls(*args: str) -> str:
    """Verify TLS configuration."""
    lines = ["TLS Audit", "=" * 40]
    ca_cert = os.environ.get("MONEYMAKER_TLS_CA_CERT", "")
    if ca_cert and Path(ca_cert).exists():
        result = run_tool(
            ["openssl", "x509", "-in", ca_cert, "-noout", "-enddate"],
        )
        lines.append(f"  CA cert: {ca_cert}")
        lines.append(f"  Expiry:  {result.strip()}")
    else:
        lines.append("  [INFO] No TLS CA cert configured")
    return "\n".join(lines)


def _audit_dependencies(*args: str) -> str:
    """Scan dependencies for vulnerabilities."""
    lines = ["Dependency Audit", "=" * 50]

    # Python
    pip_audit = run_tool(["python3", "-m", "pip_audit"], cwd=str(_PROJECT_ROOT))
    if "No known vulnerabilities" in pip_audit:
        lines.append("  [OK]   Python: No known vulnerabilities")
    elif pip_audit.strip():
        lines.append(f"  [WARN] Python: {pip_audit.strip()[:200]}")
    else:
        lines.append("  [INFO] pip-audit not installed. Run: pip install pip-audit")

    # Go
    go_dir = _PROJECT_ROOT / "services" / "data-ingestion"
    if go_dir.exists():
        go_vuln = run_tool(["govulncheck", "./..."], cwd=str(go_dir))
        if go_vuln.strip():
            lines.append(f"  [INFO] Go: {go_vuln.strip()[:200]}")
        else:
            lines.append("  [INFO] govulncheck not available")

    return "\n".join(lines)


def _audit_permissions(*args: str) -> str:
    """Check file permissions on sensitive files."""
    lines = ["Permission Audit", "=" * 50]
    sensitive = [
        _PROJECT_ROOT / ".env",
        _PROJECT_ROOT / "infra" / "tls",
    ]
    for p in sensitive:
        if p.exists():
            mode = oct(p.stat().st_mode & 0o777)
            ok = "OK" if p.stat().st_mode & 0o077 == 0 else "TOO OPEN"
            lines.append(f"  [{ok:8s}] {p.name}: {mode}")
        else:
            lines.append(f"  [SKIP]    {p}: not found")
    return "\n".join(lines)


def _audit_docker(*args: str) -> str:
    """Audit Docker configuration."""
    compose_file = _PROJECT_ROOT / "infra" / "docker" / "docker-compose.yml"
    if not compose_file.exists():
        return "[error] docker-compose.yml not found."
    content = compose_file.read_text()
    lines = ["Docker Security Audit", "=" * 50]

    checks = {
        "privileged: true": ("No privileged containers", "Privileged container found"),
        "user: root": ("No root user", "Root user detected"),
        "network_mode: host": ("No host networking", "Host network mode found"),
    }
    for pattern, (ok_msg, warn_msg) in checks.items():
        if pattern in content:
            lines.append(f"  [WARNING] {warn_msg}")
        else:
            lines.append(f"  [OK]      {ok_msg}")

    return "\n".join(lines)


def _audit_hashchain(*args: str) -> str:
    """Verify audit hash chain integrity."""
    try:
        from moneymaker_console.clients import ClientFactory

        db = ClientFactory.get_postgres()
        row = db.query_one("SELECT count(*) FROM audit_log")
        count = row[0] if row else 0
        if count == 0:
            return "No audit log entries to verify."
        return (
            f"Hash Chain Verification\n{'=' * 40}\n"
            f"  Entries: {count}\n"
            f"  [info] Full hash chain verification requires sequential scan.\n"
            f"  Use moneymaker_common.audit_pg for programmatic verification."
        )
    except Exception as exc:
        return f"[error] {exc}"


def _audit_compliance(*args: str) -> str:
    """Generate compliance report."""
    lines = [
        "Compliance Report",
        "=" * 50,
        "",
        "  1. Audit Trail:      See 'audit hashchain'",
        "  2. Data Retention:   See 'maint retention'",
        "  3. Credentials:      See 'audit secrets'",
        "  4. TLS:              See 'audit tls'",
        "  5. Access Control:   See 'audit permissions'",
        "  6. Docker Security:  See 'audit docker'",
        "",
        "  Generate full report: audit report --format md",
    ]
    return "\n".join(lines)


def _audit_env(*args: str) -> str:
    """Audit the .env file."""
    from moneymaker_console.commands.config import _read_env_file, _is_secret, _ENV_FILE

    env = _read_env_file(_ENV_FILE)
    if not env:
        return "[warning] No .env file found."
    lines = ["Environment Audit", "=" * 50]
    issues = 0
    for key, val in sorted(env.items()):
        if _is_secret(key):
            if len(val) < 16:
                lines.append(f"  [WEAK]    {key}: password too short (<16 chars)")
                issues += 1
            elif val in ("password", "changeme", "admin", "default"):
                lines.append(f"  [DEFAULT] {key}: using default value")
                issues += 1
    if issues == 0:
        lines.append("  [OK] All secrets meet minimum requirements.")
    else:
        lines.append(f"\n  {issues} issue(s) found.")
    return "\n".join(lines)


def _audit_report(*args: str) -> str:
    """Generate comprehensive audit report."""
    fmt = "md"
    for i, a in enumerate(args):
        if a == "--format" and i + 1 < len(args):
            fmt = args[i + 1]

    sections = [
        ("Security", _audit_security),
        ("Secrets", _audit_secrets),
        ("TLS", _audit_tls),
        ("Permissions", _audit_permissions),
        ("Docker", _audit_docker),
        ("Environment", _audit_env),
    ]
    parts = ["# MONEYMAKER Security Audit Report\n"]
    for name, fn in sections:
        parts.append(f"\n## {name}\n```\n{fn()}\n```\n")

    report = "\n".join(parts)

    # Save
    from datetime import datetime

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = _PROJECT_ROOT.parent / "AUDIT_REPORTS"
    report_dir.mkdir(exist_ok=True)
    out = report_dir / f"audit_{ts}.{fmt}"
    out.write_text(report)
    return f"[success] Audit report saved to {out}\n\n{report[:500]}..."


def register(registry: CommandRegistry) -> None:
    registry.register("audit", "security", _audit_security, "Full security audit")
    registry.register("audit", "secrets", _audit_secrets, "Scan for committed secrets")
    registry.register("audit", "tls", _audit_tls, "Verify TLS configuration")
    registry.register("audit", "dependencies", _audit_dependencies, "Scan for vulnerabilities")
    registry.register("audit", "permissions", _audit_permissions, "Check file permissions")
    registry.register("audit", "docker", _audit_docker, "Audit Docker configuration")
    registry.register("audit", "hashchain", _audit_hashchain, "Verify audit hash chain")
    registry.register("audit", "compliance", _audit_compliance, "Compliance report")
    registry.register("audit", "env", _audit_env, "Audit .env file")
    registry.register("audit", "report", _audit_report, "Generate full audit report")
