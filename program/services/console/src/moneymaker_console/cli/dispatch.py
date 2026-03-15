"""CLI dispatch logic with JSON output mode and standardized exit codes."""

from __future__ import annotations

import json
import sys
import time

from moneymaker_console.cli.parser import build_cli_parser
from moneymaker_console.registry import CommandRegistry

# Exit codes
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_BAD_ARGS = 2
EXIT_SERVICE_UNAVAIL = 3
EXIT_CANCELLED = 4


def run_cli(registry: CommandRegistry, argv: list[str]) -> int:
    """Execute a single CLI command and return an exit code."""
    parser = build_cli_parser(registry)
    args = parser.parse_args(argv)

    if not args.category:
        parser.print_help()
        return EXIT_BAD_ARGS

    # Set up confirmation handler based on --yes flag
    auto_yes = getattr(args, "yes", False)
    if auto_yes:
        registry.set_confirmation_handler(lambda _label: True)
    else:

        def _cli_confirm(label: str) -> bool:
            try:
                answer = input(f"  \u26a0 {label} — Are you sure? [y/N]: ").strip().lower()
                return answer == "y"
            except (EOFError, KeyboardInterrupt):
                return False

        registry.set_confirmation_handler(_cli_confirm)

    use_json = getattr(args, "json", False)

    start = time.monotonic()
    result = registry.dispatch(args.category, args.subcmd, args.args or [])
    elapsed_ms = round((time.monotonic() - start) * 1000, 1)

    if use_json:
        payload = {
            "category": args.category,
            "subcmd": args.subcmd,
            "result": result,
            "exit_code": EXIT_OK if "[error]" not in result else EXIT_ERROR,
            "duration_ms": elapsed_ms,
        }
        print(json.dumps(payload, indent=2, default=str))
    else:
        if "[error]" in result:
            print(result, file=sys.stderr)
        else:
            print(result)

    if "[cancelled]" in result:
        return EXIT_CANCELLED
    if "[error]" in result:
        if "unavailable" in result.lower() or "not connected" in result.lower():
            return EXIT_SERVICE_UNAVAIL
        return EXIT_ERROR
    return EXIT_OK
