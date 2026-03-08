"""Argparse builder for CLI mode — auto-generated from the CommandRegistry."""

from __future__ import annotations

import argparse

from moneymaker_console import __version__
from moneymaker_console.registry import CommandRegistry


def build_cli_parser(registry: CommandRegistry) -> argparse.ArgumentParser:
    """Build an argparse parser with nested subparsers for each category."""
    parser = argparse.ArgumentParser(
        prog="moneymaker",
        description=f"MONEYMAKER Trading Console v{__version__}",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--json", action="store_true", help="Output in JSON format",
    )
    parser.add_argument(
        "--yes", "-y", action="store_true",
        help="Skip confirmation prompts for dangerous commands",
    )

    subparsers = parser.add_subparsers(dest="category", help="Command category")

    for cat in registry.categories:
        cat_parser = subparsers.add_parser(cat, help=f"{cat} commands")
        cat_parser.add_argument(
            "subcmd", nargs="?", default="", help="Sub-command",
        )
        cat_parser.add_argument(
            "args", nargs="*", help="Additional arguments",
        )

    return parser
