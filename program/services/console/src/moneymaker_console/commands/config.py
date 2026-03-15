"""Configuration management commands."""

from __future__ import annotations

import os
import re as _re
from pathlib import Path

from moneymaker_console.console_logging import mask_secrets
from moneymaker_console.registry import CommandRegistry
from moneymaker_console.runner import _PROJECT_ROOT

_ENV_FILE = _PROJECT_ROOT / ".env"
_ENV_EXAMPLE = _PROJECT_ROOT / ".env.example"

_SECRET_PATTERNS = {"KEY", "SECRET", "PASSWORD", "TOKEN", "DSN"}


def _is_secret(key: str) -> bool:
    upper = key.upper()
    return any(p in upper for p in _SECRET_PATTERNS)


def _read_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _config_view(*args: str) -> str:
    """Display configuration values with secrets masked."""
    env = _read_env_file(_ENV_FILE)
    if not env:
        return f"[warning] No .env file found at {_ENV_FILE}"

    category = args[0].lower() if args else None
    category_prefixes = {
        "db": ["MONEYMAKER_DB", "ADMIN_DB", "DATABASE"],
        "redis": ["MONEYMAKER_REDIS", "REDIS"],
        "brain": ["BRAIN_"],
        "mt5": ["MT5_"],
        "risk": ["MAX_", "RISK_"],
        "api": ["POLYGON_", "MONEYMAKER_BINANCE", "API_"],
        "tls": ["MONEYMAKER_TLS", "TLS_"],
        "zmq": ["ZMQ_", "MONEYMAKER_ZMQ"],
    }

    lines = ["Configuration", "=" * 60]
    for key, val in sorted(env.items()):
        if category and category in category_prefixes:
            if not any(key.upper().startswith(p) for p in category_prefixes[category]):
                continue
        display_val = mask_secrets(val) if _is_secret(key) else val
        lines.append(f"  {key:40s} = {display_val}")

    if len(lines) == 2:
        return f"No configuration found for category '{category}'."
    return "\n".join(lines)


def _config_validate(*args: str) -> str:
    """Validate configuration against .env.example."""
    if not _ENV_EXAMPLE.exists():
        return f"[warning] No .env.example found at {_ENV_EXAMPLE}"
    example = _read_env_file(_ENV_EXAMPLE)
    current = _read_env_file(_ENV_FILE)

    lines = ["Configuration Validation", "=" * 60]
    missing = 0
    for key in sorted(example):
        if key in current and current[key]:
            lines.append(f"  [OK]      {key}")
        elif key in current:
            lines.append(f"  [EMPTY]   {key}")
            missing += 1
        else:
            lines.append(f"  [MISSING] {key}")
            missing += 1

    if missing:
        lines.append(f"\n  {missing} variables missing or empty.")
    else:
        lines.append("\n  All required variables are set.")
    return "\n".join(lines)


# Keys that config set/risk are allowed to modify.
_ALLOWED_KEY_RE = _re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Characters forbidden in values (prevent newline / carriage-return injection
# that could corrupt the .env file or inject additional variables).
_FORBIDDEN_VALUE_CHARS = _re.compile(r"[\n\r\x00]")

# Known numeric keys — validated as int/float when set.
_NUMERIC_KEYS: set[str] = {
    "MONEYMAKER_DB_PORT",
    "MONEYMAKER_REDIS_PORT",
    "DASHBOARD_PORT",
    "EXTERNAL_DATA_PORT",
    "BRAIN_PORT",
    "MT5_GRPC_PORT",
    "MAX_LOT_SIZE",
    "RISK_PER_TRADE",
    "MAX_DRAWDOWN_PCT",
    "TICK_RETENTION_DAYS",
    "BAR_RETENTION_DAYS",
}


def _config_set(*args: str) -> str:
    """Set a configuration value in .env."""
    if len(args) < 2:
        return "Usage: config set KEY VALUE"
    key, value = args[0], " ".join(args[1:])

    # --- Input validation ---------------------------------------------------
    if not _ALLOWED_KEY_RE.match(key):
        return (
            f"[error] Invalid key '{key}'. "
            "Keys must contain only letters, digits, and underscores."
        )

    if _FORBIDDEN_VALUE_CHARS.search(value):
        return "[error] Value must not contain newline or null characters."

    if key in _NUMERIC_KEYS:
        try:
            float(value)
        except ValueError:
            return f"[error] '{key}' expects a numeric value, got '{value}'."
    # -----------------------------------------------------------------------

    if not _ENV_FILE.exists():
        return f"[error] No .env file at {_ENV_FILE}"

    content = _ENV_FILE.read_text()
    new_lines = []
    found = False
    for line in content.splitlines():
        if line.strip().startswith(f"{key}=") or line.strip().startswith(f"{key} ="):
            new_lines.append(f"{key}={value}")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"{key}={value}")

    _ENV_FILE.write_text("\n".join(new_lines) + "\n")
    display = mask_secrets(value) if _is_secret(key) else value
    return f"[success] Set {key} = {display}"


