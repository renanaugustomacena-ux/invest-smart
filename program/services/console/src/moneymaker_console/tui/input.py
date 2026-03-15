"""Platform-specific non-blocking keyboard input for the TUI."""

from __future__ import annotations

import platform
import sys


class InputHandler:
    """Context manager for non-blocking character reads.

    Unix: uses termios/tty/select to set cbreak mode.
    Windows: uses msvcrt.kbhit/getwch.
    """

    def __init__(self) -> None:
        self._is_windows = platform.system() == "Windows"
        self._old_settings = None

    def __enter__(self) -> InputHandler:
        if not self._is_windows:
            import termios
            import tty

            self._old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
        return self

    def __exit__(self, *exc) -> None:
        if not self._is_windows and self._old_settings is not None:
            import termios

            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._old_settings)

    def get_char(self) -> str | None:
        """Return a single character if available, else None (non-blocking)."""
        if self._is_windows:
            return self._get_char_windows()
        return self._get_char_unix()

    @staticmethod
    def _get_char_windows() -> str | None:
        import msvcrt

        if msvcrt.kbhit():
            return msvcrt.getwch()
        return None

    @staticmethod
    def _get_char_unix() -> str | None:
        import select

        if select.select([sys.stdin], [], [], 0.0)[0]:
            return sys.stdin.read(1)
        return None
