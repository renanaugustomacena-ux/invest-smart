"""Tests for the app module — boot sequence and entry point."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from moneymaker_console.app import _boot, _load_dotenv


class TestLoadDotenv:
    def test_no_dotenv_installed(self):
        with patch.dict("sys.modules", {"dotenv": None}):
            # Should not raise even if dotenv is not installed
            _load_dotenv()

    @patch("moneymaker_console.app._CONSOLE_DIR", Path("/tmp/fake"))
    def test_dotenv_file_not_exists(self):
        # Should not raise if file doesn't exist
        _load_dotenv()


class TestBoot:
    @patch("moneymaker_console.app.discover_and_register")
    @patch("moneymaker_console.app.init_log_dir")
    @patch("moneymaker_console.app._load_dotenv")
    def test_boot_returns_registry(self, mock_dotenv, mock_logdir, mock_discover):
        registry = _boot()
        assert registry is not None
        mock_logdir.assert_called_once()
        mock_dotenv.assert_called_once()
        mock_discover.assert_called_once()

    @patch("moneymaker_console.app.discover_and_register")
    @patch("moneymaker_console.app.init_log_dir")
    @patch("moneymaker_console.app._load_dotenv")
    def test_boot_calls_log_event(self, mock_dotenv, mock_logdir, mock_discover):
        with patch("moneymaker_console.app.log_event") as mock_log:
            _boot()
            assert mock_log.call_count >= 2  # boot_start and boot_complete


class TestMain:
    @patch("moneymaker_console.app._boot")
    def test_cli_mode(self, mock_boot):
        registry = MagicMock()
        mock_boot.return_value = registry

        with patch("moneymaker_console.cli.dispatch.run_cli") as mock_run_cli, \
             patch("moneymaker_console.app.sys") as mock_sys:
            mock_sys.argv = ["moneymaker", "svc", "status"]
            mock_sys.exit = MagicMock()
            mock_run_cli.return_value = 0
            from moneymaker_console.app import main
            main()
            mock_run_cli.assert_called_once()

    @patch("moneymaker_console.app._boot")
    @patch("moneymaker_console.app.HAS_RICH", False)
    def test_cli_interactive_fallback(self, mock_boot):
        registry = MagicMock()
        mock_boot.return_value = registry

        with patch("moneymaker_console.app._run_cli_interactive") as mock_interactive, \
             patch("moneymaker_console.app.sys") as mock_sys:
            mock_sys.argv = ["moneymaker"]
            from moneymaker_console.app import main
            main()
            mock_interactive.assert_called_once_with(registry)