def _config_get(*args: str) -> str:
    """Get a single configuration value."""
    if not args:
        return "Usage: config get KEY"
    key = args[0]
    env = _read_env_file(_ENV_FILE)
    val = env.get(key) or os.environ.get(key)
    if val is None:
        return f"[warning] '{key}' not found in .env or environment."
    display = mask_secrets(val) if _is_secret(key) else val
    return f"  {key} = {display}"


def _config_diff(*args: str) -> str:
    """Compare .env against .env.example."""
    if not _ENV_EXAMPLE.exists():
        return "[warning] No .env.example found."
    example = _read_env_file(_ENV_EXAMPLE)
    current = _read_env_file(_ENV_FILE)

    lines = ["Configuration Diff", "=" * 60]
    missing = set(example) - set(current)
    extra = set(current) - set(example)

    if missing:
        lines.append("\n  Missing (in .env.example but not .env):")
        for k in sorted(missing):
            lines.append(f"    - {k}")
    if extra:
        lines.append("\n  Extra (in .env but not .env.example):")
        for k in sorted(extra):
            lines.append(f"    + {k}")
    if not missing and not extra:
        lines.append("  .env and .env.example have the same keys.")
    return "\n".join(lines)


def _config_broker(*args: str) -> str:
    """Set broker API key."""
    if not args:
        return "Usage: config broker API_KEY"
    return _config_set("POLYGON_API_KEY", args[0])


def _config_risk(*args: str) -> str:
    """Set a risk configuration parameter."""
    if len(args) < 2:
        return "Usage: config risk KEY VALUE  (e.g. config risk MAX_LOT_SIZE 0.5)"
    return _config_set(args[0], args[1])


def _config_reload(*args: str) -> str:
    """Reload configuration from .env."""
    try:
        from dotenv import load_dotenv

        load_dotenv(_ENV_FILE, override=True)
        return "[success] Configuration reloaded from .env"
    except ImportError:
        return "[warning] python-dotenv not installed. Restart services to apply changes."


def _config_export(*args: str) -> str:
    """Export configuration as JSON or YAML."""
    import json

    env = _read_env_file(_ENV_FILE)
    masked = {}
    for k, v in sorted(env.items()):
        masked[k] = mask_secrets(v) if _is_secret(k) else v
    fmt = args[0] if args else "json"
    if fmt == "json":
        return json.dumps(masked, indent=2)
    # Simple YAML-like
    lines = []
    for k, v in masked.items():
        lines.append(f"{k}: {v}")
    return "\n".join(lines)


def _config_import(*args: str) -> str:
    """Import configuration from a file."""
    if not args:
        return "Usage: config import FILE"
    return f"[info] Import from '{args[0]}' requires manual review. Use 'config set' for individual keys."


def _config_template(*args: str) -> str:
    """Generate a clean .env from .env.example."""
    if not _ENV_EXAMPLE.exists():
        return "[error] No .env.example found."
    env_type = args[0] if args else "development"
    return (
        f"[info] To generate a {env_type} .env:\n"
        f"  cp {_ENV_EXAMPLE} {_ENV_FILE}\n"
        f"  Then edit with 'config set KEY VALUE'"
    )


def _config_encrypt(*args: str) -> str:
    """Encrypt the .env file."""
    return (
        "[info] Encryption requires a master passphrase in the system keyring. Not yet implemented."
    )


def _config_decrypt(*args: str) -> str:
    """Decrypt .env.enc."""
    return (
        "[info] Decryption requires a master passphrase in the system keyring. Not yet implemented."
    )


def register(registry: CommandRegistry) -> None:
    registry.register("config", "view", _config_view, "Display configuration (secrets masked)")
    registry.register(
        "config", "validate", _config_validate, "Validate config against .env.example"
    )
    registry.register("config", "set", _config_set, "Set a configuration value")
    registry.register("config", "get", _config_get, "Get a configuration value")
    registry.register("config", "diff", _config_diff, "Compare .env with .env.example")
    registry.register("config", "broker", _config_broker, "Set broker API key")
    registry.register("config", "risk", _config_risk, "Set a risk parameter")
    registry.register("config", "reload", _config_reload, "Reload .env configuration")
    registry.register("config", "export", _config_export, "Export config as JSON/YAML")
    registry.register("config", "import", _config_import, "Import config from file")
    registry.register("config", "template", _config_template, "Generate .env from template")
    registry.register("config", "encrypt", _config_encrypt, "Encrypt .env file")
    registry.register("config", "decrypt", _config_decrypt, "Decrypt .env.enc file")
