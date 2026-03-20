# Copyright (c) 2024-2026 Renan Augusto Macena. All rights reserved.
# Licensed under Proprietary License. See LICENSE file in the project root.

"""JSON structured logging for the MONEYMAKER console.

Every command execution is logged as a JSON line to logs/console_YYYYMMDD.json.
"""

from __future__ import annotations

import datetime
import json
import re
from pathlib import Path

_LOG_DIR: Path | None = None

_SECRET_PATTERN = re.compile(
    r"(KEY|SECRET|PASSWORD|TOKEN|DSN|CREDENTIAL)",
    re.IGNORECASE,
)


def init_log_dir(log_dir: Path) -> None:
    """Set the log directory (called once at boot)."""
    global _LOG_DIR
    _LOG_DIR = log_dir
    _LOG_DIR.mkdir(parents=True, exist_ok=True)


def mask_secrets(text: str) -> str:
    """Mask values that look like secrets — keep only last 4 chars."""
    if len(text) <= 4:
        return "****"
    return "****" + text[-4:]


def mask_dict(d: dict) -> dict:
    """Return a copy of *d* with secret-looking values masked."""
    out: dict = {}
    for k, v in d.items():
        if isinstance(v, str) and _SECRET_PATTERN.search(k):
            out[k] = mask_secrets(v)
        else:
            out[k] = v
    return out


def log_event(event: str, **kwargs: object) -> None:
    """Append a structured JSON log entry."""
    if _LOG_DIR is None:
        return
    entry = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "event": event,
        **kwargs,
    }
    log_file = _LOG_DIR / f"console_{datetime.date.today():%Y%m%d}.json"
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except OSError:
        pass
