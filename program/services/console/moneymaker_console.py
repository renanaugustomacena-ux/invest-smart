#!/usr/bin/env python3
"""MONEYMAKER Trading Console v2.0 — Unified ecosystem command center.

Dual-mode: TUI interactive (default) or CLI with argparse (argv > 1).

Usage:
    TUI:   python moneymaker_console.py
    CLI:   python moneymaker_console.py brain status
           python moneymaker_console.py --json sys health
           python moneymaker_console.py --help
"""

from __future__ import annotations

import sys
from pathlib import Path

# Path stabilization — add src/ to sys.path for package imports
_SCRIPT_DIR = Path(__file__).resolve().parent
_SRC_DIR = _SCRIPT_DIR / "src"

if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

# Also add shared proto gen path for gRPC stubs
_PROTO_GEN = _SCRIPT_DIR.parent.parent / "shared" / "proto" / "gen"
if _PROTO_GEN.exists() and str(_PROTO_GEN) not in sys.path:
    sys.path.insert(0, str(_PROTO_GEN))


def main():
    from moneymaker_console.app import main as app_main

    app_main()


if __name__ == "__main__":
    main()
